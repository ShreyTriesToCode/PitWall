# PitWall Run Report

- Generated at: 2026-06-08T08:31:55.111035+00:00
- Model version: 2026.05-high-accuracy-v5
- Target event/session: Monaco Grand Prix / race
- Top 10 availability: 10 rows
- Full grid availability: 22 rows
- Contract validation: passed
- Event trust: 53.08
- Source health: Fallback / 72.09
- Source conflicts: 2
- Major model disagreements: 7
- Missing data groups: pit_stop_data, practice_or_lap_pace

## Validation Details

```json
{
  "ok": true,
  "schema_version": "2026.05-high-accuracy-v5",
  "prediction_data_version": "2026.05-race-control-contract-v2",
  "briefing_count": 6,
  "debug_payload_count": 1,
  "model_version": "2026.05-high-accuracy-v5",
  "latest_top10_count": 10,
  "latest_full_grid_count": 22,
  "latest_all_predictions_count": 22
}
```

## Next Recommended Improvements

- Review high-disagreement driver rows before presenting confident narratives.
- Keep deterministic AI text explanatory only; do not let it modify model outputs.
- Refresh source registry and FIA cache when source conflicts rise.
