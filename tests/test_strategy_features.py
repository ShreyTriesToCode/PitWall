import unittest

from pitwall.features import strategy


class StrategyFeatureTests(unittest.TestCase):
    def test_compound_mapping_uses_lowest_as_hard_middle_medium_highest_soft(self):
        mapping = strategy.compound_mapping_from_nomination(["C2", "C3", "C4"], source={"document_title": "Pirelli Preview"})

        self.assertEqual(mapping["status"], "available")
        self.assertEqual(mapping["mapping"]["hard"], "C2")
        self.assertEqual(mapping["mapping"]["medium"], "C3")
        self.assertEqual(mapping["mapping"]["soft"], "C4")
        self.assertEqual(strategy.compound_role_for_value("C2", mapping), "hard")
        self.assertEqual(strategy.compound_role_for_value("C4", mapping), "soft")

    def test_compound_mapping_direction_changes_by_event_nomination(self):
        mapping = strategy.compound_mapping_from_nomination(["C3", "C4", "C5"])

        self.assertEqual(mapping["mapping"]["hard"], "C3")
        self.assertEqual(mapping["mapping"]["medium"], "C4")
        self.assertEqual(mapping["mapping"]["soft"], "C5")

    def test_compound_mapping_rejects_missing_or_malformed_nomination(self):
        mapping = strategy.compound_mapping_from_nomination(["C3", "C5"])

        self.assertEqual(mapping["status"], "unavailable")
        self.assertEqual(mapping["reason"], "expected_exactly_three_fia_slick_compounds")

    def test_strategy_simulator_enforces_two_dry_compounds(self):
        compound_mapping = strategy.compound_mapping_from_nomination(["C2", "C3", "C4"])
        result = strategy.simulate_multi_stint_strategy(
            profile={"tyre_stress": "high", "overtaking": "medium"},
            weather={"rain_score": 0},
            compound_mapping=compound_mapping,
            historical_records=[{
                "data": {
                    "results": [{"Results": [{"laps": "60"}]}],
                    "pitstops": [{"PitStops": [
                        {"driverId": "a", "lap": "18", "duration": "22.0"},
                        {"driverId": "a", "lap": "38", "duration": "22.4"},
                        {"driverId": "b", "lap": "19", "duration": "22.8"},
                        {"driverId": "b", "lap": "39", "duration": "22.2"},
                        {"driverId": "c", "lap": "20", "duration": "23.0"},
                        {"driverId": "c", "lap": "40", "duration": "22.6"},
                    ]}],
                }
            }],
        )

        compounds = {row["compound"] for row in result["sequence"] if row["compound"] in {"soft", "medium", "hard"}}
        self.assertGreaterEqual(len(compounds), 2)
        self.assertEqual(result["status"], "data_derived")
        self.assertTrue(any(row.get("compound_identity") for row in result["sequence"]))

    def test_safety_car_window_aggregates_cached_race_control_buckets(self):
        records = [
            {"data": {"race_control": [{"lap": 16, "message": "Safety Car deployed"}]}},
            {"data": {"race_control": [{"lap_number": 18, "message": "VSC deployed"}]}},
            {"data": {"race_control": [{"lap": 31, "message": "Red flag"}]}},
        ]

        window = strategy.safety_car_window_from_history(records, bucket_size=5, min_races=3)

        self.assertEqual(window["status"], "available")
        self.assertEqual(window["windows"][0]["lap_start"], 16)
        self.assertEqual(window["windows"][0]["lap_end"], 20)
        self.assertAlmostEqual(window["windows"][0]["share"], 2 / 3, places=3)

    def test_safety_car_window_reports_thin_data(self):
        window = strategy.safety_car_window_from_history([{"data": {"race_control": []}}], min_races=3)

        self.assertEqual(window["status"], "thin_data")
        self.assertFalse(window["windows"])


if __name__ == "__main__":
    unittest.main()
