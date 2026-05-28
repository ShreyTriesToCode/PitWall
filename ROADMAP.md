# PitWall Roadmap

## Completed In The Current Hardening Pass

- Contract validator for `frontend-contract.json`, `briefings/index.json`, `latest-model-debug.json`, and `model-status.json`.
- Frontend recovery from `latest-model-debug.json` and previous valid contracts.
- Per-driver model disagreement detection and trust score.
- Prediction UI badges for trust, disagreement, expected finish, and missing data.
- `/sources` page for source-health visibility.
- Timing response cache metadata and truthful cache/source timestamps.
- Playwright smoke tests and CI steps for contract validation, backend tests, frontend build, and artifact-size checks.
- Pinned frontend and Python dependencies.

## Next Improvements

- Move large runtime caches to release assets, object storage, or Git LFS.
- Add shared timing cache with Upstash Redis or Vercel KV for deployed serverless environments.
- Expand model-vs-reality archive once more audited actual-result rows are available.
- Add heavier feature ablation retraining jobs behind `ENABLE_FEATURE_ABLATION=true`.
- Add optional MLflow or DVC experiment tracking if the local JSON run records stop being enough.
- Add legal/terms-reviewed historical odds and tyre allocation sources only if reliable licensed feeds are available.
- Split more logic from `f1_briefing.py` into `pitwall/features`, `pitwall/models`, and `pitwall/contracts` after test coverage around the current wrappers stays green.
