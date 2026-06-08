# PitWall Model Report

Generated: 2026-05-25

## Objective

PitWall predicts a Formula 1 race as a chain of uncertain outcomes: qualifying/grid strength, race pace, tyre and strategy context, reliability/DNF risk, incident risk, and final finishing order. It keeps both a clean Top 10 prediction and a complete Full Grid Prediction.

## Architecture

- Baseline strength: driver, constructor, circuit, current-season, and regulation-era form.
- Qualifying/grid: qualifying score, timing grid evidence, low-overtaking weighting, and FIA grid documents when available.
- Race pace: historical lap pace, timing lap pace, FastF1/OpenF1/F1 timing signals, and circuit-normalized lap-delta modelling.
- Tyre/strategy: tyre-stress profile, pit-window profile, pit execution, team strategy gain, stint evidence where available, post-race strategy context builder, and strategy annotations.
- Reliability/DNF: historical finish rate, status-derived DNF signals, source completeness, and simulation DNF variation.
- Final ranking: transparent component weighting plus ML probability/finish-position outputs and Monte Carlo race simulation.

## Modularization

`f1_briefing.py` remains the public orchestrator, while stable helpers now live under `pitwall.models`, `pitwall.features`, `pitwall.data`, and `pitwall.storage`. This is a strangler split: wrappers preserve old command behavior while new modules get direct tests.

## Contract Outputs

Each normalized prediction row now exposes:

- `predicted_finish`, `position_range`, `win_probability`, `podium_probability`, `points_probability`, `top10_probability`, `dnf_probability`, and `fastest_lap_probability`
- `expected_strategy` with stops, first pit lap, compound sequence, confidence, and basis
- `explanation` with pace, strategy, tyres, weather, risk, qualifying, key reasons, and missing-data notes
- `data_freshness`, `source_notes`, `confidence_label`, and `strategy_annotations`

The event-level contract exposes:

- `top10`, `top_10`, `full_grid`, `all_predictions`
- `race_factors`, `warnings`, `source_health`, `simulation`, `model_metrics`, and `strategy`

## Leakage Protections

- Promotion uses chronological grouped validation, not random row splits.
- Stage gating blocks future-session and post-race fields from earlier prediction stages.
- Target-like fields are excluded from feature columns.
- Race rows are skipped from training until the configured final-result delay has elapsed and actual results exist.

## Current Limitations

- F1 has irreducible uncertainty from crashes, weather shifts, penalties, safety cars, red flags, mechanical failures, and team decisions.
- F1DB and RelBench are optional offline enrichments unless local artifacts are configured.
- Tyre allocation and historical odds remain optional future sources; they are not faked.
- Strategy annotations are deterministic evidence flags and should be expanded as more stint, race-control, and weather data is ingested.

## Next Improvements

- Continue splitting `f1_briefing.py` into `pitwall/data`, `pitwall/features`, and `pitwall/models`.
- Add richer pit-window and compound-sequence validation when full stint data is consistently available.
- Add browser automation coverage once Playwright is installed.

## 2026-06 Update

- Added `notebooks/pitwall_model_refinement.ipynb` for cache-first model inspection and challenger analysis.
- Added reusable model modules for feature wrappers, training entrypoints, evaluation metrics, prediction row normalization, artifact IO, and validation gates.
- Changed chronological validation from fixed season windows to rolling race groups so newer completed seasons are not permanently excluded from training windows.
- Hardened generated prediction rows so Top 10 and Full Grid share one schema and expose safe defaults for optional frontend fields.
- Added cache manifest tracking for full-race data reuse/refresh/skip decisions.
- Added `model_comparison` contracts for champion/challenger status, promotion decision, ranking metrics, and Brier/calibration fields where available.
- Added `actual_result_comparison` contracts that compare predicted winner, podium, Top 10, and driver positions only when trusted actual result rows are present.
- Added visible training logs and a terminal/GitHub Actions summary table so cache reuse, feature shape, split sizes, metrics, promotion, artifacts, and contract paths are observable.

Known limitation: the model remains probabilistic and can be wrong because racing outcomes include incidents, penalties, weather shifts, reliability, strategy calls, and delayed or missing source data.
