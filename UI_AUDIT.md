> **Current consumer review:** [Updated artwork, IST display and final consumer critique](docs/CONSUMER_REVIEW.md).

> **Theme follow-up, 2026-09-22:** The Formula 1 identity has been restored. See [the separate theme, motion and visual critic](docs/THEME_REVIEW.md), scored 9.06 for that scope. The broader frontend assessment below is retained as the earlier review.

# Frontend critic — 2026-09-18

This report supersedes the old UI audit of the retired implementation. It covers
actual rendered output from the local production build. It is separate from the
[whole-product critic](docs/CRITIC_9_REVIEW.md).

## Verdict

**8.91 / 10** (equal-weight assessment below: raw 8.916666…; truncated).
The interface is materially improved. The request for 9+ in every section is
**not yet satisfied**. “Impeccable” and “no issues” would overstate this evidence.

| Area | Score | Basis and limit |
|---|---:|---|
| Hierarchy and visual consistency | 9.1 | Clear event, state and data hierarchy; restrained red/dark identity and consistent self-hosted typography |
| Responsive layout | 9.0 | Desktop, laptop, two mobile engines and 320 px checks pass; tables intentionally scroll within their containers |
| Controls and states | 9.1 | Explicit loading/failure/unavailable/no-match states; retry, search, menu, settings and focus restoration verified |
| Motion | 9.0 | Short bounded entrance/disclosure/press feedback, no continuous decoration, stationary end state and reduced-motion tests |
| Accessibility | 8.8 | Semantic tables, labeled controls, focusable scroll regions, keyboard and axe checks; no manual screen-reader certification |
| Performance evidence | 8.5 | Production build and short transitions verified, self-hosted fonts; no hosted Core Web Vitals or low-end-device measurements |

## Actual review coverage

Viewed overview at 1440×1000, methodology at 1280×800, and session timing at
390×844 in the browser. Inspected saved production-build screenshots including
rankings, results/history in mobile WebKit, methodology and the 320 px overview.
The broader browser suite covers overview, rankings, drivers, constructors,
strategy, sources, methodology, archive and timing across four projects.

States checked include current upcoming event, historical classification/timing,
unavailable qualifying, loading, API failure/retry, no matching search results,
empty calendar and isolated test-only live timing. There was no genuine live event
during the review. Test screenshots are not evidence of live production operation.

## Improvements verified

- Consistent spacing, neutral surfaces, tabular figures and compact mobile header.
- Responsive calendar/grid shrinking; no document overflow in covered checks.
- Wide classifications remain readable in contained, keyboard-scrollable tables.
- Timing selector and provenance disclosures reduce the initial information load.
- Full supplied field remains visible, including 22-driver timing fixtures.
- Settings has real labels and Escape dismissal; mobile menu restores trigger focus.
- No-result search explains the empty state instead of showing an empty table.
- Surface entrance uses 240 ms translation; controls/disclosures use 160 ms.
  Text stays fully opaque; reduced motion removes animations.
- Unsupported tyre-wear visualization and Aero / Boost removed; correct wind units,
  explicit unknown values and valid zero readings retained.
- UTC race-control messages remain correct in an Asia/Kolkata browser.

## Critical issues

None reproduced in the covered local rendered paths. This is bounded validation,
not a guarantee that every browser, provider payload or hosting state is correct.

## Major issues

**Mobile timing remains dense.** Sideways navigation is necessary to see all timing
columns. Root cause: a complete motorsport table carries more fields than a phone
can display at readable size. Best next improvement: observe actual driver-tracking
tasks and compare a compact column selector or driver detail view against the current
contained table. Do not hide legitimate rows or shrink type merely to fit.

**Real-world performance is unmeasured.** Local render success cannot establish
frame stability under a long stream or good Core Web Vitals on slow devices. Root
cause: no deployed measurements or legitimate live-session endurance run. Best fix:
measure the deployed build and an actual session, then target observed bottlenecks.

## Minor issues

- Consolidate duplicated timing state/source copy while preserving error visibility.
- Complete VoiceOver, physical-device and zoom/readability review before describing
  accessibility as comprehensive. Automated axe results alone are insufficient.

## Evidence

Full suite: **84 passed** across Chromium desktop/laptop/mobile and WebKit phone.
It includes axe checks for eight product routes and timing, 320 px containment,
keyboard entry, settings/menu focus behavior and reduced-motion/bounded-motion
assertions. Test fixtures are confined to the test suite. Separate backend/unit
results and the critic history are recorded in the whole-product report.
