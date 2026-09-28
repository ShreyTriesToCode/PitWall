# PitWall frontend

Next.js App Router, React, JavaScript and vanilla CSS. Use Node 24 LTS. Run commands in this directory.

```sh
npm ci
npm run dev
npm run build
npm run lint
npm run test:unit
npm run format:check
npx playwright install chromium webkit
npm test
```

The small version 3 `../data_cache/product.json` contains only validated current
rankings, explicit legacy history and measured evaluation evidence. The server
refreshes the calendar and results independently. It never recovers current data
from old debug or previous contracts. See [the root README](../README.md),
[operations](../RUNBOOK.md) and [methodology](../MODEL_REPORT.md).

Production must run as a Node server; static export cannot provide current race
selection, timing or data API routes. Deployment tracing includes the root product
file; an optional trusted HTTPS data directory can be configured explicitly.
There is no TypeScript configuration. Next's build checks JavaScript/JSX compilation;
Node unit tests and Playwright cover contracts and behavior. ESLint checks JavaScript and React hook rules; Prettier checks style.

Synthetic data lives only in browser/unit test files and is installed via test
request interception. The application has no production fixture mode.

## Interface validation

Playwright builds and launches the production app if port 3000 is free. Stop an old
local server first to avoid testing an outdated build. Four projects cover desktop,
laptop, mobile Chromium and mobile WebKit, all in Asia/Kolkata timezone. Additional
checks cover 320 px layout, axe rules, keyboard controls and reduced motion.

Run `PITWALL_CAPTURE_REVIEW=1 npm test` to retain review screenshots in the ignored
`test-results` directory. These are test evidence, not application assets. Self-hosted
Inter and Barlow Condensed keep fonts independent of external browser requests. Shared styles live in
`app/globals.css`; session timing styles live in `app/styles/timing.css`. The Formula 1
identity is defined in `app/styles/motorsport.css`, imported last. Decorative racing
motifs carry no telemetry meaning; the round plate uses the validated event and is
hidden on phones. The responsive hero uses decorative overhead motorsport artwork;
[artwork provenance and prompt](../docs/MOTORSPORT_ARTWORK.md) document its origin. The visible artwork caption was removed at the user’s request.
Next Image optimizes the source asset. Content and shell links disable speculative
prefetching after a reproduced WebKit cancellation error. See
[the theme critic](../docs/THEME_REVIEW.md).

See [the frontend critic](../UI_AUDIT.md) and [current full review](../docs/CRITIC_9_REVIEW.md)
for actual results and outstanding evidence requirements.

## Display timezone

All displayed instants use India Standard Time (`Asia/Kolkata`, UTC+05:30), with an
explicit IST suffix. `app/lib/time.js` owns date and clock formatting across the
overview, calendar, provenance and timing views. Source/API timestamps, HTML
`datetime` attributes, freshness calculations and race selection remain UTC. Lap
times and other durations are not timezone-converted. Missing or timezone-naive
timestamps display “Time unavailable”. Unit tests cover midnight/year rollover
and explicit source offsets; browser tests verify both schedule and message times.

## Session context and mobile timing

Times use 12-hour IST with explicit AM/PM. Scheduled UTC instants and lap
durations are unchanged. Yellow means upcoming, green requires a matching
active feed with a recent packet, and red completion needs a finalised session
or classification evidence. Clock passage alone remains unconfirmed.

`components/SessionTiming.jsx` owns selection, loading, source errors and feed
expiry for both `/live` and `/strategy`. Strategy compares reported compounds,
ages and last laps; it does not recommend pit windows. Phone timing initially
shows position, driver and interval, with all detail available via the toggle.

The footer distinguishes the saved analysis snapshot from current calendar/results
retrieval. Neither timestamp establishes live session activity.
