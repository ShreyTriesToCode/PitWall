# PitWall

[Documentation index](docs/README.md) -> [Runbook](RUNBOOK.md) -> [Model Report](MODEL_REPORT.md) -> [Data Sources](DATA_SOURCES.md) -> [Artifact Policy](ARTIFACT_POLICY.md)

PitWall generates Formula 1 sprint and race predictions, publishes readable briefings, sends optional email/GitHub notifications, and serves a Next.js dashboard with an honest timing/replay view.

The backend keeps a cache-first pipeline around Jolpica, official Formula 1 timing/static feeds, optional OpenF1 free historical timing, FastF1, Open-Meteo, FIA decision documents, Formula1.com calendar context, and local historical race caches.

## What It Produces

- Sprint Race prediction
- Final Race prediction
- Briefing markdown in `briefings/`
- Dashboard data in `briefings/index.json` and `data_cache/latest-model-debug.json`
- Frontend contract data in `data_cache/frontend-contract.json`
- Top 10 and full-grid prediction rows in both backend JSON and `/api/predictions`
- Model center JSON in `data_cache/model-status.json`
- Backtest history in `data_cache/backtest-history.json`
- Post-race correction log in `data_cache/model_corrections.json`
- Feature store JSON in `data_cache/features/`
- Source registry data in `data_cache/source_registry/`
- Incremental FIA document cache in `data_cache/fia-documents/`
- Latest run status in `data_cache/latest-run-status.json`
- Latest model/accuracy report in `MODEL_STATUS.md`
- Canonical docs in `RUNBOOK.md`, `MODEL_REPORT.md`, `DATA_SOURCES.md`, `ARTIFACT_POLICY.md`, `AUDIT.md`, and `docs/README.md`
- Optional GitHub issue and Gmail output when notification gates open

## Prediction System

The current model is a hybrid ensemble:

- regularized RF/HGB/ExtraTrees classifiers for win, podium, and top 10 probabilities, with optional LightGBM/XGBoost heads when installed
- RF/HGB/ExtraTrees regressors for predicted finishing position, with optional LightGBM finishing/lap-delta models when installed
- calibrated win/podium/top-10 probability outputs and race-level normalization
- circuit-median lap-delta pace forecasting instead of raw lap-second prediction
- season/race-group chronological validation; random row splits are not used for promotion
- Spearman, NDCG@3/NDCG@10, finish MAE/RMSE, Brier, top-N precision/recall, and baseline comparisons
- official F1 timing signals: sectors, speed trap/telemetry speed, stints, pits, starting grid, session result, and position gain
- optional OpenF1 enrichment: drivers, laps, session results, pits, stints, sector pace, speed, and grid/result cross-checks when public or authenticated access is available
- driver traits: form, racecraft, reliability, qualifying delta, circuit history, grid gain, consistency
- car/team traits: constructor form, normalized constructor aliases, current-season pace, rolling 3/5/10-race form, pit execution, team strategy, official upgrade-package traits
- FIA decision-document traits: timetable, classifications, grid, car presentation submissions, PU documents, deleted laps, infringements, decisions, and parse/cache health where available
- track/weather traits: overtaking, tyre stress, safety-car/DNF proxy, rain, heat, wind, track-position sensitivity
- regulation context for 2025 wing-flex, 2026 active-aero/power-unit reset, and later rules
- 2026 Boost / Overtake Mode Intelligence using Boost, Manual Override, energy deployment, ERS-K, and Active Aero proxy fields
- separate ranking score and confidence model, with confidence reduced by source health and missing-data penalties
- uncertainty, DNF/survival, scenario, and Monte Carlo simulation outputs
- structured race-intelligence rows with `expected_strategy`, `position_range`, `points_probability`, `fastest_lap_probability`, `explanation`, `data_freshness`, and `source_notes`

Model design and experiment notes live in `MODEL_REPORT.md`.

The dashboard intentionally keeps both views: a compact **Top 10 Prediction** for normal F1 viewers and a complete **Full Grid Prediction** from P1 through the available field for model review.

## Local Setup

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cd frontend
npm install
```

Run backend validation:

```bash
.venv/bin/python -m py_compile f1_briefing.py
.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .
```

Generate/update frontend contracts from the current briefing data:

```bash
.venv/bin/python -c "import f1_briefing as f; f.save_model_status_json(); f.generate_frontend_contract_files()"
```

Run the frontend:

```bash
cd frontend
npm run dev
```

Dashboard: `http://localhost:3000`

