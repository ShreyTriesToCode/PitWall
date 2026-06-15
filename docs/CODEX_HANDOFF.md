# Codex Handoff State

## Current objective
- [DONE] Dynamic completed-race strategy/result feature training update validated locally, committed, and pushed to main.

## Repository status
- Repo path: /Users/shrey-mac/Downloads/Codes/PitWall-main 2
- Is Git repo: yes
- Remote origin: https://github.com/ShreyTriesToCode/PitWall.git
- Branch: main
- Latest known commit: `825c6e4 fix: train with post-race strategy actuals`
- Push status: succeeded for `825c6e4`; local `origin/main` matched local HEAD. `git ls-remote origin main` could not be re-run afterward because local DNS could not resolve `github.com`.

## Completed
- [x] [REPO] Confirmed local repository and origin.
- [x] [ACTUALS] Added cached Jolpica-compatible full-race result lookup for completed race archive comparisons.
- [x] [ACTUALS] Regenerated frontend contracts so Monaco and Canada use cached actual winners while Barcelona remains pending.
- [x] [TEST] Added regression coverage for cached Monaco and Canada race actuals.
- [x] [TRAIN] Changed the scheduled briefing workflow to run `python -u` with `PYTHONUNBUFFERED=1` for visible CI logs.
- [x] [UI] Tightened archive card layout and changed pending actual-result badges from error red to pending amber.

## In progress
- None.

## Remaining
- None.

## Files changed
- f1_briefing.py: Adds completed-race strategy/weather/race-control/tyre features, prediction-row historical aggregates, and schema `2026.06-strategy-actuals-v7`.
- tests/test_f1_briefing_core.py: Covers 22-driver completed result rows and future prediction rows using historical strategy/weather actuals.
- MODEL_REPORT.md: Documents post-race actual strategy feature ingestion and no-leakage guardrails.
- f1_briefing.py: Falls back to trusted cached full-race results when archive entries do not embed actual results.
- .github/workflows/f1-briefing.yml: Runs briefing script unbuffered so workflow logs do not appear blank.
- frontend/app/archive/page.jsx: Displays actual-result status with safe labels and tones.
- frontend/app/globals.css: Tightens archive card, badge, metric, and action layouts.
- tests/test_f1_briefing_core.py: Covers Monaco and Canada cached actual-result comparison.
- data_cache/frontend-contract.json: Regenerated archive and prediction contract.
- data_cache/model-status.json: Regenerated model/readiness metadata.
- data_cache/backtest-history.json: Regenerated comparison history.
- data_cache/cache_manifest.json: Regenerated cache manifest.
- data_cache/model_corrections.json: Regenerated correction metadata.
- data_cache/pitwall.db: Regenerated local artifact database.
- model_artifacts/evaluation.json: Regenerated evaluation artifact.
- model_artifacts/feature_importance.json: Regenerated feature importance artifact.
- model_artifacts/training_metadata.json: Regenerated training metadata.

## Important decisions
- Completed race actuals are sourced dynamically from cached/API-backed race results; no driver positions, winners, or strategies are hardcoded.
- Post-race result, strategy, weather, and race-control fields are used only after the final-result gate, and future prediction rows receive historical aggregates rather than same-race actuals.
- The model schema was bumped to `2026.06-strategy-actuals-v7` so CI/local training does not silently reuse the older artifact.
- Empty post-race refreshes no longer overwrite valid cached final-result files; this protects Monaco/Canada-style actual-result comparisons during DNS/API outages while still allowing API-backed refresh when real results are returned.
- Actual results are read only from existing trusted cached race result files; no winners or classifications are fabricated.
- Barcelona remains pending because the cached round file does not contain trusted race Results rows.
- Playwright is intentionally not part of the default validation path because it caused workflow timeout through browser downloads.
- The workflow still builds the frontend with `npm run build`; it does not run Playwright in the default path.
- Current saved model metadata already includes completed results through `2026-6`; no fabricated retraining claim is made.

## Validation status
- `.venv/bin/python -m unittest tests.test_f1_briefing_core.F1BriefingCoreTests.test_completed_race_rows_flatten_full_grid_strategy_weather_features tests.test_f1_briefing_core.F1BriefingCoreTests.test_prediction_features_use_historical_strategy_weather_actuals`: passed.
- `.venv/bin/python -m py_compile f1_briefing.py`: passed.
- `.venv/bin/ruff check pitwall scripts tests`: passed.
- `FORCE_RETRAIN=true FORCE_REFRESH_DATA=false CACHE_AWARE_DOWNLOADS=true PITWALL_CI=true SHOW_TRAINING_PROGRESS=true COMPARE_ACTUAL_RESULTS=true .venv/bin/python -c 'import f1_briefing as f; ... train_ml_model(True) ...'`: passed; trained schema `2026.06-strategy-actuals-v7`, 179 cached races reused, 0 refreshed, latest completed race `2026-6`, feature count 42.
- `.venv/bin/python -m unittest discover -s ./tests -p "test_*.py" -t .`: passed, 102 tests.
- `.venv/bin/python scripts/validate_contracts.py`: passed with 22 Full Grid rows, 10 Top 10 rows, schema/model `2026.06-strategy-actuals-v7`.
- `.venv/bin/python scripts/validate_cache_manifest.py --allow-missing`: passed with 0 missing references.
- `.venv/bin/python scripts/check_artifact_sizes.py`: passed; two FastF1 Canadian GP cache files are warning-sized but below the failure threshold.
- `frontend build via bundled Node`: passed.
- `.venv/bin/python scripts/validate_contracts.py`: passed.
- `.venv/bin/python scripts/validate_cache_manifest.py --allow-missing`: passed with 0 missing references.
- `.venv/bin/python scripts/check_links.py`: passed.
- `frontend build via bundled Node`: passed.
- `frontend build via bundled Node after archive UI changes`: passed.
- `frontend npm test`: skipped because it runs Playwright, which the user asked to avoid in default workflow validation.
- `FORCE_RETRAIN=true FORCE_REFRESH_DATA=false CACHE_AWARE_DOWNLOADS=true PITWALL_CI=true SHOW_TRAINING_PROGRESS=true COMPARE_ACTUAL_RESULTS=true .venv/bin/python f1_briefing.py`: stopped locally because the process remained silent long enough to reproduce the blank-log concern; workflow now uses unbuffered Python, and targeted cache-aware generation plus validators passed.
- Contract spot check: latest payload has 10 Top 10 rows and 22 Full Grid rows; Monaco and Canada archive rows are `available`; Barcelona remains `pending`.

## Known blockers
- None.

## Resume instructions
1. Run `pwd`.
2. Run `git rev-parse --is-inside-work-tree`.
3. Run `git remote -v`.
4. Run `git status --short`.
5. Read this file fully.
6. Inspect the latest diff.
7. Continue from the first unchecked item in "Remaining".
8. Do not restart from scratch unless the repo state is broken.
