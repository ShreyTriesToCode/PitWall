# PitWall Verification Report

[Documentation index](README.md) -> [Runbook](../RUNBOOK.md)

Generated on 2026-05-24.

## 2026-05-29 Free AI Intelligence Pass

- `python -m py_compile f1_briefing.py ...`: passed.
- `ruff check pitwall scripts tests`: passed.
- `python -m unittest discover -s ./tests -p "test_*.py" -t .`: passed, 68 tests.
- `python scripts/validate_contracts.py`: passed with top10=10, full_grid=22, all_predictions=22.
- `python scripts/check_artifact_sizes.py`: passed with warnings for two existing FastF1 cache files over 25 MB.
- `python scripts/generate_run_report.py`: passed and wrote `RUN_REPORT.md`.
- `python scripts/query_local_rag.py "model trust"`: returned the expected no-index fallback, "Not enough data in local PitWall sources."
- `npm ci`: passed.
- `npm audit --audit-level=high`: passed with 0 vulnerabilities.
- `npm run build`: passed, including `/assistant`.
- `npm run test --if-present`: passed after installing Playwright Chromium, 5/5 smoke tests.

Known warnings: artifact-size checker still warns on two pre-existing FastF1 cache files (`car_data.ff1pkl`, `position_data.ff1pkl`) above 25 MB but below the configured failure threshold.

## API Documentation Checked

- OpenF1 authentication docs: https://openf1.org/auth.html
- OpenF1 API docs: https://openf1.org/docs/
- Jolpica F1 docs and pagination: https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md
- FastF1 docs: https://docs.fastf1.dev/fastf1.html
- Open-Meteo forecast docs: https://open-meteo.com/en/docs
- FIA 2026 decision documents page: https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2026-2072
- FIA 2026 regulation context: https://www.fia.com/news/new-era-competition-fia-showcases-future-focused-formula-1-regulations-2026-and-beyond
- Formula1.com 2026 calendar: https://www.formula1.com/en/racing/2026
- F1DB release/schema/license docs: https://github.com/f1db/f1db and https://github.com/f1db/f1db/releases
- RelBench rel-f1 dataset/tasks/license docs: https://relbench.stanford.edu/datasets/rel-f1/

## Commands Run

Follow-up reliability/UI release pass on 2026-05-25:

Remaining partial/missing closure pass on 2026-05-25:

```bash
.venv/bin/python -m py_compile f1_briefing.py pitwall/config.py pitwall/storage.py pitwall/models/simulation.py pitwall/models/contract.py pitwall/features/strategy.py pitwall/data/fia_documents.py pitwall/data/bootstrap.py scripts/bootstrap_datasets.py
```

Result: passed.

```bash
.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .
```

Result: passed, 52 tests.

```bash
.venv/bin/python -c "import f1_briefing as f; f.save_model_status_json(); f.generate_frontend_contract_files()"
```

Result: passed and regenerated model-status/frontend-contract artifacts.

```bash
.venv/bin/python scripts/bootstrap_datasets.py f1db
.venv/bin/python scripts/bootstrap_datasets.py relbench
```

Result: passed after fixing the script wrapper to add the repo root to `sys.path`. Both commands print dry-run setup plans and do not download datasets by default.

```bash
cd frontend && npm install
cd frontend && npm run build
```

Result: passed. The timing route now prefers season-based Formula1.com track images, for example the 2026 Montreal and Monte Carlo detailed track images, with legacy circuit maps as fallback.

```bash
node -e "...parse data_cache/frontend-contract.json..."
node -e "...inspect frontend/app/api/f1timing/route.js..."
```

Result: passed. The static contract check confirmed `top10=10`, `top_10=10`, `full_grid=22`, `all_predictions=22`, `race_factors`, warnings, strategy, explanation, and source notes. The route check confirmed season-track image helpers and timing auto-selection metadata.

Skipped: final live `npm run dev` route smoke was blocked because this environment rejected the required elevated server start approval. The production build and static route/contract checks passed, and previous local route smoke for the same app shape returned HTTP 200.

```bash
.venv/bin/python -m py_compile f1_briefing.py
```

Result: passed.

```bash
.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .
```

Result: passed, 46 tests.

```bash
.venv/bin/python -c "import f1_briefing as f; f.save_model_status_json(); f.generate_frontend_contract_files()"
```

