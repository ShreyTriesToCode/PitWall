# Frontend

Next.js dashboard for F1 Race Intel.

## Pages

```text
/      Prediction dashboard
/live  Live details dashboard
```

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
NEXT_PUBLIC_F1_DATA_BASE_URL=https://raw.githubusercontent.com/ShreyTriesToCode/f1-race-intel/main
```

Do not commit:

```text
node_modules/
.next/
.vercel/
```
