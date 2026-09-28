# Validation and critic record — 2026-09-17

> Historical record of the September 17 pass. See the [September 18 stricter review](CRITIC_9_REVIEW.md) for current test counts, ESLint/WebKit coverage and scores. The earlier “final” designation applies only to that pass.

## Scope and release status

This record concerns the repaired local checkout, not a deployment of
`pitwall.shreybuilds.com`. No commit, push, production deployment, or remote CI run
was performed. The local release candidate meets the critic threshold below;
production rollout still requires the deployment/runbook checks on its host.

Environment: macOS, Python 3.11 in `.venv`, Node 26.8.1, npm 11.19.0,
Next.js 16.3.5. CI is configured for Python 3.11 and Node 24 LTS; that hosted
combination has not been executed in this session. The source is JavaScript,
not TypeScript; Next compilation is not a claim of static type coverage.

## Executed checks

| Check | Observed outcome |
|---|---|
| Clean Python environment and installation of requirements + development requirements | Passed during initial audit |
| Clean `npm ci` from final lockfile | Passed; 28 packages installed, 0 audit vulnerabilities |
| `.venv/bin/python -m pip check` | No broken requirements |
| `.venv/bin/ruff check f1_briefing.py pitwall scripts tests` | All checks passed; includes the monolith as required |
| `.venv/bin/python -m pytest -q` | **169 passed, 9 subtests passed**; final Python run 5.55 s |
| `python scripts/validate_product.py` | Passed schema/provenance/metric gate; 0 genuine forecasts, 0 evaluations |
| `npm run test:unit` | **15 passed**, 0 failed |
| `npm run format:check` | All configured frontend files conform |
| `npm run build` | Production compilation and all routes passed |
| `npm test` | **27 passed** across desktop, laptop and mobile; final release screenshot run 9.0 s |
| `npm audit --audit-level=high` | **0 vulnerabilities** at audit time |
| `git diff --check` | Passed |
| Next output file tracing | Predictions API bundle explicitly includes `data_cache/product.json`; no legacy data-cache exports in that trace |
| Production server | Started successfully on `127.0.0.1:3000` |

npm 11 reported optional macOS `fsevents` install-script approval information;
installation, compilation, server startup and browser tests succeeded. No approval
was added merely to silence that notice. No frontend ESLint configuration exists;
formatting and compilation should not be described as a semantic lint suite.

### Baseline and intermediate failures

Before repairs, Python had 157 passes, 9 passing subtests and one failing cache test
that accidentally requested the network. It now uses an isolated fixture and rejects
unexpected requests. Brittle tests asserting obsolete UI strings/debug recovery were
removed and replaced by executable frontend and production-pipeline tests.

The original npm audit reported five vulnerable packages including a critical Next
advisory. Dependency updates removed those findings. Initial browser runs exposed
ambiguous test locators, a doubled sidebar offset and missing responsive coverage;
those were fixed before the passing runs. The final rendered timing review caught
UTF-8 BOM parsing after bounded response reading; the real feed and a regression
unit test verified its repair.

## Real provider and API observations

- Publisher and frontend selected **Azerbaijan Grand Prix**, `2026:15:race`, scheduled
  26 September 2026 at 11:00 UTC. This is a provider result, not a hardcoded choice.
  The current calendar was also checked against the official Formula 1 calendar.
- Qualifying is not yet published. The product correctly contains no new forecast.
- Latest published race classification is Spanish GP, 13 September. Overview,
  driver, constructor and archive views label it historical.
- Real F1 timing API returned Spanish GP Race, **22 timing rows**, 14 listed
  meetings, `timing_mode=archive`, `is_genuinely_live=false`, and source packet time
  `2026-09-13T14:47:48.000Z`. The scheduled local GMT offset resolves to 13:00 UTC.
- A deliberately unmatched event request returned `ok=false`, `normalized=null`,
  `timing_mode=unavailable`; it did not substitute the latest race.
- All five product APIs (predictions, archive, model-status, backtest, source-health)
  returned HTTP 200 with successful/available contracts. The final timing SSE stream
  emitted ready and message events with the same real archived packet timestamp;
  the verification client deliberately closed its connection after four seconds.
- Invalid year and disallowed audio host return 400. Retired raw local-data endpoint
  returns 410; legacy debug/probability artifacts cannot be retrieved through it.
- FIA refresh: primary document page returned 403. The existing official archive API
  succeeded with `source_authority=official_fia_archive_api` and
  `source_status=official_secondary_live`; resolver errors and original document
  flags/URLs remain available. The UI presents saved metadata as historical evidence,
  not freshly verified PDF content. No PDF was synthesized.
- New product artifact: **330,376 bytes**, replacing the active use of the old roughly
  57 MB contract. The original files remain quarantined research/history artifacts.

## Rendered visual and interaction review

Viewed actual rendered pages at **1440×1000**, **1280×800**, and **390×844**.
Reviewed overview, rankings, methodology, drivers, constructors, archive, sources,
strategy and timing. Inspected real historical timing, current upcoming event and
unavailable qualifying. Inspected screenshots from isolated browser fixtures for
loading, API failure/retry, empty/unavailable calendar, historical DSQ, populated
ranking/provenance and live status. Fixtures are confined to tests.

Verified mobile menu, form labels, table scroll containment, full-grid/Top-10 toggle,
search, provenance disclosure, retry and route navigation. Automated assertions found
no page overflow across the covered routes; the final real mobile timing inspection
also reported no overflow. The final browser console error query was empty. Live
labels expire after source packets age out, even when the browser connection stops.
There was no active race during this audit: live state was tested with isolated
fixtures, not claimed as a real live-event endurance test.

Screenshots are reproducible with `PITWALL_CAPTURE_REVIEW=1 npm test` and stored in
ignored `frontend/test-results/`. They are test evidence, not production assets.

