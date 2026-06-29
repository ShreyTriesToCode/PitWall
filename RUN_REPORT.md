# PitWall Run Report

- Generated at: 2026-06-29T11:01:06.922549+00:00
- Model version: 2026.06-strategy-actuals-v7
- Target event/session: Austrian Grand Prix / race
- Top 10 availability: 10 rows
- Full grid availability: 22 rows
- Contract validation: passed
- Event trust: 53.58
- Source health: Fallback / 72.09
- Source conflicts: 3
- Major model disagreements: 4
- Missing data groups: pit_stop_data, practice_or_lap_pace

## Validation Details

```json
{
  "ok": true,
  "schema_version": "2026.06-strategy-actuals-v7",
  "prediction_data_version": "2026.05-race-control-contract-v2",
  "briefing_count": 10,
  "debug_payload_count": 1,
  "model_version": "2026.06-strategy-actuals-v7",
  "latest_top10_count": 10,
  "latest_full_grid_count": 22,
  "latest_all_predictions_count": 22
}
```

## Next Recommended Improvements

- Review high-disagreement driver rows before presenting confident narratives.
- Keep deterministic AI text explanatory only; do not let it modify model outputs.
- Refresh source registry and FIA cache when source conflicts rise.
