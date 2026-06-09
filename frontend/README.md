# Frontend

[Documentation index](../docs/README.md)

Next.js dashboard for PitWall.

## Pages

```text
/             Race Control overview
/predictions  Prediction intelligence
/drivers      Driver analysis
/teams        Constructor intelligence
/strategy     Strategy Lab
/live         Timing replay/live-status dashboard
/model        Model Center
/archive      Race archive
```

The UI uses a shared Race Control shell, desktop sidebar, fixed viewport bottom navigation on mobile, animated ticker, loading states, bottom-sheet details on mobile, and generated backend contracts from `data_cache/frontend-contract.json`.

## Timing data policy

The timing page can use Formula 1 timing/static feeds, OpenF1 fallback data, and Jolpica latest completed event fallback. It never calls archived/static data live.

The API exposes:

```text
live_timing_status
timing_mode
timing_source
timing_last_updated_at
timing_freshness_seconds
is_genuinely_live
live_fallback_reason
```

The page auto-selects the currently active or latest available event/session. It shows `Live` only when fresh timing packets are available during an active session; otherwise it shows delayed, stale, archive, or unavailable.

## Vercel settings

```text
Root Directory: frontend
Framework Preset: Next.js
Build Command: npm run build
Install Command: npm install
Output Directory: leave empty
```

Environment variable:

```text
NEXT_PUBLIC_F1_DATA_BASE_URL=https://raw.githubusercontent.com/ShreyTriesToCode/PitWall/main
```

Do not commit:

```text
node_modules/
.next/
.vercel/
```

GitHub repository target:

```text
https://github.com/ShreyTriesToCode/PitWall
```