Result: passed. The run regenerated frontend contract/model-status artifacts and handled an optional Jolpica sprint-qualifying 404 as unavailable source data.

```bash
cd frontend && npm install
```

Result: passed, 0 vulnerabilities.

```bash
cd frontend && npm run build
```

Result: passed on Next.js 16.2.6.

```bash
curl -sS -o /tmp/pitwall-predictions.json -w "%{http_code}" http://localhost:3000/api/predictions
curl -sS -o /tmp/pitwall-model-status.json -w "%{http_code}" http://localhost:3000/api/model-status
curl -sS -o /tmp/pitwall-source-health.json -w "%{http_code}" http://localhost:3000/api/source-health
curl -sS -o /tmp/pitwall-f1timing.json -w "%{http_code}" "http://localhost:3000/api/f1timing?fast=1"
curl -sS -o /tmp/pitwall-page-predictions.html -w "%{http_code}" http://localhost:3000/predictions
curl -sS -o /tmp/pitwall-page-live.html -w "%{http_code}" http://localhost:3000/live
curl -sS -o /tmp/pitwall-page-home.html -w "%{http_code}" http://localhost:3000/
```

Result: all returned HTTP 200. `/api/predictions` included `top10`, `top_10`, `full_grid`, `all_predictions`, `race_factors`, and `warnings`; the generated top-10 length was 10 and full-grid length was 22. `/api/f1timing?fast=1` returned stable auto-selection metadata and 22 archive/fallback timing rows.

Browser automation note: Playwright was not installed in the local Node runtime, so mobile drawer verification used static unit assertions, Next production build, and route/API smoke checks rather than a Playwright screenshot run.

```bash
.venv/bin/python -m py_compile f1_briefing.py
```

Result: passed.

```bash
TARGET_SEASON=auto FIA_DOCUMENTS_ENABLED=true OPENF1_OPTIONAL_ONLY=true FULL_DATA_BACKFILL_LIMIT=0 FORCE_RETRAIN=true MAX_FIA_DOCUMENTS_PER_RUN=0 MAX_FIA_PDFS_DOWNLOAD_PER_RUN=0 KEEP_FIA_PDFS=false .venv/bin/python -u f1_briefing.py
```

Result: passed after rerunning with network access outside the sandbox. The sandboxed run failed DNS resolution for `www.fia.com`, so it was stopped and rerun with approved network access.

```bash
.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .
```

Result: passed, 34 tests.

Follow-up run after F1DB/RelBench adapters, timing fallback, path sanitation,
and CI auto-commit gate:

```bash
.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .
```

Result: passed, 41 tests.

```bash
cd frontend && npm install
```

Initial result: passed with 2 Next/PostCSS advisories. Next was updated to
`16.2.6` and PostCSS was overridden to `8.5.10`.

```bash
cd frontend && npm audit --json
```

Result: passed with 0 vulnerabilities.

```bash
cd frontend && npm run build
```

Result: passed.

Follow-up build after dependency and frontend route fixes:

```bash
cd frontend && npm run build
```

Result: passed on Next.js 16.2.6.

```bash
curl -sS -o /tmp/pitwall-predictions.json -w "%{http_code}" http://localhost:3000/api/predictions
curl -sS -o /tmp/pitwall-model-status.json -w "%{http_code}" http://localhost:3000/api/model-status
curl -sS -o /tmp/pitwall-source-health.json -w "%{http_code}" http://localhost:3000/api/source-health
curl -sS -o /tmp/pitwall-f1timing.json -w "%{http_code}" "http://localhost:3000/api/f1timing?fast=1"
```

Result: all returned HTTP 200.

After fixing the `fast=1` fallback path, `/api/f1timing?fast=1` returned
`ok: true`, `source: JolpicaFallback`, `timing_mode: archive`, and 22 fallback
result rows when primary timing feeds were empty.

```bash
curl -sS -o /tmp/pitwall-f1timing-rate-a.json -w "%{http_code}" "http://localhost:3000/api/f1timing?fast=1"
curl -sS -o /tmp/pitwall-f1timing-rate-b.json -w "%{http_code}" "http://localhost:3000/api/f1timing?fast=1"
```

Result: one request returned HTTP 200 and the duplicate request returned HTTP 429 with `retry_after_seconds`.

