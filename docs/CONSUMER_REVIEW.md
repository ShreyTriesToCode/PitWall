# Final consumer review — September 25, 2026

## Scope and verdict

Reviewed the local production build as a fan seeking the next race, session times,
results, rankings and a reason to trust those rankings. This is not an independent
user study or a fresh scientific/backend audit. Backend and model judgments retain
the evidence and limits from CRITIC_9_REVIEW.md; the actual methodology page still
shows zero prospective captures and zero evaluations.

**Consumer verdict:** recognizably a motorsport product, with deliberate racing
 typography, useful data tables and restrained visual effects. The replacement
artwork is more editorial and less like a generic showroom render. This is a
judgment about design, not a claim of human authorship: the artwork was generated
with OpenAI's image tool, and provenance is retained in MOTORSPORT_ARTWORK.md.

The interface is visually strong, but unavailable strategy functionality, dense
phone timing and technical copy prevent an honest “impeccable” verdict.

## Changes requested during review

- Replaced the garage render with `frontend/public/pitwall-racing-hero.png`: a
  warm overhead racing composition with charcoal negative space and vermilion/ivory
  kerbs. Removed the visible illustration caption as requested. The image remains
  decorative, with no claim that it depicts the selected Grand Prix.
- Converted all formatted instants to IST (Asia/Kolkata, UTC+05:30): schedules,
  results, provenance, history, session headers, refresh times, race-control and
  radio timestamps. A shared formatter rejects missing/invalid/timezone-naive input.
- UTC source timestamps, event selection and lap durations remain unchanged.
  Official message body text is preserved verbatim; any clock references embedded
  in that source text are not guessed or rewritten.
- Safari/Chromium use different locale punctuation. The first new regression run
  exposed this; formatToParts now provides consistent date/clock separators.

## Actual consumer checks

- Viewed actual overview, driver results, strategy, history, methodology and timing.
- Inspected the new overview on a 390×844 phone and a rendered 1440×1000 desktop
  test screenshot; inspected history/methodology at 1280×800.
- Driver search for Ferrari returned the two supplied classification rows, retaining
  their actual positions rather than renumbering the filtered result.
- Mobile menu and timing navigation worked. Actual timing displayed Azerbaijan
  Practice 2 as historical, with a 17:30 IST start and IST race-control timestamps.
- Phone overview document width matched its 390 px viewport.
- An older retained tab showed an unloaded image. The optimizer returned HTTP 200;
  a fresh tab decoded and displayed the artwork, and the final four-profile image
  checks passed. The retained-tab cause was not proven, so it is not described as
  a diagnosed application fix.
