# PitWall UI Audit

## Summary
- Reduced oversized card-first layouts and moved dense prediction, driver, constructor, archive, and model data into compact tables and tabs.
- Kept the dark PitWall identity while reducing red border usage for normal cards. Red is now reserved more consistently for active, warning, or critical states.
- Added shared frontend primitives for compact tables, metric cards, data-state badges, developer-only panels, and data availability checks.
- Preserved Top 10 predictions, Full Grid predictions, scenario comparison, source health, timing replay, archive comparison, and model status routes.

## Files and Components Changed
- `frontend/app/components/PitWallComponents.jsx`: added `DataStateBadge`, `SectionCard`, `MetricCard`, `CompactTable`, `DeveloperOnlyPanel`, data availability helpers, Developer Mode, compact ticker labels, and simulated scenario labeling.
- `frontend/app/predictions/page.jsx`: made Full Grid the primary component, compacted Top 10, hid raw debug fields behind Developer Mode, added low-trust warning copy, and clarified metric meaning.
- `frontend/app/drivers/page.jsx`: replaced card grid with compact sortable/filterable P1-P22 table and kept driver detail drawer.
- `frontend/app/teams/page.jsx`: replaced tall constructor cards with a constructor comparison table and selected-team detail section.
- `frontend/app/strategy/page.jsx`: compacted controls and labelled scenario/simulator output as simulated.
- `frontend/app/live/page.jsx`: labelled archived timing replay, hid blank mini-sector blocks, collapsed mostly missing telemetry, and removed audio controls for invalid/zero-duration radio rows.
- `frontend/app/model/page.jsx`: renamed visible page to Model Center and split content into Overview, Metrics, Source Health, and Developer tabs.
- `frontend/app/archive/page.jsx`: deduped archive rows, grouped by race, moved raw briefing links to Developer Mode, and gated actual-result claims.
- `frontend/app/page.jsx`: compacted dashboard sections and collapsed long explanatory content.
- `frontend/app/globals.css`: added compact layout styles, tab styles, compact table styles, developer panel styles, and responsive fixes.
- `frontend/app/api/f1timing/route.js`: tightened useful live timing detection so weather/race-control-only payloads do not suppress fallback standings.

## Page-by-Page Fixes
- Command Center: kept current race, countdown, top three, prediction trust, strategy risk, source health, timeline, calendar, and quick links while collapsing explanatory content.
- Prediction Board: Full Grid is first-class, Top 10 remains visible, low-trust predictions show a warning, and debug/internal fields require Developer Mode.
- Driver Analysis: all drivers are accessible in a compact table with team, rank range, confidence, watchlist, and sort controls.
- Team Analysis: constructor comparison table is the primary view; detailed constructor evidence appears only for the selected team.
- Strategy Wall: scenario cards are compact and marked simulated; rain scenario copy explains fallback sensitivity when live rain risk is unavailable.
- Timing Replay: archived sessions are not labelled live; blank telemetry, mini-sector placeholders, and invalid audio players are suppressed.
- Model Center: normal users see model version, key metrics, source health, and actual-result comparison; schema/bundle/validation internals live in Developer.
- Archive: duplicate race cards are removed by race + target + stage + model version; comparison requires two selected records.

## Data Correctness Fixes
- No winner match or recall is shown unless actual-result comparison is trusted and available.
- Pending actuals render as compact pending states.
- No audio player is shown for missing, zero, null, or `0:00` duration radio clips.
- No blank mini-sector block is rendered when mini-sector data is missing.
- Mostly missing car telemetry collapses to “Telemetry unavailable for this session.”
- Fallback/stale/source states are shown through badges instead of looking fully healthy.
- Scenario ranking is labelled simulated unless it is part of official final prediction output.
- Timing replay is labelled archived when the feed is not genuinely live.

## Known Remaining Limitations
- Playwright/browser route verification was not run by default because prior workflow runs timed out while downloading Playwright browsers. Production build validation is the primary automated UI check in this pass.
- The frontend still depends on generated JSON contracts; if a contract omits optional fields, compact empty states are shown instead of fabricated values.
- External F1 source freshness can only be as reliable as the backend source timestamps and cache metadata.

## How To Test The UI
1. From the repo root, run `cd frontend`.
2. Run `npm run build`.
3. Run `npm run check`.
4. Start the app with `npm run dev`.
5. Visit `/`, `/predictions`, `/drivers`, `/teams`, `/strategy`, `/live`, `/model`, `/archive`, and `/sources`.
6. Toggle Developer Mode on Prediction Board or Archive only when raw contract details are needed.

## Manual Verification Targets
- `/predictions`: Full Grid table, compact Top 10, low-trust banner, Developer Mode.
- `/drivers`: P1-P22 table, filters, watchlist, driver drawer.
- `/teams`: constructor table and selected-team detail.
- `/live`: archived timing label, no invalid radio controls, telemetry unavailable state.
- `/model`: Overview/Metrics/Source Health/Developer tabs.
- `/archive`: race grouping, no duplicate race cards, two-record comparison.
