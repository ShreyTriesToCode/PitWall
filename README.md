# F1 Race Intel

F1 Race Intel generates Formula 1 sprint and race predictions, publishes readable briefings, sends optional email/GitHub notifications, and serves a Next.js dashboard with a live timing view.

The backend keeps a cache-first pipeline around Jolpica, official Formula 1 live timing feeds, optional OpenF1 free historical timing, FastF1, Open-Meteo, FIA/F1 upgrade context, and local historical race caches.

## What It Produces

- Sprint Race prediction
- Final Race prediction
- Briefing markdown in `briefings/`
- Dashboard data in `briefings/index.json` and `data_cache/latest-model-debug.json`
- Latest model/accuracy report in `MODEL_STATUS.md`
- Optional GitHub issue and Gmail output when notification gates open

## Prediction System

The current model is a hybrid ensemble:

- RF/HGB/ExtraTrees classifiers for win, podium, and top 10 probabilities
- RF/HGB/ExtraTrees regressors for predicted finishing position
- scaled `MLPRegressor` neural submodel for lap-time pace forecasting
- official F1 timing signals: sectors, speed trap/telemetry speed, stints, pits, starting grid, session result, and position gain
- optional OpenF1 free historical timing signals: drivers, laps, session results, pits, stints, sector pace, speed, and grid/result cross-checks
- driver traits: form, racecraft, reliability, qualifying delta, circuit history, grid gain, consistency
- car/team traits: constructor form, current-season pace, recent form, pit execution, team strategy, official upgrade-package traits
- track/weather traits: overtaking, tyre stress, safety-car/DNF proxy, rain, heat, wind, track-position sensitivity
- regulation context for 2025 wing-flex, 2026 active-aero/power-unit reset, and later rules

Model design notes live in `MODEL_DESIGN.md`.

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
.venv/bin/python -m unittest discover -s tests
```

Run the frontend:

```bash
cd frontend
npm run dev
```

Dashboard: `http://localhost:3000`

## Generate A Briefing

Required for calendar matching:

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
FULL_DATA_BACKFILL_LIMIT=10
OUTPUT_MODE=auto
FORCE_NOTIFY=false
NOTIFICATION_WINDOW_HOURS=8
```

Use `FORCE_RETRAIN=true` after model schema changes. Increase `FULL_DATA_BACKFILL_LIMIT` only when intentionally refreshing historical cache.

## Frontend

Pages:

- `/` prediction dashboard
- `/live` live timing dashboard
- `/api/f1timing` Formula 1 live timing proxy with Jolpica fallback
- `/api/audio` radio/audio proxy

The live page auto-selects the active or latest useful F1 session. It formats driver names, leaderboard, tyres/stints, weather, race control, and team radio when the source allows access.

## GitHub Workflow

`.github/workflows/f1-briefing.yml` runs on schedule and manual dispatch.

Workflow shape:

1. Restore FastF1, HTTP, full-race, and model caches.
2. Install Python dependencies.
3. Compile and run unit tests.
4. Check whether Jolpica has a newly completed GP result after `FINAL_RESULTS_DELAY_HOURS`.
5. Retrain automatically if a new result exists, the model is missing, the schema changed, or manual force retrain was requested.
6. Generate sprint/race predictions.
7. Update `MODEL_STATUS.md`, `briefings/`, `briefings/index.json`, and `data_cache/latest-model-debug.json`.
8. Upload complete artifacts for inspection.

Automatic behavior:

- Scheduled runs happen daily and every 6 hours Thursday through Monday around race weekends.
- Scheduled `OUTPUT_MODE=auto` resolves to today-only Sprint/Race output.
- If a Grand Prix has just ended, the workflow waits until `FINAL_RESULTS_DELAY_HOURS` has passed.
- After that cutoff, it bypasses stale HTTP result cache and retrains only once the API returns final `Results` rows.
- If the API still has no final results, it records that state in `MODEL_STATUS.md` and keeps the current model for predictions.
- Email/GitHub issue output is sent only inside the notification window unless `FORCE_NOTIFY=true`.

Manual controls from `workflow_dispatch`:

- `force_retrain`: retrain even when no new race result is available.
- `full_data_backfill_limit`: fetch more uncached historical races.
- `lookahead_days`: search further ahead in the calendar.
- `output_mode`: choose `auto`, `weekend`, `today`, or `next`.
- `send_email`: allow or suppress email output.
- `force_notify`: send notifications outside the normal gate.
- `notification_window_hours`: change the event notification window.

Generated runtime state is ignored for new files. Existing tracked caches are left alone to avoid a noisy repository rewrite.

## Data Policy

Primary backend sources:

- Jolpica/Ergast-compatible race, standings, qualifying, laps, pit stops, sprint data
- official Formula 1 live timing static feeds
- OpenF1 free historical timing/session API when reachable
- FastF1 session data when available
- Open-Meteo forecast and historical weather
- Formula1.com calendar checks
- FIA/F1 upgrade and regulation pages, including car-presentation PDFs when reachable

The project degrades gracefully. If a source is unavailable, it records source status and falls back to cached or lower-confidence signals instead of stopping the run.

## Do Not Commit

New generated cache/model churn is ignored:

- `data_cache/http/`
- `data_cache/full_races/`
- `data_cache/ml_*`
- `models/saved_models/`
- `fastf1_cache/`
- `frontend/.next/`
- `frontend/node_modules/`
