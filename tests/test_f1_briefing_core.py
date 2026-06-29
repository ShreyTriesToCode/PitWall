import unittest
import importlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import f1_briefing as f1
from pitwall.data import f1db, relbench_f1


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

    def test_completed_race_rows_flatten_full_grid_strategy_weather_features(self):
        race = {
            "raceName": "Example Grand Prix",
            "Circuit": {"circuitId": "example", "circuitName": "Example Circuit"},
            "date": "2025-05-04",
            "time": "12:00:00Z",
        }
        results = []
        timings = []
        pitstops = []
        stints = []
        for idx in range(1, 23):
            driver_id = f"driver_{idx:02d}"
            results.append({
                "positionOrder": str(idx),
                "grid": str(idx),
                "points": str(max(0, 26 - idx)),
                "status": "Finished",
                "Driver": {"driverId": driver_id, "givenName": "Driver", "familyName": str(idx)},
                "Constructor": {"name": f"Team {((idx - 1) // 2) + 1}"},
                "FastestLap": {"Time": {"time": "1:31.000"}},
            })
            pitstops.append({"driverId": driver_id, "lap": "18", "duration": "2.7"})
            stints.append({"driver_id": driver_id, "compound": "MEDIUM", "stint_number": 1})
            timings.append({"driverId": driver_id, "time": "1:31.000"})
        data = {
            "results": [{"Results": results}],
            "qualifying": [{"QualifyingResults": [
                {"position": str(idx), "Driver": {"driverId": f"driver_{idx:02d}"}} for idx in range(1, 23)
            ]}],
            "sprint": [],
            "laps": [{"Laps": [{"number": str(lap_no), "Timings": timings} for lap_no in range(1, 5)]}],
            "pitstops": [{"PitStops": pitstops}],
            "stints": stints,
            "race_control": [{"lap": "18", "message": "Safety car deployed"}],
            "weather": {"rainfall_actual": 0.2, "rain_probability": 0.7},
        }

        rows = f1.result_rows_from_race_data(2025, 1, race, data)

        self.assertEqual(len(rows), 22)
        first = rows[0]
        self.assertEqual(first["actual_first_pit_lap"], 18)
        self.assertEqual(first["actual_pit_stop_count"], 1)
        self.assertGreater(first["actual_starting_compound_code"], 0)
        self.assertEqual(first["actual_race_control_event_count"], 1)
        self.assertAlmostEqual(first["actual_weather_rainfall"], 0.2)
        self.assertIn("actual_strategy_annotation_count", first)

        feature_df, feature_columns = f1.create_ml_features(pd.DataFrame(rows))
        for feature in [
            "driver_strategy_first_pit_lap",
            "team_strategy_pit_stop_count",
            "track_strategy_safety_car_rate",
            "track_weather_rainfall_rate",
        ]:
            self.assertIn(feature, feature_columns)
            self.assertIn(feature, feature_df.columns)

    def test_ml_features_include_fia_upgrade_package_signals(self):
        base = {
            "race_name": "Example Grand Prix",
            "circuit_id": "example",
            "driver_id": "driver_a",
            "driver_name": "Driver A",
            "constructor": "Ferrari",
            "grid": 3,
            "qualifying": 3,
            "sprint_position": 20,
            "finish_position": 2,
            "points": 18,
            "is_win": 0,
            "is_podium": 1,
            "is_top10": 1,
            "is_finished": 1,
            "best_clean_lap": 91.0,
            "avg_best_35pct_lap": 91.2,
            "lap_consistency": 0.4,
            "valid_laps": 55,
            "pit_stop_count": 1,
            "avg_pit_duration": 2.8,
            "min_pit_duration": 2.7,
            "actual_first_pit_lap": 18,
            "actual_pit_stop_count": 1,
            "actual_starting_compound_code": 2,
            "actual_strategy_annotation_count": 1,
            "actual_safety_car_strategy_flag": 0,
            "actual_race_control_event_count": 0,
            "actual_weather_rainfall": 0,
            "actual_weather_rain_probability": 0,
            "actual_post_switch_pace_delta": 0,
            "actual_degradation_slope": 0,
            "actual_double_stack_loss": 0,
            "actual_traffic_loss": 0,
        }
        rows = [
            {
                **base,
                "race_id": "2026-1",
                "season": 2026,
                "round": 1,
                "fia_upgrade_score": 0,
                "fia_upgrade_count": 0,
                "fia_upgrade_component_count": 0,
                "fia_upgrade_trait_count": 0,
                "fia_upgrade_aero_score": 0,
                "missing_fia_upgrade_data": 1,
            },
            {
                **base,
                "race_id": "2026-2",
                "season": 2026,
                "round": 2,
                "fia_upgrade_score": 82,
                "fia_upgrade_count": 2,
                "fia_upgrade_component_count": 2,
                "fia_upgrade_trait_count": 5,
                "fia_upgrade_aero_score": 3,
                "missing_fia_upgrade_data": 0,
            },
        ]

        feature_df, feature_columns = f1.create_ml_features(pd.DataFrame(rows))
        target = feature_df[feature_df["race_id"] == "2026-2"].iloc[0]

        for feature in [
            "fia_upgrade_score",
            "fia_upgrade_count",
            "fia_upgrade_component_count",
            "fia_upgrade_trait_count",
            "fia_upgrade_aero_score",
            "missing_fia_upgrade_data",
        ]:
            self.assertIn(feature, feature_columns)
            self.assertIn(feature, feature_df.columns)
        self.assertEqual(target["fia_upgrade_score"], 82)
        self.assertEqual(target["fia_upgrade_count"], 2)
        self.assertEqual(target["fia_upgrade_aero_score"], 3)
        self.assertEqual(target["missing_fia_upgrade_data"], 0)

    def test_prediction_features_use_historical_strategy_weather_actuals(self):
        historical_df = pd.DataFrame([{
            "season": 2025,
            "round": 1,
            "driver_id": "driver_a",
            "constructor": "Team A",
            "circuit_id": "example",
            "finish_position": 4,
            "points": 12,
            "is_win": 0,
            "is_podium": 0,
            "is_top10": 1,
            "is_finished": 1,
            "grid": 5,
            "qualifying": 5,
            "sprint_position": 20,
            "avg_best_35pct_lap": 91.2,
            "lap_consistency": 0.4,
            "valid_laps": 55,
            "pit_stop_count": 1,
            "avg_pit_duration": 2.8,
            "min_pit_duration": 2.7,
            "actual_first_pit_lap": 18,
            "actual_pit_stop_count": 1,
            "actual_starting_compound_code": 2,
            "actual_strategy_annotation_count": 1,
            "actual_safety_car_strategy_flag": 1,
            "actual_race_control_event_count": 1,
            "actual_weather_rainfall": 0.2,
            "actual_weather_rain_probability": 0.7,
        }])
        race = {
            "season": "2025",
            "round": "2",
            "Circuit": {"circuitId": "example"},
        }
        feature_columns = [
            "driver_strategy_first_pit_lap",
            "team_strategy_pit_stop_count",
            "track_strategy_safety_car_rate",
            "track_weather_rainfall_rate",
        ]

        rows = f1.build_prediction_feature_rows(
            [{"driver_id": "driver_a", "name": "Driver A", "team": "Team A", "position": 1}],
            race,
            {},
            historical_df,
            feature_columns,
        )

        self.assertEqual(rows.loc[0, "driver_strategy_first_pit_lap"], 18)
        self.assertEqual(rows.loc[0, "team_strategy_pit_stop_count"], 1)
        self.assertEqual(rows.loc[0, "track_strategy_safety_car_rate"], 1)
        self.assertAlmostEqual(rows.loc[0, "track_weather_rainfall_rate"], 0.2)

    def test_prediction_feature_rows_include_fia_upgrade_context_for_model_inference(self):
        historical_df = pd.DataFrame([{
            "season": 2025,
            "round": 1,
            "driver_id": "driver_a",
            "constructor": "Ferrari",
            "circuit_id": "example",
            "finish_position": 4,
            "points": 12,
            "is_win": 0,
            "is_podium": 0,
            "is_top10": 1,
            "is_finished": 1,
            "grid": 5,
            "qualifying": 5,
            "sprint_position": 20,
            "avg_best_35pct_lap": 91.2,
            "lap_consistency": 0.4,
            "valid_laps": 55,
            "pit_stop_count": 1,
            "avg_pit_duration": 2.8,
            "min_pit_duration": 2.7,
        }])
        race = {
            "season": "2026",
            "round": "2",
            "Circuit": {"circuitId": "example"},
        }
        feature_columns = [
            "fia_upgrade_score",
            "fia_upgrade_count",
            "fia_upgrade_component_count",
            "fia_upgrade_trait_count",
            "fia_upgrade_aero_score",
            "fia_upgrade_cooling_score",
            "missing_fia_upgrade_data",
        ]
        upgrade_context = {
            "provider_status": "official_upgrade_data_used",
            "team_scores": {"Ferrari": 86.0},
            "team_traits": {"Ferrari": {"downforce": 1.0, "aero_efficiency": 1.0, "cooling": 1.0}},
            "notes": [
                {"team": "Ferrari", "component": "floor", "traits": ["downforce", "aero_efficiency"]},
                {"team": "Ferrari", "component": "sidepod", "traits": ["cooling"]},
            ],
        }

        rows = f1.build_prediction_feature_rows(
            [
                {"driver_id": "driver_a", "name": "Driver A", "team": "Ferrari", "position": 1},
                {"driver_id": "driver_b", "name": "Driver B", "team": "Mercedes", "position": 2},
            ],
            race,
            {},
            historical_df,
            feature_columns,
            upgrade_context=upgrade_context,
        )

        ferrari = rows[rows["constructor"] == "Ferrari"].iloc[0]
        mercedes = rows[rows["constructor"] == "Mercedes"].iloc[0]
        self.assertEqual(ferrari["fia_upgrade_score"], 86.0)
        self.assertEqual(ferrari["fia_upgrade_count"], 2)
        self.assertEqual(ferrari["fia_upgrade_component_count"], 2)
        self.assertGreaterEqual(ferrari["fia_upgrade_aero_score"], 2)
        self.assertEqual(ferrari["missing_fia_upgrade_data"], 0)
        self.assertEqual(mercedes["fia_upgrade_score"], 0)
        self.assertEqual(mercedes["missing_fia_upgrade_data"], 1)

    def test_upgrade_package_context_uses_cached_fia_documents_before_live_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            parsed_dir = cache_dir / "2026" / "austrian-grand-prix" / "parsed"
            parsed_dir.mkdir(parents=True)
            (parsed_dir / "doc-14-car-presentation-submissions.json").write_text(json.dumps({
                "document_type": "car_presentation_submissions",
                "source_url": "https://www.fia.com/documents/austria/doc-14",
                "upgrades": [
                    {
                        "team": "Ferrari",
                        "component": "floor",
                        "components": ["floor", "sidepod"],
                        "primary_reason_for_update": "performance",
                        "traits": ["downforce", "aero_efficiency", "cooling", "tyre_management"],
                        "source_url": "https://www.fia.com/documents/austria/doc-14",
                    }
                ],
            }), encoding="utf-8")
            race = {
                "season": "2026",
                "round": "10",
                "raceName": "Austrian Grand Prix",
                "Circuit": {"circuitName": "Red Bull Ring"},
            }
            drivers = [{"driver_id": "lec", "name": "Charles Leclerc", "team": "Ferrari"}]
            with patch.object(f1, "FIA_DOCUMENT_CACHE_DIR", cache_dir), \
                 patch.object(f1, "fetch_text_from_trusted_url", side_effect=AssertionError("live upgrade URL should not be used")):
                context = f1.fetch_upgrade_package_context(
                    race,
                    drivers,
                    profile={"dominance": "aero", "speed_profile": "medium", "tyre_stress": "high"},
                    weather_summary={"rain_score": 0, "heat_score": 65, "wind_score": 10},
                    regulation_context={"boost_traits": ["aero_efficiency", "cooling"]},
                )

        self.assertEqual(context["provider_status"], "official_upgrade_data_used")
        self.assertGreater(context["team_scores"]["Ferrari"], 40)
        self.assertEqual(context["source_status"], "verified_cache")
        self.assertTrue(context["notes"])

    def test_blocked_upgrade_url_is_attempted_once_and_then_skipped(self):
        response = f1.requests.Response()
        response.status_code = 403
        response.url = "https://www.fia.com/news/f1-tech-updates-austrian-grand-prix"
        response._content = b"Forbidden"
        with patch.object(f1.requests, "get", return_value=response) as get_mock, \
             patch.object(f1.time, "sleep") as sleep_mock:
            text = f1.fetch_text_from_trusted_url(response.url)

        self.assertIsNone(text)
        self.assertEqual(get_mock.call_count, 1)
        sleep_mock.assert_not_called()

    def test_daily_workflow_refreshes_fia_document_metadata_by_default(self):
        workflow = Path(".github/workflows/f1-briefing.yml").read_text(encoding="utf-8")
        self.assertIn("REFRESH_FIA_DOCUMENTS: ${{ github.event.inputs.refresh_fia_documents || 'true' }}", workflow)
        self.assertIn("FIA_DOCUMENTS_ENABLED: \"true\"", workflow)

    def test_fia_pirelli_preview_extracts_event_relative_compounds(self):
        text = """
        Compound
        C4
        C3
        C5
        Q3 tyre
        C5
        Mandatory race tyres
        C3
        C4
        """
        mapping = f1.extract_fia_tyre_compound_nomination(
            text,
            {"title": "Competition Notes - Pirelli Preview", "source_url": "https://www.fia.com/pirelli.pdf"},
        )

        self.assertEqual(mapping["status"], "available")
        self.assertEqual(mapping["mapping"], {"hard": "C3", "medium": "C4", "soft": "C5"})
        self.assertEqual(mapping["source"]["source_url"], "https://www.fia.com/pirelli.pdf")

    def test_fia_pirelli_preview_missing_compounds_does_not_default(self):
        mapping = f1.extract_fia_tyre_compound_nomination("Compound C3 Mandatory race tyres C3", {"title": "Pirelli Preview"})

        self.assertEqual(mapping["status"], "unavailable")
        self.assertIn("expected_exactly_three", mapping["reason"])

    def test_tyre_compound_code_uses_event_mapping_for_c_numbers_only_when_available(self):
        mapping = f1.extract_fia_tyre_compound_nomination("Compound C2 C3 C4 Q3 tyre C4", {"title": "Pirelli Preview"})

        self.assertEqual(f1.tyre_compound_code("C2", mapping), 3)
        self.assertEqual(f1.tyre_compound_code("C4", mapping), 1)
        self.assertEqual(f1.tyre_compound_code("C2"), 0)
        self.assertEqual(f1.tyre_compound_code("SOFT"), 1)

    def test_load_fia_tyre_mapping_reuses_cached_text_when_parsed_json_is_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            parsed_dir = cache_dir / "2026" / "austrian-grand-prix" / "parsed"
            text_dir = cache_dir / "2026" / "austrian-grand-prix" / "text"
            parsed_dir.mkdir(parents=True)
            text_dir.mkdir(parents=True)
            (parsed_dir / "doc-3-pirelli.json").write_text(json.dumps({
                "document_id": "doc-3",
                "document_type": "pirelli_preview",
                "source_url": "https://www.fia.com/austria-pirelli.pdf",
            }), encoding="utf-8")
            (text_dir / "doc-3-pirelli.txt").write_text("Compound C4 C3 C5 Q3 tyre C5", encoding="utf-8")
            with patch.object(f1, "FIA_DOCUMENT_CACHE_DIR", cache_dir):
                mapping = f1.load_fia_tyre_compound_mapping(2026, "austrian-grand-prix")

        self.assertEqual(mapping["status"], "available")
        self.assertEqual(mapping["mapping"]["hard"], "C3")
        self.assertEqual(mapping["mapping"]["soft"], "C5")

    def test_jolpica_cache_hit_does_not_sleep_or_fetch_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            url = "https://api.jolpi.ca/ergast/f1/2025/1/results.json"
            cache_path = cache_dir / f"{f1.cache_key_for_url(url, {})}.json"
            cache_path.write_text('{"MRData": {"RaceTable": {"Races": []}}}', encoding="utf-8")
            with patch.object(f1, "HTTP_CACHE_DIR", cache_dir), \
                 patch.object(f1.time, "sleep") as sleep_mock, \
                 patch.object(f1.requests, "get", side_effect=AssertionError("network should not be called")):
                response = f1.safe_get(url, use_cache=True, request_sleep=9.0)
            self.assertEqual(response.status_code, 200)
            sleep_mock.assert_not_called()

    def test_safe_get_honors_retry_after_and_atomic_json_cache(self):
        first = f1.requests.Response()
        first.status_code = 429
        first.headers["Retry-After"] = "0"
        first._content = b'{"detail":"rate limited"}'
        second = f1.requests.Response()
        second.status_code = 200
        second.headers["content-type"] = ""
        second._content = b'{"ok":true}'
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            url = "https://api.jolpi.ca/ergast/f1/2025.json"
            with patch.object(f1, "HTTP_CACHE_DIR", cache_dir), \
                 patch.object(f1.requests, "get", side_effect=[first, second]) as get_mock, \
                 patch.object(f1.time, "sleep") as sleep_mock:
                response = f1.safe_get(url, use_cache=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(get_mock.call_count, 2)
            sleep_mock.assert_any_call(0.0)
            self.assertTrue((cache_dir / f"{f1.cache_key_for_url(url, {})}.json").exists())

    def test_safe_get_optional_forbidden_returns_none_without_retries(self):
        response = f1.requests.Response()
        response.status_code = 403
        response._content = b"Forbidden"
        url = "https://www.fia.com/documents/example"
        with patch.object(f1.requests, "get", return_value=response) as get_mock, \
             patch.object(f1.time, "sleep") as sleep_mock:
            result = f1.safe_get(url, optional_404=True, use_cache=False)
        self.assertIsNone(result)
        self.assertEqual(get_mock.call_count, 1)
        sleep_mock.assert_not_called()

    def test_cache_key_uses_hash_not_sluggable_url(self):
        key_a = f1.cache_key_for_url("https://example.test/path", {"offset": 0, "limit": 100})
        key_b = f1.cache_key_for_url("https://example.test/path", {"offset": 100, "limit": 100})
        self.assertRegex(key_a, r"^[0-9a-f]{32}$")
        self.assertNotEqual(key_a, key_b)

    def test_jolpica_lap_pagination_fetches_all_offsets(self):
        pages = [
            {
                "MRData": {
                    "total": "101",
                    "offset": "0",
                    "limit": "100",
                    "RaceTable": {"Races": [{"season": "2025", "round": "1", "raceName": "Race", "Laps": [{"number": "1"}]}]},
                }
            },
            {
                "MRData": {
                    "total": "101",
                    "offset": "100",
                    "limit": "100",
                    "RaceTable": {"Races": [{"season": "2025", "round": "1", "raceName": "Race", "Laps": [{"number": "101"}]}]},
                }
            },
        ]
        with patch.object(f1, "jolpica_get", side_effect=pages) as get_mock:
            races = f1.jolpica_laps_races(2025, 1)
        self.assertEqual([lap["number"] for lap in races[0]["Laps"]], ["1", "101"])
        self.assertEqual(get_mock.call_args_list[0].kwargs["params"]["offset"], 0)
        self.assertEqual(get_mock.call_args_list[1].kwargs["params"]["offset"], 100)

    def test_grid_zero_is_pit_lane_not_qualifying_fallback(self):
        race = {
            "raceName": "Example Grand Prix",
            "Circuit": {"circuitId": "example", "circuitName": "Example Circuit"},
            "date": "2025-05-04",
            "time": "12:00:00Z",
        }
        data = {
            "results": [{
                "Results": [
                    {
                        "positionOrder": "1",
                        "grid": "0",
                        "points": "25",
                        "status": "Finished",
                        "Driver": {"driverId": "driver_a", "givenName": "Driver", "familyName": "A"},
                        "Constructor": {"name": "Team A"},
                    },
                    {
                        "positionOrder": "2",
                        "grid": "1",
                        "points": "18",
                        "status": "Finished",
                        "Driver": {"driverId": "driver_b", "givenName": "Driver", "familyName": "B"},
                        "Constructor": {"name": "Team B"},
                    },
                ]
            }],
            "qualifying": [{
                "QualifyingResults": [
                    {"position": "5", "Driver": {"driverId": "driver_a"}},
                    {"position": "1", "Driver": {"driverId": "driver_b"}},
                ]
            }],
            "sprint": [],
            "laps": [],
            "pitstops": [],
        }
        rows = f1.result_rows_from_race_data(2025, 1, race, data)
        self.assertEqual(rows[0]["grid"], 3)

    def test_score_position_uses_dynamic_field_size(self):
        self.assertEqual(f1.score_position(22, field_size=22), 0.0)
        self.assertEqual(f1.score_position(24, field_size=24), 0.0)
        self.assertGreater(f1.score_position(12, field_size=24), f1.score_position(12, field_size=20))

    def test_regulation_era_factor_is_monotonic_across_eras(self):
        values = [f1.regulation_era_factor(year) for year in [2021, 2022, 2025, 2026, 2027]]
        self.assertEqual(values, sorted(values))

    def test_constructor_alias_normalization_preserves_cross_season_form(self):
        self.assertEqual(f1.canonical_constructor_name("Mercedes-AMG Petronas F1 Team"), "Mercedes")
        self.assertEqual(f1.canonical_constructor_name("MoneyGram Haas F1 Team"), "Haas")
        self.assertEqual(f1.canonical_constructor_name("Renault"), "Alpine")
        self.assertEqual(f1.canonical_constructor_name("Force India"), "Aston Martin")

    def test_weighted_average_reports_completeness_penalty(self):
        raw, coverage = f1.weighted_average_with_coverage([(100, 1), (None, 3)])
        penalized = f1.weighted_average_penalized([(100, 1), (None, 3)], neutral=0)
        self.assertEqual(raw, 100)
        self.assertAlmostEqual(coverage, 0.25)
        self.assertLess(penalized, raw)

    def test_feature_hash_is_stable_and_order_sensitive(self):
        self.assertEqual(f1.feature_columns_hash(["a", "b"]), f1.feature_columns_hash(["a", "b"]))
        self.assertNotEqual(f1.feature_columns_hash(["a", "b"]), f1.feature_columns_hash(["b", "a"]))

    def test_frontend_timing_route_has_rate_limit_guard(self):
        route = Path("frontend/app/api/f1timing/route.js").read_text(encoding="utf-8")
        self.assertIn("F1_TIMING_RATE_LIMIT_MS", route)
        self.assertIn("Timing endpoint rate limit exceeded", route)
        self.assertIn("const normalizedJolpica = normalizeJolpicaFallback(jolpicaFallback)", route)
        self.assertIn("normalizedOpenF1 || normalizedJolpica || normalized", route)

    def test_mobile_driver_drawer_is_viewport_fixed_bottom_sheet(self):
        css = Path("frontend/app/globals.css").read_text(encoding="utf-8")
        component = Path("frontend/app/components/PitWallComponents.jsx").read_text(encoding="utf-8")
        self.assertIn("position: fixed", css)
        self.assertIn("bottom: 0", css)
        self.assertIn("88dvh", css)
        self.assertIn("env(safe-area-inset-bottom)", css)
        self.assertIn('document.body.style.overflow = "hidden"', component)

    def test_predictions_page_uses_selected_target_payload(self):
        page = Path("frontend/app/predictions/page.jsx").read_text(encoding="utf-8")
        self.assertIn("selectedPayload", page)
        self.assertIn("selectedPayload.fia_document_count", page)
        self.assertIn("selectedPayload.timing_mode", page)

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

    def test_single_feature_leakage_diagnostic_flags_extreme_collapse(self):
        class LeakModel:
            def predict_proba(self, matrix):
                p = matrix["leak"].astype(float).to_numpy()
                return pd.DataFrame({0: 1 - p, 1: p}).to_numpy()

        valid_df = pd.DataFrame({"is_win": [0, 0, 0, 0, 1, 1, 1, 1, 1, 1]})
        valid_matrix = pd.DataFrame({
            "leak": valid_df["is_win"].astype(float),
            "noise": [0.4, 0.2, 0.6, 0.3, 0.5, 0.8, 0.1, 0.7, 0.9, 0.0],
        })
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"PITWALL_CI": "false"}):
            path = Path(tmp) / "leakage.json"
            report = f1.run_single_feature_leakage_diagnostic(
                {"rf": LeakModel()},
                valid_matrix,
                valid_df,
                ["leak", "noise"],
                top_n=2,
                threshold=0.2,
                output_path=path,
            )
            self.assertTrue(path.exists())

        self.assertEqual(report["status"], "flagged")
        self.assertEqual(report["flagged"][0]["feature"], "leak")

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

    def test_normalized_prediction_contract_exposes_race_intelligence_shape(self):
        entry = {
            "title": "Example Grand Prix",
            "race_name": "Example Grand Prix",
            "season": 2026,
            "round": 1,
            "stage": "pre_race",
            "target_type": "race",
            "generated_iso": "2026-05-25T00:00:00+00:00",
            "weather": {"rain_score": 35, "rain_probability": 0.35},
            "tyre_stress": "high",
            "overtaking": "low",
            "safety_car": "high",
            "top10": [
                {
                    "driver_id": "driver_a",
                    "name": "Driver A",
                    "team": "Mercedes-AMG Petronas F1 Team",
                    "rank": 1,
                    "score": 82,
                    "confidence": 71,
                    "component_scores": {
                        "ml_win_probability": 38,
                        "ml_podium_probability": 75,
                        "ml_top10_probability": 98,
                        "reliability": 78,
                        "qualifying": 82,
                        "race_pace": 84,
                        "team_strategy": 63,
                        "pit_execution": 70,
                    },
                }
            ],
            "full_grid": [
                {
                    "driver_id": "driver_a",
                    "name": "Driver A",
                    "team": "Mercedes-AMG Petronas F1 Team",
                    "rank": 1,
                    "score": 82,
                    "confidence": 71,
                    "component_scores": {
                        "ml_win_probability": 38,
                        "ml_podium_probability": 75,
                        "ml_top10_probability": 98,
                        "reliability": 78,
                        "qualifying": 82,
                        "race_pace": 84,
                        "team_strategy": 63,
                        "pit_execution": 70,
                    },
                },
                {
                    "driver_id": "driver_b",
                    "name": "Driver B",
                    "team": "Ferrari",
                    "rank": 2,
                    "score": 74,
                    "confidence": 64,
                    "component_scores": {
                        "ml_win_probability": 24,
                        "ml_podium_probability": 58,
                        "ml_top10_probability": 93,
                        "reliability": 69,
                        "qualifying": 74,
                        "race_pace": 75,
                        "team_strategy": 55,
                        "pit_execution": 61,
                    },
                },
            ],
        }

        normalized = f1.normalize_entry_contract(entry)
        row = normalized["full_grid"][0]

        self.assertIn("top_10", normalized)
        self.assertEqual(normalized["top_10"], normalized["top10"])
        self.assertIn("race_factors", normalized)
        self.assertIn("warnings", normalized)
        for key in [
            "points_probability",
            "fastest_lap_probability",
            "dnf_probability",
            "position_range",
            "expected_strategy",
            "explanation",
            "data_freshness",
            "source_notes",
        ]:
            self.assertIn(key, row)
        self.assertIn("pace", row["explanation"])
        self.assertIn("strategy", row["explanation"])
        self.assertEqual(row["position_range"], [row["best_case_finish"], row["worst_case_finish"]])

    def test_strategy_context_annotations_detect_weather_tyre_mismatch(self):
        annotations = f1.detect_strategy_context_annotations(
            {
                "starting_compound": "INTERMEDIATE",
                "first_pit_lap": 4,
                "post_switch_pace_delta": -0.42,
                "pit_context": "normal",
            },
            {
                "rainfall_actual": 0,
                "rain_probability": 0.68,
                "track_status_events": [],
            },
        )

        labels = {item["label"] for item in annotations}
        self.assertIn("wrong_starting_tyre_for_actual_weather", labels)
        self.assertIn("early_tyre_correction", labels)
        self.assertIn("competitive_after_compound_switch", labels)

    def test_predictions_page_renders_top10_and_full_grid_sections(self):
        page = Path("frontend/app/predictions/page.jsx").read_text(encoding="utf-8")
        self.assertIn("top10Rows", page)
        self.assertIn("fullGridRows", page)
        self.assertIn("Top 10 Prediction", page)
        self.assertIn("Full Grid Prediction", page)
        self.assertIn("Race Overview", page)

    def test_model_and_archive_pages_render_comparison_sections(self):
        model_page = Path("frontend/app/model/page.jsx").read_text(encoding="utf-8")
        model_client = Path("frontend/app/model/ModelCenterClient.jsx").read_text(encoding="utf-8")
        archive_page = Path("frontend/app/archive/page.jsx").read_text(encoding="utf-8")
        self.assertIn("loadPredictionsPayload", model_page)
        self.assertIn("Actual Result Comparison", model_client)
        self.assertIn("Model Comparison Metrics", model_client)
        self.assertIn("actual_result_comparison", archive_page)
        self.assertIn("Top 10 Recall", archive_page)

    def test_training_summary_has_visible_output_labels(self):
        lines = f1.training_summary_lines({
            "cache_reused": 2,
            "cache_refreshed": 1,
            "training_races": 10,
            "validation_races": 2,
            "feature_columns": 42,
            "promotion": "accepted",
        })
        text = "\n".join(lines)
        self.assertIn("PitWall training summary", text)
        self.assertIn("Cache reused: 2 files", text)
        self.assertIn("Promotion: accepted", text)

    def test_driver_detail_drawer_is_scrollable_and_rich(self):
        css = Path("frontend/app/globals.css").read_text(encoding="utf-8")
        component = Path("frontend/app/components/PitWallComponents.jsx").read_text(encoding="utf-8")
        self.assertIn("overflow-y: auto", css)
        self.assertIn("-webkit-overflow-scrolling: touch", css)
        self.assertIn("driver-detail-content", component)
        self.assertIn("Fastest lap", component)
        self.assertIn("Expected strategy", component)
        self.assertIn("Source notes", component)

    def test_f1timing_route_exposes_auto_selection_metadata(self):
        route = Path("frontend/app/api/f1timing/route.js").read_text(encoding="utf-8")
        self.assertIn("auto_selected_session", route)
        self.assertIn("session_resolution", route)
        self.assertIn("warnings", route)
        self.assertIn("safeNormalizedTimingPayload", route)

    def test_f1timing_uses_self_hosted_track_visuals(self):
        route = Path("frontend/app/api/f1timing/route.js").read_text(encoding="utf-8")
        self.assertIn('image_url: "/pitwall-hero.svg"', route)
        self.assertIn('source: "PitWall self-hosted visual"', route)
        self.assertIn("page_url: pageUrl", route)
        self.assertNotIn("media.formula1.com", route)

    def test_extracted_modules_preserve_public_wrapper_outputs(self):
        simulation = importlib.import_module("pitwall.models.simulation")
        strategy = importlib.import_module("pitwall.features.strategy")
        rows = [
            {"driver_id": "a", "rank": 1, "score": 82, "reliability": 88, "top10_probability": 96},
            {"driver_id": "b", "rank": 2, "score": 76, "reliability": 82, "top10_probability": 91},
            {"driver_id": "c", "rank": 3, "score": 64, "reliability": 69, "top10_probability": 80},
        ]

        self.assertEqual(
            f1.simulate_race_outcomes(rows, runs=50, seed=7),
            simulation.simulate_race_outcomes(rows, runs=50, seed=7),
        )
        self.assertEqual(f1.confidence_label(73), simulation.confidence_label(73))
        strategy_context = {"starting_compound": "INTERMEDIATE", "first_pit_lap": 4}
        weather_context = {"rainfall_actual": 0, "rain_probability": 0.7}
        self.assertEqual(
            f1.detect_strategy_context_annotations(strategy_context, weather_context),
            strategy.detect_strategy_context_annotations(strategy_context, weather_context),
        )

    def test_fia_pdf_403_uses_cached_text_without_retry_storm(self):
        with tempfile.TemporaryDirectory() as tmp:
            text_path = Path(tmp) / "doc.txt"
            parsed_path = Path(tmp) / "doc.json"
            pdf_path = Path(tmp) / "doc.pdf"
            text_path.write_text("cached official FIA text", encoding="utf-8")
            response = f1.requests.Response()
            response.status_code = 403
            response._content = b"forbidden"
            with patch.object(f1.requests, "get", return_value=response) as get_mock:
                result = f1.fetch_fia_document_text(
                    {"source_url": "https://www.fia.com/system/files/decision-document/example.pdf"},
                    text_path,
                    parsed_path,
                    pdf_path,
                )

        self.assertEqual(get_mock.call_count, 1)
        self.assertEqual(result["parse_status"], "stale_cache_forbidden")
        self.assertEqual(result["text"], "cached official FIA text")
        self.assertEqual(result["http_status"], 403)

    def test_fia_pdf_403_without_cache_is_marked_forbidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            response = f1.requests.Response()
            response.status_code = 403
            response._content = b"forbidden"
            with patch.object(f1.requests, "get", return_value=response) as get_mock:
                result = f1.fetch_fia_document_text(
                    {"source_url": "https://www.fia.com/system/files/decision-document/example.pdf"},
                    Path(tmp) / "missing.txt",
                    Path(tmp) / "missing.json",
                    Path(tmp) / "missing.pdf",
                )

        self.assertEqual(get_mock.call_count, 1)
        self.assertEqual(result["parse_status"], "forbidden")
        self.assertIsNone(result["text"])
        self.assertIn("403", result["error"])

    def test_fia_season_index_success_writes_cache_without_model_context(self):
        html = """
        <html><body>
          <h2>Example Grand Prix</h2>
          <a href="/system/files/decision-document/2026_example_doc_01.pdf">Document 1 - Decision</a>
        </body></html>
        """
        response = f1.requests.Response()
        response.status_code = 200
        response._content = html.encode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "fia-documents"
            registry = {"fia_season_document_url": "https://www.fia.com/documents/example-season"}
            with patch.object(f1, "FIA_DOCUMENT_CACHE_DIR", cache_dir), \
                 patch.object(f1, "FIA_DOCUMENTS_ENABLED", True), \
                 patch.object(f1, "REFRESH_FIA_DOCUMENTS", False), \
                 patch.object(f1, "FIA_DOCUMENT_CACHE_TTL_MINUTES", 0), \
                 patch.object(f1, "safe_get", return_value=response):
                payload = f1.fetch_fia_season_index(2026, registry=registry, refresh=True)

            self.assertEqual(payload["status"], "available")
            self.assertEqual(len(payload["documents"]), 1)
            self.assertEqual(payload["documents"][0]["source_url"], "https://www.fia.com/system/files/decision-document/2026_example_doc_01.pdf")
            cached = json.loads((cache_dir / "2026" / "season_index.json").read_text(encoding="utf-8"))
            self.assertEqual(cached["documents"][0]["source_url"], payload["documents"][0]["source_url"])

    def test_issue_notification_labels_and_auto_closes(self):
        calls = []

        def fake_github_api(method, endpoint, payload=None):
            calls.append((method, endpoint, payload))
            if method == "GET":
                return []
            if method == "POST" and endpoint == "/issues":
                return {"number": 42}
            return {}

        with patch.object(f1, "github_api", side_effect=fake_github_api), \
             patch.object(f1, "BRIEFING_NOTIFICATION_AUTO_CLOSE_ISSUES", True):
            f1.create_or_update_issue("PitWall Briefing", "body")

        issue_posts = [payload for method, endpoint, payload in calls if method == "POST" and endpoint == "/issues"]
        self.assertEqual(issue_posts[0]["labels"], ["f1-briefing", "briefing-notification"])
        self.assertIn(("PATCH", "/issues/42", {"state": "closed", "state_reason": "completed"}), calls)

    def test_notification_target_none_skips_github_api(self):
        with patch.object(f1, "BRIEFING_NOTIFICATION_TARGET", "none"), \
             patch.object(f1, "github_api", side_effect=AssertionError("github should not be called")):
            self.assertIsNone(f1.publish_github_notification("title", "body"))

    def test_strategy_context_builder_uses_pit_weather_race_control_and_pace(self):
        strategy = importlib.import_module("pitwall.features.strategy")
        context = strategy.build_strategy_context_for_driver(
            "driver_a",
            pitstops=[
                {"driverId": "driver_a", "lap": "4", "duration": "4.2"},
                {"driverId": "driver_b", "lap": "20", "duration": "2.4"},
            ],
            stints=[{"driver_id": "driver_a", "compound": "INTERMEDIATE", "stint_number": 1}],
            race_control=[{"lap_number": 4, "message": "SAFETY CAR DEPLOYED"}],
            weather={"rainfall_actual": 0, "rain_probability": 0.68},
            lap_metrics={"post_switch_pace_delta": -0.34, "degradation_slope": 0.18},
        )

        labels = {item["label"] for item in context["annotations"]}
        self.assertEqual(context["first_pit_lap"], 4)
        self.assertEqual(context["starting_compound"], "INTERMEDIATE")
        self.assertIn("early_tyre_correction", labels)
        self.assertIn("wrong_starting_tyre_for_actual_weather", labels)
        self.assertIn("safety_car_aided_stop", labels)
        self.assertIn("competitive_after_compound_switch", labels)
        self.assertIn("degradation_cliff", labels)

    def test_dataset_bootstrap_plans_are_dry_run_and_no_download_by_default(self):
        bootstrap = importlib.import_module("pitwall.data.bootstrap")
        with tempfile.TemporaryDirectory() as tmp:
            f1db_plan = bootstrap.dataset_bootstrap_plan("f1db", base_dir=Path(tmp), dry_run=True)
            relbench_plan = bootstrap.dataset_bootstrap_plan("relbench", base_dir=Path(tmp), dry_run=True)

        self.assertTrue(f1db_plan["dry_run"])
        self.assertEqual(f1db_plan["source"], "f1db")
        self.assertIn("F1DB_SQLITE_PATH", f1db_plan["env"])
        self.assertTrue(relbench_plan["dry_run"])
        self.assertEqual(relbench_plan["source"], "relbench")
        self.assertFalse(relbench_plan["will_download"])

    def test_f1db_adapter_reports_disabled_without_downloading(self):
        with patch.dict(os.environ, {"F1DB_ENABLED": "false", "F1DB_SQLITE_PATH": "", "F1DB_CSV_DIR": ""}, clear=False):
            status = f1db.f1db_status()
        self.assertEqual(status["source_name"], "F1DB")
        self.assertFalse(status["available"])
        self.assertEqual(status["license"], "CC-BY-4.0")
        self.assertIn("v2026.4.2", f1db.f1db_metadata()["latest_verified_release"])

    def test_f1db_adapter_reads_local_sqlite_circuits(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f1db.sqlite"
            with sqlite3.connect(path) as conn:
                conn.execute("CREATE TABLE circuits (id INTEGER, ref TEXT, name TEXT, country TEXT, locality TEXT, latitude REAL, longitude REAL)")
                conn.execute("INSERT INTO circuits VALUES (1, 'monza', 'Autodromo Nazionale Monza', 'Italy', 'Monza', 45.62, 9.28)")
                conn.commit()
            with patch.dict(os.environ, {"F1DB_ENABLED": "true", "F1DB_SQLITE_PATH": str(path), "F1DB_CSV_DIR": ""}, clear=False):
                status = f1db.f1db_status()
                rows = f1db.read_circuits()
        self.assertTrue(status["available"])
        self.assertEqual(rows[0]["circuit_ref"], "monza")
        self.assertEqual(rows[0]["source"], "F1DB")

    def test_relbench_adapter_is_offline_optional(self):
        with patch.dict(os.environ, {"RELBENCH_F1_ENABLED": "false"}, clear=False):
            status = relbench_f1.relbench_status(download=False)
        self.assertEqual(status["source_name"], "RelBench rel-f1")
        self.assertFalse(status["available"])
        self.assertIn("driver-top3", relbench_f1.relbench_metadata()["tasks"])

    def test_model_artifacts_export_from_existing_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(f1, "MODEL_ARTIFACTS_DIR", Path(tmp)):
                artifacts = f1.write_model_artifacts()
                self.assertIn("evaluation.json", artifacts)
                evaluation_path = Path(tmp) / "evaluation.json"
                self.assertTrue(evaluation_path.exists())
                evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
                self.assertIn("dataset_sources", evaluation)
                self.assertIn("drift_monitor", evaluation)

    def test_auto_commit_is_env_gated(self):
        source = Path("f1_briefing.py").read_text(encoding="utf-8")
        self.assertIn('os.getenv("AUTO_COMMIT_ENABLED", "false")', source)
        self.assertIn("Auto commit disabled", source)

    def test_public_path_sanitizer_strips_workspace_prefix(self):
        absolute = str(Path.cwd() / "data_cache" / "frontend-contract.json")
        self.assertEqual(f1.public_path(absolute), "data_cache/frontend-contract.json")

    def test_session_timeline_stage_sanitizer_marks_ingested_session(self):
        timeline = [
            {"session_type": "fp1", "status": "waiting_for_api_data"},
            {"session_type": "qualifying", "status": "waiting_for_api_data"},
            {"session_type": "race", "status": "scheduled"},
        ]
        sanitized = f1.sanitize_session_timeline_for_stage(timeline, "post_qualifying")
        state = f1.session_contract_state(sanitized)
        self.assertEqual(state["last_ingested_session"]["session_type"], "qualifying")
        self.assertEqual(state["next_session_to_ingest"]["session_type"], "race")
        self.assertEqual(state["session_data_delay_status"], "clear")

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

    def test_actual_result_comparison_uses_cached_completed_race_results(self):
        def cached_round(seed):
            results = []
            for idx in range(1, 23):
                results.append({
                    "positionOrder": str(idx),
                    "position": str(idx),
                    "points": str(max(0, 26 - idx)),
                    "status": "Finished",
                    "Driver": {
                        "driverId": f"{seed}_driver_{idx:02d}",
                        "givenName": f"{seed.title()}",
                        "familyName": f"Driver {idx:02d}",
                    },
                    "Constructor": {"name": f"Fixture Team {((idx - 1) // 2) + 1}"},
                })
            return {
                "source": "jolpica_api",
                "status": "final_results_available",
                "data": {"results": [{"Results": results}]},
            }

        cached_results = {
            6: cached_round("round6"),
            5: cached_round("round5"),
        }

        with patch.object(f1, "read_full_race_cache", side_effect=lambda _season, round_no: cached_results.get(int(round_no))):
            round6_actual = f1.actual_result_from_cached_round(2026, 6, "race")
            round5_actual = f1.actual_result_from_cached_round(2026, 5, "race")

        self.assertIsNotNone(round6_actual)
        self.assertIsNotNone(round5_actual)
        self.assertEqual(round6_actual["winner"]["driver_id"], round6_actual["classification"][0]["driver_id"])
        self.assertEqual(round5_actual["winner"]["driver_id"], round5_actual["classification"][0]["driver_id"])
        self.assertGreaterEqual(len(round6_actual["classification"]), 20)
        self.assertGreaterEqual(len(round5_actual["classification"]), 20)

        comparison = f1.actual_result_comparison_for_entry(
            {
                "season": 2026,
                "round": 6,
                "target_type": "race",
                "race_name": "Fixture Grand Prix",
                "actual_result": round6_actual,
            },
            [{
                "driver_id": round6_actual["winner"]["driver_id"],
                "name": round6_actual["winner"]["name"],
                "rank": 1,
                "predicted_position": 1,
            }],
        )
        self.assertEqual(comparison["status"], "available")
        self.assertTrue(comparison["winner_hit"])
        self.assertEqual(comparison["actual_winner"]["driver_id"], round6_actual["winner"]["driver_id"])

    def test_empty_completed_refresh_preserves_existing_final_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cached_data = {
                "results": [{
                    "Results": [{
                        "positionOrder": "1",
                        "position": "1",
                        "points": "25",
                        "status": "Finished",
                        "Driver": {"driverId": "cached_driver", "givenName": "Cached", "familyName": "Driver"},
                        "Constructor": {"name": "Cached Team"},
                    }]
                }],
                "qualifying": [],
                "pitstops": [],
                "laps": [],
                "sprint": [],
                "sprint_qualifying": [],
            }
            race = {
                "season": "2026",
                "round": "99",
                "raceName": "Synthetic Past Grand Prix",
                "date": "2026-01-01",
                "time": "12:00:00Z",
            }
            payload = {
                "season": 2026,
                "round": "99",
                "status": "final_results_available",
                "data": cached_data,
            }
            with patch.object(f1, "FULL_RACE_CACHE_DIR", Path(tmp)), patch.object(f1, "CACHE_AWARE_DOWNLOADS", False):
                f1.write_full_race_cache(2026, 99, payload)
                with patch.object(f1, "fetch_round_data_direct", return_value={"results": []}):
                    data = f1.fetch_round_data_cached(
                        2026,
                        99,
                        race=race,
                        training_mode=True,
                        force_fetch=True,
                    )
        self.assertEqual(data["results"][0]["Results"][0]["Driver"]["driverId"], "cached_driver")

    def test_actual_result_comparison_fetches_completed_race_from_api_when_cache_missing(self):
        completed_race = {
            "season": "2026",
            "round": "8",
            "raceName": "Example Grand Prix",
            "date": "2026-06-01",
            "time": "13:00:00Z",
        }
        api_payload = {
            "results": [{
                "Results": [{
                    "Driver": {"driverId": "api_driver", "givenName": "API", "familyName": "Driver"},
                    "Constructor": {"name": "API Team"},
                    "positionOrder": "1",
                    "position": "1",
                    "status": "Finished",
                    "points": "25",
                }]
            }]
        }

        with patch.object(f1, "read_full_race_cache", return_value=None), \
             patch.object(f1, "fetch_round_data_cached", return_value=api_payload) as fetch_mock, \
             patch.object(f1, "now_local", return_value=f1.datetime(2026, 6, 3, 12, 0, tzinfo=f1.USER_TIMEZONE)):
            comparison = f1.actual_result_comparison_for_entry(
                {
                    "season": 2026,
                    "round": 8,
                    "target_type": "race",
                    "race_name": "Example Grand Prix",
                    "jolpica_race": completed_race,
                },
                [{"driver_id": "api_driver", "name": "API Driver", "rank": 1, "predicted_position": 1}],
            )

        fetch_mock.assert_called_once()
        self.assertEqual(comparison["status"], "available")
        self.assertEqual(comparison["actual_winner"]["driver_id"], "api_driver")

    def test_actual_result_comparison_refreshes_unmarked_cache_after_cutoff(self):
        completed_race = {
            "season": "2026",
            "round": "8",
            "raceName": "Example Grand Prix",
            "date": "2026-06-01",
            "time": "13:00:00Z",
        }
        unmarked_cache = {
            "status": "final_results_available",
            "data": {
                "results": [{
                    "Results": [{
                        "Driver": {"driverId": "stale_driver", "givenName": "Stale", "familyName": "Driver"},
                        "Constructor": {"name": "Stale Team"},
                        "positionOrder": "1",
                        "position": "1",
                    }]
                }]
            },
        }
        api_payload = {
            "results": [{
                "Results": [{
                    "Driver": {"driverId": "api_driver", "givenName": "API", "familyName": "Driver"},
                    "Constructor": {"name": "API Team"},
                    "positionOrder": "1",
                    "position": "1",
                }]
            }]
        }

        with patch.object(f1, "read_full_race_cache", return_value=unmarked_cache), \
             patch.object(f1, "fetch_round_data_cached", return_value=api_payload) as fetch_mock, \
             patch.object(f1, "now_local", return_value=f1.datetime(2026, 6, 3, 12, 0, tzinfo=f1.USER_TIMEZONE)):
            comparison = f1.actual_result_comparison_for_entry(
                {
                    "season": 2026,
                    "round": 8,
                    "target_type": "race",
                    "race_name": "Example Grand Prix",
                    "jolpica_race": completed_race,
                },
                [{"driver_id": "api_driver", "name": "API Driver", "rank": 1, "predicted_position": 1}],
            )

        fetch_mock.assert_called_once()
        self.assertEqual(comparison["status"], "available")
        self.assertEqual(comparison["actual_winner"]["driver_id"], "api_driver")

    def test_normalized_contract_recomputes_stale_pending_actuals_after_cutoff(self):
        completed_race = {
            "season": "2026",
            "round": "7",
            "raceName": "Example Completed Grand Prix",
            "date": "2026-06-14",
            "time": "13:00:00Z",
        }
        stale_cache = {
            "status": "future_or_partial",
            "data": {"results": [], "qualifying": [], "pitstops": [], "laps": [], "sprint": [], "sprint_qualifying": []},
        }
        api_payload = {
            "results": [{
                "Results": [{
                    "Driver": {"driverId": "api_driver", "givenName": "API", "familyName": "Driver"},
                    "Constructor": {"name": "API Team"},
                    "positionOrder": "1",
                    "position": "1",
                    "status": "Finished",
                    "points": "25",
                }]
            }]
        }
        entry = {
            "season": 2026,
            "round": 7,
            "race_name": "Example Completed Grand Prix",
            "title": "Example Completed Grand Prix",
            "target_type": "race",
            "stage": "post_race",
            "jolpica_race": completed_race,
            "top10": [{"driver_id": "api_driver", "name": "API Driver", "rank": 1, "score": 95}],
            "actual_result_comparison": f1.pitwall_default_actual_result_comparison(
                status="pending",
                race={"season": 2026, "round": 7, "race_name": "Example Completed Grand Prix"},
            ),
        }

        with patch.object(f1, "read_full_race_cache", return_value=stale_cache), \
             patch.object(f1, "fetch_round_data_cached", return_value=api_payload) as fetch_mock, \
             patch.object(f1, "now_local", return_value=f1.datetime(2026, 6, 15, 12, 0, tzinfo=f1.USER_TIMEZONE)):
            normalized = f1.normalize_entry_contract(entry)

        fetch_mock.assert_called_once()
        self.assertEqual(normalized["actual_result"]["winner"]["driver_id"], "api_driver")
        self.assertEqual(normalized["actual_result_comparison"]["status"], "available")
        self.assertTrue(normalized["actual_result_comparison"]["winner_hit"])
        self.assertEqual(normalized["actual_result_comparison"]["actual_winner"]["driver_id"], "api_driver")

    def test_training_rows_include_completed_monaco_and_skip_pending_barcelona(self):
        monaco = {
            "season": "2026",
            "round": "6",
            "raceName": "Monaco Grand Prix",
            "date": "2026-06-07",
            "time": "13:00:00Z",
            "Circuit": {"circuitId": "monaco", "circuitName": "Circuit de Monaco"},
        }
        barcelona = {
            "season": "2026",
            "round": "7",
            "raceName": "Barcelona Grand Prix",
            "date": "2026-06-14",
            "time": "13:00:00Z",
            "Circuit": {"circuitId": "catalunya", "circuitName": "Circuit de Barcelona-Catalunya"},
        }
        fixed_now = f1.datetime(2026, 6, 9, 12, 0, tzinfo=f1.USER_TIMEZONE)

        with patch.object(f1, "fetch_schedule", return_value=[monaco, barcelona]), \
             patch.object(f1, "now_local", return_value=fixed_now), \
             patch.object(f1, "record_full_race_cache_manifest"):
            rows = f1.collect_race_rows(2026, 2026)

        self.assertIn("2026-6", set(rows["race_id"]))
        self.assertNotIn("2026-7", set(rows["race_id"]))
        monaco_rows = rows[rows["race_id"] == "2026-6"]
        self.assertGreaterEqual(len(monaco_rows), 20)
        self.assertEqual(monaco_rows.sort_values("finish_position").iloc[0]["finish_position"], 1)

    def test_training_cache_respects_final_result_cutoff_before_using_cached_actuals(self):
        barcelona = {
            "season": "2026",
            "round": "7",
            "raceName": "Barcelona Grand Prix",
            "date": "2026-06-14",
            "time": "13:00:00Z",
            "Circuit": {"circuitId": "catalunya", "circuitName": "Circuit de Barcelona-Catalunya"},
        }
        cached_actual = {
            "status": "final_results_available",
            "data": {
                "results": [{
                    "Results": [{
                        "Driver": {"driverId": "cached_driver", "givenName": "Cached", "familyName": "Driver"},
                        "Constructor": {"name": "Cached Team"},
                        "positionOrder": "1",
                        "position": "1",
                        "grid": "1",
                        "status": "Finished",
                        "points": "25",
                    }]
                }]
            },
        }

        before_cutoff = f1.datetime(2026, 6, 9, 12, 0, tzinfo=f1.USER_TIMEZONE)
        after_cutoff = f1.datetime(2026, 6, 15, 12, 0, tzinfo=f1.USER_TIMEZONE)

        with patch.object(f1, "read_full_race_cache", return_value=cached_actual), \
             patch.object(f1, "record_full_race_cache_manifest"), \
             patch.object(f1, "now_local", return_value=before_cutoff):
            self.assertEqual(f1.fetch_round_data_cached(2026, "7", race=barcelona, training_mode=True), {})

        with patch.object(f1, "read_full_race_cache", return_value=cached_actual), \
             patch.object(f1, "record_full_race_cache_manifest"), \
             patch.object(f1, "now_local", return_value=after_cutoff):
            data = f1.fetch_round_data_cached(2026, "7", race=barcelona, training_mode=True)

        self.assertTrue(f1.race_has_results(data))

    def test_training_refreshes_stale_completed_cache_even_when_backfill_budget_is_zero(self):
        completed_race = {
            "season": "2026",
            "round": "7",
            "raceName": "Example Completed Grand Prix",
            "date": "2026-06-14",
            "time": "13:00:00Z",
            "Circuit": {"circuitId": "example", "circuitName": "Example Circuit"},
        }
        api_results = []
        for idx in range(1, 23):
            api_results.append({
                "Driver": {"driverId": f"driver_{idx}", "givenName": "Driver", "familyName": str(idx)},
                "Constructor": {"name": "Example Team"},
                "positionOrder": str(idx),
                "position": str(idx),
                "grid": str(idx),
                "status": "Finished",
                "points": str(max(0, 26 - idx)),
            })
        api_payload = {
            "results": [{"Results": api_results}],
            "qualifying": [],
            "pitstops": [],
            "laps": [],
            "sprint": [],
            "sprint_qualifying": [],
        }
        stale_payload = {
            "season": 2026,
            "round": "7",
            "source": "jolpica_api",
            "status": "future_or_partial",
            "data": {"results": [], "qualifying": [], "pitstops": [], "laps": [], "sprint": [], "sprint_qualifying": []},
        }

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(f1, "FULL_RACE_CACHE_DIR", Path(tmp)), \
                 patch.object(f1, "fetch_schedule", return_value=[completed_race]), \
                 patch.object(f1, "fetch_round_data_direct", return_value=api_payload) as fetch_mock, \
                 patch.object(f1, "BACKFILL_BUDGET", f1.BackfillBudget(0)), \
                 patch.object(f1, "CACHE_AWARE_DOWNLOADS", False), \
                 patch.object(f1, "now_local", return_value=f1.datetime(2026, 6, 15, 12, 0, tzinfo=f1.USER_TIMEZONE)):
                f1.write_full_race_cache(2026, 7, stale_payload)
                rows = f1.collect_race_rows(2026, 2026)

        fetch_mock.assert_called_once()
        self.assertEqual(len(rows[rows["race_id"] == "2026-7"]), 22)
        self.assertIn("actual_pit_stop_count", rows.columns)

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
