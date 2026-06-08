import tempfile
import unittest
from pathlib import Path

from pitwall.ai.deterministic import build_driver_ai_explanation, enrich_driver_ai_explanation
from pitwall.ai.local_rag import query_keyword_index
from pitwall.ai.post_race import build_post_race_ai_review
from pitwall.ai.source_conflicts import detect_source_conflicts
from pitwall.ai.summaries import build_changed_since_last_run, build_race_intelligence_summary
from pitwall.models.agreement import enrich_model_disagreement
from pitwall.models.trust import enrich_prediction_trust, trust_label
from pitwall.validation.contracts import validate_frontend_contract


class FreeAiIntelligenceTests(unittest.TestCase):
    def test_deterministic_explanation_uses_available_fields(self):
        row = {
            "driver_id": "nor",
            "name": "Lando Norris",
            "team": "McLaren",
            "rank": 2,
            "predicted_finish": 3,
            "confidence": 61,
            "prediction_trust_score": 58,
            "prediction_trust_label": "Medium trust",
            "win_probability": 18,
            "top10_probability": 86,
            "reason_tags": ["race pace"],
            "missing_feature_groups": ["final grid"],
            "model_disagreement_level": "low",
        }
        explanation = build_driver_ai_explanation(row, {"stage": "pre_weekend"})
        self.assertIn("Lando Norris", explanation["simple_explanation"])
        self.assertIn("final grid", explanation["missing_data_note"])
        self.assertIn("pre-weekend", explanation["scenario_note"])
        self.assertEqual(explanation["generated_by"], "deterministic")

    def test_missing_data_note_and_enrichment_shape(self):
        row = enrich_driver_ai_explanation({
            "driver_id": "rookie",
            "name": "Rookie Driver",
            "team": "Example",
            "rank": 12,
            "confidence": 35,
            "missing_feature_groups": ["rookie/substitute history", "practice pace"],
            "model_disagreement_level": "medium",
            "model_disagreement_reasons": ["top10_rank_low_points_probability"],
        })
        self.assertIn("ai_explanation", row)
        self.assertIn("rookie/substitute history", row["ai_explanation"]["missing_data_note"])

    def test_model_disagreement_rules(self):
        row = enrich_model_disagreement({
            "driver_id": "x",
            "name": "Driver X",
            "rank": 2,
            "predicted_finish_position": 11,
            "win_probability": 3,
            "top10_probability": 88,
            "confidence": 70,
        })
        self.assertEqual(row["model_disagreement_level"], "high")
        self.assertIn("front_rank_conflicts_with_finish_model", row["model_disagreement_reasons"])

    def test_trust_score_and_label_bounds(self):
        row = enrich_prediction_trust({
            "driver_id": "x",
            "rank": 5,
            "confidence": 60,
            "model_agreement_score": 70,
            "available_feature_groups": ["driver form", "team form"],
            "missing_feature_groups": ["weather"],
        }, source_health={"overall_score": 65}, stage="pre_weekend")
        self.assertGreaterEqual(row["prediction_trust_score"], 0)
        self.assertLessEqual(row["prediction_trust_score"], 100)
        self.assertEqual(trust_label(75), "High trust")
        self.assertEqual(trust_label(50), "Medium trust")
        self.assertEqual(trust_label(49), "Low trust")

    def test_source_conflict_detector_classifies_basic_conflicts(self):
        conflicts = detect_source_conflicts({
            "latest": {
                "source_health": {"sources": [{"source": "OpenF1", "status": "Unavailable", "auth_restricted": True}]},
                "warnings": ["FIA document unavailable: 403 forbidden"],
            }
        })
        types = {row["conflict_type"] for row in conflicts}
        self.assertIn("auth_restricted", types)
        self.assertIn("fia_document_unavailable", types)

    def test_enhanced_contract_validator_accepts_ai_fields(self):
        row = {
            "driver_id": "ham",
            "name": "Lewis Hamilton",
            "team": "Ferrari",
            "rank": 1,
            "score": 88,
            "rank_score": 88,
            "confidence": 64,
            "win_probability": 30,
            "podium_probability": 70,
            "top10_probability": 94,
            "points_probability": 94,
            "fastest_lap_probability": 7,
            "predicted_position": 1,
            "probability": 94,
            "prediction_trust": "Medium trust",
            "position_range": [1, 3],
            "expected_strategy": {},
            "explanation": {},
            "source_notes": {},
            "prediction_trust_score": 66,
            "model_disagreement_level": "low",
            "ai_explanation": {"simple_explanation": "Grounded text."},
        }
        result = validate_frontend_contract({
            "model_comparison": {
                "champion": {},
                "challenger": {},
                "promotion_decision": {},
                "metrics": {},
                "warnings": [],
            },
            "actual_result_comparison": {
                "status": "pending",
                "race": {},
                "predicted_winner": {},
                "actual_winner": {},
                "winner_hit": False,
                "predicted_podium": [],
                "actual_podium": [],
                "podium_recall": None,
                "predicted_top10": [],
                "actual_top10": [],
                "top10_recall": None,
                "driver_position_errors": [],
                "metrics": {},
                "source_health": [],
                "warnings": [],
            },
            "latest": {
                "top10": [row],
                "full_grid": [row],
                "all_predictions": [row],
                "race_intelligence_summary": {"headline": "Summary"},
                "changed_since_last_run": {"summary": "No previous valid contract available."},
            }
        })
        self.assertEqual(result["latest_top10_count"], 1)

    def test_local_rag_missing_index_returns_not_enough_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = query_keyword_index("model status", base_dir=Path(tmp))
        self.assertFalse(result["ok"])
        self.assertEqual(result["answer"], "Not enough data in local PitWall sources.")

    def test_race_and_change_summaries_are_deterministic(self):
        latest = {
            "race_name": "Example GP",
            "stage": "pre_weekend",
            "prediction_trust_score": 44,
            "full_grid": [{"driver_id": "a", "name": "Driver A", "model_disagreement_level": "high", "missing_feature_groups": ["weather"]}],
        }
        summary = build_race_intelligence_summary(latest)
        self.assertEqual(summary["generated_by"], "deterministic")
        self.assertIn("Example GP", summary["headline"])
        change = build_changed_since_last_run(None, {"latest": latest})
        self.assertFalse(change["available"])

    def test_post_race_review_pending_and_available(self):
        pending = build_post_race_ai_review([])
        self.assertEqual(pending["generated_by"], "deterministic")
        available = build_post_race_ai_review({"corrections": [{"errors": [{"name": "Driver A", "predicted_position": 1, "actual_position": 8, "position_error": 7}]}]})
        self.assertIn("Driver A", available["worst_miss"])


if __name__ == "__main__":
    unittest.main()
