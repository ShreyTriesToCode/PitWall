# Artifact policy

Production reads `data_cache/product.json` (schema 3), with a strict 5 MB limit.
Published forecasts and evaluations are stored separately in append-only ledger
files. The contract and evaluated dataset are derived views; rebuilding them must
not mutate a forecast or change its capture time/model version.

Commit only small reviewed product/backtest/evaluated-dataset files, ledger records,
and FIA index metadata. Keep original source authority, status, verified/stale flags,
URLs, errors and retrieval timestamps. Do not commit PDF mirrors, FastF1 caches,
full-race runtime caches, model bundles or provider runtime responses.

Older tracked `frontend-contract.json`, debug snapshots, SQLite and CSV outputs
remain legacy research artifacts. They are not loaded by the application, included
in its deployment bundle, or used as missing-data fallbacks. The local-data API
returns 410 for retired raw exports. Their data cannot be relabeled as a verified
forecast history. Git history cleanup is a separate destructive operation and
has not been performed.

`data_cache/http` contains the historical source responses used for the retrospective
report; their response URLs and hashes are recorded in that report. Do not substitute
synthetic data to repair a missing source. New browser/unit fixtures belong only
under tests. Large captures and browser traces are ignored runtime evidence.
