# Codex Handoff State

## Current objective
- [BLOCKED] Feed trusted FIA car-presentation upgrade package data into direct ML training/inference features. Local work is committed, but GitHub push is blocked by HTTPS authentication.

## Repository status
- Repo path: /Users/shrey-mac/Downloads/Codes/PitWall-main 2
- Is Git repo: yes
- Remote origin: https://github.com/ShreyTriesToCode/PitWall.git
- Branch: main
- Latest known local commit: run `git log -1 --oneline` after reading this file; the commit message is `feat: feed FIA upgrades into ML features`.
- Push status: failed. Command: `git push origin main`. Error: `fatal: could not read Username for 'https://github.com': Device not configured`.

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
- `docs/CODEX_HANDOFF.md`: Records current commit and push blocker.

## Important decisions
- No race results, winners, strategies, FIA documents, or upgrade packages were hardcoded.
- Upgrade-package features are derived from trusted parsed FIA/F1 upgrade context or marked missing with `missing_fia_upgrade_data`.
- Existing Top 10 and Full Grid contract behavior was not changed.
- Model schema version was not bumped in this commit because generated artifacts were not retrained locally; the workflow/forced retrain path will train with the new feature columns.

## Validation status
- `.venv/bin/python -m compileall f1_briefing.py pitwall scripts tests`: passed.
- `.venv/bin/ruff check f1_briefing.py pitwall scripts tests`: passed.
- `.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .`: passed, 137 tests.
- `.venv/bin/python scripts/validate_contracts.py`: passed; Top 10 = 10, Full Grid = 22.
- `.venv/bin/python scripts/check_artifact_sizes.py`: passed; existing large runtime artifacts warn only, no failed policy checks.
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
