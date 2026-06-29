# PitWall Model Report

[Documentation index](docs/README.md) -> [Data Sources](DATA_SOURCES.md) -> [Runbook](RUNBOOK.md) -> [Artifact Policy](ARTIFACT_POLICY.md)

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
- ML heads: RandomForest, ExtraTrees, HistGradientBoosting, and optional LightGBM/XGBoost classifiers for win/podium/top 10; tree regressors for finishing position; circuit-median lap-delta pace forecasting.
- Scenario layer: baseline, rain, safety car, high degradation, low overtaking, and high wind when weather data supports it.
- Session lifecycle: `pre_weekend`, `post_fp1`, `post_fp2`, `post_fp3`, `post_sprint_qualifying`, `post_sprint`, `post_qualifying`, `pre_race`, `live_adjusted`, and `post_race_audited`.
- Source-health layer: official FIA documents, Formula 1 timing/static feeds, Jolpica, optional OpenF1, optional FastF1, Open-Meteo, F1DB, RelBench, and local caches all report available/fresh/stale/failed/delayed/blocked states.

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
- A bounded single-feature leakage diagnostic permutes the top selected features on validation data, writes `model_artifacts/leakage_diagnostic.json`, and flags extreme AUC collapse. Local runs warn/report; CI can fail only when the drop exceeds `LEAKAGE_DIAGNOSTIC_AUC_DROP_THRESHOLD` and the feature is not in `LEAKAGE_DIAGNOSTIC_ALLOWLIST`.
- Challenger promotion requires valid data checks, no-leakage checks, ranking metrics, artifact save/load checks, backend tests, frontend contract validation, and frontend build.
- Ranking quality matters more than classifier-only metrics because F1 prediction quality is primarily ordered-grid quality.

## Experiment Records

PitWall keeps lightweight experiment records as JSON rather than requiring MLflow or DVC at runtime:

- `model_artifacts/evaluation.json`
- `model_artifacts/feature_importance.json`
- `model_artifacts/training_metadata.json`
- `data_cache/model-status.json`
- `data_cache/backtest-history.json`

Use `notebooks/pitwall_model_refinement.ipynb` for local refinement. It checks cached data/artifact availability, missingness, schema stability, stage leakage, chronological race-group splits, champion artifact load state, finish MAE/RMSE, Spearman, NDCG@3/NDCG@10, top-3/top-10 recall, winner hit rate, and Brier score where probability targets exist.

Challenger training is disabled by default in the notebook. Set `RUN_CHALLENGER = True` only when cached training data is valid and you intend to spend the runtime. Actual-result metrics must only be recorded for races with trusted cached classifications; pending or unavailable actuals are valid outcomes, not blanks to fill in.

Optional heavy tools such as MLflow, DVC, Optuna, SHAP, LightGBM, and XGBoost should stay optional unless they improve verified metrics or operator visibility.

## Current Limitations

- F1 has irreducible uncertainty from crashes, weather shifts, penalties, safety cars, red flags, mechanical failures, and team decisions.
- F1DB and RelBench are optional offline enrichments unless local artifacts are configured.
- Tyre allocation and historical odds remain optional future sources; they are not faked.
- Strategy annotations are deterministic evidence flags and should be expanded as more stint, race-control, and weather data is ingested.

## Next Improvements

- Continue splitting `f1_briefing.py` into `pitwall/data`, `pitwall/features`, and `pitwall/models`.
- Add richer pit-window and compound-sequence validation when full stint data is consistently available.
- Move large runtime caches to release assets, object storage, or Git LFS when routine commits become noisy.
- Add shared timing cache with Upstash Redis or Vercel KV if deployed serverless timing cache needs cross-instance sharing.
- Expand model-vs-reality archive once more audited actual-result rows are available.
- Keep heavier feature ablation and hyperparameter search behind explicit flags.

## 2026-06 Update

- Added `notebooks/pitwall_model_refinement.ipynb` for cache-first model inspection and challenger analysis.
- Added reusable model modules for feature wrappers, training entrypoints, evaluation metrics, prediction row normalization, artifact IO, and validation gates.
- Changed chronological validation from fixed season windows to rolling race groups so newer completed seasons are not permanently excluded from training windows.
- Added model schema `2026.06-strategy-actuals-v7`, which forces retraining/evaluation when completed-race actual strategy signals are added to the feature set.
- Completed race rows now preserve every classified driver returned by the Jolpica-compatible results API, including 22-driver grids when the source provides them.
- Post-race strategy, stint, race-control, weather, pit-stop, and tyre-compound signals are flattened into training rows after the final-result delay, then converted into historical driver/team/track aggregates for future prediction rows. These fields are never used from the same race before that race is final.
- Hardened generated prediction rows so Top 10 and Full Grid share one schema and expose safe defaults for optional frontend fields.
- Added cache manifest tracking for full-race data reuse/refresh/skip decisions.
- Added `model_comparison` contracts for champion/challenger status, promotion decision, ranking metrics, and Brier/calibration fields where available.
- Added `actual_result_comparison` contracts that compare predicted winner, podium, Top 10, and driver positions only when trusted actual result rows are present.
- Added visible training logs and a terminal/GitHub Actions summary table so cache reuse, feature shape, split sizes, metrics, promotion, artifacts, and contract paths are observable.

