# Model Design

The model is a hybrid system.

It combines:

1. ML model trained from historical Jolpica data:
   - RandomForestClassifier
   - ExtraTreesClassifier
   - HistGradientBoostingClassifier
   - optional LightGBM and XGBoost classifiers when those dependencies are installed
   - targets: win, podium, top 10
   - RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor, and optional LightGBM for finishing position
   - circuit-median lap-delta model for pace forecasting, with optional LightGBM regressor and HGB fallback
   - grouped chronological race validation; driver rows from the same race are not split across train/validation
   - no random row split promotion fallback

2. Rule-based racing ensemble:
   - driver form
   - constructor form
   - qualifying/grid importance
   - circuit history
   - race pace from lap data
   - pit execution
   - strategy gain from grid-to-finish change
   - reliability
   - team-track fit
   - weather adaptation

3. Optional FastF1 signals:
   - clean-lap pace
   - lap-time consistency
   - longest stint proxy
   - loaded session audit

4. Dashboard scenario layer:
   - rain risk
   - safety car
   - high tyre degradation
   - low overtaking
   - baseline
   - high wind when weather data supports it

5. Official Formula 1 timing layer:
   - sector performance
   - speed-trap/telemetry speed
   - session result and starting-grid signal
   - pit execution
   - tyre stint length
   - position gain
   - team-level car-performance aggregation

6. Optional OpenF1 free historical timing layer:
   - session result and driver metadata
   - lap duration and sector duration pace
   - speed trap/intermediate speed
   - pit lane/pit duration
   - stint length
   - grid/result cross-checks where available

7. FIA decision-document layer:
   - season document-page discovery through source registry
   - incremental FIA index caching
   - timetable, classification, starting-grid, car presentation, PU, deleted-lap, infringement, summons, decision, scrutineering, and post-race document typing
   - text/parsed JSON cache with per-document parse status and errors
   - FIA documents are highest-confidence evidence, but missing/delayed documents reduce confidence instead of inventing data

8. Session lifecycle layer:
   - stages: `pre_weekend`, `post_fp1`, `post_fp2`, `post_fp3`, `post_sprint_qualifying`, `post_sprint`, `post_qualifying`, `pre_race`, `live_adjusted`, and `post_race_audited`
   - normal, sprint, shortened, missing, delayed, stale, and unavailable sessions are represented explicitly
   - race results are not audited/retrained until the final-result delay passes and final classification rows exist

## Current upgrade direction

The 2026.05 model schema keeps the hybrid approach but makes accuracy auditable:

- classification targets: win, podium, top 10
- regression targets: finishing position and circuit-relative lap-time delta
- model regularization: tree depth, leaf count, feature subsampling, and HGB L2 controls are set to reduce overfitting
- feature selection: low-signal features are pruned by feature importance while keeping mandatory source/stage/missingness fields
- ranking metrics: winner hit rate, top-3 recall, top-5 recall, top-10 recall, exact position accuracy, mean position error, finish-position MAE/RMSE, Spearman rank correlation, NDCG@3, NDCG@10, and lap-delta MAE/RMSE
- strong baselines: grid order, constructor standings, driver standings, previous race, recent 3-race form, qualifying-only, practice-only, and the old hybrid hand-weighted fallback
- calibration and race-level normalization: win sums to about 1, podium to about 3, top 10 to about 10 in percentage terms
- DNF/survival head: DNF probability, classified-finish probability, and reliability-adjusted finish risk
- uncertainty and simulation: per-driver model/data/source/stage/reliability uncertainty plus Monte Carlo finish distributions and volatility tags
- feature groups: rolling 3/5/10 driver and team form, teammate-relative deltas, qualifying/grid, same-circuit specialization, recent grid gain, finish consistency, momentum, reliability, pit execution mean/std, lap pace, car-vs-field pace, track overtake sensitivity, circuit DNF/safety-car proxy, track pit/lap baselines, schedule fatigue proxy, tyre/degradation era, weather, regulation fit, official upgrade-package traits, official F1 timing, optional OpenF1 timing, and optional FastF1 signals
- sample weights: recent seasons and current regulation eras receive higher weight, while older eras are decayed
- rookie/substitute handling: sparse-history drivers receive team/teammate priors plus explicit `rookie_prior` and `insufficient_history` flags
- output surfaces: dashboard, markdown, GitHub issue, and HTML email all expose compact model-quality evidence

## Frontend contract and audit layer

The backend now writes frontend-friendly JSON contracts in addition to markdown:

