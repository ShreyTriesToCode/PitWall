# PitWall critic report — 28 September 2026

## Scope

This review follows the September 25 consumer review and the September 26–28
implementation pass. It assesses the actual local production build, real provider
responses and executed regression tests. It is an engineering review, not an
independent user study or a statistically established accuracy claim.

## Initial diagnosis and root causes

| Priority | Finding | Root cause and repair |
|---|---|---|
| P1 | Tyre compounds disappeared from real session observations | Sparse `Stints` updates replaced previous records. Merge indexed patches without collapsing numeric keys. Keep the current stint, even when incomplete; never borrow an older compound. Verified all 22 compounds in the same practice feed after repair. |
| P1 | Missing prospective history | The repaired publisher was not deployed. Capture a genuine forecast before start, preserve immutable provenance, and evaluate only after matching classifications arrive. Change publication to hourly; isolate daily FIA retrieval from capture. |
| P1 | Results outage could prevent capture | Calendar, results and qualifying shared one failure boundary. Isolate results failure and expose it without blocking otherwise valid qualifying inputs. |
| P1 | Completion/live labels could overstate evidence | A scheduled end is not proof of completion; qualifying segment finishes are not whole-session finishes. Require recent packets and Started status for live, and Finalised/Ends or classification evidence for completion. |
| P2 | Strategy was an unavailable placeholder | Reuse the timing data and session selection to provide compound/age comparison, sorting, filtering, weather and race control. No unsupported pit-window optimization. |
| P2 | Mobile timing was dense | Compact phone view prioritises position, driver and interval. Full detail is available with one toggle. Move provenance disclosures below the data. |
| P2 | Freshness wording was ambiguous | Distinguish analysis snapshot, calendar/results retrieval, source packet and screen refresh. Retain historical/unavailable labels. |
| P3 | Display preferences | Use 12-hour IST with AM/PM. Upcoming yellow, verified ongoing green, verified completed muted red; uncertainty remains neutral. |

## Prediction validity and actual evidence

Production remains `qualifying-order-v1`: the published qualifying order is a
baseline estimate of final classification, including classified non-finishers.
It does not predict calibrated winner probabilities, tyre degradation or pace.
Top 10 derives from the ordered full field.

Azerbaijan 2026 was genuinely captured locally at
`2026-09-26T10:58:15.783851+00:00`, before the scheduled `11:00 UTC` start.
Input cutoff: `2026-09-26T10:58:15.778280+00:00`. The record was first published
to GitHub after the event; its capture was local, not an independently timestamped
public pre-race forecast. It has not been recreated or backdated.

The original record was evaluated on September 28 against a complete matching
22-driver provider classification: MAE **5.00 places**, RMSE **6.4385 places**,
Spearman **0.4850**, winner hit **1**, winner in predicted top three **1**.
One race is not a reliable performance estimate. Future hourly captures will
build a publicly inspectable history. Corrections append evaluation revisions.

Retrospective 2024–2025 comparison: 39 eligible races; qualifying-order MAE
**3.0719** versus candidate MAE **3.1908**. Candidate rank correlation also loses
(**0.6928** versus **0.7057**). It was not promoted. This is a reconstruction from
historical provider records, whose revisions may differ from pre-race publication.
Duplicate race groups now fail backtesting; history is restricted to strictly
earlier starts. Future promotion still requires untouched chronological validation,
multiple season blocks and review. No automatic weight mutation is enabled.

## Verification

- Ruff across `f1_briefing.py pitwall scripts tests`: passed.
- Python: **173 passed, 14 subtests passed**.
- Frontend unit tests: **28 passed**, including noon/midnight IST, packet expiry,
  sparse stint/sector patches and segmented qualifying completion.
- Browser suite: **96 passed** across desktop, laptop, phone Chromium and phone
  WebKit. Includes axe, error/unavailable states, full-grid/Top 10, forecast expiry,
  Strategy controls, compact timing, 320px overflow and reduced motion.
- Production build, ESLint, Prettier and product validation passed.
- `npm audit --audit-level=high`: **0 vulnerabilities** at execution.
- Real API: practice field retained all 22 compounds after sparse-patch repair;
  live race without an available static path stayed unavailable on September 26.
- September 28: real race Strategy data contains all 22 compounds; archive has one
  immutable capture and one actual evaluation; overview selects the next race.
- GitHub CI and publication details are recorded in the PR/workflow linked by the
  delivery message; local checks alone do not prove hosted deployment success.

## PITWALL CRITIC REPORT

Overall: **8.90 / 10**. Equal weights (10% per category); no upward rounding.

| Category | Score | Evidence and limitation |
|---|---:|---|
| Data Correctness | 9.1 | Real sources, explicit failure, repaired sparse feed merge; provider availability is external. |
| Prediction Validity | 8.4 | Deterministic baseline, failed candidate disclosed, real capture/evaluation lifecycle; one prospective race and no calibrated probability model. |
| Backend | 9.0 | Validated contracts, immutable ledger, independent publication failures; legacy research code remains large. |
| Frontend | 9.0 | Shared timing/Strategy data path, accessible controls, compact phone timing, honest states. |
| Product Design | 9.1 | Deliberate motorsport typography, seamless artwork, restrained motion; detailed Strategy table still scrolls on narrow phones. |
| F1 Accuracy | 8.8 | Sprint schedules and classification statuses retained; qualifying segments handled; substitutions and complete-field mismatch require review. |
| Product Credibility | 9.0 | Provenance, clearly labelled baseline and historical data; no invented confidence or strategy advice. |
| Non-AI Quality | 9.0 | Purposeful racing identity and useful data controls; generated artwork provenance is documented. |
| Testing | 9.0 | Regression, accessibility and browser matrix; live-event endurance remains limited. |
| Maintainability | 8.6 | Shared components and documented operations; legacy research monolith remains isolated but costly to maintain. |

### Critical issues

No known local correctness/build blocker remains in the exercised paths. Release
still requires successful repository CI; hosting verification is separate.

### Major limitations — why, root cause and best fix

1. **Prospective sample size is one.** No stable accuracy conclusion is defensible.
   The new ledger only just started. Retain hourly captures, publish timestamps,
   evaluate full results and wait for enough untouched races before promotion.
2. **Live feed access is not guaranteed.** Formula 1's static feeds can omit active
   session paths and packet timestamps. Preserve unavailable/stale states; any
   contracted live provider integration needs legitimate credentials and validation.
3. **Strategy is observational.** Fuel, traffic, clean-lap selection and pit-loss
   inputs are insufficient for validated optimization. Do not add pit advice until
   those inputs and out-of-sample evidence exist.

### Minor issues

- Narrow-screen Strategy comparisons use horizontal scrolling for all columns.
  A future driver comparison drawer could make detailed lap inspection easier.
- Legacy research modules remain much larger than the production publishing path.
  Refactor them only with an explicit research requirement and regression coverage.

### Critic history

- Earlier full review: **8.72** (September 18; see CRITIC_9_REVIEW.md).
- Consumer review: **8.67** (September 25; different consumer-weighted assessment).
- This release review: **8.90**. Strategy, sparse tyre updates, phone density,
  timestamp wording and the capture/evaluation lifecycle improved. The requested
  9+ in every category is not supported by the available prediction evidence.

## Important files

`SessionTiming.jsx`, `ObservedStrategy.jsx`, `ProductViews.jsx`, `time.js`,
`session-status.js`, timing route/helpers, ranking/ledger/backtest/publish modules,
three workflows, unit/browser/Python regression tests and RUNBOOK.md.
