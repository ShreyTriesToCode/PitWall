# Codex Handoff State

## Current objective
- [PUSH] Final push to `main` and verify local HEAD matches remote main.

## Repository status
- Repo path: /Users/shrey-mac/Downloads/Codes/PitWall-main 2
- Is Git repo: yes
- Remote origin: https://github.com/ShreyTriesToCode/PitWall.git
- Branch: main
- Latest known commit: local rebased feature commit; run `git rev-parse HEAD` for the exact final amended hash.
- Push status: ready to push after successful `git fetch origin main` and `git rebase origin/main`; first push attempt failed because remote main advanced.

## Completed
- [x] [REPO] Attached local `main` to `origin/main` with `git reset --mixed origin/main` while preserving the working tree.
- [x] [AUDIT] Inspected backend, frontend, workflow, contracts, docs, cache, and generated artifacts.
- [x] [MODEL] Added `notebooks/pitwall_model_refinement.ipynb` with cache-first diagnostics, leakage checks, chronological validation, champion loading, challenger scaffolding, ranking/regression metrics, and artifact utility usage.
- [x] [MODEL] Added reusable model modules for features, training, evaluation, prediction, artifacts, and validation.
- [x] [CACHE] Added cache-aware manifest handling and validation script.
- [x] [TRAIN] Updated race cache writes to use atomic temporary files and manifest events.
- [x] [UI] Fixed several frontend contract, source-health, archive confidence, live-page, accessibility, and Playwright self-hosting issues.
- [x] [TEST] Backend unit tests, contract validation, cache manifest validation, artifact reload, frontend build, and Playwright tests passed before this handoff update.
- [x] [ACTUALS] Added `pitwall/models/compare_actuals.py` and contract/UI defaults for available/pending/unavailable comparisons.
- [x] [MODEL] Added `model_comparison` contract normalization and `/model` rendering.
- [x] [LINK] Added `scripts/check_links.py` and unit tests for internal route/link validation.
- [x] [TRAIN] Added visible training progress markers and `PitWall training summary` output.
- [x] [PUSH] Rebasing onto latest `origin/main` completed after resolving generated artifact conflicts toward the regenerated feature artifacts.

## In progress
- [ ] [PUSH] Push `main`, then verify local HEAD matches remote main.

## Remaining
- [x] Inspect current diffs and remove local junk such as `frontend/test-results/`.
- [x] Implement `pitwall/models/compare_actuals.py`.
- [x] Extend backend/frontend contract validation for `model_comparison` and `actual_result_comparison`.
- [x] Render model comparison and actual-result comparison on `/model`.
- [x] Add API-route/link smoke coverage.
- [x] Update `.github/workflows/f1-briefing.yml` with `SHOW_TRAINING_PROGRESS=true`, `COMPARE_ACTUAL_RESULTS=true`, and link checks.
- [x] Rerun Python validation, training path, contract/cache checks, link checks, frontend build/tests, and notebook structure checks.
- [x] Stage only allowed files and commit `feat: harden PitWall model pipeline and result comparison`.
- [ ] Push `origin main` and verify hashes.