Optional frontend fallback source:

```bash
export NEXT_PUBLIC_F1_DATA_BASE_URL="https://raw.githubusercontent.com/ShreyTriesToCode/PitWall/main"
```

Leave it unset when running locally with generated `data_cache/` and `briefings/` files.

## Generate A Briefing

Optional for calendar matching. If this is unset or the feed is unavailable, PitWall now falls back to the Jolpica season schedule so local generation and retraining still run:

```bash
export F1_ICS_URL="https://your-calendar-feed.ics"
```

Optional email settings:

```bash
export EMAIL_ENABLED=true
export EMAIL_ADDRESS="..."
export EMAIL_APP_PASSWORD="..."
export EMAIL_TO="..."
```

Run:

```bash
.venv/bin/python f1_briefing.py
```

Useful controls:

```bash
FORCE_RETRAIN=true
FULL_DATA_BACKFILL_LIMIT=0
OUTPUT_MODE=auto
AUTO_COMMIT_ENABLED=false
FORCE_NOTIFY=false
NOTIFICATION_WINDOW_HOURS=8
TARGET_SEASON=auto
TARGET_EVENT=
TARGET_SESSION=
```

Use `FORCE_RETRAIN=true` after model schema changes. `FULL_DATA_BACKFILL_LIMIT=0` means no artificial cap; set a positive value only when you deliberately want to bound a run for CI time or upstream politeness.

Full retrain with FIA enabled and OpenF1 optional:

```bash
TARGET_SEASON=auto \
FIA_DOCUMENTS_ENABLED=true \
OPENF1_OPTIONAL_ONLY=true \
FULL_DATA_BACKFILL_LIMIT=0 \
FORCE_RETRAIN=true \
.venv/bin/python f1_briefing.py
```

## Season Replenishment And FIA Documents

PitWall is season-replenishable. `TARGET_SEASON=auto` resolves to the current calendar year, and operators can override future seasons without code edits:

```bash
TARGET_SEASON=2027
FIA_DOCUMENTS_SEASON_URL_2027="https://www.fia.com/..."
FORMULA1_CALENDAR_BASE_URL="https://www.formula1.com/en/racing"
```

Source discovery writes `data_cache/source_registry/{season}.json`. If a future FIA page is not configured or discoverable yet, PitWall marks FIA documents `pending_unavailable` and continues with Formula1.com, Jolpica, ICS, OpenF1, FastF1, and local cache. It never fabricates a future FIA URL and never treats a previous season page as active current-season truth.

FIA decision documents are treated as highest-confidence official evidence when available. The incremental cache lives under:

```text
data_cache/fia-documents/{season}/season_index.json
data_cache/fia-documents/{season}/{event_slug}/text/
data_cache/fia-documents/{season}/{event_slug}/parsed/
```

The index can be refreshed without redownloading every PDF:

```bash
REFRESH_FIA_DOCUMENTS=true .venv/bin/python f1_briefing.py
```

Reparse cached FIA text/PDF output:

```bash
FORCE_REPARSE_FIA_DOCUMENTS=true .venv/bin/python f1_briefing.py
```

Redownload FIA PDFs only when intentionally needed:

```bash
FORCE_REDOWNLOAD_FIA_DOCUMENTS=true KEEP_FIA_PDFS=false .venv/bin/python f1_briefing.py
```

If FIA serves a deterministic `403` for an individual decision PDF, PitWall now makes one browser-header request, reuses cached official text/parsed JSON when present, marks the document `stale_cache_forbidden`, and continues the run. Without cache it marks the document `forbidden` in source health instead of retrying four times or hiding the failure.

Session ingestion uses official session windows when available, waits after completed sessions, then marks `waiting_for_api_data`, `data_ingested`, or `unavailable` in the contract. Common controls:

```bash
SESSION_INGESTION_ENABLED=true
SESSION_RESULT_DELAY_MINUTES=30
PRACTICE_RESULT_DELAY_MINUTES=20
QUALIFYING_RESULT_DELAY_MINUTES=30
SPRINT_RESULT_DELAY_MINUTES=45
RACE_RESULT_DELAY_HOURS=8
FORCE_SESSION_INGEST=false
DRY_RUN_SESSION_INGEST=false
```

To ingest one event/session:

