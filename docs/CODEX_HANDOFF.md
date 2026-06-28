# Codex Handoff State

## Current objective
- [VALIDATE] Harden FIA upgrade-package source fallback so daily automation uses verified parsed FIA documents first, skips blocked live sources after one attempt, and exposes unavailable rather than retrying forbidden URLs.

## Repository status
- Repo path: /Users/shrey-mac/Downloads/Codes/PitWall-main 2
- Is Git repo: yes
- Remote origin: https://github.com/ShreyTriesToCode/PitWall.git
- Branch: main
- Latest known local commit: run `git log -1 --oneline` after reading this file.
- Push status: failed. Command: `git push origin main`. Error: `fatal: could not read Username for 'https://github.com': Device not configured`. Current changes are validated and committed locally; push needs GitHub authentication from an authenticated shell/session.

## Completed
- [x] [REPO] Rebasing on latest `origin/main` completed with `git pull --rebase --autostash origin main`.
- [x] [MODEL] Added `fia_upgrade_*` feature columns and stage-gated them as pre-weekend FIA upgrade signals.
- [x] [MODEL] Expanded FIA car-presentation parsing so table-style team sections produce real upgrade rows from official cached text.
- [x] [MODEL] Added safe summarizers for FIA upgrade package intensity, component counts, trait groups, performance counts, and missing-data flags.
- [x] [MODEL] Completed-race training rows now read parsed FIA upgrade documents from `data_cache/fia-documents/<season>/<event>/parsed/` and reparse cached text in-memory when old parsed JSON lacks upgrade rows.
- [x] [MODEL] Current-race inference rows now receive the same feature schema from `upgrade_context`, so retrained models can use upgrade signals at prediction time.
- [x] [TEST] Added regression tests proving ML training rows and prediction rows include FIA upgrade features without hardcoded race results.
- [x] [DOCS] Updated `AUDIT.md` and `MODEL_REPORT.md` to document direct ML upgrade-package features.
- [x] [VALIDATE] Backend lint, contract validation, artifact-size policy, compile, and unit tests passed.
- [x] [PUSH] Created local commit `feat: feed FIA upgrades into ML features`; push attempted and failed due missing GitHub HTTPS credentials.
- [x] [CACHE] FIA upgrade context now checks verified parsed FIA car-presentation docs before probing guessed live FIA/news URLs.
- [x] [CACHE] Blocked or missing FIA upgrade URLs use a single guarded request and then move to the next trusted candidate.
- [x] [TRAIN] Cached official upgrade package rows are converted into the same bounded `upgrade_context` consumed by training/inference features.
- [x] [TRAIN] If no trusted source is available, upgrade-package context returns `source_status=unavailable` and missing feature flags instead of fabricated data.
- [x] [WORKFLOW] Scheduled briefing runs now refresh FIA document metadata and source registry by default while keeping forced PDF redownload disabled.
- [x] [TEST] Added regressions for cache-first FIA upgrade context, single-attempt 403 handling, and daily workflow FIA refresh defaults.
- [x] [VALIDATE] Re-ran compile, Ruff, contracts, artifact-size policy, and 140 unit tests after fallback changes.
- [x] [PUSH] Created local commit `fix: harden FIA upgrade fallback automation`; push attempted and failed due missing GitHub HTTPS credentials.

## In progress
- [ ] [PUSH] Push local `main` to GitHub after authentication is available.

## Remaining
- [ ] Run `git push origin main` from an authenticated shell/session.
- [ ] Verify `git rev-parse HEAD` matches `git ls-remote origin main`.

## Files changed
- `f1_briefing.py`: Adds FIA upgrade ML feature columns, parser improvements, training-row extraction, inference-row plumbing, and mandatory feature-selection retention for core upgrade signals.
- `tests/test_f1_briefing_core.py`: Adds direct ML training/inference regression coverage for FIA upgrade features.
- `MODEL_REPORT.md`: Documents FIA upgrade package features as direct ML inputs with missing-data flags.
- `AUDIT.md`: Notes that FIA upgrade packages are no longer transparent-ranking only.
- `RUNBOOK.md`: Documents daily FIA metadata refresh defaults and cache-first upgrade source fallback.
- `.github/workflows/f1-briefing.yml`: Defaults FIA document and source-registry refresh to true for scheduled automation.
- `docs/CODEX_HANDOFF.md`: Records current commit and push blocker.

## Important decisions
- No race results, winners, strategies, FIA documents, or upgrade packages were hardcoded.
- Upgrade-package features are derived from trusted parsed FIA/F1 upgrade context or marked missing with `missing_fia_upgrade_data`.
- Guessed FIA/news upgrade URLs are only a fallback probe, not the primary source; they must not be retried repeatedly when returning 401/403/404.
- Daily automation refreshes FIA metadata so newly published car-presentation submissions can enter the next model run without manual action.
- Existing Top 10 and Full Grid contract behavior was not changed.
- Model schema version was not bumped in this commit because generated artifacts were not retrained locally; the workflow/forced retrain path will train with the new feature columns.

## Validation status
- `.venv/bin/python -m compileall f1_briefing.py pitwall scripts tests`: passed.
- `.venv/bin/ruff check f1_briefing.py pitwall scripts tests`: passed.
- `.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .`: passed, 140 tests.
- `.venv/bin/python scripts/validate_contracts.py`: passed; Top 10 = 10, Full Grid = 22.
- `.venv/bin/python scripts/check_artifact_sizes.py`: passed; existing large runtime artifacts warn only, no failed policy checks.
- Targeted FIA fallback regression tests: passed, 3 tests.
- `git push origin main`: failed with `fatal: could not read Username for 'https://github.com': Device not configured`.

## Known blockers
- GitHub HTTPS authentication is unavailable in this Codex session. Local work is committed and validated; push needs credentials.

## Resume instructions
1. Run `pwd`.
2. Run `git rev-parse --is-inside-work-tree`.
3. Run `git remote -v`.
4. Run `git status --short`.
5. Read this file fully.
6. Run `git log -1 --oneline`.
7. If the working tree is clean, run `git push origin main` after configuring GitHub authentication.
8. Verify local and remote hashes with `git rev-parse HEAD` and `git ls-remote origin main`.
