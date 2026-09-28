"""Synthetic fixtures are confined to tests; production uses provider records."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import requests

from pitwall.io.atomic import atomic_write_json
from pitwall.data.jolpica import BASE, digest, DataUnavailable, Jolpica, classification, instant, race_event, races, select_event
from pitwall.models.backtest import run_backtest
from pitwall.models.ledger import capture, compare, evaluated_dataset, read_records
from pitwall.models.ranking import evaluate, make_prediction, predict, validate_prediction
from pitwall.publish import publish


def fixture_race(round_no=1, date="2030-03-10", time="14:00:00Z"):
    return {"season": "2030", "round": str(round_no), "raceName": "Fixture GP",
            "Circuit": {"circuitId": "fixture", "circuitName": "Fixture circuit"}, "date": date, "time": time}


def fixture_rows():
    return [{"driver_id": str(i), "name": f"Fixture driver {i}", "team": "Fixture team", "position": i} for i in range(1, 13)]


class ProductionRankingTests(unittest.TestCase):
    def setUp(self):
        self.event = race_event(fixture_race())
        self.now = instant("2030-03-10T12:00:00Z")
        self.sources = [{"url": "https://api.jolpi.ca/ergast/f1/2030/1/qualifying/", "retrieved_at": self.now.isoformat(), "status": "AVAILABLE"}]

    def test_old_italian_like_event_never_current(self):
        past = race_event(fixture_race(date="2030-03-01"))
        self.assertEqual(select_event([past, self.event], set(), self.now)["event"]["id"], self.event["id"])

    def test_start_boundary_is_not_live_or_upcoming(self):
        current = select_event([self.event], set(), instant(self.event["start_at"]))
        self.assertEqual(current["state"], "UPDATING")

    def test_completed_result_moves_to_next_event(self):
        next_event = race_event(fixture_race(2, "2030-03-17"))
        self.assertEqual(select_event([self.event, next_event], {self.event["id"]}, self.now)["event"], next_event)

    def test_timezone_boundary_and_missing_timezone(self):
        self.assertEqual(instant("2030-03-10T19:30:00+05:30"), instant(self.event["start_at"]))
        with self.assertRaises(DataUnavailable):
            instant("2030-03-10T14:00:00")

    def test_unknown_race_time_blocks_current_selection(self):
        event = race_event(fixture_race(time=None))
        self.assertIsNone(event["start_at"])
        self.assertEqual(select_event([event], set(), self.now)["state"], "UNAVAILABLE")

    def test_calendar_supports_sprint_and_no_fabricated_practice(self):
        raw = fixture_race()
        raw["Sprint"] = {"date": "2030-03-09", "time": "12:00:00Z"}
        self.assertEqual([s["name"] for s in race_event(raw)["sessions"]], ["Sprint", "Race"])

    def test_invalid_provider_schema_and_season_fail(self):
        with self.assertRaises(DataUnavailable):
            races({"races": []})
        with self.assertRaises(DataUnavailable):
            races({"MRData": {"RaceTable": {"Races": [fixture_race()]}}}, 2029)

    def test_duplicate_and_partial_classification_rejected(self):
        for rows in [[], [{"position": "1"}]]:
            with self.assertRaises(DataUnavailable):
                classification({"Results": rows}, "Results")
        rows = fixture_rows()
        rows[0]["driver_id"] = rows[1]["driver_id"]
        with self.assertRaises(DataUnavailable):
            predict(rows)

    def test_determinism_and_top10_derivation(self):
        p = make_prediction(self.event, fixture_rows(), self.sources, self.now)
        self.assertEqual(p["full_grid"], make_prediction(self.event, list(reversed(fixture_rows())), self.sources, self.now)["full_grid"])
        self.assertEqual(p["top10"], p["full_grid"][:10])
        self.assertNotIn("probability", p["full_grid"][0])

    def test_capture_rejects_race_started_and_future_cutoff(self):
        with self.assertRaises(DataUnavailable):
            make_prediction(self.event, fixture_rows(), self.sources, instant(self.event["start_at"]))
        with self.assertRaises(DataUnavailable):
            make_prediction(self.event, fixture_rows(), [{**self.sources[0], "retrieved_at": (self.now+timedelta(hours=1)).isoformat()}], self.now)

    def test_append_only_history_and_model_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = make_prediction(self.event, fixture_rows(), self.sources, self.now)
            directory = Path(tmp)
            capture(directory, p)
            capture(directory, p)
            changed = {**p, "model_version": "another-model"}
            with self.assertRaises(DataUnavailable):
                capture(directory, changed)
            self.assertEqual(read_records(directory), [p])

    def test_post_race_evaluation_and_result_revision_preserve_prediction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = make_prediction(self.event, fixture_rows(), self.sources, self.now)
            capture(root / "predictions", p)
            now = self.now+timedelta(days=1)
            first = compare(root / "evaluations", p, self.event, fixture_rows(), self.sources[0], now)
            self.assertEqual(first["metrics"]["mae"], 0)
            self.assertEqual(compare(root / "evaluations", p, self.event, fixture_rows(), self.sources[0], now+timedelta(days=1)), first)
            revised = fixture_rows()
            revised[0]["position"], revised[1]["position"] = 2, 1
            compare(root / "evaluations", p, self.event, revised, self.sources[0], now)
            self.assertEqual(len(read_records(root / "evaluations")), 2)
            self.assertEqual(read_records(root / "predictions"), [p])

    def test_substitution_or_wrong_event_cannot_be_evaluated(self):
        p = make_prediction(self.event, fixture_rows(), self.sources, self.now)
        actual = fixture_rows()
        actual[0]["driver_id"] = "reserve"
        with self.assertRaises(DataUnavailable):
            evaluate(p["full_grid"], actual)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(DataUnavailable):
                compare(Path(tmp), p, {**self.event, "id": "wrong"}, fixture_rows(), self.sources[0], self.now+timedelta(days=1))

    def test_target_and_future_results_cannot_change_historical_prediction(self):
        dataset = []
        for year in [2018, 2023, 2024, 2025]:
            event = {**self.event, "id": f"{year}:1:race", "season": year, "start_at": f"{year}-03-10T14:00:00+00:00"}
            dataset.append({"event": event, "qualifying": fixture_rows(), "results": fixture_rows(), "sources": []})
        before = run_backtest(dataset)
        altered = deepcopy(dataset)
        altered[-1]["results"] = [{**r, "position": 13-r["position"]} for r in fixture_rows()]
        after = run_backtest(altered)
        self.assertEqual(before["races"][-1]["input_hash"], after["races"][-1]["input_hash"])
        self.assertEqual(before["races"][:-1], after["races"][:-1])
        self.assertFalse(after["promotion"]["promoted"])

    def test_backtest_rejects_duplicate_race_groups(self):
        race = {"event": self.event, "qualifying": fixture_rows(), "results": fixture_rows(), "sources": []}
        with self.assertRaisesRegex(DataUnavailable, "Duplicate race groups"):
            run_backtest([race, deepcopy(race)])

    def test_provider_failure_and_expired_cache_never_return_stale_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = Jolpica(Path(tmp))
            url = f"{BASE}/2030/races/?limit=100"
            valid = {"MRData": {"total": "1", "limit": "100", "offset": "0", "RaceTable": {"Races": [fixture_race()]}}}
            stamp = datetime.now(timezone.utc)
            for data, retrieved in [(valid, stamp-timedelta(hours=1)), ({"MRData": {}}, stamp)]:
                atomic_write_json(Path(tmp)/f"{digest(url)}.json", {"url": url, "retrieved_at": retrieved.isoformat(), "data": data})
                with patch("pitwall.data.jolpica.requests.get", side_effect=requests.Timeout):
                    with self.assertRaises(DataUnavailable):
                        client.fetch("2030/races")
                self.assertEqual(client.sources[-1]["status"], "UNAVAILABLE")

    def test_corrupted_ledger_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/"bad.json").write_text("{broken")
            with self.assertRaises(DataUnavailable):
                read_records(Path(tmp))

    def test_publish_capture_then_actual_evaluation_integration(self):
        raw = fixture_race()
        qualifying = [{"Driver": {"driverId": row["driver_id"], "givenName": "Fixture", "familyName": row["driver_id"]},
                       "Constructor": {"name": "Fixture team"}, "position": str(row["position"])} for row in fixture_rows()]
        raw["QualifyingResults"] = qualifying
        result = {**raw, "Results": [{**r, "status": "Finished", "points": "0"} for r in qualifying]}

        class FixtureProvider:
            def __init__(self, stamp, finished=False):
                self.sources = []
                self.stamp, self.finished = stamp, finished

            def fetch(self, endpoint):
                self.sources.append({"url": f"https://api.jolpi.ca/ergast/f1/{endpoint}/", "retrieved_at": self.stamp.isoformat(), "status": "AVAILABLE"})
                rows = [result] if endpoint.endswith("/results") and self.finished else [] if endpoint.endswith("/results") else [raw]
                return {"MRData": {"RaceTable": {"Races": rows}}}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = publish(root, provider=FixtureProvider(self.now), now=self.now)
            self.assertEqual(len(first["predictions"]), 1)
            saved = read_records(root / "data_cache/ledger/predictions")
            future = self.now+timedelta(hours=4)
            second = publish(root, provider=FixtureProvider(future, finished=True), now=future)
            self.assertEqual(len(second["evaluations"]), 1)
            self.assertIsNone(second["prediction"])
            self.assertEqual(read_records(root / "data_cache/ledger/predictions"), saved)
            dataset = evaluated_dataset(saved, second["evaluations"])
            self.assertEqual(len(dataset), 1)
            self.assertEqual(dataset[0]["metrics"]["mae"], 0)
            self.assertEqual(dataset[0]["qualifying"], saved[0]["inputs"]["qualifying"])

    def test_results_outage_does_not_block_legitimate_capture(self):
        raw = fixture_race()
        raw["QualifyingResults"] = [{"Driver": {"driverId": r["driver_id"], "givenName": "Fixture", "familyName": r["driver_id"]},
                                    "Constructor": {"name": "Fixture team"}, "position": str(r["position"])} for r in fixture_rows()]
        stamp = self.now.isoformat()

        class Provider:
            sources = []

            def fetch(self, endpoint):
                if endpoint.endswith("results"):
                    self.sources.append({"url": endpoint, "retrieved_at": None, "status": "UNAVAILABLE"})
                    raise DataUnavailable("Results temporarily unavailable")
                self.sources.append({"url": endpoint, "retrieved_at": stamp, "status": "AVAILABLE"})
                return {"MRData": {"RaceTable": {"Races": [raw]}}}

        with tempfile.TemporaryDirectory() as tmp:
            result = publish(Path(tmp), provider=Provider(), now=self.now)
            self.assertEqual(len(result["predictions"]), 1)
            self.assertTrue(any("Latest results unavailable" in w for w in result["warnings"]))
            self.assertEqual(result["generated_at"], stamp)

    def test_publisher_provider_failure_produces_unavailable_contract(self):
        class FailedProvider:
            sources = []

            def fetch(self, _endpoint):
                raise DataUnavailable("Provider timed out")

        with tempfile.TemporaryDirectory() as tmp:
            result = publish(Path(tmp), provider=FailedProvider(), now=self.now)
            self.assertEqual(result["current"]["state"], "UNAVAILABLE")
            self.assertIsNone(result["prediction"])
            self.assertIn("Provider timed out", result["warnings"])

    def test_legacy_training_cannot_replace_production(self):
        from f1_briefing import train_ml_model
        with self.assertRaisesRegex(RuntimeError, "unvalidated"):
            train_ml_model(force=True)

    def test_published_contract_has_no_current_legacy_prediction(self):
        product = json.loads(Path("data_cache/product.json").read_text())
        self.assertEqual(product["schema_version"], 3)
        for row in product["legacy_archive"]:
            self.assertEqual(row["status"], "UNVERIFIED_LEGACY")
            self.assertFalse(any("probability" in k for r in row["rows"] for k in r))


class PredictionIntegrityTests(unittest.TestCase):
    def test_modified_ranks_cannot_be_signed_with_original_provenance(self):
        now = instant("2030-03-10T12:00:00Z")
        p = make_prediction(race_event(fixture_race()), fixture_rows(),
                            [{"url": "https://example.com/test-fixture", "retrieved_at": now.isoformat()}], now)
        self.assertEqual(validate_prediction(p), p)
        for key, replacement in [("input_hash", "tampered"), ("prediction_id", "tampered"),
                                 ("feature_version", "unknown"), ("objective", "win_probability"),
                                 ("data_cutoff", "2030-03-10T11:00:00Z")]:
            with self.subTest(key=key), self.assertRaises(DataUnavailable):
                validate_prediction({**p, key: replacement})
        changed = json.loads(json.dumps(p))
        changed["full_grid"][0]["ranking_score"] = 99
        changed["top10"] = changed["full_grid"][:10]
        with self.assertRaises(DataUnavailable):
            validate_prediction(changed)

    def test_ledger_rejects_non_object_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            atomic_write_json(Path(tmp) / "bad.json", [])
            with self.assertRaises(DataUnavailable):
                read_records(Path(tmp))