```bash
TARGET_EVENT=canadian-grand-prix TARGET_SESSION=qualifying FORCE_SESSION_INGEST=true .venv/bin/python f1_briefing.py
```

Refresh FIA index only:

```bash
REFRESH_FIA_DOCUMENTS=true MAX_FIA_PDFS_DOWNLOAD_PER_RUN=0 .venv/bin/python f1_briefing.py
```

Regenerate frontend contracts from the latest backend artifacts:

```bash
.venv/bin/python -c "import f1_briefing as f; f.save_model_status_json(); f.generate_frontend_contract_files()"
```

## OpenF1 Auth And Live Timing

OpenF1 is optional enrichment. During live sessions, OpenF1 can require authenticated API access. PitWall exposes that as `openf1_auth_required`/source-health state and falls back to Formula 1 timing/static feeds, FastF1, Jolpica, and cache-backed data. It does not hide 401/403 responses and does not fake live telemetry.

Optional OpenF1 credentials:

```bash
OPENF1_ACCESS_TOKEN=
OPENF1_USERNAME=
OPENF1_PASSWORD=
OPENF1_OPTIONAL_ONLY=true
```

The `/live` page shows `Live`, `Delayed`, `Stale`, `Archive`, or `Unavailable` based on actual freshness. `/api/f1timing` is rate-limited by IP so a deployed frontend does not hammer upstream timing sources:

```bash
F1_TIMING_RATE_LIMIT_MS=5000
```

## Local Store And Optional Supabase

PitWall keeps JSON contracts for the Next.js app, and also writes run status, feature snapshots, and prediction history into `data_cache/pitwall.db`. Supabase sync is optional and disabled unless credentials are present:

```bash
PITWALL_DB_PATH=data_cache/pitwall.db
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

Supabase is not required for local tests, retraining, or Vercel deployment.

## Optional Historical Datasets

PitWall has optional adapters for F1DB and RelBench rel-f1. They are not live
race-week sources and they are disabled by default so CI and local prediction
runs never download heavy datasets unexpectedly.

```bash
F1DB_ENABLED=false
F1DB_RELEASE_TAG=v2026.4.2
F1DB_SQLITE_PATH=
F1DB_CSV_DIR=
RELBENCH_F1_ENABLED=false
RELBENCH_F1_DOWNLOAD=false
MODEL_ARTIFACTS_DIR=model_artifacts
DRIFT_SPEARMAN_THRESHOLD=0.55
```

Use F1DB by downloading a release artifact from `https://github.com/f1db/f1db`
and pointing `F1DB_SQLITE_PATH` at the local SQLite file, or `F1DB_CSV_DIR` at
the extracted CSV directory. F1DB is CC-BY-4.0 and is used for historical
circuit/pit-stop/relational context only when explicitly configured. RelBench
rel-f1 is treated as an offline benchmark source, not direct live prediction
truth.

Dry-run discovery without publishing production contracts:

```bash
DRY_RUN_SESSION_INGEST=true REFRESH_SOURCE_REGISTRY=true .venv/bin/python f1_briefing.py
```

## Timing Status

The `/live` page is a timing dashboard, not a fake telemetry stream. It shows `Live` only when fresh timing packets are available during an active session. Otherwise it downgrades to `Delayed`, `Stale`, `Archive`, or `Unavailable`, and exposes `timing_mode`, `timing_source`, `timing_last_updated_at`, `timing_freshness_seconds`, `is_genuinely_live`, and `live_fallback_reason`.

Controls:

```bash
LIVE_TIMING_ENABLED=true
LIVE_STALE_AFTER_SECONDS=60
DISABLE_LIVE_MODE=false
TIMING_REPLAY_MODE_ALLOWED=true
```

## Frontend

Pages:

- `/` Race Control overview
- `/predictions` prediction intelligence board
- `/drivers` driver analysis
- `/teams` constructor/team analysis
- `/strategy` Strategy Lab
- `/live` timing replay/live-status dashboard
- `/model` Model Center
- `/archive` race archive

API routes:

- `/api/predictions`
- `/api/model-status`
- `/api/archive`
- `/api/source-health`
- `/api/backtest`
- `/api/f1timing`
- `/api/audio`

The timing page auto-selects the active or latest useful F1 session. It formats driver names, leaderboard, tyres/stints, weather, race control, and team radio when the source allows access. It only labels a feed live when freshness checks pass.

