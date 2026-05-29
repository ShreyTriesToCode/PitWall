# PitWall Methodology

## Problem Statement

PitWall predicts Formula 1 sprint and race outcomes from public, cacheable, source-attributed data. The goal is highest practical accuracy with calibrated uncertainty, not guaranteed certainty. Crashes, safety cars, red flags, mechanical failures, team orders, weather swings, penalties, and delayed official documents are treated as uncertainty drivers rather than hidden knowledge the model pretends to know.

## Data Sources

Primary official sources:

- FIA decision-document pages and PDFs for timetables, classifications, grids, car presentation submissions, PU documents, deleted laps, infringements, decisions, and scrutineering context.
- Formula 1 timing/static feeds for timing replay/latest session data where available.
- Formula1.com calendar pages for event context.

Structured fallback and enrichment sources:

- Jolpica, an Ergast-compatible API, for schedules, results, qualifying, laps, pits, sprints, and standings.
- FastF1 for cached timing/session features when session loading succeeds.
- OpenF1 as optional enrichment. Authenticated or live-session restrictions are exposed as source-health warnings and do not block the pipeline.
- Open-Meteo for weather forecast context when coordinates are available.
- F1DB as an optional local historical dataset when `F1DB_SQLITE_PATH` or `F1DB_CSV_DIR` is configured. The verified release reference is `v2026.4.2`; it is CC-BY-4.0 and used for stable historical/circuit/pit-stop context rather than live truth.
- RelBench rel-f1 as an optional offline relational benchmark. It is used for task-style validation only when `RELBENCH_F1_ENABLED=true` and the `relbench` package/data are available.
- Local generated caches and SQLite snapshots for reproducible reruns.

Optional sources such as historical odds, Pirelli allocation details, and technical-directive timelines should be added only through documented, permitted APIs or manually curated fixtures. PitWall does not scrape blocked sites or use social media as primary evidence.

## Feature Design

PitWall uses a hybrid feature set:

- Driver form: rolling 3/5/10 race finish, points, qualifying, DNF, consistency, momentum, and circuit history.
- Team form: constructor points, rolling finish quality, pit execution mean/std, reliability, strategy, and current-season pace.
- Teammate-relative features: qualifying/race/pace deltas when both drivers have enough evidence.
- Circuit features: overtake sensitivity, track position value, DNF/safety-car proxy, pit/lap baselines, speed/traction/degradation/cooling archetypes.
- Session features: official timing, classification, practice/qualifying/sprint/race signals, and FIA document IDs used.
- FIA technical features: upgrade packages, PU component freshness, infringement/grid correction, and source-confidence state.
- Weather and scenario features: dry, rain, heat, wind, high degradation, safety-car-heavy, grid-dominant, and pace-dominant variants.
- Sparse-data features: rookie prior, insufficient history, missing source flags, and stage-based missing-data penalties.

Constructor names are normalized across branding changes so historical form does not reset when teams rename. Pit-lane starts from Jolpica grid `0` are treated as back-of-grid starts, not as missing grid data.

## Model Stack

The model keeps a maintainable tabular ensemble:

- Regularized RandomForest, ExtraTrees, and HistGradientBoosting classifiers for win, podium, and top 10.
- Optional LightGBM/XGBoost classifiers if installed.
- Regularized tree regressors for finishing position.
- Circuit-median lap-delta forecasting instead of raw lap-time seconds.
- Optional LightGBM LambdaMART/ranking components when available, with sklearn fallback.
- Empirical calibration and race-level probability normalization.
- Monte Carlo finishing distribution, DNF/survival probabilities, prediction intervals, and volatility tags.

The ensemble is intentionally explainable. SHAP is optional when installed; otherwise PitWall falls back to feature importance, component scores, and source-backed reason tags.

## Free AI Methodology

PitWall uses deterministic templates for AI-style text. The templates can only read fields already present in the prediction row, model status, archive, source health, or correction artifacts. They summarize, classify, and explain; they never infer new race facts or override model predictions. When local evidence is missing, the required response is "Not enough data in local PitWall sources" or a visible missing-data warning.

Model artifacts are mirrored to `model_artifacts/evaluation.json`, `model_artifacts/feature_importance.json`, and `model_artifacts/training_metadata.json` so validation, drift status, feature selection, optional dataset status, and training metadata can be reviewed without opening the pickle bundle.

## Validation

PitWall avoids random row splits because they leak race context across drivers from the same event. Validation is grouped by race and chronological:

- Initial training window: 2018-2021.
- Large validation window: 2022-2024.
- Out-of-time test/promotion gate: completed 2025-2026 races when available.
- Rolling season folds are recorded in metadata.

Promotion requires no leakage, valid frontend contracts, saved artifacts, and baseline comparisons. A challenger cannot replace the champion if it does not beat practical baselines such as grid order, qualifying-only, constructor standings, or recent form on finish and ranking metrics.

Tracked metrics include finish MAE/RMSE, winner hit, top-3/top-5/top-10 recall and precision, exact position accuracy, Spearman rank correlation, NDCG@3/NDCG@10, Brier score, calibration bins, race probability sum error, per-constructor bias, and drift over recent completed races.

## Source Honesty

Every generated prediction should expose:

- Prediction stage.
- Model training timestamp and schema.
- Evidence used.
- Missing data warnings.
- Data freshness and source health.
- OpenF1 auth restriction state when relevant.
- FIA cache hit/miss and parse status.
- Confidence, uncertainty, and cannot-know factors.

The UI must not say "live" unless fresh timing packets exist during an active session. Archive, stale, delayed, and unavailable data are labelled separately.

## Known Failure Modes

PitWall cannot reliably predict first-lap contact, surprise mechanical failures, emergency strategy calls, sudden weather cells, major parc ferme changes, unreported damage, team orders, or delayed/recalled FIA decisions before they are published. The correct behavior is to lower confidence, surface the missing evidence, and update predictions after authoritative data appears.
