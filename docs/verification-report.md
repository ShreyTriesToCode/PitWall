# PitWall Verification Report

Generated on 2026-05-24.

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

- Model schema: `2026.05-high-accuracy-v5`
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
