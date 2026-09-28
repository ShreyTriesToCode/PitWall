// Scheduled time alone cannot establish a start or completion (delays/cancellations).
export function sessionStatus(session, event, data, timing, now = Date.now()) {
  const start = Date.parse(session.start_at || "");
  if (!Number.isFinite(start))
    return { label: "Time unavailable", tone: "neutral" };
  const observed = timing?.normalized?.session;
  const matching =
    Date.parse(observed?.date_start || "") === start &&
    (observed?.session_name || observed?.session_type || "").toLowerCase() ===
      session.name.toLowerCase();
  if (matching && timing?.ok) {
    const packet = Date.parse(
      timing.source_packet_at || timing.timing_last_updated_at || "",
    );
    if (timing.is_genuinely_live && packet <= now && now - packet <= 60_000)
      return { label: "Ongoing", tone: "green" };
    if (timing.completion_verified === true)
      return { label: "Completed", tone: "red" };
  }
  const result =
    session.name === "Race" && data.latest_result?.event?.id === event.id;
  const qualifying =
    session.name === "Qualifying" &&
    data.predictions?.some((p) => p.race_id === event.id);
  if (start <= now && (result || qualifying))
    return { label: "Completed", tone: "red" };
  return start > now
    ? { label: "Upcoming", tone: "amber" }
    : { label: "Status unconfirmed", tone: "neutral" };
}
