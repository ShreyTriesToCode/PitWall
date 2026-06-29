# PitWall Audit

[Documentation index](docs/README.md) -> [README](README.md) -> [Runbook](RUNBOOK.md)

Generated: 2026-05-28

## 2026-05-29 Free AI Intelligence Audit

- DONE: Existing trust/disagreement modules were preserved and extended with deterministic AI summaries.
- DONE: `frontend-contract.json` now carries `race_intelligence_summary`, `changed_since_last_run`, `ai_features`, `source_conflicts`, event trust aliases, and per-driver `ai_explanation`.
- DONE: Local RAG and Ollama support are optional and disabled by default; deterministic provider remains the default.
- DONE: `/`, `/predictions`, `/model`, `/archive`, `/sources`, `/live`, and `/assistant` expose clearer AI-style, trust, source, and freshness states.
- DONE: GitHub Actions generated commits now use `Shreyansh Singhal <111811929+ShreyTriesToCode@users.noreply.github.com>` as author.
- PARTIAL: Optional local RAG currently uses keyword/BM25-style search only; embeddings remain a future local-only enhancement.
- NOT APPLICABLE: Paid hosted LLM or vector database integration was intentionally not added.

## DONE

- Backend entrypoint exists in `f1_briefing.py` and still supports the public briefing, retrain, model-status, and frontend-contract commands.
- Strangler modules now exist for config, SQLite storage, simulation helpers, prediction-contract helpers, and strategy-context features while `f1_briefing.py` keeps backward-compatible wrappers.
- Jolpica fetching is cache-aware, paginated for laps, and uses SHA-256 cache keys with atomic writes.
- FastF1, OpenF1, FIA documents, Open-Meteo, F1 timing/static feeds, F1DB, and RelBench are represented in source-health metadata.
- SQLite local storage exists at `data_cache/pitwall.db` for run/status style persistence while JSON contracts remain available for the frontend.
- The backend already emits `top10`, `full_grid`, and `all_predictions` fields.
- `/api/f1timing` has per-IP rate limiting and OpenF1 auth-restriction handling.
- Unit tests cover core API/cache/model contract behavior.
- FIA PDF `403/404` handling avoids retry storms, reuses stale official cached text where available, and reports forbidden documents clearly.
- F1DB/RelBench bootstrap planning exists without bundling large external artifacts.
- Contract validation now fails blank/invalid `frontend-contract.json`, `briefings/index.json`, `latest-model-debug.json`, and `model-status.json`.
- Frontend recovery now uses `latest-model-debug.json` first and previous valid contracts second, with visible warnings.
- Prediction rows now include model disagreement and prediction trust fields.
- `/sources`, Playwright smoke tests, ruff lint config, artifact-size checks, and rollback contracts are present.

## PARTIAL

- The modelling code is still mostly concentrated in `f1_briefing.py`; the system now exposes modular submodel outputs, but the file has not yet been fully split into `pitwall/models` and `pitwall/features`.
- F1DB and RelBench adapters are optional/offline. They report status and can read local data, but no dataset artifact is bundled by default.
- Post-race learning exists through cached race/result ingestion, but strategy context now needs continued expansion as more tyre/stint/race-control data becomes available.
- The frontend has a PitWall identity and several dashboards; continued polish should focus on browser-level interaction testing and richer charts rather than raw data density.
- Large runtime caches are still committed for reproducibility; the new artifact policy documents when to move them to external storage.

## BROKEN FIXED IN THIS PASS

- `/predictions` was driven by the selected target's `top10` rows only, so Full Grid Prediction was not first-class in the UI.
- Driver detail contained too little information and could be hard to scroll on small screens.
- `/api/f1timing` did not expose explicit auto-selection metadata or stable warning fields for active/live-session fallback states.
- Prediction rows lacked a complete race-intelligence shape for `points_probability`, `fastest_lap_probability`, `position_range`, `expected_strategy`, structured `explanation`, `data_freshness`, and `source_notes`.

## MISSING ADDED IN THIS PASS

- Canonical `top_10` alias in the normalized prediction contract.
- Strategy context annotations for tyre/weather mismatch, early tyre correction, safety-car/VSC/red-flag pit context, double-stack loss, and degradation cliff.
- Explicit `race_factors` and top-level `warnings` in normalized prediction output.
- `scripts/validate_contracts.py`
- `scripts/check_artifact_sizes.py`
- Canonical docs now live in `README.md`, `RUNBOOK.md`, `MODEL_REPORT.md`, `DATA_SOURCES.md`, `ARTIFACT_POLICY.md`, and `docs/README.md`.

## NOT APPLICABLE

- Paid-only APIs are not required.
- Supabase is not required for local or CI verification.
- The project must not claim predictions are always correct.
- Historical betting odds and Pirelli allocation are not scraped from unreliable or terms-hostile sources.

