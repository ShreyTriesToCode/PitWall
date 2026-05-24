import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import f1_briefing as f1


class SeasonReplenishmentTests(unittest.TestCase):
    def test_target_season_auto_uses_current_year(self):
        self.assertEqual(
            f1.resolve_target_season({"TARGET_SEASON": "auto"}, now=datetime(2027, 1, 3, tzinfo=timezone.utc)),
            2027,
        )

    def test_fia_source_url_prefers_exact_env_and_never_fabricates_future_url(self):
        env = {
            "FIA_DOCUMENTS_BASE_URL": "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14",
            "FIA_DOCUMENTS_SEASON_URL_2026": "https://www.fia.com/known-2026",
            "FIA_DOCUMENTS_SEASON_URL_2027": "",
        }
        self.assertEqual(f1.resolve_fia_season_url(2026, env=env).get("url"), "https://www.fia.com/known-2026")
        unresolved = f1.resolve_fia_season_url(2027, env=env, championship_html="<a href='/season/season-2026-2072'>2026</a>")
        self.assertIsNone(unresolved.get("url"))
        self.assertEqual(unresolved.get("status"), "pending_unavailable")

    def test_source_registry_written_for_future_pending_fia(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = f1.build_source_registry(
                2027,
                env={
                    "FIA_DOCUMENTS_SEASON_URL_2027": "",
                    "FORMULA1_CALENDAR_BASE_URL": "https://www.formula1.com/en/racing",
                },
                cache_dir=Path(tmp),
                championship_html="",
                formula1_html='<a href="/en/racing/2027/australia">Australia</a>',
                now=datetime(2026, 5, 23, tzinfo=timezone.utc),
            )
            self.assertEqual(registry["season"], 2027)
            self.assertEqual(registry["fia_source_discovery_status"], "pending_unavailable")
            self.assertEqual(registry["formula1_season_url"], "https://www.formula1.com/en/racing/2027")
            self.assertIn("australia", registry["discovered_event_slugs"])
            self.assertTrue((Path(tmp) / "source_registry" / "2027.json").exists())


class FiaDocumentParsingTests(unittest.TestCase):
    def test_document_type_classifier_recognizes_key_fia_documents(self):
        cases = {
            "Doc 12 - Car Presentation Submissions": "car_presentation_submissions",
            "Document 18 - New PU Elements for this Competition": "new_pu_elements",
            "Provisional Starting Grid": "starting_grid",
            "Free Practice 1 Classification": "free_practice_classification",
            "Sprint Qualifying Classification": "sprint_qualifying_classification",
            "Deleted Lap Times - Qualifying": "deleted_lap_times",
            "Race Director Event Notes": "race_director_notes",
            "Decision - Car 44 impeding": "decision",
            "Recalled Document": "recalled_document",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(f1.classify_fia_document_type(title), expected)

    def test_parse_fia_document_index_extracts_metadata(self):
        html = """
        <h3>Canadian Grand Prix</h3>
        <a href="/sites/default/files/doc_12_car_presentation.pdf">Doc 12 - Car Presentation Submissions</a>
        <time datetime="2026-05-22T12:30:00+02:00">22.05.26 12:30 CET</time>
        <a href="https://www.fia.com/file/qualifying-classification.pdf">Document 22 - Qualifying Classification</a>
        """
        docs = f1.parse_fia_document_index(html, season=2026, season_url="https://www.fia.com/season-2026")
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0]["document_number"], 12)
        self.assertEqual(docs[0]["event_slug"], "canadian-grand-prix")
        self.assertEqual(docs[0]["document_type"], "car_presentation_submissions")
        self.assertTrue(docs[0]["source_url"].startswith("https://www.fia.com/"))
        self.assertEqual(docs[1]["document_type"], "qualifying_classification")

    def test_extract_classification_rows_from_text(self):
        text = """
        POS NO DRIVER NAT TEAM TIME LAPS
        1 16 Charles LECLERC Ferrari 1:11.111 24
        2 44 Lewis HAMILTON Ferrari +0.123 23
        """
        rows = f1.extract_fia_classification_rows(text)
        self.assertEqual(rows[0]["position"], 1)
        self.assertEqual(rows[0]["driver_number"], "16")
        self.assertEqual(rows[0]["driver_name"], "Charles Leclerc")
        self.assertEqual(rows[1]["gap"], "+0.123")

    def test_extract_upgrade_pu_and_infringement_features(self):
        update_text = """
        Team Component Primary reason for update Geometric differences Brief description
        Ferrari Floor Performance - Local Load Revised floor edge improves sealing and tyre management
        """
        updates = f1.extract_car_presentation_updates(update_text, event_name="Canadian Grand Prix")
        self.assertEqual(updates[0]["team"], "Ferrari")
        self.assertIn("tyre_management", updates[0]["traits"])

        pu = f1.extract_pu_features("44 Lewis Hamilton New ICE TC MGU-H ES CE Exhaust")
        self.assertTrue(pu["44"]["new_ice"])
        self.assertTrue(pu["44"]["new_mgu_h"])

        infringement = f1.extract_infringement_features("Car 4 deleted lap time for track limits. Decision: 3 grid place penalty.")
        self.assertEqual(infringement["deleted_lap_count"], 1)
        self.assertEqual(infringement["grid_penalty_places"], 3)


