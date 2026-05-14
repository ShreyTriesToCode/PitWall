# Frontend

Next.js dashboard for PitWall.

## Pages

```text
/             Race Control overview
/predictions  Prediction intelligence
/drivers      Driver analysis
/teams        Constructor intelligence
/strategy     Strategy Lab
/live         Live timing
/model        Model Center
/archive      Race archive
```

The UI uses a shared Race Control shell, desktop sidebar, fixed viewport bottom navigation on mobile, animated ticker, loading states, bottom-sheet details on mobile, and generated backend contracts from `data_cache/frontend-contract.json`.

## Live data policy

The live page does not use OpenF1.

It uses:

```text
Formula 1 livetiming static feeds
Jolpica latest completed event fallback
```

The page no longer asks for a manual session key. It auto-selects the currently active or latest available event/session.

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
