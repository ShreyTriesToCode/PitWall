// Current forecasts expire at the start; immutable captures remain readable.
export function capturedRanking(data, now = Date.now()) {
  const current = data.current;
  if (current?.state !== "UPDATING" || !current.event) return null;
  const instant = (value) =>
    typeof value === "string" && /(Z|[+-]\d{2}:\d{2})$/.test(value)
      ? Date.parse(value)
      : NaN;
  const start = instant(current.event.start_at);
  if (!(start <= now)) return null;
  return (
    (data.predictions || [])
      .filter(
        (p) =>
          p.race_id === current.event.id &&
          p.event?.id === current.event.id &&
          instant(p.event.start_at) === start &&
          instant(p.data_cutoff) <= instant(p.generated_at) &&
          instant(p.generated_at) < start,
      )
      .sort((a, b) => instant(b.generated_at) - instant(a.generated_at))[0] ||
    null
  );
}