Known limitation: the model remains probabilistic and can be wrong because racing outcomes include incidents, penalties, weather shifts, reliability, strategy calls, and delayed or missing source data.

## 2026-06-28 Validation Hardening

- `f1_briefing.py` is now part of Ruff coverage, closing the lint escape that hid an undefined-name live FIA index crash.
- Empirical probability calibration remains intentionally unweighted; model fit paths continue to use season sample weights.
- `standing_proxy` was removed as dead inference-only code rather than adding an asymmetric feature outside the training schema.
- Single-feature leakage diagnostics are bounded by `LEAKAGE_DIAGNOSTIC_TOP_N` so routine training does not become a full ablation run.
- FIA car-presentation upgrade packages now feed the ML feature matrix directly through `fia_upgrade_*` columns for completed-race training rows and current-race inference rows. Missing or unverified upgrade data remains an explicit `missing_fia_upgrade_data` signal rather than fabricated input.
- Upgrade package context is cache-first: verified parsed FIA car-presentation documents are used before any live URL probes. If live FIA/news candidates return 401/403/404 or empty content, each candidate is skipped after one attempt and the source state becomes `unavailable` when no trusted replacement exists.
- Scheduled briefing runs refresh FIA document metadata and the source registry by default so newly published upgrade-package documents can flow into the next training/inference pass without manual intervention.

## 2026-06-29 FIA Fallback Source Status

- The 2026 official FIA archive/API URL is configured as a live secondary official source after `www.fia.com` season-index requests returned 403 from this environment.
- A live refresh returned `official_fia_archive_api` with 131 indexed documents; this means FIA upgrade-package features can still be populated from live official metadata when the primary FIA host blocks the request.
- Wayback is configured only as a stale season-index fallback before verified cache. It is not treated as live official data and must preserve `source_authority=wayback_snapshot`.
- F1LivePulse remains disabled by default because the public URL currently resolves to a feature page rather than a verified, machine-parseable FIA document index.
- Verified cache remains the last data-bearing fallback; it may feed model features only with stale/cache metadata. No unavailable FIA document is synthesized.

## 2026-06-29 Strategy And Tyre Evidence

- FIA Pirelli Preview/Competition Notes documents now produce event-specific dry-compound mappings only when exactly three slick compounds are found. The model and UI do not infer a C-number mapping from circuit history or general tyre knowledge.
- `tyre_compound_code()` accepts event-specific FIA mappings for C-number compounds while preserving existing relative `SOFT`/`MEDIUM`/`HARD` labels from timing/stint feeds. A C-number without a verified mapping encodes as unknown.
- Strategy output now includes `predicted_strategy` with stint sequence, lap ranges, basis, confidence, pit-duration sample count, and degradation sample status. When cached same-circuit pit data is thin, the status is `heuristic_fallback` and the basis says so explicitly.
- Safety-car windows are derived from cached race-control history by lap bucket only when enough same-circuit races are available. Otherwise the output is `thin_data`, not a fabricated probability window.
- The `/strategy` page now shows the stint plan and FIA compound source attribution only when the backend contract contains verified mapping data. Missing FIA tyre documents intentionally render no C-number identity field.

## 2026-06-29 Model Center Rendering

- `/model` now receives model-status and prediction comparison contracts through server-side data loading before hydration.
- The Model Center still does not invent actual-result comparison metrics; pending/unavailable actual results remain hidden behind the explicit pending state until trusted result rows exist.
- The frontend now exposes existing Monte Carlo simulation output in prediction views as probabilistic simulation output, not as observed race data.

## 2026-06-29 Score Missingness Guardrails

- Legacy contract backfill no longer converts missing reliability, active-aero, energy-boost, defend-risk, top-10-safety, DNF, or classified-finish fields into neutral-looking shared values. Missing values stay `null` with `*_available=false` and a `score_unavailable_reasons` entry.
- Race simulation still uses a bounded 5% DNF assumption when no reliability/DNF signal exists, but each simulated driver row now includes `dnf_probability_basis` and `dnf_probability_fallback_used` so the UI/reporting layer can disclose the assumption.
- The ranking model still uses weighted component coverage; missing `team_track_fit`, `weather_adaptation`, and `reliability` inputs reduce available evidence instead of being treated as trusted observed data.