## Files changed
- f1_briefing.py: cache-aware data reuse, atomic cache writes, rolling chronological split, safer imports, and prediction row normalization.
- pitwall/features/build_features.py: reusable feature schema, grouping, imputation, and leakage-aware helpers.
- pitwall/models/*.py: reusable train/evaluate/predict/artifact/validation helpers.
- pitwall/data/cache_manager.py: manifest validation, atomic writes, source health, and in-run de-duplication helpers.
- pitwall/validation/contracts.py: stricter prediction row and Top 10/Full Grid contract validation.
- frontend/app/**: safer contract defaults, source health UI, live fallback states, archive confidence, and Playwright server config.
- .github/workflows/f1-briefing.yml: cache-aware training and frontend validation updates.
- docs and root markdown files: notebook, cache, workflow, artifact, source-health, and probabilistic prediction docs.
- data_cache/, model_artifacts/, models/saved_models/, briefings/: regenerated allowed model/contract/cache artifacts.

## Important decisions
- Use chronological race-group validation for promotion; do not use random row splits.
- Keep full refresh behind `FORCE_REFRESH_DATA=true`; default workflow uses valid cached data and targeted refresh.
- Treat optional external source failures as visible source-health/fallback states instead of fatal app crashes when valid cache exists.
- Keep Top 10 derived from the same ordered Full Grid contract table.
- Never fabricate actual results; actual-result comparison must be pending/unavailable/incomplete when trusted actuals are missing.

## Validation status
- `.venv/bin/python -m py_compile f1_briefing.py`: passed.
- `.venv/bin/ruff check pitwall scripts tests`: passed.
- `.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .`: passed, 78 tests.
- `.venv/bin/python scripts/validate_contracts.py`: passed.
- `.venv/bin/python scripts/validate_cache_manifest.py`: passed.
- `.venv/bin/python scripts/check_artifact_sizes.py`: passed with existing FastF1 cache size warnings.
- CI-style `f1_briefing.py` run with cache-aware flags: passed, reused cache/fallbacks and regenerated artifacts.
- Frontend `npm ci`, `npm run build`, and `npm test`: passed using the bundled Codex Node runtime; `npm test` required elevated execution for localhost binding.
- Notebook JSON/import structure check: passed.
- Full notebook execution: skipped because `nbformat`, `nbconvert`, and `jupyter` are not installed in the local virtual environment.
- CI-style `f1_briefing.py` rerun after comparison changes: failed after successful model training/artifact save because `save_model_status_json` referenced `comparison` before assignment. Fixed by assigning `comparison = model_comparison_contract(decision, metrics, meta)` before payload assembly.
- `.venv/bin/python -m py_compile f1_briefing.py`: passed after final code changes.
- `.venv/bin/ruff check pitwall scripts tests`: passed after final code changes.
- `.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .`: passed, 86 tests.
- `FORCE_RETRAIN=true FORCE_REFRESH_DATA=false CACHE_AWARE_DOWNLOADS=true PITWALL_CI=true SHOW_TRAINING_PROGRESS=true COMPARE_ACTUAL_RESULTS=true EMAIL_ENABLED=false SKIP_NETWORK_TESTS=true OPENF1_OPTIONAL_ONLY=true FULL_DATA_BACKFILL_LIMIT=0 MAX_FIA_PDFS_DOWNLOAD_PER_RUN=0 MAX_FIA_DOCUMENTS_PER_RUN=0 .venv/bin/python f1_briefing.py`: passed; reused 179 cached datasets, refreshed 0, retrained model, held champion, generated contracts, surfaced DNS/source fallbacks.
- `.venv/bin/python scripts/validate_contracts.py`: passed; latest Top 10 10, Full Grid 22, all_predictions 22.
- `.venv/bin/python scripts/validate_cache_manifest.py`: passed; 195 entries.
- `.venv/bin/python scripts/check_links.py`: passed with 0 warnings.
- `.venv/bin/python scripts/check_artifact_sizes.py`: passed with existing FastF1 cache warnings at 27.681 MB and 26.841 MB.
- `frontend npm ci`: passed using bundled Codex Node runtime.
- `frontend npm run build`: passed using bundled Codex Node runtime.
- `frontend npm test`: first failed in sandbox with `EPERM listen 127.0.0.1:3000`, rerun with elevated localhost permission passed, 6 tests.
- Notebook structure/import validation: passed, 17 cells.
- `git push origin main`: failed with non-fast-forward because remote contains work not present locally.
- `git fetch origin main`: passed after first push rejection; remote advanced from `23a92ed` to `f8eddfb`.
- `git rebase origin/main`: passed after resolving generated artifact conflicts (`MODEL_STATUS.md`, `briefings/latest-run-status.md`, generated `data_cache/*.json`, and saved model bundle/meta) in favor of the regenerated feature artifacts.
- Post-rebase `.venv/bin/python -m py_compile f1_briefing.py`: passed.
- Post-rebase `.venv/bin/ruff check pitwall scripts tests`: passed.
- Post-rebase `.venv/bin/python scripts/validate_contracts.py`: passed; latest Top 10 10, Full Grid 22, all_predictions 22.
- Post-rebase `.venv/bin/python scripts/validate_cache_manifest.py`: passed; 195 entries.
- Post-rebase `.venv/bin/python scripts/check_links.py`: passed with 0 warnings.
- Post-rebase notebook JSON structure validation: passed.
- Post-rebase `.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .`: passed, 86 tests.
- Post-rebase frontend `npm run build`: passed using bundled Codex Node runtime.
- Post-rebase frontend `npm test`: skipped because the required elevated localhost test run was blocked by the platform usage-limit gate; the same Playwright suite passed before the rebase, and no hand-written frontend conflicts occurred during the rebase.

## Known blockers
- None currently for source code. Push authentication has not been tested after the rebase.

## Resume instructions
1. Run `pwd`.
2. Run `git rev-parse --is-inside-work-tree`.
3. Run `git remote -v`.
4. Run `git status --short`.
5. Read this file fully.
6. Inspect the latest diff.
7. Continue from the first unchecked item in "Remaining".
8. Do not restart from scratch unless the repo state is broken.