## 2026-06-08 Model Notebook And Workflow Hardening

- ADDED: `notebooks/pitwall_model_refinement.ipynb` with cache-first model inspection, leakage checks, chronological split checks, champion artifact inspection, ranking/regression metrics, and optional challenger training.
- ADDED: wrapper-based modules under `pitwall/features` and `pitwall/models` for feature, train, evaluate, predict, artifact, and validation concerns while preserving `f1_briefing.py` orchestration.
- FIXED: chronological model split is rolling by race group instead of hard-coded to old seasons.
- FIXED: full-race cache writes are atomic and record reuse/refresh/skip decisions in `data_cache/cache_manifest.json`.
- FIXED: prediction rows expose a stable alias schema and Top 10 is derived from the ordered Full Grid table.
- FIXED: frontend source-health tones distinguish fallback/stale/partial from healthy, archive confidence preserves `0%`, live controls refetch selected sessions, and Full Grid ranges can render from `position_range`.
- UPDATED: GitHub Actions runs cache-aware validation, trains/refreshes through `f1_briefing.py`, validates contracts, runs backend tests, runs frontend tests, and builds the frontend.
- ADDED: `model_comparison` and `actual_result_comparison` contract sections with frontend rendering on `/model` and `/archive`.
- ADDED: `pitwall/models/compare_actuals.py` for trusted predicted-vs-actual winner, podium, Top 10, Full Grid, and driver error metrics with pending/unavailable states.
- ADDED: visible `[TRAIN]`, `[CACHE]`, `[MODEL]`, `[VALIDATE]`, `[ACTUALS]`, `[ROUTE]`, and `[DONE]` logs plus a compact training summary table.
- ADDED: `scripts/check_links.py` and unit tests for offline route/link validation.

Remaining limitation: feature-building logic is still duplicated between historical and online prediction paths behind wrappers. Tests now cover schema and contract behavior, but a future deeper extraction should make the shared feature list a single source of truth.

## 2026-06-28 FIA, Lint, Atomic Artifact, And Notification Hardening

- FIXED: `fetch_fia_season_index()` no longer references out-of-scope model comparison variables on a successful FIA index fetch.
- ADDED: regression coverage for a mocked successful FIA season-index fetch with a cache miss, without live FIA network access.
- UPDATED: Ruff coverage now includes `f1_briefing.py` in local commands and CI workflows.
- ADDED: shared atomic text/JSON writers under `pitwall/io/atomic.py`; source registry, FIA index/parsed docs, model metadata, model artifacts, run status, feature snapshots, correction history, backtest history, frontend contracts, and local RAG JSON now route through atomic writes.
- ADDED: trust-aware FIA document resolver with official FIA, official event/archive, verified third-party index, regulation-mirror, verified-cache, summary-only, and unavailable states. It never synthesizes FIA documents.
- ADDED: bounded single-feature leakage diagnostic that writes `model_artifacts/leakage_diagnostic.json` and can fail CI only for extreme non-allowlisted metric collapse.
- UPDATED: workflow generated-output commits no longer stage reproducible runtime caches such as `data_cache/full_races/`, `fastf1_cache/`, or `models/saved_models/`.
- ADDED: staged artifact-policy check for forbidden runtime cache paths.
- UPDATED: GitHub notification fallback issues are labeled `briefing-notification` and auto-closed by default so automated briefings do not appear as open bugs.
- FIXED: FIA car-presentation upgrade packages are no longer limited to transparent ranking adjustments; parsed official upgrade rows now become bounded `fia_upgrade_*` ML training and inference features with explicit missing-data flags.
- FIXED: FIA upgrade context now reuses verified parsed car-presentation documents before probing live URLs. Blocked FIA/news URLs are attempted once, then the resolver moves to the next trusted candidate and finally exposes an explicit unavailable state instead of retrying the same forbidden source repeatedly.
- UPDATED: The scheduled briefing workflow refreshes FIA document metadata and the source registry by default, while still avoiding forced PDF redownloads unless explicitly requested.

## 2026-06-29 FIA Resolver Fallback Verification

- FIXED: FIA season-index fallback is now wired to the live-verified 2026 `api.fia.com` archive route when `www.fia.com` returns 403.
- FIXED: Resolver deduplication now prefers live official/archive documents over identical verified-cache rows, so stale cache cannot mask a working official fallback.
- FIXED: Optional 401/403/404/410 source failures return after one attempt and allow the resolver to continue to the next configured source.
- ADDED: Wayback season-index fallback before verified cache, labelled `source_authority=wayback_snapshot` and `source_status=archived_snapshot`; it is stale context, not live FIA.
- UPDATED: F1LivePulse is disabled by default until a stable machine-parseable FIA document feed is verified.
- VERIFIED: Live probe on 2026-06-29 returned `www.fia.com=403`, `api.fia.com=200`, Wayback availability `200` with a snapshot URL, and F1LivePulse redirecting to a feature page.
- VERIFIED: `fetch_fia_season_index(2026, refresh=True)` returned `status=available`, `source_authority=official_fia_archive_api`, `source_status=official_secondary_live`, and `documents=131`.

