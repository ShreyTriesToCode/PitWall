export function sessionDate(value, offset) {
  if (!value || typeof value !== "string") return null;
  let stamp = value;
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(stamp)) {
    if (!offset || !/^[+-]?\d{2}:\d{2}(?::\d{2})?$/.test(offset)) return null;
    const zone =
      offset.slice(0, 1) === "-" || offset.slice(0, 1) === "+"
        ? offset
        : `+${offset}`;
    stamp += zone.slice(0, 6);
  }
  const result = new Date(stamp);
  return Number.isFinite(result.getTime()) ? result : null;
}

export function packetTimestamp(feeds) {
  const values = [];
  function visit(value, depth = 0) {
    if (!value || typeof value !== "object" || depth > 5) return;
    for (const [key, item] of Object.entries(value)) {
      // Only explicit provider UTC fields establish packet freshness. Relative
      // stream offsets or a scheduled start cannot be converted into evidence.
      if ((key === "Utc" || key === "utc") && typeof item === "string") {
        const date = sessionDate(item, "+00:00");
        if (date) values.push(date.getTime());
      } else if (typeof item === "object") visit(item, depth + 1);
    }
  }
  for (const feed of Object.values(feeds || {})) {
    visit(feed.json);
    for (const entry of (feed.entries || []).slice(-5)) visit(entry.data);
  }
  return values.length ? new Date(Math.max(...values)).toISOString() : null;
}

export function freshness(
  lifecycle,
  hasData,
  source,
  packetAt,
  now = Date.now(),
  enabled = true,
) {
  const stamp = packetAt ? Date.parse(packetAt) : NaN;
  const age =
    Number.isFinite(stamp) && stamp <= now ? (now - stamp) / 1000 : null;
  const live =
    enabled &&
    hasData &&
    lifecycle.state === "active" &&
    age !== null &&
    age <= 60;
  const mode = live
    ? "live"
    : hasData && lifecycle.state === "archive"
      ? "archive"
      : hasData
        ? "stale"
        : "unavailable";
  return {
    live_timing_status: mode,
    timing_mode: mode,
    timing_source: source,
    timing_last_updated_at:
      Number.isFinite(stamp) && stamp <= now
        ? new Date(stamp).toISOString()
        : null,
    timing_freshness_seconds: age === null ? null : Math.round(age),
    is_genuinely_live: live,
    live_fallback_reason: live
      ? ""
      : mode === "archive"
        ? "Historical session data; retrieval time is not a live packet timestamp."
        : "Fresh source packet time could not be verified for an active session.",
  };
}

// A disconnected client must expire a LIVE label without receiving another packet.
export function expireLivePayload(payload, now = Date.now()) {
  if (!payload?.is_genuinely_live) return payload;
  const stamp = Date.parse(
    payload.source_packet_at || payload.timing_last_updated_at || "",
  );
  if (Number.isFinite(stamp) && stamp <= now && now - stamp <= 60_000)
    return payload;
  return {
    ...payload,
    is_genuinely_live: false,
    timing_mode: "stale",
    live_timing_status: "stale",
    live_fallback_reason: "The last verified source packet is no longer fresh.",
  };
}

export function parseTimingJson(text, fallback = null) {
  try {
    return JSON.parse(String(text).replace(/^\uFEFF/, ""));
  } catch {
    return fallback;
  }
}

// Status codes documented by FastF1's track_status_data parser. Unknown codes
// remain explicit; neither clock time nor missing messages establishes a clear track.
export function trackStateLabel(code) {
  return (
    {
      1: "Track clear",
      2: "Yellow flag",
      4: "Safety car",
      5: "Red flag",
      6: "Virtual safety car",
      7: "Virtual safety car ending",
    }[String(code)] ||
    (code ? `Unknown status (${code})` : "Status unavailable")
  );
}

export function messageTimestamp(item) {
  // The feed names this field Utc, including when it omits an explicit Z.
  const utc = item?.Utc ?? item?.utc;
  const date = utc
    ? sessionDate(utc, "+00:00")
    : sessionDate(item?.Date ?? item?.date);
  return date ? date.toISOString() : null;
}

// F1 sends sparse dictionaries keyed by array index. Converting them with
// Object.values shifts a patch for stint/sector 2 onto index 0 and loses evidence.
export function mergeTimingLine(previous = {}, update = {}) {
  const merged = { ...previous, ...update };
  for (const key of [
    "Sectors",
    "sectors",
    "Segments",
    "segments",
    "Speeds",
    "speeds",
    "Stints",
    "stints",
  ]) {
    if (previous?.[key] || update?.[key]) {
      const before = previous?.[key] || {};
      const patch = update?.[key] || {};
      const collection = { ...before };
      for (const [index, value] of Object.entries(patch)) {
        collection[index] =
          value &&
          typeof value === "object" &&
          before[index] &&
          typeof before[index] === "object"
            ? mergeTimingLine(before[index], value)
            : value;
      }
      merged[key] = collection;
    }
  }
  return merged;
}

export function applySessionStatus(lifecycle, status) {
  const completionVerified = ["Finalised", "Ends"].includes(status);
  if (completionVerified)
    return {
      ...lifecycle,
      state: "archive",
      is_live: false,
      completion_verified: true,
    };
  if (lifecycle.state === "active" && status !== "Started")
    return {
      ...lifecycle,
      state: "status_unconfirmed",
      is_live: false,
      completion_verified: false,
    };
  return { ...lifecycle, completion_verified: false };
}
