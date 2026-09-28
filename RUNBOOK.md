# PitWall operations

## Supported runtime

Python 3.11; Node 24 LTS; Next.js 16.3.5. The clean local verification used Python
3.11 and Node 26.8.1; CI targets Node 24. Do not infer that a cloud deployment or
GitHub workflow has run from local tests.

## Publish

From the repository root:

```sh
.venv/bin/python scripts/refresh_fia_metadata.py
.venv/bin/python -m pitwall.publish
.venv/bin/python scripts/validate_product.py
```

FIA metadata refresh retains the existing resolver, including official archive
fallbacks and source/error metadata. A 403 from the primary FIA page is possible;
do not erase the error or relabel a cached fallback as a fresh primary result.
No PDF downloading or model training is needed for this publication command.

`--backtest` explicitly regenerates the retrospective report from original local
provider records. Review dataset hashes, exclusions and results before committing
an updated report; do not automatically run model selection on each race.

The workflow runs hourly with a single concurrency group. It records
forecasts when qualifying is available before race start, and compares captured
past events after a complete result appears. Git push conflicts fail for human
review; no automatic merge resolution discards forecast history.

## Persistent files

- `data_cache/product.json`: version 3 published application contract; below 5 MB.
- `data_cache/ledger/predictions/*.json`: immutable captured forecasts.
- `data_cache/ledger/evaluations/*.json`: immutable result/evaluation revisions.
- `data_cache/evaluated-dataset.json`: derived final-capture/latest-result dataset.
- `data_cache/ranking-backtest.json`: reviewed retrospective report.
- `data_cache/fia-documents/*/season_index.json`: original FIA metadata provenance.

Back up ledger directories and use durable storage. Forecasts are appended using
atomic hard links on the same filesystem. Ephemeral serverless filesystems cannot
replace persistent storage. The Next app is read-only; it does not capture forecasts
or write to the ledger from a GET request.

Runtime provider caches (`data_cache/provider`) expire in five minutes and are
ignored by Git. The scheduled job's cache is an optimization, never the source
of forecast history. Existing old HTTP/CSV/model/SQLite files are research inputs;
they are not current production fallbacks.

## Environment

| Setting | Meaning |
|---|---|
| `PITWALL_PROJECT_ROOT` | Optional absolute root containing `data_cache`. Python defaults to its module root; Next defaults to the parent of its frontend working directory. |
| `PITWALL_DATA_BASE_URL` | Optional trusted HTTPS directory for missing local product files. No implicit cross-version GitHub fallback. |
| `F1_TIMING_RATE_LIMIT_MS` | Timing request interval per forwarded client identity; default 5000 ms. This is process-local protection, not a distributed security boundary. |
| `PITWALL_TIMING_AUTO_SELECT` | Prefer scheduled current sessions when available; default true. |
| `LIVE_TIMING_ENABLED` / `DISABLE_LIVE_MODE` | Enable the live label only when source evidence also meets the freshness rules. |

The example values are in `.env.example`. Next reads `frontend/.env.local`.
Do not put secrets into `NEXT_PUBLIC_*` variables. There are no required AI,
OpenF1, email or database credentials for the active product.

## Deploy

1. Run the complete validation commands in the README.
2. Deploy `frontend` using `npm ci`, `npm run build`, `npm start`. The Next tracing
   includes the small root `data_cache/product.json`; verify the deployment bundle
   has it or configure a trusted published data base explicitly.
3. Verify `/api/predictions`, `/api/archive`, `/api/model-status`, `/api/backtest`,
   `/api/source-health`, `/live` and all main pages after deployment.
4. Confirm the current calendar comes from a fresh request. A stale contract must
   never reinstate a completed race as current.
5. Confirm scheduled publication permissions/branch protection and persistent
   ledger storage. Missing workflows should surface as failed/missing publication,
   not made-up data. The request-time calendar and browser expiry remain defenses.

No changes in this audit automatically publish or deploy to the existing public site.

## Failure handling

- **Calendar unavailable:** check the provider request/error logs. The UI must show
  unavailable current event data. Do not copy a hardcoded next race into the app.
- **Qualifying empty:** normal before qualifying; ranking remains unavailable.
- **Result/entrant mismatch:** leave evaluation pending, investigate substitution,
  disqualification or incomplete source data. Never compare only a convenient subset.
- **Corrupt ledger:** stop publication, preserve the corrupt file for investigation,
  restore from a verified backup. Do not delete it merely to make the job pass.
- **Result correction:** retain original evaluation, append the new revision. The
  derived dataset chooses the latest revision, preserving original evidence.
- **FIA page 403:** official archive metadata or verified cache may be available.
  Keep source authority, source status, stale flags, document URLs and errors.
- **Timing unavailable:** use the selected session's explicit failure state. Do not
  load OpenF1/Jolpica `latest` data into a different requested event.
- **Rate limit:** respect `Retry-After`; avoid repeated manual sync requests.
- **Audio:** proxy only approved Formula 1 static radio URLs, with no redirects,
  15-second timeout and 12 MB bound. Missing duration is learned by the audio element,
  not filled with a fake clip length.

## Rollback

Rollback code and the reviewed model version as one change. Never roll back or
rewrite immutable ledger entries. Do not redeploy the old probability contract
as a fallback: that would restore known integrity defects. If a release fails,
keep current rankings unavailable while repairing the production contract.

## Capture operations

Forecast publication runs hourly, independently of daily FIA metadata refresh.
Both workflows share a non-cancelling concurrency group and rebase before pushing
small artifacts. GitHub scheduling is best effort: dispatch the publisher manually
after qualifying if the next scheduled run may miss the start. A run after race
start cannot recover a missed forecast. Monitor Actions failures; never backdate
records or treat retrospective reconstruction as prospective evidence.

A results-provider outage is exposed in warnings but does not suppress otherwise
valid qualifying-based capture. A corrupt ledger remains a hard failure.
Predictions remain immutable; post-race result revisions append evaluations.
