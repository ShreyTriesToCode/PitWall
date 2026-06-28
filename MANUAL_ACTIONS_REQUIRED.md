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
- Current finding: the public F1LivePulse FIA documents URL resolves to a feature/marketing page, not a confirmed machine-parseable document feed.
- Planned behavior: keep `FIA_DOCUMENT_F1LIVEPULSE_ENABLED=false` until a stable parseable page or API endpoint is verified.
