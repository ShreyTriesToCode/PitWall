// Convert instants for display only. Provider timestamps and race selection stay in UTC.
export const DISPLAY_TIME_ZONE = "Asia/Kolkata";
const dateTime = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h12",
  timeZone: DISPLAY_TIME_ZONE,
});
const clockTime = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h12",
  timeZone: DISPLAY_TIME_ZONE,
});

function formatInstant(value, formatter) {
  if (typeof value !== "string" || !/(Z|[+-]\d{2}:\d{2})$/.test(value))
    return "Time unavailable";
  const instant = new Date(value);
  if (!Number.isFinite(instant.getTime())) return "Time unavailable";
  // Assemble punctuation ourselves: Safari's locale data uses "at" while
  // Chromium uses a comma, which otherwise changes layout across browsers.
  const parts = Object.fromEntries(
    formatter.formatToParts(instant).map(({ type, value }) => [type, value]),
  );
  const clock = `${parts.hour}:${parts.minute}`;
  const period = parts.dayPeriod.toUpperCase();
  return parts.year
    ? `${parts.day} ${parts.month} ${parts.year}, ${clock} ${period} IST`
    : `${clock}:${parts.second} ${period} IST`;
}

export const formatISTDateTime = (value) => formatInstant(value, dateTime);
export const formatISTTime = (value) => formatInstant(value, clockTime);
