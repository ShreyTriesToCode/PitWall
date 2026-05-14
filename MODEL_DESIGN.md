# Model Design

The model is a hybrid system.

It combines:

1. ML model trained from historical Jolpica data:
   - RandomForestClassifier
   - ExtraTreesClassifier
   - HistGradientBoostingClassifier
   - targets: win, podium, top 10
   - RandomForestRegressor, ExtraTreesRegressor, and HistGradientBoostingRegressor for finishing position
   - scaled MLPRegressor neural submodel for lap-time pace forecasting
   - time-aware validation using the most recent available season

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

## Current upgrade direction

The 2026.05 model schema keeps the hybrid approach but makes accuracy auditable:

- classification targets: win, podium, top 10
- regression targets: finishing position and neural lap-time pace
- ranking metrics: winner hit rate, top-3 recall, top-5 recall, top-10 recall, exact position accuracy, mean position error, finish-position MAE/RMSE, and lap-time MAE/RMSE
- feature groups: qualifying/grid, driver form, constructor form, same-circuit history, recent grid gain, finish consistency, momentum, reliability, pit execution, lap pace, car-vs-field pace, track overtake sensitivity, track pit/lap baselines, tyre/degradation era, weather, regulation fit, official upgrade-package traits, official F1 timing, optional OpenF1 timing, and optional FastF1 signals
- output surfaces: dashboard, markdown, GitHub issue, and HTML email all expose compact model-quality evidence

## Frontend contract and audit layer

The backend now writes frontend-friendly JSON contracts in addition to markdown:

- `data_cache/frontend-contract.json`: latest briefing, archive, scenarios, strategy, source health, prediction explainability, and top 10 driver fields
- `data_cache/model-status.json`: schema version, trained-at state, latest result readiness, metrics, source health, correction summary, champion/challenger status, promotion decision, and limitations
- `data_cache/backtest-history.json`: race-by-race model-card history for the archive and Model Center
- `data_cache/model_corrections.json`: post-race correction records when actual result rows are available
- `data_cache/features/*.json`: race, driver, team, and session feature stores for audit/debug UI

Prediction stages are first-class contract values: `pre_weekend`, `post_practice`, `post_qualifying`, `pre_race`, `live_adjusted`, and `post_race_audited`.

Ranking score predicts order. Confidence predicts trust. Confidence and reliability use model agreement, data completeness, source freshness, stage, validation history, and missing-data penalties.

The 2026 layer uses official-style terminology: Overtake Mode, Boost, Manual Override, energy deployment, ERS-K, Active Aero, Straight Mode, and Corner Mode. Exact 2026 telemetry is not always available yet, so those fields are explicit explainable proxies derived from regulation context, track traits, speed/pace evidence, strategy, and source health.

Champion/challenger promotion is controlled. A challenger can replace the champion only when validation metrics and acceptance rules pass, critical sources did not fail, generated contracts remain valid, tests pass, and artifacts save correctly.