class SessionLifecycleAndModelGuardTests(unittest.TestCase):
    def test_missing_ics_url_uses_jolpica_schedule_fallback_calendar(self):
        race = {
            "round": "1",
            "raceName": "Australian Grand Prix",
            "date": "2026-06-21",
            "time": "05:00:00Z",
            "Circuit": {"Location": {"country": "Australia"}},
        }
        with patch.object(f1, "F1_ICS_URL", ""), patch.object(f1, "fetch_schedule", return_value=[race]):
            calendar = f1.fetch_ics_calendar()
        events = f1.get_f1_calendar_events(calendar)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["target_type"], "race")
        self.assertIn("Australian Grand Prix", events[0]["title"])

    def test_session_lifecycle_waits_after_completion_and_then_retries(self):
        session = {
            "session_type": "qualifying",
            "official_start_time_utc": "2026-05-23T18:00:00+00:00",
            "official_end_time_utc": "2026-05-23T19:00:00+00:00",
            "ingestion_attempts": 1,
        }
        waiting = f1.evaluate_session_lifecycle(
            session,
            now=datetime(2026, 5, 23, 19, 10, tzinfo=timezone.utc),
            data_available=False,
        )
        self.assertEqual(waiting["status"], "completed")

        retry = f1.evaluate_session_lifecycle(
            session,
            now=datetime(2026, 5, 23, 19, 45, tzinfo=timezone.utc),
            data_available=False,
        )
        self.assertEqual(retry["status"], "waiting_for_api_data")
        self.assertIsNotNone(retry["next_check_at"])

    def test_stage_feature_matrix_blocks_future_session_leakage(self):
        audit = f1.audit_feature_leakage("post_fp1", ["fp1_pace", "qualifying_position", "race_result"])
        self.assertFalse(audit["passed"])
        self.assertIn("qualifying_position", audit["blocked_features"])
        self.assertIn("race_result", audit["blocked_features"])

    def test_stage_weights_are_normalized_and_upgrade_caps_hold(self):
        weights = f1.stage_prediction_weights("post_qualifying", track_traits={"overtaking": "low"}, weather={"rain_probability": 0.65})
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)
        self.assertGreater(weights["qualifying_grid"], weights["fia_upgrades"])
        self.assertLessEqual(weights["fia_upgrades"], 0.03)

    def test_probability_normalization_and_simulation_shape(self):
        rows = [
            {"driver_id": "a", "score": 88, "win_probability": 55, "podium_probability": 75, "top10_probability": 99, "dnf_probability": 5},
            {"driver_id": "b", "score": 74, "win_probability": 35, "podium_probability": 65, "top10_probability": 96, "dnf_probability": 8},
            {"driver_id": "c", "score": 58, "win_probability": 20, "podium_probability": 30, "top10_probability": 80, "dnf_probability": 12},
        ]
        normalized = f1.normalize_race_probabilities(rows)
        self.assertAlmostEqual(sum(row["win_probability"] for row in normalized), 100.0, places=3)
        sim = f1.simulate_race_outcomes(normalized, runs=200, seed=7)
        self.assertEqual(len(sim["drivers"]), 3)
        self.assertIn("most_volatile_drivers", sim)
        self.assertIn("confidence_interval_width", sim["drivers"][0])

    def test_timing_freshness_never_marks_archive_as_live(self):
        status = f1.timing_freshness_status(
            last_updated=datetime(2026, 5, 23, 18, 0, tzinfo=timezone.utc),
            now=datetime(2026, 5, 23, 18, 5, tzinfo=timezone.utc),
            session_end=datetime(2026, 5, 23, 18, 1, tzinfo=timezone.utc),
            has_fresh_packets=True,
        )
        self.assertEqual(status["timing_mode"], "archive")
        self.assertFalse(status["is_genuinely_live"])

    def test_contract_contains_new_top_level_operational_fields(self):
        contract = json.loads(Path("data_cache/frontend-contract.json").read_text(encoding="utf-8"))
        for key in [
            "season",
            "source_registry",
            "session_timeline",
            "source_conflicts",
            "timing_mode",
            "is_genuinely_live",
        ]:
            self.assertIn(key, contract)
        latest = contract["latest"]
        for key in [
            "fia_documents_enabled",
            "fia_source_discovery_status",
            "fia_document_count",
            "effective_model_weights",
            "confidence_breakdown",
            "simulation",
            "timing_mode",
        ]:
            self.assertIn(key, latest)


if __name__ == "__main__":
    unittest.main()
