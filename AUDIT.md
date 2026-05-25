# PitWall Audit

Generated: 2026-05-25

## DONE

- Backend entrypoint exists in `f1_briefing.py` and still supports the public briefing, retrain, model-status, and frontend-contract commands.
- Strangler modules now exist for config, SQLite storage, simulation helpers, prediction-contract helpers, and strategy-context features while `f1_briefing.py` keeps backward-compatible wrappers.
- Jolpica fetching is cache-aware, paginated for laps, and uses SHA-256 cache keys with atomic writes.
- FastF1, OpenF1, FIA documents, Open-Meteo, F1 timing/static feeds, F1DB, and RelBench are represented in source-health metadata.
- SQLite local storage exists at `data_cache/pitwall.db` for run/status style persistence while JSON contracts remain available for the frontend.
- The backend already emits `top10`, `full_grid`, and `all_predictions` fields.
- `/api/f1timing` has per-IP rate limiting and OpenF1 auth-restriction handling.
- Unit tests cover core API/cache/model contract behavior.
- FIA PDF `403/404` handling avoids retry storms, reuses stale official cached text where available, and reports forbidden documents clearly.
- F1DB/RelBench bootstrap planning exists without bundling large external artifacts.

## PARTIAL

- The modelling code is still mostly concentrated in `f1_briefing.py`; the system now exposes modular submodel outputs, but the file has not yet been fully split into `pitwall/models` and `pitwall/features`.
- F1DB and RelBench adapters are optional/offline. They report status and can read local data, but no dataset artifact is bundled by default.
- Post-race learning exists through cached race/result ingestion, but strategy context now needs continued expansion as more tyre/stint/race-control data becomes available.
- The frontend has a PitWall identity and several dashboards; continued polish should focus on browser-level interaction testing and richer charts rather than raw data density.

## BROKEN FIXED IN THIS PASS

- `/predictions` was driven by the selected target's `top10` rows only, so Full Grid Prediction was not first-class in the UI.
- Driver detail contained too little information and could be hard to scroll on small screens.
- `/api/f1timing` did not expose explicit auto-selection metadata or stable warning fields for active/live-session fallback states.
- Prediction rows lacked a complete race-intelligence shape for `points_probability`, `fastest_lap_probability`, `position_range`, `expected_strategy`, structured `explanation`, `data_freshness`, and `source_notes`.

## MISSING ADDED IN THIS PASS

- `MODEL_REPORT.md`
- `DATA_SOURCES.md`
- `SETUP.md`
- Canonical `top_10` alias in the normalized prediction contract.
- Strategy context annotations for tyre/weather mismatch, early tyre correction, safety-car/VSC/red-flag pit context, double-stack loss, and degradation cliff.
- Explicit `race_factors` and top-level `warnings` in normalized prediction output.

## NOT APPLICABLE

- Paid-only APIs are not required.
- Supabase is not required for local or CI verification.
- The project must not claim predictions are always correct.
- Historical betting odds and Pirelli allocation are not scraped from unreliable or terms-hostile sources.
