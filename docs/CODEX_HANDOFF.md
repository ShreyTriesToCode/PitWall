# Codex Handoff State

## Current objective
- [BLOCKED] Fix FIA document source resilience, lint coverage, atomic JSON writes, leakage diagnostics, artifact bloat controls, and notification cleanup; local commit is complete, but GitHub push is blocked by HTTPS authentication.

## Repository status
- Repo path: /Users/shrey-mac/Downloads/Codes/PitWall-main 2
- Is Git repo: yes
- Remote origin: https://github.com/ShreyTriesToCode/PitWall.git
- Branch: main
- Latest known local commit before this handoff update: `4194c67 Fix FIA docs sources, lint coverage, and atomic artifacts`
- Push status: failed. Command: `git push origin main`. Error: `fatal: could not read Username for 'https://github.com': Device not configured`.

## Completed
- [x] [REPO] Confirmed repository, branch, and origin.
- [x] [AUDIT] Inspected workflows, docs, relevant Python modules, tests, artifact policy, and existing handoff.
- [x] [TEST] Added a regression test for the FIA season-index live-path cache-miss success path that failed before the undefined-name fix.
- [x] [MODEL] Removed the stray undefined `model_comparison_contract(decision, metrics, meta)` call from `fetch_fia_season_index()`.
- [x] [TEST] Added no-network FIA resolver tests covering official, secondary official, archive/API, third-party index, summary-only, regulation mirror, verified cache, stale cache, SHA mismatch, HTML masquerading as PDF, conflict, dedupe, and failure states.
- [x] [DOCS] Added `AGENTS.md` with durable project rules.
- [x] [CACHE] Added shared atomic text/JSON writers and routed key JSON artifacts through them.
- [x] [VALIDATE] Expanded Ruff coverage to `f1_briefing.py pitwall scripts tests` in local docs and workflows.
- [x] [MODEL] Added bounded single-feature leakage diagnostic reporting.
- [x] [DOCS] Updated README, RUNBOOK, AUDIT, MODEL_REPORT, and ARTIFACT_POLICY.
- [x] [PUSH] Created the local commit and rebased it on `origin/main`.

## In progress
- [ ] [PUSH] Push local `main` to GitHub after HTTPS credentials are available.

## Remaining
- [ ] Run `git push origin main` once GitHub authentication is configured for this machine/session.
- [ ] Verify `git rev-parse HEAD` matches `git ls-remote origin main`.

## Files changed
- `f1_briefing.py`: Fixes the FIA season-index undefined-name crash, integrates the FIA resolver, adds leakage diagnostics, atomic writes, and notification target/auto-close behavior.
- `pitwall/data/fia_document_resolver.py`: Adds the real multi-source FIA document resolver with trust/status metadata and no synthetic document creation.
- `pitwall/io/atomic.py`: Adds shared atomic text/JSON writers.
- `pitwall/contracts/frontend_contract.py`, `pitwall/data/cache_manager.py`, `pitwall/models/artifacts.py`, `pitwall/ai/local_rag.py`: Route JSON/text artifact writes through shared atomic helpers.
- `scripts/check_artifact_sizes.py`: Adds staged cache/PDF guardrails while allowing small FIA parsed/index JSON.
- `.github/workflows/*.yml`: Expands Ruff coverage and adds staged artifact checks plus notification env defaults.
- `tests/`: Adds resolver, atomic writer, artifact policy, notification, leakage, and FIA season-index regression tests.
- Docs: Adds/updates durable project rules, FIA trust/fallback docs, leakage diagnostics, and artifact policy.

## Important decisions
- FIA documents are never synthesized. Third-party summaries are context only and cannot replace official documents.
- Official FIA sources win over third-party copies; verified cache is used only as an explicit cache/stale fallback.
- FIA PDF mirrors and runtime caches are blocked from staged commits; small FIA parsed/index JSON remains allowed when validated.
- Probability/model validation behavior is unchanged except for added bounded leakage diagnostics.
- Dependency pins were not bumped because package-index verification is unavailable in this restricted session and the existing pins are already recent/future-looking.

## Validation status
- `.venv/bin/python -m compileall f1_briefing.py pitwall scripts tests`: passed after rebase.
- `.venv/bin/ruff check f1_briefing.py pitwall scripts tests`: passed after rebase.
- `.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .`: passed after rebase, 135 tests.
- `.venv/bin/pytest`: passed after rebase, 135 tests.
- `.venv/bin/python scripts/validate_contracts.py`: passed; Top 10 = 10, Full Grid = 22.
- `.venv/bin/python scripts/validate_cache_manifest.py --allow-missing`: passed; 0 missing references.
- `.venv/bin/python scripts/check_artifact_sizes.py`: passed; existing local large cache files only warned.
- `.venv/bin/python scripts/check_artifact_sizes.py --staged --fail-cache-paths`: passed; no staged large artifacts, runtime caches, or FIA PDFs.
- `.venv/bin/python scripts/check_links.py`: passed with 0 warnings.
- `npm run build` in `frontend/`: passed after rebase.
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
