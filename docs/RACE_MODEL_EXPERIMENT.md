# Race ranking experiment: prior-form-ridge-v1

Protocol fixed before fitting this candidate, 27 October 2026.

Objective: final classified order including non-finishers. Predictions are ordered
expected normalized finishing positions, not probabilities or pace estimates.

Features: current qualifying percentile; previous five race driver finish and
qualifying percentiles; previous five race constructor finish percentile; previous
five race driver non-finish proportion; observed driver/constructor sample counts.
Only races with a strictly earlier start enter history. Missing history is encoded
as missing with training-set median imputation and missingness indicators, never
reported as observed F1 data. No target-race laps, weather, pit stops, grid or results
enter prediction. All feature values are field-size normalized.

Model: standardized Ridge regression. Select alpha from 0.1, 1, 10, 100 by race-mean
MAE on 2022–2023 after fitting 2019–2021 (2018 provides history). Refit the selected
alpha on 2019–2023. Report 2024–2025 once; these years were examined for the previous
candidate, so they are comparative validation, not an untouched holdout. No further
feature/parameter search against these scores. Evaluate a frozen artifact on 2026
separately before any production promotion.

Compare against qualifying order on exactly the same complete race fields. Report
MAE (primary), RMSE, Spearman, winner hit/coverage (secondary), coverage/exclusions,
per-season results, and paired race-level bootstrap MAE-difference interval. The
bootstrap seed is fixed and affects only the uncertainty interval, not predictions.

Promotion is not automatic: require >=30 validation races across >=2 seasons,
>=5% MAE improvement, no per-season MAE regression, no rank-correlation regression,
and separately reviewed 2026 evaluation plus prospective evidence. A failed
candidate must remain research-only. Do not alter existing captures or history.

Limitations: retrospective provider revisions; constructor name changes; small
rookie history; qualifying is not penalized starting grid; no clean race pace,
fuel, weather forecast or strategy features. These limits must remain visible.
