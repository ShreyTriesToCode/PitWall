# PitWall reliability audit — 2026-09-17

## Scope and evidence before changes

Inspected the repository tree, Python briefing/ingestion/model/storage modules,
Next routes, components and CSS, workflow/configuration, generated data, tests,
documentation and dataset caches. Ran a clean Python 3.11 dependency install,
`npm ci`, production build and Ruff. Reproduced the Italian GP on both the
deployed website and local production server. Inspected rendered home, model,
and timing pages, including desktop and mobile. Existing documentation's
readiness claims are not accepted as evidence.

## Data flow

Legacy: ICS/Jolpica/F1 static/OpenF1/FastF1/weather/FIA → monolithic ingestion
and feature generation → HTTP/CSV/model caches → weighted ranking and synthetic
simulation → briefings/index.json + SQLite upserts → export normalization →
57 MB frontend contract → Next filesystem/GitHub fallbacks → browser.

Timing: F1 season index → selected meeting/session → static streams/keyframes →
Next timing proxy/cache/SSE → timing table, weather, race control and radio.

## Issue inventory (priority order)

| ID | Priority | Reproduction / root cause | Required resolution |
|---|---|---|---|
| R01 | P0 | Latest saved briefing selected without checking race time; skipped cron run republishes Italian GP | Current calendar selection plus read-time expiry; completed events only in history |
| R02 | P0 | Probabilities derived from arbitrary scores; Gaussian simulations, strategy risks, confidence and source scores lack validation | Withdraw unsupported quantities; use explicitly named rank prediction with measured evaluation |
| R03 | P0 | Export rewrites old model versions, features and predictions; SQLite upsert replaces payload | Append-only predictions, separate immutable evaluations and provenance |
| R04 | P0 | Target-race lap/pit missingness leaks outcome availability into features; final blended predictor never evaluated | Shared pre-race feature path; chronological backtest of exactly the published algorithm |
| R05 | P0 | Training writes production model before promotion decision; gate only tests metric presence | Disable automatic legacy promotion; compare candidate/baseline on held-out races and require review |
| R06 | P0 | Timing packet timestamp manufactured from request time; mismatched latest fallback used for explicit historical sessions | Real source timestamp or unknown; preserve requested identity on failure |
| R07 | P0 | npm audit reports critical Next vulnerability plus high transitive vulnerabilities | Upgrade compatible dependencies and rebuild/audit |
| R08 | P1 | Backtest repeats latest training metrics for unrelated saved predictions | Separate retrospective reconstruction and genuine captured forecasts; per-race actual comparison |
| R09 | P1 | Static 2026 calendar contradicts provider schedule; sprint/race identity ambiguity and timezone-naive timing dates | Provider calendar with explicit UTC times and stable season/round/session IDs |
| R10 | P1 | Previous/debug/GitHub fallback hides corrupt or obsolete contracts; schema coercion turns null into zero | Strict versioned small contract, bounded reads, explicit stale/unavailable states |
| R11 | P1 | Source registry configuration treated as availability, no observable provenance cutoff | Record successful retrieval separately from source publication and prediction cutoff |
| R12 | P1 | Audio follows redirects without timeout/size cap; SSE cancellation/error details | Bounded trusted-host proxy and abort cleanup; sanitized errors |
| R13 | P2 | Giant repeated contract, obsolete raw debug endpoint and runtime files tracked | Small published artifact; isolate legacy outputs and runtime caches |
| R14 | P2 | Synthetic strategy sliders, duplicate percentages, fallback teams and misleading AI copy | Useful observed information and explicit limits; remove unsupported claims |
| R15 | P2 | Route preloader, scanlines/glow and crowded mobile nav; hydration error observed | Preserve dark/red identity with clearer hierarchy, usable navigation and stable rendering |
| R16 | P2 | Browser tests refer to old text/races; CI does not run them | Critical path tests for calendar, failures, provenance, immutable history and rendered routes |
| R17 | P2 | Documentation and deployment workflow overstate readiness and silently recover generated conflicts | Document actual methods, assumptions, limitations and safe scheduled publication |

The legacy numerical enrichment/publishing subsystem cannot be repaired by
renaming its percentages: its final output has no defensible probability model,
its history has already been rewritten, and provenance cannot be reconstructed.
It is retained as research code, excluded from production publication. Existing
saved forecasts must be marked unverified legacy history, never retrospectively
promoted into genuine captured forecasts. No old timestamp will be invented.

## Verification log

- Baseline clean Python install: passed (3.11).
- Baseline clean npm install and production build: passed (Next 16.2.6).
- Baseline Ruff: passed.
- Baseline npm audit: 5 vulnerable packages, including critical Next advisory.
- Further executed tests and critic iterations are recorded in VALIDATION.md.

## Resolution boundary

R01–R12 are addressed in the active publisher/API/timing paths with executable
regression coverage. R13–R17 are addressed by the small contract, truthful product
views, responsive review, CI gates and current documentation. Original model outputs
and research code are retained but excluded from production. The final visual review
also found and fixed a UTF-8 BOM parsing regression and removed a generic car SVG
wrapped as an official race visual. See [VALIDATION.md](VALIDATION.md) for precise
outcomes, critic scores and the remaining deployment/scientific limitations.