```bash
curl -sS -o /tmp/pitwall-page-home.html -w "%{http_code}" http://localhost:3000/
curl -sS -o /tmp/pitwall-page-predictions.html -w "%{http_code}" http://localhost:3000/predictions
curl -sS -o /tmp/pitwall-page-live.html -w "%{http_code}" http://localhost:3000/live
curl -sS -o /tmp/pitwall-page-model.html -w "%{http_code}" http://localhost:3000/model
curl -sS -o /tmp/pitwall-page-drivers.html -w "%{http_code}" http://localhost:3000/drivers
curl -sS -o /tmp/pitwall-page-teams.html -w "%{http_code}" http://localhost:3000/teams
curl -sS -o /tmp/pitwall-page-strategy.html -w "%{http_code}" http://localhost:3000/strategy
curl -sS -o /tmp/pitwall-page-archive.html -w "%{http_code}" http://localhost:3000/archive
```

Result: all returned HTTP 200.

## Retrain Summary

- Model schema: `2026.06-barcelona-preweekend-v6`
- Trained at: `2026-05-24T12:12:55.906446+05:30`
- Historical completed races used: 177
- Future or not-final 2026 races skipped: 18
- Feature count after pruning: 42
- Validation rows: 1359
- Out-of-time rows: 567
- Out-of-time seasons: 2025 and completed 2026 races

Validation metrics:

- Win AUC: 0.9630
- Podium AUC: 0.9343
- Top-10 AUC: 0.8799
- Finish MAE: 3.2158
- Finish RMSE: 4.1115
- Winner hit rate: 0.2941
- Top-3 recall: 0.6127
- Top-10 recall: 0.8206
- Spearman: 0.7227
- NDCG@3: 0.8843
- NDCG@10: 0.9028

Out-of-time gate:

- Finish MAE: 3.3675
- Top-3 recall: 0.6429
- Top-10 recall: 0.7786
- Spearman: 0.7250
- NDCG@3: 0.9170
- NDCG@10: 0.9090

Promotion decision: hold champion. The challenger did not beat grid/qualifying baselines on every out-of-time race-order metric, so the system now reports this honestly instead of promoting on AUC alone.

## Source Status

- FIA 2026 decision index was available and cached.
- 85 FIA documents were indexed for the current 2026 season context.
- OpenF1 is optional. No live OpenF1 auth error remained in the generated run; the frontend and backend expose auth-restricted states when 401/403 responses occur.
- FastF1 loaded Canada qualifying, sprint qualifying, sprint, and FP1. Canada race data remained unavailable before the final-result delay, which is correct.
- Jolpica schedule/results endpoints were available.

## Frontend Notes

- Next.js production build passed.
- Driver detail drawer now uses a viewport-fixed mobile bottom sheet with safe-area padding and scroll lock.
- `/predictions` target switching now uses selected-target values for metrics, FIA counts, timing mode, source state, and scenarios.
- `/api/f1timing` rate limit verified.
- `/api/f1timing?fast=1` now materializes public Jolpica fallback data even when fast mode skips OpenF1 enrichment.
- `/live` labels archive/replay data separately from genuine live timing.
- Generated JSON and SQLite payloads were scanned for the local workspace path and no absolute local paths remained.

## Remaining Gaps

- Browser-level Playwright testing was not available because `playwright` is not installed and dependency download was not possible in this run. Static tests and route smoke checks cover the mobile drawer and page availability.
- Historical odds, Pirelli allocation, and technical-directive timeline sources remain optional future improvements unless legal, reliable APIs or curated fixtures are added.
- F1DB and RelBench rel-f1 are integrated as optional adapters/source-health entries only. No F1DB release artifact or RelBench package/data is bundled by default, so they did not affect the retrained metrics in this run.
- The challenger model is better than several baselines but still fails the strict out-of-time promotion gate against grid/qualifying on some ranking metrics.

## Remaining Partial Closure Pass

Date: 2026-05-25.

Additional implementation completed:

