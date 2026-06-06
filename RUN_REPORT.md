# PitWall Run Report

- Generated at: 2026-06-06T06:43:55.860523+00:00
- Model version: 2026.05-high-accuracy-v5
- Target event/session: Monaco Grand Prix / race
- Top 10 availability: 10 rows
- Full grid availability: 22 rows
- Contract validation: passed
- Event trust: 43.1
- Source health: Fallback / 70.27
- Source conflicts: 2
- Major model disagreements: 9
- Missing data groups: pit_stop_data, practice_or_lap_pace, qualifying

## Validation Details

```json
{
  "ok": true,
  "schema_version": "2026.05-high-accuracy-v5",
  "prediction_data_version": "2026.05-race-control-contract-v2",
  "briefing_count": 5,
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
