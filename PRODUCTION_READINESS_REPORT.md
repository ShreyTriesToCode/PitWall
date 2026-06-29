# Production Readiness Report

## 2026-06-29 Status

PitWall has active hardening for source-aware predictions, FIA document fallback, cache-aware training, frontend contract validation, and transparent unavailable states. The project still treats predictions as probabilistic and never substitutes fake race results or synthetic FIA documents for missing trusted data.

## Hardened In This Pass

- `/` and `/model` use server-side contract loaders so the first render is backed by current generated prediction/model data instead of waiting for client-only fetches.
- `/api/predictions` and server-rendered pages share `loadPredictionsPayload()` to avoid shape drift.
- The frontend no longer embeds Formula 1 CDN image assets. It uses self-hosted PitWall SVG visuals and keeps official race pages as outbound links only.
- SEO, Open Graph, Twitter metadata, and basic security headers are configured.
- `/predictions` and `/live` have route error boundaries for malformed or temporarily unavailable contracts.
- `/sources` exposes FIA resolver trust metadata, including source authority/status, official/verified/stale flags, URLs, and SHA256 where present.
- `/predictions` surfaces Monte Carlo simulation output from the contract as simulation, not actual race outcome data.

## Verification Evidence

- `npm run build` passed with Next.js 16.2.6.
- Direct contract-loader probe returned:
  - Race: Austrian Grand Prix
  - Top prediction: Lewis Hamilton
  - Full grid rows: 22
  - Model version: 2026.06-strategy-actuals-v7
- The compiled `/` and `/model` server bundles call `loadPredictionsPayload()`.

## Known Limitations

- Local raw HTTP verification through `next start` was blocked by sandbox port permissions. `MANUAL_ACTIONS_REQUIRED.md` contains the exact manual curl check.
- Full backend extraction from `f1_briefing.py` remains incomplete and is tracked as a later phase.
- Large generated frontend contracts and historical caches still need a broader storage policy decision before history cleanup.
- FIA third-party document index fallback via F1LivePulse remains disabled until a stable parseable feed is verified.