## 2026-06-29 FIA Tyres And Strategy Timeline

- ADDED: FIA Pirelli Preview/Competition Notes parsing for exactly three nominated slick compounds. The mapping is event-relative: lowest C-number is Hard, middle is Medium, highest is Soft.
- FIXED: C-number tyre handling no longer assumes a global compound identity. `C2` without a verified event mapping remains unknown; relative `SOFT`/`MEDIUM`/`HARD` labels continue to work.
- ADDED: cache-aware FIA tyre mapping lookup from `data_cache/fia-documents/<season>/<event>/text|parsed`, including compatibility for older parsed JSON that lacks the new `tyre_compound_nomination` field.
- ADDED: `predicted_strategy` contract output with stint sequence, lap ranges, mandatory two-dry-compound rule status, pit-duration basis, degradation basis, and explicit `data_derived` vs `heuristic_fallback` state.
- ADDED: same-circuit safety-car/VSC/red-flag lap-window aggregation from cached race-control rows. Thin history reports `thin_data` instead of presenting a fragile window as robust.
- UPDATED: `/strategy` now renders a compact stint timeline, safety-car window notes, and FIA compound source attribution only when the FIA mapping is available.
- VERIFIED: Unit tests cover C2/C3/C4 and C3/C4/C5 mapping direction, missing/malformed nominations, strategy mandatory-compound enforcement, safety-car buckets, thin-data state, and legacy parsed-cache reuse.

## 2026-06-29 Frontend SSR And Public Rendering

- FIXED: `/` and `/model` now load prediction/model contracts in server components and pass real initial data into the existing interactive client UI, so first render is driven by current generated data instead of a client-only placeholder shell.
- ADDED: shared `loadPredictionsPayload()` contract builder used by both `/api/predictions` and the server-rendered pages, reducing route drift between SSR and API responses.
- ADDED: SEO/Open Graph/Twitter metadata with a self-hosted PitWall visual asset.
- UPDATED: general hero/metadata visuals use self-hosted PitWall assets; the route preloader intentionally uses the real Formula1.com team car renders requested for the loading transition and falls back to the self-hosted PitWall SVG if an external render is unavailable.
- ADDED: route error boundaries for `/predictions` and `/live` so malformed contracts show a clear retryable fallback.
- ADDED: `/sources` now displays FIA resolver trust metadata (`source_authority`, `source_status`, official/verified/stale flags, URLs, and SHA256 when present).
- ADDED: `/predictions` now surfaces existing Monte Carlo simulation output from the generated contract without presenting it as actual race results.
- VERIFIED: `npm run build` passes and the server bundle imports `loadPredictionsPayload()` for `/` and `/model`; local `next start` HTTP verification was blocked by sandbox port binding, so raw HTTP fetch needs a human/local shell check.

## 2026-06-29 Score Missingness And Repo Hygiene Audit

- FIXED: Legacy contract normalization no longer fills `energy_boost_advantage_score`, `active_aero_suitability_score`, `defend_risk_score`, `top10_safety_score`, DNF probability, or classified-finish probability with shared neutral constants when the underlying per-driver components are missing. Those fields now expose `*_available=false` and `score_unavailable_reasons`.
- FIXED: Monte Carlo race simulation now labels when DNF probability used the explicit `fallback_default_unavailable_reliability` assumption rather than a contract-provided driver value.
- AUDITED: `team_track_fit`, `weather_adaptation`, and `reliability` ranking inputs are already carried through `component_scores`; unavailable inputs remain `None` for weighted scoring instead of being promoted as measured per-driver data.
- FOUND: 295 reproducible cache/model files were still tracked from earlier history across `fastf1_cache/`, `data_cache/full_races/`, and `models/saved_models/`. `.gitignore` blocks future additions.
- MEASURED: `data_cache/frontend-contract.json` is 28.18 MB with 10 briefing/archive entries; growth should be monitored before adding many more archived contracts to the canonical JSON.

## 2026-06-29 Real-Car Preloader And Cache Untracking

- UPDATED: The start/loading transition now uses the real Formula1.com 2026 team car renders again, matching the earlier visual behavior. The owned PitWall SVG remains only as an error fallback when a remote car render cannot load.
- FIXED: `fastf1_cache/`, `data_cache/full_races/`, and `models/saved_models/` were untracked with `git rm --cached` while preserving the local files on disk. `git ls-files` now reports 0 tracked paths under those reproducible cache/model directories.
- VERIFIED: Cache untracking is accepted by `scripts/check_artifact_sizes.py`; staged deletions of ignored cache files are not treated as newly staged forbidden cache artifacts.