- `data_cache/frontend-contract.json`: latest briefing, archive, scenarios, strategy, source health, prediction explainability, and top 10 driver fields
- `data_cache/model-status.json`: schema version, trained-at state, latest result readiness, metrics, source health, correction summary, champion/challenger status, promotion decision, and limitations
- `data_cache/backtest-history.json`: race-by-race model-card history for the archive and Model Center
- `data_cache/model_corrections.json`: post-race correction records when actual result rows are available
- `data_cache/features/*.json`: race, driver, team, and session feature stores for audit/debug UI
- `data_cache/source_registry/*.json`: season-replenishable source discovery and health
- `data_cache/fia-documents/{season}/`: FIA index/text/parsed cache
- `data_cache/latest-run-status.json`: compact observability payload for source discovery, FIA cache, session waiting states, contract writes, warnings, and errors

Prediction stages are first-class contract values: `pre_weekend`, `post_fp1`, `post_fp2`, `post_fp3`, `post_sprint_qualifying`, `post_sprint`, `post_qualifying`, `pre_race`, `live_adjusted`, and `post_race_audited`.

Ranking score predicts order. Confidence predicts trust. Confidence and reliability use model agreement, data completeness, source freshness, stage, validation history, and missing-data penalties.

The 2026 layer uses official-style terminology: Overtake Mode, Boost, Manual Override, energy deployment, ERS-K, Active Aero, Straight Mode, and Corner Mode. Exact 2026 telemetry is not always available yet, so those fields are explicit explainable proxies derived from regulation context, track traits, speed/pace evidence, strategy, and source health.

Champion/challenger promotion is controlled. A challenger can replace the champion only when validation metrics and acceptance rules pass, critical sources did not fail, generated contracts remain valid, tests pass, and artifacts save correctly.

## OpenF1 And Source Health

OpenF1 is useful enrichment, but it is not required for PitWall to generate predictions. Authenticated or live-session restrictions are surfaced as source-health warnings and the pipeline falls back to Formula 1 timing/static feeds, FIA documents, FastF1, Jolpica, and cached historical data. A 401/403 is not treated as successful data and is never converted into invented timing rows.

Each source contributes health metadata: available, fresh, stale, failed, delayed, blocked, last checked, last success, confidence, supported categories, and missing categories. These values reduce prediction confidence and appear in the dashboard contract.

## Storage

JSON remains the frontend contract format for compatibility with the existing Next.js routes. A local SQLite store at `data_cache/pitwall.db` now mirrors run status, feature snapshots, and prediction history so archive/model pages can query durable structured data later without loading every JSON file. Supabase sync is optional and only activates when credentials are configured.

Optional F1DB and RelBench rel-f1 adapters live under `pitwall/data/`. F1DB can enrich historical circuit and pit-stop context from a locally configured release artifact. RelBench rel-f1 is an offline benchmark adapter for driver DNF, top-3, position, qualifying-position, result-position, and driver-circuit competition tasks. Both adapters report source health and licensing metadata, and neither downloads data during normal prediction runs.

## Leakage And Honesty Rules

Feature availability is stage-gated. Pre-weekend predictions cannot use same-weekend practice, sprint, qualifying, grid, or race-result fields. Post-FP1 can use FP1 only. Sprint Qualifying and Sprint affect later sprint/race predictions only after those sessions exist. Race result fields are allowed only for post-race audit/training after the final-result delay.

Explanation tags must map to available feature groups. PitWall must not claim practice pace, strong qualifying, upgrade validation, PU reliability, weather advantage, penalties, or live pace unless that source exists for the current stage. Missing data appears as a confidence reducer, not positive evidence.

## Deterministic Intelligence Layer

The AI-style layer is not a model input and does not change numeric outputs. It reads the generated contract after rankings/probabilities are produced, then creates per-driver `ai_explanation`, `race_intelligence_summary`, `changed_since_last_run`, deterministic source conflict classifications, and post-race audit summaries when actual result rows exist.

This keeps the prediction system honest: model output remains model output, while the intelligence layer translates uncertainty and evidence into readable text.

## Future Seasons

`TARGET_SEASON=auto` uses the current season; future seasons can be configured through `FIA_DOCUMENTS_SEASON_URL_{YEAR}` and Formula1.com/Jolpica discovery. If a future FIA page is unavailable, the registry marks it pending and continues from fallbacks. The 2026 regulation context can be inherited for 2027+ only as an explicit proxy until newer official sources are configured or discovered.

## Timing Limitation

The `/live` route is an honest timing surface. It exposes `live_timing_status`, `timing_mode`, `timing_source`, `timing_last_updated_at`, `timing_freshness_seconds`, `is_genuinely_live`, and `live_fallback_reason`. Archived OpenF1/Jolpica/static timing is never called live.
