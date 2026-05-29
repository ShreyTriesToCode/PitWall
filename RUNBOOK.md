# PitWall Runbook

## Local Verification

```bash
.venv/bin/python -m py_compile f1_briefing.py
.venv/bin/ruff check pitwall scripts tests
.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .
.venv/bin/python scripts/validate_contracts.py
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
