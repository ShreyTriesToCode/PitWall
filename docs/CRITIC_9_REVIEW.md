# Second review: target 9 in every category

This review is separate from the earlier 8.16 local candidate report. Scores must reflect verified results, not the requested target.

## Issue inventory before the implementation pass

- P1: Timing tyre age coerces null to zero and a bar assumes a 35-lap tyre lifetime. Remove unsupported wear visualization and preserve unknown age.
- P1: Feed WindSpeed is m/s (FastF1 parser contract); the UI labels it km/h. Correct the unit.
- P1: Timing channel 45 is presented as Aero / Boost without a verified current-season channel contract. Withdraw that column.
- P1: Tyre and sector lists truncate at 20 drivers; current fields can contain 22. Render the supplied field.
- P2: Driver search has no explicit no-match state.
- P2: Timing tables use layout divs; settings have an unlabeled select, ineffective delay setting and no Escape dismissal.
- P2: Large obsolete CSS cascade causes mobile header bloat, inconsistent timing surfaces and unnecessary visual effects.
- P2: No automated accessibility audit or JavaScript lint gate.
- P3: Fonts require third-party browser requests; motion and press/focus feedback are inconsistent.

Prospective prediction evaluation, actual live-event endurance and hosted deployment verification remain evidence requirements. UI changes cannot satisfy those requirements.

## Completed review — 2026-09-18

This is iteration 3, following the real 7.69 and 8.16 reviews in
[VALIDATION.md](VALIDATION.md). No intermediate numerical score was invented for
this pass. The requested target is **9.0 in every category**, stricter than the
original release threshold. This checkout does not yet satisfy that target.
No commit, push, deployment or hosted CI execution was performed.

### Repairs and verification

- Removed the unsupported 35-lap tyre wear assumption and unverified Aero / Boost
  channel. Unknown tyre ages stay unknown; observed zero age remains zero.
- Corrected wind to m/s. Zero speed, RPM, gear and brake observations survive
  normalization. Partial car readings remain available with their limitations.
- Removed 20-driver and miniature-sector truncation. Unknown positions are not
  replaced with array indices. Track flag labels follow the documented code map.
- Normalized provider `Utc` fields to explicit UTC before sending them to the
  browser. Zone-less generic dates and relative audio offsets do not become
  invented absolute timestamps. A real archived message now renders 14:47:48 UTC,
  matching its normalized `2026-09-13T14:47:48.000Z` source value.
- Recomputed forecast identities, input hashes, rankings, versions and cutoffs at
  the ledger/contract boundary. Corrupt or tampered records fail publication.
- Replaced the obsolete CSS cascade with shared styles and a separate timing
  stylesheet; retained PitWall's dark/red identity. Self-hosted Inter, compact
  mobile navigation, readable tables and consistent controls replace decorative
  effects. No third-party font request is needed.
- Added explicit no-match results, semantic timing tables, keyboard-accessible
  table scrolling, labeled settings, Escape dismissal and focus restoration.
- Added 160 ms control/disclosure feedback and a 240 ms, 6 px surface entrance.
  Text opacity stays opaque during entrance to avoid transient contrast loss.
  Reduced-motion disables animation. Loading rotation stops with loading.
- Fixed a reproduced 320 px grid overflow with an explicit shrinking constraint.
  The regression check compares document width with the configured viewport,
  avoiding mobile viewport expansion masking the defect.
- Added ESLint and React hook checks, axe accessibility checks, mobile WebKit,
  non-UTC browser execution and forecast integrity regression tests.

### Executed gates

| Check | Outcome |
|---|---|
| Clean frontend `npm ci` | Passed; 150 packages installed, 151 audited, zero vulnerabilities at execution |
| Python dependency consistency | `pip check` passed |
| Ruff: `f1_briefing.py pitwall scripts tests` | Passed |
| Python suite | **171 passed, 14 subtests passed**; final run 6.97 s |
| Node unit tests | **19 passed** |
| Product artifact validation | Passed; **0 genuine forecasts, 0 evaluations** |
| Frontend ESLint and React hook checks | Passed, zero warnings |
| Frontend Prettier | Passed |
| Production build | Passed; browser runner built and launched with Node 24 |
| Full browser suite | **84 passed**, 23.9 s; 21 checks across four projects |
| Final metric-label polish | Rebuilt; 4 methodology browser checks passed; lint, formatting and diff checks passed |
| Production timing endpoint | HTTP 200; archive state, not live, source UTC retained |
| Actual rendered mobile timing | 390 px document / 390 px viewport; no alert; UTC messages correct |

Browser projects: Chromium desktop 1440×1000, laptop 1280×800, mobile 390×844,
and WebKit phone 390×844. Extra checks cover 320 px and reduced motion. All use
Asia/Kolkata timezone to expose implicit-local-time bugs. Screenshots are in the
ignored `frontend/test-results/` directory and reproducible with
`PITWALL_CAPTURE_REVIEW=1 npm test`. Synthetic timing and scenario data are isolated
in tests. The main accessibility screenshots use the real published snapshot.

An intermediate 84-check run had four failures: the animation test treated a
stationary identity matrix as movement, and WebKit required Option-Tab to enter
links. Correcting those test assumptions produced four targeted passes, then the
84-pass run above. Earlier runs also exposed the actual narrow-grid and transient
contrast defects repaired in this pass. Tests were not disabled to obtain a pass.

## PITWALL CRITIC REPORT — iteration 3

