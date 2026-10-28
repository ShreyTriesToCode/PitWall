export function selectExperimental(records, current, now = Date.now()) {
  if (!current.event || !["UPCOMING", "UPDATING"].includes(current.state))
    return null;
  return (
    [...records]
      .filter(
        (p) =>
          p.race_id === current.event.id &&
          Date.parse(p.event.start_at) === Date.parse(current.event.start_at) &&
          Date.parse(p.generated_at) <= now,
      )
      .sort(
        (a, b) => Date.parse(b.generated_at) - Date.parse(a.generated_at),
      )[0] || null
  );
}
