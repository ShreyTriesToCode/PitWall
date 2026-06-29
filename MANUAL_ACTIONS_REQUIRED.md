# Manual Actions Required

## 2026-06-29 GitHub push authentication

- Status: resolved for this local Codex session.
- Evidence: `git push origin main --dry-run` initially failed with `fatal: could not read Username for 'https://github.com': Device not configured`.
- Resolution used: `gh auth setup-git`, using the already-authenticated GitHub CLI account `ShreyTriesToCode`.
- Follow-up: none unless a future shell/session loses GitHub CLI credential-helper configuration.

## 2026-06-29 License default

- Status: pending owner review.
- Planned default: MIT license, unless the repository owner prefers another license.

## 2026-06-29 F1LivePulse FIA documents fallback

- Status: pending owner/API verification.
- Current finding: `https://f1livepulse.com/fia-documents` returns HTTP 200 but redirects to `https://www.f1livepulse.com/en/features/fia-documents/`, a feature/marketing page rather than a confirmed machine-parseable document feed.
- Planned behavior: keep `FIA_DOCUMENT_F1LIVEPULSE_ENABLED=false` until a stable parseable page or API endpoint is verified.

## 2026-06-29 Local SSR HTTP verification

- Status: manual verification recommended outside this sandbox.
- Blocker: `npm run start -- -p 3017` failed with `listen EPERM: operation not permitted 0.0.0.0:3017`, and escalation for local port binding was unavailable in this session.
- What was verified instead: `npm run build` passed, the compiled `/` and `/model` server bundles call `loadPredictionsPayload()`, and a direct contract-loader probe returned the real current race, top prediction, full-grid size, and model version.
- Manual check: from a normal local shell, run `cd frontend && npm run build && npm run start -- -p 3017`, then `curl -s http://127.0.0.1:3017/ | grep -E "Austrian Grand Prix|Lewis Hamilton"` and `curl -s http://127.0.0.1:3017/model | grep -E "Model Center|2026.06"`.