## GitHub Workflow

`.github/workflows/f1-briefing.yml` runs on schedule and manual dispatch.

Workflow shape:

1. Restore FastF1, HTTP, full-race, FIA document, source-registry, and model caches.
2. Install Python dependencies.
3. Compile and run unit tests.
4. Install frontend dependencies and run the Next.js build.
5. Check whether Jolpica has a newly completed GP result after `FINAL_RESULTS_DELAY_HOURS`.
6. Retrain automatically if a new result exists, the model is missing, the schema changed, or manual force retrain was requested.
7. Refresh source registry/FIA index incrementally, ingest eligible sessions, generate sprint/race predictions, and write frontend JSON contracts.
8. Validate generated JSON contracts and run unit tests again.
9. Update `MODEL_STATUS.md`, `briefings/`, `briefings/index.json`, `data_cache/latest-model-debug.json`, `data_cache/frontend-contract.json`, `data_cache/model-status.json`, `data_cache/backtest-history.json`, `data_cache/model_corrections.json`, `data_cache/latest-run-status.json`, `data_cache/source_registry/`, and FIA/session feature artifacts.
10. Upload complete artifacts for inspection.

Automatic behavior:

- Scheduled runs happen daily and every 6 hours Thursday through Monday around race weekends.
- Scheduled `OUTPUT_MODE=auto` resolves to today-only Sprint/Race output.
- If a Grand Prix has just ended, the workflow waits until `FINAL_RESULTS_DELAY_HOURS` has passed.
- After that cutoff, it bypasses stale HTTP result cache and retrains only once the API returns final `Results` rows.
- If the API still has no final results, it records that state in `MODEL_STATUS.md` and keeps the current model for predictions.
- Email/GitHub issue output is sent only inside the notification window unless `FORCE_NOTIFY=true`.
- Challenger promotion remains gated: finish-position MAE, top-3 recall, top-10 recall, Brier score, critical source health, contract validation, unit tests, and saved artifacts must pass before the champion model is replaced.

Manual controls from `workflow_dispatch`:

- `force_retrain`: retrain even when no new race result is available.
- `full_data_backfill_limit`: fetch more uncached historical races.
- `lookahead_days`: search further ahead in the calendar.
- `output_mode`: choose `auto`, `weekend`, `today`, or `next`.
- `send_email`: allow or suppress email output.
- `force_notify`: send notifications outside the normal gate.
- `notification_window_hours`: change the event notification window.
- `target_season`, `target_event`, `target_session`: focus a season/event/session.
- `force_session_ingest`, `session_delay_minutes`, `dry_run_session_ingest`: control session lifecycle ingestion.
- `refresh_fia_documents`, `refresh_source_registry`, `force_reparse_fia_documents`, `force_redownload_fia_documents`: control official source refreshes.
- `disable_live_mode`: force timing UI away from true live labels.
- `enable_feature_ablation`, `enable_hyperparameter_search`: opt into heavier manual model diagnostics.

## GitHub Ready Checklist

Target repository:

```text
https://github.com/ShreyTriesToCode/PitWall
```

This project intentionally commits generated briefing/model artifacts so a fresh clone can show predictions without rerunning the full data pipeline.

Commit these project artifacts:

- `briefings/`
- `data_cache/`
- `fastf1_cache/`
- `models/saved_models/`
- `MODEL_STATUS.md`
- frontend source and package lock files
- workflow and documentation files

Do not commit local machine/build junk:

- `.venv/`
- `frontend/node_modules/`
- `frontend/.next/`
- `frontend/.vercel/`
- `__pycache__/`
- `.pytest_cache/`
- `.env` and `*.local` secret files

Before pushing, run:

```bash
.venv/bin/python -m py_compile f1_briefing.py
.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .
cd frontend
npm install
npm run build
cd ..
```

Then initialize or connect Git, preview ignored files, commit, and push:

```bash
git init -b main
git remote add origin https://github.com/ShreyTriesToCode/PitWall.git
git status --ignored
git add -n .
git add .
git status --short
git commit -m "feat: launch PitWall dashboard and prediction pipeline"
git push -u origin main
```

If the local repository already exists, use `git remote set-url origin https://github.com/ShreyTriesToCode/PitWall.git` instead of `git remote add origin ...`.

## Data Policy

Primary backend sources:

