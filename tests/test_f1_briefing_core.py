import unittest
import importlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

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

    def test_f1timing_uses_season_based_track_images_first(self):
        route = Path("frontend/app/api/f1timing/route.js").read_text(encoding="utf-8")
        self.assertIn("seasonTrackImageUrl", route)
        self.assertIn("common/f1/${cleanYear}/track/${cleanYear}track${trackSlug}detailed.webp", route)
        self.assertIn("2026trackmontrealdetailed.webp", route)
        self.assertIn("2026trackmontecarlodetailed.webp", route)

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
