# Manual Actions Required

## 2026-06-29 GitHub push authentication

- Status: resolved for this local Codex session.
- Evidence: `git push origin main --dry-run` initially failed with `fatal: could not read Username for 'https://github.com': Device not configured`.
- Resolution used: `gh auth setup-git`, using the already-authenticated GitHub CLI account `ShreyTriesToCode`.
- Follow-up: none unless a future shell/session loses GitHub CLI credential-helper configuration.

## 2026-06-29 License default

- Status: pending owner review.
- Planned default: MIT license, unless the repository owner prefers another license.
- Current repo state: `LICENSE` was added with the MIT text as the default project license. Replace it before the next release if another license is preferred.

## 2026-06-29 F1LivePulse FIA documents fallback

- Status: pending owner/API verification.
- Current finding: `https://f1livepulse.com/fia-documents` returns HTTP 200 but redirects to `https://www.f1livepulse.com/en/features/fia-documents/`, a feature/marketing page rather than a confirmed machine-parseable document feed.
- Planned behavior: keep `FIA_DOCUMENT_F1LIVEPULSE_ENABLED=false` until a stable parseable page or API endpoint is verified.

## 2026-06-29 Local SSR HTTP verification

- Status: manual verification recommended outside this sandbox.
- Blocker: `npm run start -- -p 3017` failed with `listen EPERM: operation not permitted 0.0.0.0:3017`, and escalation for local port binding was unavailable in this session.
- What was verified instead: `npm run build` passed, the compiled `/` and `/model` server bundles call `loadPredictionsPayload()`, and a direct contract-loader probe returned the real current race, top prediction, full-grid size, and model version.
- Manual check: from a normal local shell, run `cd frontend && npm run build && npm run start -- -p 3017`, then `curl -s http://127.0.0.1:3017/ | grep -E "Austrian Grand Prix|Lewis Hamilton"` and `curl -s http://127.0.0.1:3017/model | grep -E "Model Center|2026.06"`.

## 2026-06-29 Cache untracking blocked by escalation window

- Status: pending git-index action.
- Finding: `git ls-files fastf1_cache data_cache/full_races models/saved_models | wc -l` reports 295 tracked reproducible runtime cache/model files.
- Local disk footprint at inspection: `fastf1_cache` 547 MB, `data_cache/full_races` 852 KB, `models/saved_models` 32 MB.
- Required action when git index writes are available: run `git rm -r --cached fastf1_cache data_cache/full_races models/saved_models`, verify no files were deleted from disk, run the full validation gate, commit as `chore: untrack reproducible runtime caches`, and push.
- Do not rewrite git history without explicit owner approval.

## 2026-06-29 Phase 3 safe-slice commit blocked by escalation window

- Status: pending commit/push.
- Completed locally: hidden neutral score fallbacks were removed from legacy contract normalization, Monte Carlo DNF fallback basis is now explicit, `models/saved_models/` is ignored, MIT `LICENSE` was added, and repo-footprint docs were updated.
- Validation passed locally: py_compile, Ruff, 158 unit tests, contract validation, artifact-size check, run report, `npm ci`, and `npm run build`.
- Required action when git index/ref writes are available: run `git add .`, `git commit -m "fix: expose missing score states"`, `git push origin main`, then verify local/remote hashes.