- Jolpica/Ergast-compatible race, standings, qualifying, laps, pit stops, sprint data
- FIA decision documents: timetable, classifications, starting grids, car presentation submissions, PU documents, race director notes, infringements, deleted laps, decisions, scrutineering, and post-race checks
- Formula1.com season calendar and event pages
- official Formula 1 timing/static feeds
- OpenF1 free historical timing/session API when reachable
- FastF1 session data when available
- Open-Meteo forecast and historical weather
- FIA/F1 regulation pages

Source confidence is explicit. FIA decision documents are highest confidence, Formula1.com and structured APIs are official/fallback context, and social upgrade sources are disabled by default because they are low-confidence and easy to misread.

The project degrades gracefully. If a source is unavailable, it records source status and falls back to cached or lower-confidence signals instead of stopping the run.

## Environment Reference

Supported season/source/session/model controls include:

```text
TARGET_SEASON=auto
SOURCE_DISCOVERY_ENABLED=true
REFRESH_SOURCE_REGISTRY=false
FIA_DOCUMENTS_ENABLED=true
FIA_DOCUMENTS_BASE_URL=https://www.fia.com/documents/championships/fia-formula-one-world-championship-14
FIA_DOCUMENTS_SEASON_URL=
FIA_DOCUMENTS_SEASON_URL_2026=https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2026-2072
FIA_DOCUMENTS_SEASON_URL_2027=
FIA_DOCUMENTS_SEASON_URL_2028=
FIA_DOCUMENT_CACHE_DIR=data_cache/fia-documents
REFRESH_FIA_DOCUMENTS=false
FORCE_REPARSE_FIA_DOCUMENTS=false
FORCE_REDOWNLOAD_FIA_DOCUMENTS=false
FIA_DOCUMENT_CACHE_TTL_MINUTES=60
FIA_REQUEST_SLEEP_SECONDS=1.0
MAX_FIA_DOCUMENTS_PER_RUN=0
MAX_FIA_PDFS_DOWNLOAD_PER_RUN=0
KEEP_FIA_PDFS=false
FIA_DOCUMENT_USER_AGENT=Mozilla/5.0 (compatible; PitWall/3.0; +https://github.com/ShreyTriesToCode/PitWall)
FIA_DOCUMENT_REFERER=https://www.fia.com/documents/championships/fia-formula-one-world-championship-14
FIA_DOCUMENT_STRICT_DOWNLOADS=false
FORMULA1_CALENDAR_BASE_URL=https://www.formula1.com/en/racing
FORMULA1_SEASON_URL=
SESSION_INGESTION_ENABLED=true
SESSION_RESULT_DELAY_MINUTES=30
PRACTICE_RESULT_DELAY_MINUTES=20
QUALIFYING_RESULT_DELAY_MINUTES=30
SPRINT_QUALIFYING_RESULT_DELAY_MINUTES=30
SPRINT_RESULT_DELAY_MINUTES=45
RACE_RESULT_DELAY_HOURS=8
SESSION_RETRY_INTERVAL_MINUTES=20
MAX_SESSION_RETRIES=8
FORCE_SESSION_INGEST=false
TARGET_EVENT=
TARGET_SESSION=
DRY_RUN_SESSION_INGEST=false
LIVE_TIMING_ENABLED=true
LIVE_STALE_AFTER_SECONDS=60
DISABLE_LIVE_MODE=false
TIMING_REPLAY_MODE_ALLOWED=true
USE_SOCIAL_UPGRADE_SOURCES=false
UPGRADE_MAX_WEIGHT_PRE_RUNNING=0.08
UPGRADE_MAX_WEIGHT_POST_PRACTICE=0.05
UPGRADE_MAX_WEIGHT_POST_QUALIFYING=0.03
REGULATION_CONTEXT_URL_2026=https://www.fia.com/news/new-era-competition-fia-showcases-future-focused-formula-1-regulations-2026-and-beyond
REGULATION_CONTEXT_URL_2027=
REGULATION_CONTEXT_URL_2028=
ENABLE_RACE_SIMULATION=true
RACE_SIMULATION_RUNS=5000
GITHUB_ACTIONS_RACE_SIMULATION_RUNS=1000
TRAINING_MODE=auto
MODEL_TRAINING_MAX_SECONDS=900
ENABLE_FEATURE_ABLATION=false
ENABLE_HYPERPARAMETER_SEARCH=false
MAX_TRAINING_RACES=auto
MODEL_LIGHT_MODE=false
LATEST_RUN_STATUS_PATH=data_cache/latest-run-status.json
MODEL_ARTIFACTS_DIR=model_artifacts
PITWALL_DB_PATH=data_cache/pitwall.db
F1DB_ENABLED=false
F1DB_RELEASE_TAG=v2026.4.2
F1DB_SQLITE_PATH=
F1DB_CSV_DIR=
RELBENCH_F1_ENABLED=false
RELBENCH_F1_DOWNLOAD=false
DRIFT_SPEARMAN_THRESHOLD=0.55
USE_LAST_VALID_CONTRACT_ON_ERROR=true
SKIP_NETWORK_TESTS=true
```

