# PitWall Runbook

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

For browser smoke tests:

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

## Free AI And Contribution Notes

Deterministic AI summaries are generated from existing contract fields only. To rebuild optional local search:

```bash
python scripts/build_local_rag_index.py
python scripts/query_local_rag.py "source warnings"
```

Local Ollama is disabled unless `LOCAL_LLM_ENABLED=true` and `OLLAMA_MODEL` is set. It is never used in GitHub Actions or Vercel by default.

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
