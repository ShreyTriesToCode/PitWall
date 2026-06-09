# PitWall Runbook

[Documentation index](docs/README.md) -> [README](README.md) -> [Model Report](MODEL_REPORT.md) -> [Data Sources](DATA_SOURCES.md) -> [Artifact Policy](ARTIFACT_POLICY.md)

## Setup

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cd frontend
npm install
```

The app works locally without private credentials. Useful defaults:

```bash
TARGET_SEASON=auto
OPENF1_OPTIONAL_ONLY=true
FULL_DATA_BACKFILL_LIMIT=0
FORCE_RETRAIN=false
ENABLE_RACE_SIMULATION=true
RACE_SIMULATION_RUNS=10000
F1_TIMING_RATE_LIMIT_MS=5000
```

Optional OpenF1, F1DB, RelBench, local LLM, and local RAG settings should stay in your shell or deployment environment, never in Git. Use `.env.example` as the safe reference.

Plan optional offline dataset setup without downloading large artifacts:

```bash
.venv/bin/python scripts/bootstrap_datasets.py f1db
.venv/bin/python scripts/bootstrap_datasets.py relbench
```

## Local Verification

```bash
.venv/bin/python -m py_compile f1_briefing.py
.venv/bin/ruff check pitwall scripts tests
.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .
.venv/bin/python scripts/validate_contracts.py
.venv/bin/python scripts/validate_cache_manifest.py
.venv/bin/python scripts/check_links.py
.venv/bin/python scripts/check_artifact_sizes.py
cd frontend && npm ci && npm run build
```

Browser smoke tests are optional local checks, not part of the default GitHub Actions path:

```bash
cd frontend
npx playwright install chromium
npm test
```

## Regenerate Contracts

```bash
.venv/bin/python -c "import f1_briefing as f; f.save_model_status_json(); f.generate_frontend_contract_files()"
.venv/bin/python scripts/validate_contracts.py
.venv/bin/python scripts/validate_cache_manifest.py --allow-missing
```

This updates frontend contracts, rollback contracts, feature summaries, backtest summaries, and model status.

## Broken Contract Recovery

1. Run `python scripts/validate_contracts.py`.
2. If `frontend-contract.json` is invalid, inspect `data_cache/latest-model-debug.json`.
3. The frontend API will recover from debug payloads when possible and set `contract_recovered_from_debug: true`.
4. If debug payloads are unavailable, the frontend tries `data_cache/frontend-contract.previous.json`.
5. Regenerate contracts before committing.

## FIA Document 403s

FIA PDFs can return deterministic `403`. PitWall fetches decision documents with browser-like headers once. If a cached parse exists, it marks the source as `stale_cache_forbidden`; otherwise it marks the document `forbidden` and continues with warnings. Do not hide these warnings.

## Live Timing

`/api/f1timing` labels data as `Live`, `Delayed`, `Stale`, `Archive`, or `Unavailable` based on packet freshness and session state. It uses a short in-memory response cache:

- live/active: 3 seconds
- delayed/recent: 30 seconds
- archive/fallback: 6 hours

Serverless instances do not share in-memory cache. Redis/Vercel KV can be added later if shared cache becomes necessary.

## Free Deployment, AI, And Contribution Notes

PitWall is designed to run without paid AI, paid databases, paid Redis, or paid model hosting:

- GitHub Actions performs heavy Python/model generation.
- Generated JSON artifacts are committed to `main` only after validation passes.
- Vercel Hobby can serve the Next.js frontend and lightweight API routes.
- Deterministic AI-style features summarize existing structured fields only.

Default no-paid-service flags:

```env
FREE_MODE=true
AI_FEATURES_ENABLED=false
DETERMINISTIC_EXPLANATIONS_ENABLED=true
LOCAL_LLM_ENABLED=false
LOCAL_RAG_ENABLED=false
HUGGINGFACE_SPACE_AI_ENABLED=false
GITHUB_RAW_DATA_FALLBACK=true
USE_LAST_VALID_CONTRACT_ON_ERROR=true
```

Deterministic AI summaries are generated from existing contract fields only. To rebuild optional local search:

```bash
.venv/bin/python scripts/build_local_rag_index.py
.venv/bin/python scripts/query_local_rag.py "source warnings"
```

Local Ollama is disabled unless `LOCAL_LLM_ENABLED=true` and `OLLAMA_MODEL` is set. It is never used in GitHub Actions or Vercel by default, and local AI text cannot change rankings, probabilities, race results, weather, FIA notes, penalties, or live timing labels.

Workflow-generated commits use `Shreyansh Singhal <111811929+ShreyTriesToCode@users.noreply.github.com>` as the author so real generated-output commits on `main` can count toward the linked GitHub contribution graph. GitHub can take up to 24 hours to show contributions; bot-only author emails may not appear.

## Retraining And Cache Reuse

Local CI-style run:

```bash
FORCE_RETRAIN=true FORCE_REFRESH_DATA=false CACHE_AWARE_DOWNLOADS=true PITWALL_CI=true .venv/bin/python f1_briefing.py
```

Use `FORCE_REFRESH_DATA=true` only when the manifest or cache validation says data is missing, stale, corrupted, or schema-invalid. Inspect `data_cache/cache_manifest.json` to see which datasets were reused, refreshed, skipped, or served as fallback.

Notebook:

```bash
jupyter notebook notebooks/pitwall_model_refinement.ipynb
```

The notebook is read-mostly by default. It explains metrics and has an explicit `RUN_CHALLENGER` switch for heavier retraining.

## Visible Training Logs

Set these flags for the same progress output used in GitHub Actions:

```bash
FORCE_RETRAIN=true FORCE_REFRESH_DATA=false CACHE_AWARE_DOWNLOADS=true PITWALL_CI=true SHOW_TRAINING_PROGRESS=true COMPARE_ACTUAL_RESULTS=true .venv/bin/python f1_briefing.py
```

The run prints `[TRAIN]`, `[CACHE]`, `[MODEL]`, `[VALIDATE]`, `[ACTUALS]`, `[ROUTE]`, and `[DONE]` markers plus a `PitWall training summary` table. The summary reports cache reuse/refresh counts, race-group split sizes, feature count, ranking metrics, promotion decision, artifact path, contract path, and total runtime.

## Model And Actual Comparisons

`data_cache/model-status.json` exposes `model_comparison`; `data_cache/frontend-contract.json` exposes both `model_comparison` and `actual_result_comparison`. The actual comparison is `available` only when trusted actual result rows exist in cached/project sources. Otherwise it stays `pending`, `unavailable`, or `incomplete` and the frontend renders that state instead of inventing race results.

The model page shows champion/challenger, promotion, ranking/calibration metrics, and predicted-vs-actual details. The archive page shows per-briefing actual-result status and recall when available.

## Link Checks

Offline route/link validation:

```bash
.venv/bin/python scripts/check_links.py
```

Optional bounded external checks:

```bash
.venv/bin/python scripts/check_links.py --check-external
```

## Required Output Checks

- `/predictions` shows Race Overview, Top 10 Prediction, and Full Grid Prediction.
- Driver details open in a scrollable drawer with probabilities, strategy, explanation, risk, and source notes.
- `/live` auto-selects the best available timing session or shows a safe fallback state.
- `/api/predictions` includes `top10`, `top_10`, `full_grid`, `all_predictions`, `race_factors`, and `warnings`.
- `/sources` shows source-health status and any auth/fallback warnings.

Continue with [Model Report](MODEL_REPORT.md) for modelling details and [Artifact Policy](ARTIFACT_POLICY.md) for what is allowed in Git.