## Repository Hygiene

The repo is configured to include generated prediction/model data:

- `data_cache/`
- `models/saved_models/`
- `fastf1_cache/`
- `briefings/`

Local-only files are ignored:

- `.venv/`
- `frontend/.next/`
- `frontend/node_modules/`
- `__pycache__/`
- local `.env` files

## Contract Hardening

Run this before committing generated outputs:

```bash
python scripts/validate_contracts.py
python scripts/check_artifact_sizes.py
```

`validate_contracts.py` fails on blank, missing, or invalid contracts and requires `latest.top10`, `latest.full_grid`, `latest.all_predictions`, debug payloads, and model metrics. The frontend first reads `data_cache/frontend-contract.json`; if it is unusable it recovers from `data_cache/latest-model-debug.json`, then from `data_cache/frontend-contract.previous.json`, and shows a warning banner.

## Quality Commands

```bash
python -m py_compile f1_briefing.py
ruff check pitwall scripts tests
python -m unittest discover -s ./tests -p "test_*.py" -t .
cd frontend && npm ci && npm run build && npm test
```

See `RUNBOOK.md`, `MODEL_REPORT.md`, and `ARTIFACT_POLICY.md` for operator details, model design, experiment guidance, and remaining work.

## Free AI-Style Intelligence

PitWall includes deterministic AI-style summaries with no paid API requirement. These fields explain trust, source warnings, missing data, model disagreement, race-week uncertainty, and post-race audit themes from existing structured data only.

The default provider is `deterministic`; local Ollama and local RAG are optional development helpers. AI text is never allowed to modify rankings, Top 10, Full Grid, probabilities, race results, weather values, FIA notes, or live timing state.

See `RUNBOOK.md` for free deployment and optional local AI details.

## Model Notebook And Cache-Aware Training

Model refinement now has a dedicated notebook:

```bash
jupyter notebook notebooks/pitwall_model_refinement.ipynb
```

The notebook loads local artifacts from `data_cache/`, `model_artifacts/`, `models/saved_models/`, and `briefings/`; checks feature availability, missing values, schema stability, leakage rules, chronological race grouping, champion metadata, ranking/regression metrics, and optional challenger training gates. It keeps outputs small and does not redownload upstream data.

Workflow training is cache-aware. `CACHE_AWARE_DOWNLOADS=true` records reuse/refresh/skip decisions in `data_cache/cache_manifest.json`; `FORCE_REFRESH_DATA=true` refreshes stale or invalid data; `FORCE_RETRAIN=true` requests model retraining. Valid cached historical race files are reused, corrupted or schema-invalid files are refreshed, optional source failures are surfaced through source health, and required training data failures block promotion.

Before trusting a run, verify both compact and complete prediction surfaces:

```bash
python3 scripts/validate_contracts.py
python3 scripts/validate_cache_manifest.py
```

`latest.top10` is the compact Top 10 view, while `latest.full_grid` and `latest.all_predictions` preserve the complete grid. Predictions are probabilistic estimates, not guaranteed race results or fabricated confidence claims.

## Model And Actual-Result Comparison

Generated contracts now include `model_comparison` and `actual_result_comparison`. The model comparison records champion/challenger metadata, promotion decision, ranking metrics, and Brier/calibration fields where available. The actual-result comparison uses only trusted cached `Results` classifications; if those rows are missing, delayed, stale, or incomplete, the contract status is `pending`, `unavailable`, or `incomplete` with warnings.

The website renders these states on `/model` and `/archive`. Link and route checks can be run locally:

```bash
python scripts/check_links.py
```

Use `--check-external` only when you intentionally want bounded HTTP checks against external links.
