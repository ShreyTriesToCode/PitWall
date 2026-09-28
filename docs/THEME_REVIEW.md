> **Latest review:** The user requested a different hero and IST display. See [the September 25 consumer review](CONSUMER_REVIEW.md) for the current artwork, scores and validation. Earlier iterations below are retained as history.

# PitWall theme, motion and visual critic

Validation run: **2026-09-22**. Final visual follow-up: **2026-09-24**. This is a scoped visual review of the local production
build, following the user's feedback that the earlier cleanup removed the original
Formula 1 identity. It does not replace the scientific or operational assessment in
[the whole-product critic](CRITIC_9_REVIEW.md).

## Reference and diagnosis

The [original PitWall site](https://pitwall.shreybuilds.com/) was opened and visually
inspected during this pass. Its recognizable elements were the italic wordmark,
bold uppercase racing headlines, red rules, compact control panels and dark surfaces.
The previous local version retained dark colors but lost too much of that character.
That was an overcorrection: removing unsupported numbers did not require removing
motorsport art direction.

The original's stale Italian GP selection and confidence figures were not used as
current data. Existing validated event selection and honest unavailable states remain
in place. All displayed round/season values come from the supplied event.

## Implementation

- Self-hosted Barlow Condensed, including a true 800 italic face, restores the
  racing wordmark and display headings. Inter remains the reading/table typeface.
  Font licensing is retained with the installed package.
- A compact Formula 1 race-centre masthead includes a decorative chequered motif.
  It is not a live-status indicator or an official affiliation claim.
- Red panel rules, pit-lane stripe details, navigation corner marks and numerical
  row styling establish a consistent identity across routes.
- The race hero has a round plate derived from the provider event. It is hidden
  from assistive technology because the same round is already readable above the
  heading. No circuit map, telemetry chart or car-performance graphic is invented.
- On phones, the redundant round plate is hidden to bring the actual data higher.
  The current round remains visible in the event text. Missing events use the full
  width with no phantom plate.
- Motion is limited to a 280 ms red-rule reveal, 240 ms surface entrance, 180 ms
  mobile-menu entrance, 160 ms control/link feedback and existing disclosures.
  Motion is finite except the existing request-in-progress indicator. All decorative
  motion respects reduced-motion settings; text does not fade through poor contrast.
- Shell links no longer speculatively prefetch every route. A WebKit navigation
  trace showed a cancelled RSC prefetch and an access-control page error during
  rapid route changes. Removing this unnecessary shell prefetch mitigates that
  path; the final complete suite passes without ignoring page errors.

## Critic loop

### Initial visual findings

1. **Theme identity was too generic.** Plain Inter headings and uniform neutral
   panels made the product resemble a general data dashboard. Consequence: it no
   longer matched the user's Formula 1 product. Root cause: the earlier cleanup
   treated too much branding as decoration. Fix: restore race typography and a
   coherent motorsport system while keeping readable analytical content.
2. **The first mobile round plate pushed data down.** The large desktop motif was
   repeated below already visible round text. Consequence: lower useful information
   density on phones. Fix: retain it on larger screens, hide it below 600 px, and
   visually inspect the resulting phone layout. Verified.
3. **One WebKit navigation run failed.** Initial suite: 83 passed, one page-error
   assertion failed. Three focused repetitions passed, indicating an intermittent
   cancellation path. The trace identified prefetch cancellation, and the shell
   prefetch refinement above was made. No test was disabled or error filtered out.

### Final critic score

**Overall: 9.06 / 10** — equal-weight mean 9.0666…, truncated.
These are bounded design judgments about the inspected local build, not measured
performance statistics or a guarantee of perfection.

| Category | Score | Reason |
|---|---:|---|
| Formula 1 theme | 9.2 | Racing typography, red rules, chequered details, event-derived round plate and consistent navigation restore recognizable motorsport character |
| Visual aesthetic | 9.0 | Clear hierarchy, restrained surfaces, readable data typography and a compact phone treatment; wide timing tables remain an intentional density tradeoff |
| Animations and interaction feel | 9.0 | Short, purposeful entrances and control feedback, no blocking splash screen, no fake live effects, finite animation and reduced-motion coverage |

### Critical issues

None reproduced in the final theme/layout/motion checks. This verdict is confined
to the tested local views and states; it is not a claim that every device is covered.

### Major issues

No unresolved theme-specific blocker was found. Existing whole-product limitations
(prospective prediction evidence, hosted performance and live endurance) still apply.

### Minor issues and limits

- Dense timing tables still require contained horizontal scrolling on small phones.
  For detailed timing this preserves readable type and the complete supplied field.
  A task-based user study is the best basis for any later compact-column mode.
- Local screenshots and bounded-motion tests do not establish frame consistency on
  every low-end device. Measure the hosted build before making a field-performance
  claim. Physical-device and manual screen-reader review remain outside this pass.
- Small uppercase labels are reserved for secondary context; primary headings,
  controls and race data retain larger type. Future theme changes should preserve
  that hierarchy rather than applying the condensed face to all content.

## Executed validation

Final September 22 run:

- Production build and local startup: passed, using Node 24.21.0.
- **88 browser checks passed in 28.6 s**: 22 checks across desktop 1440×1000,
  laptop 1280×800, mobile Chromium and mobile WebKit 390×844.
- Includes 320 px containment, axe accessibility checks, keyboard/focus, failures,
  loading, empty states, test-only live/historical states, finite decorative motion
  and reduced motion. Synthetic scenarios remain isolated in tests.
- **19 Node unit tests passed**.
- ESLint, Prettier, `git diff --check` and Ruff against
  `f1_briefing.py pitwall scripts tests`: passed.
- Inspected actual desktop and phone overview renders, mobile menu/focus, laptop
  timing, and rendered test screenshots for methodology, sources, drivers and timing.
- Actual desktop browser error-log query: empty. Phone document width was 390 px
  for a 390 px viewport after opening the navigation menu.

The interrupted laptop timing inspection was completed on September 24 at
1280×800: the real archived session rendered with the new theme, readable timing
rows and an empty browser error-log query. Ruff and diff checks passed again.
No code changed after the passing September 22 browser suite.

Screenshots are reproducible with `PITWALL_CAPTURE_REVIEW=1 npm test` and remain in
ignored `frontend/test-results/`. The test screenshot with an “Isolated test session”
is a fixture, not a real event. No deployment or publication was performed.

## Files

- `frontend/app/styles/motorsport.css`: shared theme and responsive motion rules.
- `frontend/app/layout.jsx`, package files: licensed self-hosted display font.
- `frontend/app/components/PitWallComponents.jsx`: masthead, navigation details
  and controlled shell prefetch behavior.
- `frontend/app/components/ProductViews.jsx`: event-derived visual round plate.
- `frontend/tests/accessibility.spec.js`: decorative/data separation and finite,
  reduced-motion behavior.

## Commercial visual pass — September 25, 2026

The user's next review asked for a stronger, more commercial motorsport aesthetic.
The earlier typography pass was recognizable but its large empty hero still lacked
a distinctive visual focus. This pass adds a fictional graphite-and-red race car
in a garage, with clear separation between artwork and provider-backed event data.
See [artwork provenance and the exact generation prompt](MOTORSPORT_ARTWORK.md).

### Changes and critique

- The wide hero now pairs the actual event with a strong automotive composition.
  A dark overlay maintains text contrast; a compact round marker replaces the
  previous oversized boxed plate. Red primary and dark secondary actions have
  distinct hierarchy, hover feedback and 44 px minimum height.
- On phones, the artwork sits below the event information instead of behind the
  text. This adds roughly 210 px of brand imagery before the analytical sections;
  it is a deliberate commercial-presentation tradeoff, not improved data density.
- A final phone review found the full hero duplicated on the ranking page, with a
  redundant self-link. The ranking view now uses a compact event header and only
  the timing action; the overview retains the larger commercial artwork.
- The artwork is static, optimized through Next Image and visibly labeled as a
  concept illustration. Existing finite motion and reduced-motion rules remain.
- The first regression run passed 87/88 checks. WebKit reported a sources-route
  access-control error during rapid navigation. The trace showed speculative RSC
  prefetches still originating from content/footer links. Content links now use
  the same `prefetch={false}` policy as the shell; normal client navigation remains.
  The full rerun passed 88/88, followed by three passing focused repetitions.
  After the compact-header refinement, another full run passed 88/88.
  No page-error assertions were removed or filtered.

### Scoped visual critic

**Overall: 9.16 / 10** (equal-weight mean 9.1666…, truncated).

| Category | Score | Basis |
|---|---:|---|
| Formula 1 theme | 9.4 | Strong automotive imagery, racing typography and red/graphite composition; actual event remains the focal content |
| Visual aesthetic | 9.2 | Cohesive desktop/laptop hero, clear action hierarchy and separately composed phone image area |
| Animations and interaction feel | 8.9 | Purposeful, finite feedback and reduced-motion support; this pass improves hierarchy rather than adding elaborate choreography, and physical-device smoothness is unmeasured |

**Critical issues:** none reproduced in this scoped pass.

**Major issues:** none remaining in the tested theme paths. This score does not
upgrade the whole-product scientific/operational score, nor satisfy the earlier
request for every category to exceed 9. The evidence does not justify that claim.

**Minor issues / why they matter / best next step:**

- Phone artwork length delays the data sections. Observe actual user navigation
  before adding a compact overview preference; avoid another permanent control
  without evidence it helps.
- The small concept caption is secondary provenance rather than a reading target.
  It is present in text and documented; consider a fuller artwork credit page if
  future assets need licensing or additional attribution.
- No physical-device, low-end GPU or hosted Core Web Vitals measurements were
  collected. Those are the basis for stronger motion/performance claims, not more
  local screenshot iterations.

### Executed validation

- Fresh production build and local startup succeeded with Node 24.21.0.
- Final full browser run after the compact-header refinement: **88 passed in 26.1 s**, across desktop, laptop,
  Chromium phone and WebKit phone. Includes 320 px containment, axe, keyboard,
  failure/loading/unavailable/historical/test-only live states and reduced motion.
- Focused WebKit navigation follow-up: **3 passed in 3.1 s**.
- **19 Node unit tests passed**. ESLint, Prettier, full-scope Ruff and diff checks
  passed. Python behavior was not modified or re-tested in this visual pass.
- Manually inspected the rendered overview at 1440×1000, 1280×800 and 390×844.
  Laptop document width matched the viewport (1280 px); browser error log was empty.
- Verified the hero image decoded successfully and the primary ranking link works.
  The existing theme test now checks image decoding, decorative accessibility
  semantics and the visible concept label.

No deployment, commit or publication was performed.

## Continuous background follow-up

At the user’s request, the artwork now spans the overview/ranking title and event
copy inside a shared `race-intro` wrapper. The bordered hero card, corner decoration
and separate lower mobile image area were removed. Responsive dark overlays keep
text legible; a bottom fade joins the normal page background. The existing asset
was sufficient, so no additional artwork or download was introduced. IST remains
unchanged.

Validation: fresh production build, **88 browser checks passed in 40.6 s**, ESLint,
Prettier, full-scope Ruff and diff checks passed. Inspected rendered desktop and
phone screenshots for the continuous composition and text readability. No score
change is claimed from this presentation-only adjustment.
