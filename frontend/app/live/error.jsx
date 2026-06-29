"use client";

import { AppShell, InlineNotice, PageHeader } from "../components/PitWallComponents";

export default function LiveError({ error, reset }) {
  return (
    <AppShell active="/live">
      <PageHeader
        eyebrow="Timing Replay"
        title="Timing replay unavailable"
        description="PitWall could not render the timing replay from the current session contract."
      />
      <InlineNotice
        title="Timing route failed"
        body={error?.message || "Archived timing data or fallback session data may be malformed or temporarily unavailable."}
        tone="error"
        action={<button className="control-btn" onClick={reset} type="button">Retry</button>}
      />
    </AppShell>
  );
}