- The unusual “Bahrain Grand Prix in Malaysia” label was verified against the
  [official Formula 1 race page](https://www.formula1.com/en/racing/2026/bahrain).
  It was not replaced based on an outdated assumption.

## PITWALL CRITIC REPORT

**Overall: 8.67 / 10.** Raw weighted score 8.678, truncated. Same weights as the
previous whole-product review. The 9-in-every-category target is **not met**.
Scores are reviewer judgments, not measured quality statistics.

| Category | Weight | Score | Reason / limit |
|---|---:|---:|---|
| Data Correctness | 18% | 9.0 | Honest states and provider-backed event selection; IST conversion preserves instants; not an independent audit of every upstream record |
| Prediction Validity | 16% | 7.8 | Documented deterministic baseline and chronological reconstruction; still no prospective performance record |
| Backend | 10% | 8.8 | Prior validated contracts and bounded errors; hosted persistence/load/live endurance unverified |
| Frontend | 10% | 9.0 | 88 passing browser checks, shared timezone formatting, useful controls; some dense interactions remain |
| Product Design | 8% | 8.9 | Strong visual identity; primary Strategy navigation still leads chiefly to an unavailable-state explanation |
| F1 Accuracy | 10% | 8.6 | Sessions and historical status are explicit; some raw feed fields remain difficult for a fan to interpret |
| Product Credibility | 10% | 8.8 | No unearned confidence claim; old generic Published footer alongside newer retrieved dates creates freshness ambiguity |
| Non-AI / Non-vibe-coded Quality | 6% | 9.0 | Purposeful typography, artwork and data hierarchy; some engineering-oriented wording still reads like internal documentation |
| Testing & Reliability | 7% | 8.9 | Fresh 88 browser + 23 unit passes; physical-device and deployed endurance measurements missing |
| Maintainability | 5% | 8.3 | Centralized display formatter and documented asset provenance; previously identified legacy research debt persists |

### Separate visual assessment

| Area | Score |
|---|---:|
| Motorsport identity | 9.3 |
| Visual composition | 9.2 |
| Motion and interaction feel | 8.8 |

**Visual mean: 9.10 / 10.** Finite motion and reduced-motion behavior are tested;
physical-device frame pacing has not been measured. This supersedes the previous
hero's visual verdict without rewriting that historical review.

### Critical issues

No release-blocking defect reproduced in this local consumer pass. Public deployment
and genuine live-session endurance remain unverified. This is not a release sign-off
for the hosted site or a claim that the entire product has been re-audited.

### Major issues: consequence, root cause, best fix

1. **Strategy is a prominent dead end.** A fan expects strategy information from
   primary navigation but mostly receives an unavailable explanation. The numerical
   model was correctly withdrawn because it lacks validation. Best fix: offer a
   genuinely useful observed-stint view with clear limits, or explicitly position
   the page as methodology until validated forecasting exists. Do not invent a model.
2. **Prediction usefulness is not established prospectively.** A fan cannot judge
   genuine future accuracy from the current zero captured/evaluated records. Legacy
   records lack pre-race provenance. Collect immutable forecasts and official
   evaluations before raising the model score or making effectiveness claims.
3. **Phone timing demands substantial scrolling.** Complete timing columns exceed
   phone width, and many full-field sections follow. Containment prevents page
   breakage but not interaction cost. Validate a driver-focused or compact-column
   view with actual fan tasks while retaining access to every supplied observation.
4. **Freshness wording needs more precision.** A generic Published September 17
   footer sits beside newer September 25 retrieval timestamps. These refer to
   different artifacts but can look contradictory. Label the footer “Analysis
   snapshot” and expose per-source retrieval information where consumers use it;
   never replace the old timestamp with the current clock.

### Minor issues: consequence, root cause, best fix

- Phrases such as “traceable race rankings” and “reproducible forecast with explicit
  limits” sound like engineering review copy. Use plain descriptions of what fans
  can find; retain technical provenance in methodology/disclosures.
- Timing repeats historical/source labels and exposes raw values such as Brake 104
  without explaining the feed encoding. Retained observations are not automatically
  intelligible. Verify provider semantics before decoding; label raw channels
  explicitly or move them under advanced feed details.
- The overview's mobile art adds vertical length. The ranking page already uses a
  compact header; measure whether frequent overview users need a denser preference.
- Manual screen-reader testing and low-end-device/hosted performance measurements
  are still needed. Automated accessibility checks do not replace those activities.

## Executed validation

- Production build and local launch passed with Node 24.21.0.
- Initial IST/artwork run: 87 passed, one Safari date-punctuation assertion failed.
- After the formatter correction: **88 passed in 24.6 seconds** across Chromium
  desktop/laptop/phone and WebKit phone. Includes 320 px, axe, keyboard, reduced
  motion, image decoding, failure/loading states and isolated timing fixtures.
- **23 Node unit tests passed**, including four new timezone tests, with TZ=UTC.
- ESLint and Prettier passed. Ruff passed for `f1_briefing.py pitwall scripts tests`.
- Python/backend behavior was not changed or re-tested in this pass. Earlier
  scientific/back-end results are explicitly historical evidence, not new runs.
- No commit, push or deployment performed.