- Extracted stable simulation, contract, strategy, FIA document, SQLite storage, and dataset-bootstrap helpers into `pitwall/` modules while keeping `f1_briefing.py` public wrappers intact.
- Added deterministic FIA PDF `403/404` handling so forbidden decision documents do not retry four times. Cached parsed text is reused with `stale_cache_forbidden`; uncached documents are marked `forbidden` and surfaced through warnings.
- Added strategy-context annotations for tyre/weather mismatch, early tyre correction, safety-car/VSC/red-flag pit context, double-stack loss, traffic hints, degradation cliffs, and post-switch pace improvement.
- Added dry-run F1DB and RelBench bootstrap tooling. No external dataset artifacts are downloaded or committed by default.
- Updated timing track visuals to prefer season-based Formula1.com detailed track images, including 2026 Montreal and Monte Carlo examples.

Commands run:

```bash
.venv/bin/python -m py_compile f1_briefing.py pitwall/config.py pitwall/storage.py pitwall/models/simulation.py pitwall/models/contract.py pitwall/features/strategy.py pitwall/data/fia_documents.py pitwall/data/bootstrap.py scripts/bootstrap_datasets.py
.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .
.venv/bin/python -c "import f1_briefing as f; f.save_model_status_json(); f.generate_frontend_contract_files()"
.venv/bin/python scripts/bootstrap_datasets.py f1db
.venv/bin/python scripts/bootstrap_datasets.py relbench
cd frontend && npm install
cd frontend && npm run build
```

Results:

- Python compile passed.
- Unit tests passed: 52 tests.
- Frontend contracts/model status regenerated.
- F1DB and RelBench bootstrap commands produced dry-run plans only.
- Frontend install passed with 0 vulnerabilities.
- Next.js production build passed on Next.js 16.2.6.
- Static contract smoke passed: `top10`, `top_10`, `full_grid`, `all_predictions`, `race_factors`, row explanations, source notes, and strategy fields are present under the latest prediction contract.
- Static timing smoke passed: season-based track-image URL builder, 2026 Montreal and Monte Carlo image examples, auto session selection fields, warnings, and safe normalized timing payload handling are present.

Skipped:

- Final live `npm run dev` HTTP smoke was skipped because the required elevated local server start was rejected by the app approval layer. Production build, unit tests, contract checks, and static route-code checks passed.

## Contract Trust Hardening Pass

Date: 2026-05-28.

Additional implementation completed:

- Added `scripts/validate_contracts.py` to reject blank/invalid frontend, briefing, debug, and model-status artifacts.
- Added `data_cache/frontend-contract.previous.json`, `data_cache/model-status.previous.json`, and `briefings/index.previous.json` rollback writes.
- Added frontend recovery from `data_cache/latest-model-debug.json` and previous valid contract artifacts, with visible warning flags.
- Added per-driver `model_disagreement_level`, `model_disagreement_reasons`, `prediction_trust_score`, `prediction_trust_label`, missing feature groups, source warnings, and stage limitations.
- Added `/sources` route, Playwright smoke tests, pinned frontend dependencies, pinned Python runtime dependencies, ruff config, and artifact-size checking.
- Added `/api/f1timing` short TTL response caching with `timing_cache_status`, `server_fetched_at`, and `source_packet_at`.

Commands run:

```bash
.venv/bin/python -m py_compile f1_briefing.py pitwall/models/agreement.py pitwall/models/trust.py pitwall/contracts/frontend_contract.py pitwall/validation/contracts.py pitwall/validation/leakage.py scripts/validate_contracts.py scripts/check_artifact_sizes.py
.venv/bin/ruff check pitwall scripts tests
.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .
.venv/bin/python scripts/validate_contracts.py
.venv/bin/python scripts/check_artifact_sizes.py
cd frontend && npm ci
cd frontend && npm run build
cd frontend && npm audit --audit-level=high
```

Results:

- Python compile passed.
- Ruff passed.
- Unit tests passed: 59 tests.
- Contract validator passed with 10 Top 10 rows and 22 full-grid/all-prediction rows.
- Artifact-size checker passed. It reported two FastF1 cache warnings above 25 MB and no failures above 95 MB.
- Frontend install passed.
- Next.js production build passed and included the new `/sources` route.
- npm audit passed with 0 high-or-higher vulnerabilities.
- Static contract smoke confirmed trust/disagreement fields, change summary, rollback contract, debug recovery hooks, and timing cache metadata.

Skipped:

- Local Playwright execution was attempted but blocked by sandbox permissions: Next could not bind `127.0.0.1:3000`, and the elevated `npm test` retry was rejected by the app approval layer. The Playwright smoke tests and CI steps are committed so GitHub Actions can run them in an environment that allows local server binding.
