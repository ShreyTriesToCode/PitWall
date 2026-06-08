import tempfile
import unittest
from pathlib import Path

import pandas as pd

from pitwall.data.cache_manager import cache_aware_json_loader, load_manifest, validate_json_cache
from pitwall.features.build_features import feature_schema, missing_value_report
from pitwall.models.evaluate import evaluate_finish_predictions
from pitwall.models.predict import normalize_prediction_row, top10_from_full_grid, validate_top10_subset
from pitwall.models.validation import assert_chronological_split, promotion_gate, validate_training_frame


class ModelModuleTests(unittest.TestCase):
    def test_prediction_helpers_keep_top10_subset_of_full_grid(self):
        full_grid = [
            {"driver_id": "driver_b", "rank": 2, "score": 75},
            {"driver_id": "driver_a", "rank": 1, "score": 82},
            {"driver_id": "driver_c", "rank": 11, "score": 40},
        ]
        top10 = top10_from_full_grid(full_grid)
        self.assertEqual([row["driver_id"] for row in top10[:2]], ["driver_a", "driver_b"])
        self.assertTrue(validate_top10_subset(top10, full_grid))

    def test_normalize_prediction_row_adds_contract_aliases(self):
        row = normalize_prediction_row({"driver_id": "driver_a", "team": "Team A", "score": 88, "top10_probability": 92}, rank=1)
        self.assertEqual(row["predicted_position"], 1)
        self.assertEqual(row["probability"], 92)
        self.assertEqual(row["rank_score"], 88)
        self.assertIn("expected_strategy", row)

    def test_evaluate_finish_predictions_returns_ranking_metrics(self):
        frame = pd.DataFrame([
            {"race_id": "r1", "driver_id": "a", "finish_position": 1},
            {"race_id": "r1", "driver_id": "b", "finish_position": 2},
            {"race_id": "r1", "driver_id": "c", "finish_position": 3},
            {"race_id": "r2", "driver_id": "a", "finish_position": 2},
            {"race_id": "r2", "driver_id": "b", "finish_position": 1},
            {"race_id": "r2", "driver_id": "c", "finish_position": 3},
        ])
        metrics = evaluate_finish_predictions(frame, [1, 2, 3, 2, 1, 3])
        self.assertEqual(metrics["finish_mae"], 0)
        self.assertEqual(metrics["ranking"]["winner_hit_rate"], 1)

    def test_training_validation_blocks_target_columns_in_features(self):
        frame = pd.DataFrame([
            {"race_id": "r1", "season": 2024, "round": 1, "driver_id": "a", "finish_position": 1, "driver_form": 80},
            {"race_id": "r2", "season": 2024, "round": 2, "driver_id": "a", "finish_position": 2, "driver_form": 70},
            {"race_id": "r3", "season": 2024, "round": 3, "driver_id": "a", "finish_position": 3, "driver_form": 60},
            {"race_id": "r4", "season": 2024, "round": 4, "driver_id": "a", "finish_position": 4, "driver_form": 50},
        ])
        ok = validate_training_frame(frame, ["driver_form"])
        bad = validate_training_frame(frame, ["driver_form", "finish_position"])
        self.assertTrue(ok["ok"])
        self.assertFalse(bad["ok"])

    def test_chronological_split_assertion(self):
        train = pd.DataFrame([{"season": 2023, "round": 22}])
        valid = pd.DataFrame([{"season": 2024, "round": 1}])
        assert_chronological_split(train, valid)
        with self.assertRaises(AssertionError):
            assert_chronological_split(valid, train)

    def test_feature_schema_and_missing_report(self):
        frame = pd.DataFrame({"a": [1, None], "missing_a": [0, 1]})
        schema = feature_schema(["a", "missing_a"])
        self.assertEqual(schema["missingness_indicators"], ["missing_a"])
        self.assertEqual(missing_value_report(frame, ["a"])["a"], 1)

    def test_cache_aware_loader_reuses_valid_cache_and_updates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / "payload.json"
            manifest = root / "cache_manifest.json"
            cache.write_text('{"ok": true}', encoding="utf-8")
            calls = {"fetch": 0}

            def fetcher():
                calls["fetch"] += 1
                return {"ok": False}

            def writer(payload):
                cache.write_text(str(payload), encoding="utf-8")
                return cache

            payload = cache_aware_json_loader(
                cache_key="unit",
                source="unit-source",
                file_path=cache,
                manifest_path=manifest,
                fetcher=fetcher,
                writer=writer,
            )
            self.assertEqual(payload, {"ok": True})
            self.assertEqual(calls["fetch"], 0)
            entry = load_manifest(manifest)["entries"]["unit"]
            self.assertEqual(entry["latest_run_action"], "reused")

    def test_cache_aware_loader_refreshes_corrupt_cache_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / "payload.json"
            manifest = root / "cache_manifest.json"
            cache.write_text("{bad", encoding="utf-8")
            calls = {"fetch": 0}

            def fetcher():
                calls["fetch"] += 1
                return {"ok": True}

            def writer(payload):
                cache.write_text('{"ok": true}', encoding="utf-8")
                return cache

            payload = cache_aware_json_loader(
                cache_key="unit",
                source="unit-source",
                file_path=cache,
                manifest_path=manifest,
                fetcher=fetcher,
                writer=writer,
                validator=lambda path: validate_json_cache(path, required_top_level_keys=["ok"]),
            )
            self.assertEqual(payload, {"ok": True})
            self.assertEqual(calls["fetch"], 1)
            self.assertEqual(load_manifest(manifest)["entries"]["unit"]["latest_run_action"], "refreshed")

    def test_promotion_gate_requires_ranking_metrics(self):
        decision = promotion_gate({}, {"finish_mae": 3.0})
        self.assertFalse(decision["approved"])
        self.assertFalse(decision["checks"]["has_ranking_metrics"])


if __name__ == "__main__":
    unittest.main()