**Overall: 8.72 / 10. Target 9 in every category: NOT MET.**
Raw weighted score: **8.728**, truncated to two decimals. Weights are unchanged
from iteration 2. Scores are reviewer judgments about this local candidate, not
statistical measurements of reliability. No local release-blocking defect was
reproduced in the final tested paths; hosted release remains unverified.

| Category | Weight | Score | Evidence and limit |
|---|---:|---:|---|
| Data Correctness | 18% | 9.0 | Dynamic event selection, explicit unknowns, corrected units/UTC/zero handling, hash validation; upstream revisions still possible |
| Prediction Validity | 16% | 7.8 | Reproducible baseline, immutable validated records and chronological comparison; zero prospective outcomes and later-retrieved historical data |
| Backend | 10% | 8.8 | Bounded provider handling, integrity checks and controlled failures; real live-event endurance and hosted persistence not verified |
| Frontend | 10% | 9.0 | Four browser projects, explicit states, keyboard controls, semantic tables and strict hook checks; no manual assistive-technology certification |
| Product Design | 8% | 8.9 | Consistent identity, improved density and hierarchy, inspected actual renders; mobile timing still requires substantial table navigation |
| F1 Accuracy | 10% | 8.8 | Complete supplied field, corrected timing semantics, UTC and flag mapping; grid penalties and strategy effects remain outside prediction scope |
| Product Credibility | 10% | 9.1 | Visible provenance, honest unavailable states and rejected candidate; published backtest is explicitly retrospective |
| Non-AI Quality | 6% | 9.0 | Removed invented wear/unsupported channels, obsolete decoration and repeated CSS; deliberate typography and useful information hierarchy |
| Testing | 7% | 8.9 | 171 Python + 14 subtests, 19 Node and 84 browser passes; no production load/endurance or real-device assistive-technology run |
| Maintainability | 5% | 8.3 | Smaller active styles/modules, lint/CI and updated docs; large quarantined legacy research tree remains |

### CRITICAL ISSUES

None reproduced in the final validated local production paths. **Do not interpret
this as verification of the public deployment.** The 9-per-category acceptance
criterion remains unmet. It cannot be made true by changing a score or inventing
prediction records.

### MAJOR ISSUES — why, root cause and best fix

1. **No prospective performance history.** Users cannot establish predictive
   usefulness from genuinely pre-race captures yet. Legacy provenance was
   inadequate; retrospective caches may contain later corrections. Keep the
   reconstruction label, collect immutable new forecasts as qualifying becomes
   available, evaluate official classifications, and reserve future events for
   untouched candidate comparison. No model promotion or confidence claim is
   justified by the current empty prospective sample.
2. **Live and hosted operational endurance remains unverified.** Fixture tests
   exercise states but cannot establish upstream continuity, production load or
   durable host writes. The source is undocumented and no active session occurred
   during this audit. Run the runbook on the deployment host, verify persistence
   and scheduled publication, and observe a legitimate live session through
   interruptions before promising an operational SLA.
3. **Mobile timing is inherently wide and dense.** Full timing fields require
   horizontal table scrolling and several sections. This is contained, labeled and
   keyboard accessible, but still needs task-based fan testing to establish an
   excellent phone experience. Preserve full observations; measure whether a
   compact column selection or driver-focused detail view improves actual tasks
   before introducing another interaction layer.
4. **Legacy research debt persists.** Large inactive modules and old artifacts make
   contributor onboarding harder despite the enforced production boundary. Keep
   the active paths documented; migrate or archive research modules in bounded
   changes with regression coverage. A blanket rewrite/deletion risks losing
   provenance and working research behavior.

### MINOR ISSUES

- Manual VoiceOver/screen-reader review and physical-device checks are still needed;
  zero axe findings only covers the tested machine-detectable rules.
- Hosted Core Web Vitals, sustained streaming memory and low-end-phone performance
  have not been measured. Short CSS transitions are not proof of smooth field
  performance. Gather those measurements before a performance score of 9+.
- A timing status/source label is repeated between the heading and status area.
  It is accurate but could be consolidated while retaining visible failure states.

## Important files changed in this pass

- `frontend/app/globals.css`, `app/styles/timing.css`: shared design and motion,
  responsive containment, removal of obsolete styling.
- `frontend/app/live/page.jsx`: timing semantics, complete field, accessibility,
  settings and consistent loading behavior.
- `frontend/app/api/f1timing/route.js`, `api/_lib/timing.js`: preserve observed zero,
  normalize UTC, remove unsupported channel output.
- `frontend/app/components/ProductViews.jsx`, `PitWallComponents.jsx`: empty search,
  calendar disclosure, focus/navigation and safe unavailable metric formatting.
- `frontend/app/api/_lib/contracts.js`, `pitwall/models/ranking.py`, `ledger.py`,
  `scripts/validate_product.py`: validate forecast provenance against actual inputs.
- `frontend/tests/accessibility.spec.js`, `tests/unit/`, `tests/test_production_ranking.py`:
  rendered accessibility, motion, timezone and data-integrity regressions.
- `frontend/eslint.config.mjs`, `playwright.config.mjs`, package files and CI:
  repeatable lint, WebKit and self-hosted fonts.
- `UI_AUDIT.md`, `frontend/README.md`, `MODEL_REPORT.md`, `DATA_SOURCES.md` and this
  report: current behavior, actual evidence and explicit limitations.

The separate frontend critic is in [UI_AUDIT.md](../UI_AUDIT.md).
