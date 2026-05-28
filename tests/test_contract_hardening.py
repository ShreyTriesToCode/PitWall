import json
import tempfile
import unittest
from pathlib import Path

from pitwall.models.agreement import enrich_model_disagreement
from pitwall.models.trust import enrich_prediction_trust
from pitwall.validation.contracts import ContractValidationError, validate_contract_files
from pitwall.validation.leakage import assert_no_future_leakage, forbidden_feature_columns


class ContractHardeningTests(unittest.TestCase):
    def write_json(self, base, relative, payload):
        path = Path(base) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def valid_prediction_row(self):
        return {
            "driver_id": "driver_a",
            "name": "Driver A",
            "team": "Team A",
            "rank": 1,
            "score": 82,
            "confidence": 64,
            "win_probability": 22,
            "podium_probability": 70,
            "top10_probability": 96,
            "predicted_finish_position": 2,
            "position_range": [1, 4],
            "component_scores": {"race_pace": 80},
            "evidence_status": {"available": ["race_pace"], "missing": [], "penalties": {}, "penalty_total": 0},
            "source_notes": {"warnings": []},
        }

    def test_contract_validator_rejects_blank_required_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_json(tmp, "data_cache/frontend-contract.json", {})
            self.write_json(tmp, "briefings/index.json", {})
            self.write_json(tmp, "data_cache/latest-model-debug.json", {})
            self.write_json(tmp, "data_cache/model-status.json", {})

            with self.assertRaises(ContractValidationError):
                validate_contract_files(Path(tmp))

    def test_contract_validator_accepts_top10_and_full_grid(self):
        row = self.valid_prediction_row()
        with tempfile.TemporaryDirectory() as tmp:
            self.write_json(tmp, "data_cache/frontend-contract.json", {
                "schema_version": "test",
                "prediction_data_version": "test-data",
                "latest": {
                    "top10": [row],
                    "top_10": [row],
                    "full_grid": [row, {**row, "driver_id": "driver_b", "name": "Driver B", "rank": 2}],
                    "all_predictions": [row, {**row, "driver_id": "driver_b", "name": "Driver B", "rank": 2}],
                },
            })
            self.write_json(tmp, "briefings/index.json", {"briefings": [{"latest": True}]})
            self.write_json(tmp, "data_cache/latest-model-debug.json", {"payloads": [{"top10": [row], "full_grid": [row]}]})
            self.write_json(tmp, "data_cache/model-status.json", {
                "model_version": "test-model",
                "schema_version": "test",
                "metrics": {"finish_position_mae": 3.2},
            })

            result = validate_contract_files(Path(tmp))

        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["latest_top10_count"], 1)
        self.assertGreaterEqual(result["latest_full_grid_count"], result["latest_top10_count"])

    def test_model_disagreement_flags_contradictory_top_rank(self):
        row = enrich_model_disagreement({
            "rank": 1,
            "predicted_finish_position": 12,
            "win_probability": 3,
            "top10_probability": 42,
            "confidence": 70,
            "model_agreement_score": 80,
        })

        self.assertEqual(row["model_disagreement_level"], "high")
        self.assertLess(row["confidence"], 70)
        self.assertTrue(row["model_disagreement_reasons"])

    def test_prediction_trust_score_uses_source_and_completeness(self):
        row = enrich_prediction_trust(
            {
                "model_agreement_score": 70,
                "confidence": 62,
                "evidence_status": {"available": ["race_pace"], "missing": ["qualifying", "weather"], "penalties": {}, "penalty_total": 18},
                "source_notes": {"warnings": ["OpenF1 auth restricted"]},
            },
            source_health={"overall_score": 48},
            stage="pre_race",
            validation_strength=64,
        )

        self.assertIn(row["prediction_trust_label"], {"Low trust", "Medium trust"})
        self.assertLess(row["prediction_trust_score"], 70)
        self.assertIn("qualifying", row["missing_feature_groups"])

    def test_frontend_contract_loader_contains_debug_recovery_path(self):
        source = Path("frontend/app/api/_lib/contracts.js").read_text(encoding="utf-8")
        self.assertIn("contract_recovered_from_debug", source)
        self.assertIn("recoverContractFromDebug", source)
        self.assertIn("latest-model-debug.json", source)

    def test_stage_leakage_rules_block_future_session_columns(self):
        self.assertIn("qualifying_gap", forbidden_feature_columns("post_fp1", ["fp1_pace", "qualifying_gap"]))
        assert_no_future_leakage("post_qualifying", ["qualifying_gap", "grid_position"])
        with self.assertRaises(AssertionError):
            assert_no_future_leakage("pre_weekend", ["driver_form_5", "race_result_position"])

    def test_generated_probability_normalization_sums_are_reasonable(self):
        contract = json.loads(Path("data_cache/frontend-contract.json").read_text(encoding="utf-8"))
        rows = contract["latest"]["full_grid"]
        sums = {
            "win": sum(float(row.get("win_probability") or 0) for row in rows),
            "podium": sum(float(row.get("podium_probability") or 0) for row in rows),
            "top10": sum(float(row.get("top10_probability") or 0) for row in rows),
        }
        self.assertAlmostEqual(sums["win"], 100, delta=1.5)
        self.assertAlmostEqual(sums["podium"], 300, delta=5)
        self.assertAlmostEqual(sums["top10"], 1000, delta=8)


if __name__ == "__main__":
    unittest.main()
