# PitWall Model Experiments

[Documentation index](docs/README.md)

PitWall currently keeps lightweight experiment records as JSON rather than requiring MLflow or DVC at runtime.

## Current Artifacts

- `model_artifacts/evaluation.json`
- `model_artifacts/feature_importance.json`
- `model_artifacts/training_metadata.json`
- `data_cache/model-status.json`
- `data_cache/backtest-history.json`

## Future Run Directory Shape

When full experiment tracking is needed, write each run under:

```text
model_artifacts/runs/{timestamp}/
  metrics.json
  features.json
  config.json
  validation.json
```

## Minimum Required Fields

- model version and schema version
- training window and validation window
- feature hash and feature count
- source coverage
- baseline comparison
- calibration summary
- promotion decision
- known limitations

## Optional Heavy Tools

MLflow, DVC, Optuna, SHAP, LightGBM, and XGBoost are useful only when they improve verified metrics or operator visibility. They should stay optional and documented instead of becoming a hard runtime dependency for Vercel.

## Notebook Workflow

Use `notebooks/pitwall_model_refinement.ipynb` for local refinement. It checks:

- cached data and artifact availability
- feature schema and missingness
- categorical/numeric handling assumptions
- stage leakage rules
- chronological race-group splits
- champion metadata and artifact load state
- finish MAE/RMSE, Spearman, NDCG@3, NDCG@10, top-3/top-10 recall, winner hit rate, and Brier score where targets exist

Challenger training is disabled by default in the notebook. Set `RUN_CHALLENGER = True` only when cached training data is valid and you intend to spend the runtime. A challenger should not be promoted unless ranking metrics, backend tests, contract validation, artifact save/load, frontend tests, and frontend build all pass.

Experiment notes should also inspect `model_comparison` and `actual_result_comparison` in `data_cache/frontend-contract.json`. Actual-result metrics must only be recorded for races with trusted cached classifications; pending or unavailable actuals are a valid experiment outcome, not a failure to fill in numbers.
