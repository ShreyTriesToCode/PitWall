# PitWall Data Sources

Generated: 2026-05-25

## Primary Sources

- OpenF1: https://openf1.org/docs/ and https://openf1.org/auth.html
  - Used as optional 2023+ enrichment for sessions, drivers, laps, pit data, stints, race control, weather, and session results.
  - Live or restricted sessions may return 401/403 unless authenticated. PitWall reports this as auth-restricted and falls back.
- Jolpica: https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md
  - Ergast-compatible historical schedule/results/qualifying/laps/pit stops/status.
  - Pagination uses `limit` and `offset`; default is 30 and max is 100.
- FastF1: https://docs.fastf1.dev/fastf1.html
  - Optional session timing, laps, telemetry, tyres, weather, and cache-backed F1 timing access.
- Open-Meteo: https://open-meteo.com/en/docs
  - Forecast/historical weather by latitude/longitude and hourly fields.
- FIA documents:
  - Official documents, classifications, decisions, race director notes, infringements, PU documents, grid documents, and context where available.
  - Individual PDF downloads that return `403` are marked as forbidden; cached official text is reused as stale evidence when present.
- Formula 1 timing/static feeds:
  - Used for the `/live` timing dashboard with archive/live/stale/unavailable states.
  - Track visuals use season-based Formula1.com track images such as `common/f1/2026/track/2026trackmontrealdetailed.webp` before falling back to legacy circuit maps.

## Optional Offline Datasets

- F1DB: https://github.com/f1db/f1db
  - License: CC-BY-4.0.
  - Release format: CSV, JSON, SQL, SQLite, and split artifacts.
  - Current verified release in config/tests: `v2026.4.2`.
  - Used only when `F1DB_ENABLED=true` plus a local SQLite or CSV path is configured.
  - Bootstrap planning: `.venv/bin/python scripts/bootstrap_datasets.py f1db`.
- RelBench rel-f1: https://relbench.stanford.edu/datasets/rel-f1/
  - License: CC-BY-4.0 via F1DB reference.
  - Used as an offline relational benchmark, not a live prediction source.
  - Bootstrap planning: `.venv/bin/python scripts/bootstrap_datasets.py relbench`.

## Source Rules

- Prefer official FIA/F1 documents for penalties, classification, timing/race documents, and rules context.
- Prefer live/current APIs for race-week data when available and healthy.
- Prefer F1DB/RelBench for stable historical/offline benchmarking.
- Do not use future data in chronological training.
- Do not fake missing API data; expose unavailable/auth-restricted/stale states.
