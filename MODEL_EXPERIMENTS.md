# PitWall Model Experiments

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
