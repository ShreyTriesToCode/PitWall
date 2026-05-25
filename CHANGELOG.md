# Changelog

## 2026-05-25

### Added

- Strangler modules for config, SQLite storage, model simulation helpers, prediction-contract helpers, and strategy-context features.
- FIA decision-document fetch handling that avoids retry storms on deterministic `403/404`, reuses cached official text where available, and reports forbidden documents.
- Optional dataset bootstrap planning script for F1DB and RelBench without committing full external artifacts.
- Season-based Formula1.com track images for the timing page, including the 2026 Montreal and Monte Carlo detailed track images.
- Canonical `top_10` alias, `race_factors`, and warning fields in normalized prediction contracts.
- Rich per-driver prediction fields: points probability, fastest-lap probability, DNF risk, position range, expected strategy, structured explanation, data freshness, and source notes.
- Strategy-context annotations for wrong tyre/weather mismatch, early tyre correction, safety-car/VSC/red-flag pit context, double-stack loss, and degradation cliff.
- `AUDIT.md`, `MODEL_REPORT.md`, `DATA_SOURCES.md`, and `SETUP.md`.

### Changed

- `/predictions` now separates Race Overview, Top 10 Prediction, and Full Grid Prediction instead of rendering only the selected top-10 board.
- Driver detail drawer now shows all key probabilities, strategy, tyre/weather/risk notes, model reasons, and source notes in a scrollable viewport-fixed panel.
- `/api/f1timing` now returns explicit auto-selection metadata, warning arrays, and safe normalized timing payloads for live, stale, archive, and fallback states.
- Default local race simulation count documented as 10,000 while CI remains configurable lower.

## 2026-05-24

### Added

- Season-replenishable source registry and FIA document status fields in generated contracts.
- SQLite-backed local store for run status, feature snapshots, and prediction history while keeping JSON contracts for the frontend.
- Optional Supabase sync configuration, disabled unless credentials are present.
- Optional OpenF1 authentication environment variables and source-health reporting for auth-restricted responses.
- Optional F1DB and RelBench rel-f1 adapters with source-health metadata, licensing notes, and no automatic heavy downloads.
- Stable `model_artifacts/` exports for evaluation, feature importance, drift status, and training metadata.
- Chronological grouped validation with larger 2022-2024 validation and 2025-2026 out-of-time reporting.
- Regularized model settings, feature importance pruning, empirical calibration, race-level normalization, Spearman, NDCG, top-N precision/recall, and stricter champion promotion gates.
- Rolling 3/5/10 driver and team form, teammate deltas, constructor alias normalization, pit execution variability, circuit DNF proxy, sparse-history flags, and season recency weighting.
- Circuit-relative lap-delta pace model to replace the old raw-lap neural forecast.
- `/api/f1timing` per-IP rate limiting.
- Verification report at `docs/verification-report.md`.
- Methodology document at `METHODOLOGY.md`.

### Changed

- Jolpica cache hits no longer sleep before reading cached data.
- Jolpica round data fetches results, qualifying, pits, sprint, sprint qualifying, and paginated laps concurrently.
- Jolpica laps now page with `limit=100` and `offset` until `MRData.total` is satisfied.
- HTTP cache keys now use SHA-256 and cache writes are atomic.
- 429 handling honors `Retry-After`.
- ICS calendar fetch now caches and falls back to the last valid cached calendar.
- FastF1 session loading is wrapped with a timeout.
- Jolpica grid `0` is treated as pit-lane/back-of-grid instead of missing grid data.
- `/predictions` now uses the selected target payload consistently.
- Mobile driver detail UI now opens as a fixed bottom sheet at the bottom of the viewport.
- `/teams` normalizes constructor names before grouping.
- GitHub Actions now reports cache presence and defaults historical backfill/FIA document limits to unlimited unless configured.

### Fixed

- Overstated promotion behavior caused by validation-only baseline checks.
- OpenF1 401/403 live-session restrictions being too easy to misread as broken timing.
- Fast timing API mode suppressing public fallback data when primary timing feeds were empty.
- Python-side auto-commit now honors `AUTO_COMMIT_ENABLED=false` so GitHub Actions can own the commit/rebase/push flow.
- Generated public JSON now strips absolute local workspace paths from source registry and FIA cache metadata.
- Cache key collision risk from slugified URLs.
- Weighted averages inflating confidence when most component weights were missing.
- Frontend route and API source-health fallbacks missing selected/generated metadata.

### Known Limitations

- The latest challenger is held back because it does not beat grid/qualifying baselines on every out-of-time ranking metric.
- npm audit could not be completed in this run due registry access restrictions in the environment.
- Playwright browser automation was unavailable because the package is not installed and dependency download could not be performed.
