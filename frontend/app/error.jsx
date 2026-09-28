"use client";
import { AppShell, InlineNotice } from "./components/PitWallComponents";
export default function ErrorPage({ reset }) {
  return (
    <AppShell>
      <h1>Page unavailable</h1>
      <InlineNotice
        title="Unable to display this page"
        body="Try loading the page again. Your saved forecasts are unaffected."
        tone="error"
        action={
          <button className="control-btn" onClick={reset}>
            Try again
          </button>
        }
      />
    </AppShell>
  );
}
