import unittest

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


if __name__ == "__main__":
    unittest.main()
