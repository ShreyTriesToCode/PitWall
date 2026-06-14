# PitWall Run Report

- Generated at: 2026-06-14T14:01:18.595043+00:00
- Model version: 2026.06-barcelona-preweekend-v6
- Target event/session: Barcelona Grand Prix / race
- Top 10 availability: 10 rows
- Full grid availability: 22 rows
- Contract validation: passed
- Event trust: 51.7
- Source health: Fallback / 72.09
- Source conflicts: 2
- Major model disagreements: 4
- Missing data groups: pit_stop_data, practice_or_lap_pace

## Validation Details

```json
{
  "ok": true,
  "schema_version": "2026.06-barcelona-preweekend-v6",
  "prediction_data_version": "2026.05-race-control-contract-v2",
  "briefing_count": 8,
  "debug_payload_count": 1,
  "model_version": "2026.06-barcelona-preweekend-v6",
  "latest_top10_count": 10,
  "latest_full_grid_count": 22,
  "latest_all_predictions_count": 22
}
```

## Next Recommended Improvements

- Review high-disagreement driver rows before presenting confident narratives.
- Keep deterministic AI text explanatory only; do not let it modify model outputs.
- Refresh source registry and FIA cache when source conflicts rise.
