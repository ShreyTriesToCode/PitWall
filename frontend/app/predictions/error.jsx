"use client";

import { AppShell, InlineNotice, PageHeader } from "../components/PitWallComponents";

export default function PredictionsError({ error, reset }) {
  return (
    <AppShell active="/predictions">
      <PageHeader
        eyebrow="Prediction Intelligence"
        title="Predictions unavailable"
        description="PitWall could not render the prediction board from the current contract."
      />
      <InlineNotice
        title="Prediction route failed"
        body={error?.message || "The generated prediction contract may be malformed or temporarily unavailable."}
        tone="error"
        action={<button className="control-btn" onClick={reset} type="button">Retry</button>}
      />
    </AppShell>
  );
}
