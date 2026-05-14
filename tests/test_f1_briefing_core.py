import unittest
import json
from pathlib import Path

import f1_briefing as f1


class F1BriefingCoreTests(unittest.TestCase):
    def test_parse_lap_time_to_seconds(self):
        self.assertAlmostEqual(f1.parse_lap_time_to_seconds("1:31.869"), 91.869)
        self.assertAlmostEqual(f1.parse_lap_time_to_seconds("27.625"), 27.625)
        self.assertIsNone(f1.parse_lap_time_to_seconds(""))

    def test_fastest_lap_fallback_becomes_lap_target(self):
        race = {
            "raceName": "Example Grand Prix",
            "Circuit": {"circuitId": "example", "circuitName": "Example Circuit"},
            "date": "2025-05-04",
            "time": "12:00:00Z",
        }
        data = {
            "results": [{
                "Results": [{
                    "positionOrder": "1",
                    "grid": "2",
                    "points": "25",
                    "status": "Finished",
                    "Driver": {"driverId": "driver_a", "givenName": "Driver", "familyName": "A"},
                    "Constructor": {"name": "Team A"},
                    "FastestLap": {"Time": {"time": "1:31.869"}},
                }]
            }],
            "qualifying": [{
                "QualifyingResults": [{
                    "position": "2",
                    "Driver": {"driverId": "driver_a"},
                }]
            }],
            "sprint": [],
            "laps": [],
            "pitstops": [],
        }

        rows = f1.result_rows_from_race_data(2025, 1, race, data)

        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["best_clean_lap"], 91.869)
        self.assertAlmostEqual(rows[0]["avg_best_35pct_lap"], 91.869)

    def test_f1_driver_number_map_uses_permanent_number(self):
        driver_list = {
            "12": {
                "RacingNumber": "12",
                "FullName": "Kimi Antonelli",
                "TeamName": "Mercedes",
            }
        }
        known_drivers = [{
            "driver_id": "antonelli",
            "name": "Kimi Antonelli",
            "team": "Mercedes",
            "number": "12",
        }]

        mapped = f1.f1_driver_number_map(driver_list, known_drivers)

        self.assertEqual(mapped["12"]["driver_id"], "antonelli")
        self.assertEqual(mapped["12"]["team"], "Mercedes")

    def test_reverse_normalization_rewards_lower_values(self):
        scores = f1.normalize_scores({"fast": 91.0, "slow": 95.0}, reverse=True)

        self.assertGreater(scores["fast"], scores["slow"])
        self.assertEqual(scores["fast"], 100.0)
        self.assertEqual(scores["slow"], 0.0)

    def test_prediction_contract_files_are_frontend_safe(self):
        contract_path = Path("data_cache/frontend-contract.json")
        self.assertTrue(contract_path.exists())
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        latest = contract.get("latest")
        self.assertIsInstance(latest, dict)
        top10 = latest.get("top10")
        self.assertIsInstance(top10, list)
        self.assertGreaterEqual(len(top10), 1)
        self.assertLessEqual(len(top10), 10)
        full_grid = latest.get("full_grid")
        self.assertIsInstance(full_grid, list)
        self.assertGreaterEqual(len(full_grid), len(top10))
        driver_ids = [item.get("driver_id") for item in top10]
        self.assertEqual(len(driver_ids), len(set(driver_ids)))
        full_driver_ids = [item.get("driver_id") for item in full_grid]
        self.assertEqual(len(full_driver_ids), len(set(full_driver_ids)))
        self.assertEqual([item.get("driver_id") for item in top10], [item.get("driver_id") for item in full_grid[:len(top10)]])

        required = {
            "name",
            "team",
            "driver_id",
            "rank",
            "score",
            "confidence",
            "component_scores",
            "win_probability",
            "podium_probability",
            "top10_probability",
            "best_case_finish",
            "worst_case_finish",
            "model_agreement_score",
            "evidence_status",
            "missing_data_penalties",
            "attack_potential_score",
            "defend_risk_score",
            "energy_boost_advantage_score",
            "active_aero_suitability_score",
            "expected_points",
            "top10_safety_score",
        }
        for item in full_grid:
            self.assertTrue(required.issubset(item.keys()))
            self.assertIsInstance(item["component_scores"], dict)
            self.assertIsInstance(item["score"], (int, float))
            self.assertGreaterEqual(item["confidence"], 0)
            self.assertLessEqual(item["confidence"], 100)
            for key in ["win_probability", "podium_probability", "top10_probability"]:
                if item[key] is not None:
                    self.assertGreaterEqual(item[key], 0)
                    self.assertLessEqual(item[key], 100)

        self.assertIn("weather", latest)
        self.assertIn("prediction_model", latest)
        self.assertIn("source_status", latest)
        self.assertIn("model_metrics", latest)
        self.assertIn("strategy", latest)
        self.assertIn("scenarios", latest)
        self.assertIn("archive", contract)

    def test_model_status_and_audit_contracts_are_valid(self):
        model_status = json.loads(Path("data_cache/model-status.json").read_text(encoding="utf-8"))
        self.assertEqual(model_status.get("schema_version"), f1.MODEL_SCHEMA_VERSION)
        self.assertIn("metrics", model_status)
        self.assertIn("source_health", model_status)
        self.assertIn("champion_challenger", model_status)
        self.assertIn("promotion_decision", model_status)
        self.assertIn("readiness_state", model_status)

        backtest = json.loads(Path("data_cache/backtest-history.json").read_text(encoding="utf-8"))
        self.assertIn("history", backtest)
        self.assertIsInstance(backtest["history"], list)

        corrections = json.loads(Path("data_cache/model_corrections.json").read_text(encoding="utf-8"))
        self.assertIn("corrections", corrections)

    def test_generated_feature_store_exists(self):
        for name in ["race_features.json", "driver_features.json", "team_features.json", "session_features.json"]:
            path = Path("data_cache/features") / name
            self.assertTrue(path.exists(), name)
            self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), list)

    def test_generated_debug_targets_are_safe_for_target_switching(self):
        debug = json.loads(Path("data_cache/latest-model-debug.json").read_text(encoding="utf-8"))
        payloads = debug.get("payloads", [])
        self.assertIsInstance(payloads, list)
        self.assertGreaterEqual(len(payloads), 1)

        seen_targets = set()
        for payload in payloads:
            target_type = payload.get("target_type")
            self.assertIn(target_type, {"sprint", "race"})
            self.assertNotIn(target_type, seen_targets)
            seen_targets.add(target_type)

            top10 = payload.get("top10", [])
            self.assertIsInstance(top10, list)
            self.assertGreaterEqual(len(top10), 1)
            full_grid = payload.get("full_grid", [])
            self.assertIsInstance(full_grid, list)
            self.assertGreaterEqual(len(full_grid), len(top10))
            driver_ids = [row.get("driver_id") for row in top10]
            self.assertEqual(len(driver_ids), len(set(driver_ids)))
            full_driver_ids = [row.get("driver_id") for row in full_grid]
            self.assertEqual(len(full_driver_ids), len(set(full_driver_ids)))

    def test_archive_entries_reference_existing_local_briefings(self):
        contract = json.loads(Path("data_cache/frontend-contract.json").read_text(encoding="utf-8"))
        for row in contract.get("archive", []):
            path = row.get("path")
            if not path:
                continue
            self.assertTrue(path.startswith("briefings/"))
            self.assertTrue(Path(path).exists(), path)


if __name__ == "__main__":
    unittest.main()
