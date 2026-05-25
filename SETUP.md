# PitWall Setup

## 1. Install

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cd frontend
npm install
```

## 2. Configure

Copy `.env.example` into your shell or deployment environment. The app works locally without private credentials.

Useful defaults:

```bash
TARGET_SEASON=auto
OPENF1_OPTIONAL_ONLY=true
FULL_DATA_BACKFILL_LIMIT=0
FORCE_RETRAIN=false
ENABLE_RACE_SIMULATION=true
RACE_SIMULATION_RUNS=10000
F1_TIMING_RATE_LIMIT_MS=5000
```

OpenF1 live/higher-access data may need:

```bash
OPENF1_ACCESS_TOKEN=
OPENF1_USERNAME=
OPENF1_PASSWORD=
```

Optional offline datasets:

```bash
F1DB_ENABLED=false
F1DB_SQLITE_PATH=
F1DB_CSV_DIR=
RELBENCH_F1_ENABLED=false
```

## 3. Verify Backend

```bash
.venv/bin/python -m py_compile f1_briefing.py
.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .
```

## 4. Generate Prediction Contracts

```bash
.venv/bin/python -c "import f1_briefing as f; f.save_model_status_json(); f.generate_frontend_contract_files()"
```

Full run/retrain when needed:

```bash
TARGET_SEASON=auto FIA_DOCUMENTS_ENABLED=true OPENF1_OPTIONAL_ONLY=true FULL_DATA_BACKFILL_LIMIT=0 FORCE_RETRAIN=true .venv/bin/python f1_briefing.py
```

## 5. Run Frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000`.

## 6. Check Required Outputs

- `/predictions` should show Race Overview, Top 10 Prediction, and Full Grid Prediction.
- Clicking a driver should open a scrollable detail drawer with probabilities, strategy, explanation, risk, and source notes.
- `/live` should auto-select the best available timing session or show a safe fallback state.
- `/api/predictions` should include `top10`, `top_10`, `full_grid`, `all_predictions`, `race_factors`, and `warnings`.