## PITWALL CRITIC REPORT — iteration 1

**Overall: 7.69 / 10 — FAIL** (raw weighted score 7.696; displayed by truncation).
This was the first formally scored implementation review, not a fabricated baseline
score for the untouched repository.

| Category | Score |
|---|---:|
| Data Correctness | 8.2 |
| Prediction Validity | 7.7 |
| Backend | 7.0 |
| Frontend | 7.7 |
| Product Design | 7.0 |
| F1 Accuracy | 8.0 |
| Product Credibility | 7.8 |
| Non-AI Quality | 7.7 |
| Testing | 7.8 |
| Maintainability | 7.4 |

### Critical issues

**Timing was unavailable despite a valid provider index.** Bounded byte reading kept
F1's UTF-8 BOM, unlike the former text decoder. JSON parsing then failed. This breaks
a core route. Best fix: strip only the leading BOM at the parser boundary, retain
size/time bounds, add a regression test and verify the real feed. All were completed.

### Major issues

**Timing named removed providers and retained inconsistent, decorative UI.** Old
fallback paths and an "official visual" wrapper around a generic local car SVG made
source claims and visual hierarchy misleading. Best fix: remove those unused paths
and visual, name actual sources, retain useful timing controls, align typography and
surfaces, and inspect the rendered result. Completed and re-reviewed.

**Prospective prediction validity is unmeasured.** No genuine new pre-race records
exist yet, and old captures lack trustworthy provenance. Root cause is the old
rewriting pipeline. Best fix: immutable captures and separate evaluations, with
explicitly retrospective backtests until enough new evidence exists. Infrastructure
is tested; the scientific limitation remains and caps the score.

### Minor issues

**Large legacy research files and unused styles remain.** Broad deletion would create
unnecessary regression risk. Best fix: enforce the production boundary now, remove
provably dead UI/fallback code, document remaining research ownership, then prune in
separate reviewed changes. Partial cleanup completed; debt remains explicit.

## PITWALL CRITIC REPORT — iteration 2 / final local review

**Overall: 8.16 / 10 — PASS for the validated local release candidate.**
Raw weighted score is 8.161; no rounding across a release threshold. No category is
below 7.5. This is an engineering judgment, not a measured probability of reliability
or proof that the public deployment has been updated.

| Category | Weight | Score | Evidence and practical limit |
|---|---:|---:|---|
| Data Correctness | 18% | 8.6 | Real dynamic calendar, explicit failures, expired forecast rejection; community provider revisions remain possible |
| Prediction Validity | 16% | 7.7 | Deterministic shared baseline, chronological comparison, immutable captures; zero prospective evaluations and reconstructed historical inputs |
| Backend | 10% | 8.1 | Bounded providers/cache/proxy, atomic ledger and strict contract; undocumented timing feed remains an operational dependency |
| Frontend | 10% | 8.2 | Correct states, expiry, controls and responsive routes; no static TypeScript coverage |
| Product Design | 8% | 7.8 | Actual desktop/mobile review, readable hierarchy/tables, restrained identity; timing page remains dense |
| F1 Accuracy | 10% | 8.2 | Sprint schedule fields, explicit UTC offsets, matching sessions and classification status; penalties and sprint forecasts are not modeled |
| Product Credibility | 10% | 8.6 | Unsupported probabilities/AI claims withdrawn, visible provenance and missing-data states; upstream source accuracy is not independently guaranteed |
| Non-AI Quality | 6% | 8.1 | Removed decorative visual, synthetic metrics and generic effects; useful original layout retained |
| Testing | 7% | 8.3 | 169 Python tests + 9 subtests, 15 JS tests, 27 browser checks, build/install/audit; no real live-event endurance run or hosted CI execution |
| Maintainability | 5% | 7.6 | Small active modules, reviewed pipeline boundaries and current docs; quarantined monolith, CSS and repository history still require staged cleanup |

### Critical issues

None reproduced in the validated local production paths. The original stale-race,
unsupported probabilities, mutable forecasts, target leakage, fabricated timing
freshness, dependency advisory and BOM regression are resolved or excluded from
production with explicit unavailability. The public deployment is not covered by
this pass until these changes are deployed and verified there.

### Major issues / remaining limits

1. **No prospective performance sample.** Historical caches were retrieved later and
   may contain later corrections. They cannot prove what every source published
   before each old race. Keep the reconstruction label; accumulate immutable new
   forecasts and evaluate them before making predictive performance claims.
2. **No validated strategy, sprint or weather model.** The old numbers had no
   defensible basis. These capabilities explicitly remain unavailable. Develop each
   only with suitable data, chronological validation and a declared objective.
3. **Deployment and operations still need host verification.** Local tracing/build
   passed, but remote CI, permissions, persistence and deployment have not been run.
   Follow RUNBOOK, retain ledger backups and verify real API states on the host.
4. **Undocumented timing and community results providers.** Availability and schemas
   can change. Controlled errors, bounded refresh and provenance reduce impact; they
   do not create an SLA or guarantee official sporting adjudication.

### Minor issues

Timing still has a denser layout than classification pages. Legacy Python/CSS and
large historical Git artifacts remain outside the active contract. Cleanup should
retain source evidence and legal attribution. A separate accessibility audit with
assistive technology and production load testing would improve evidence; neither
was falsely claimed here.

## Promotion result

132 paired development/test races; 39 eligible races in the reserved 2024–2025 period.
Qualifying baseline MAE **3.07193** versus candidate **3.19082**; rank correlation
**0.705668** versus **0.692764**. The candidate fails improvement and season-regression
checks. **Not promoted.** See MODEL_REPORT for exact metrics, cohort exclusions,
source revision limitations and the future reviewed promotion process.
