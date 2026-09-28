import {
  sessionDate,
  mergeTimingLine,
  applySessionStatus,
  messageTimestamp,
  packetTimestamp,
  freshness,
  parseTimingJson as safeJson,
} from "../_lib/timing";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { inflateRawSync } from "node:zlib";

const F1_BASE = "https://livetiming.formula1.com/static";
const RATE_LIMIT_MS = Math.max(
  1000,
  Number(process.env.F1_TIMING_RATE_LIMIT_MS || 5000),
);
const TIMING_AUTO_SELECT_ENABLED =
  String(process.env.PITWALL_TIMING_AUTO_SELECT || "true").toLowerCase() !==
  "false";
const RATE_LIMIT_BUCKET = globalThis.__pitwallF1TimingRateLimit || new Map();
globalThis.__pitwallF1TimingRateLimit = RATE_LIMIT_BUCKET;
const TIMING_RESPONSE_CACHE =
  globalThis.__pitwallF1TimingResponseCache || new Map();
globalThis.__pitwallF1TimingResponseCache = TIMING_RESPONSE_CACHE;

const FEEDS = [
  "SessionInfo.json",
  "SessionInfo.jsonStream",
  "DriverList.json",
  "DriverList.jsonStream",
  "TimingData.json",
  "TimingData.jsonStream",
  "TimingAppData.json",
  "TimingAppData.jsonStream",
  "LapCount.json",
  "LapCount.jsonStream",
  "TrackStatus.json",
  "TrackStatus.jsonStream",
  "SessionStatus.json",
  "SessionStatus.jsonStream",
  "WeatherData.json",
  "WeatherData.jsonStream",
  "RaceControlMessages.json",
  "RaceControlMessages.jsonStream",
  "PitLaneTimeCollection.json",
  "PitLaneTimeCollection.jsonStream",
  "TeamRadio.json",
  "TeamRadio.jsonStream",
  "CarData.z.json",
  "CarData.z.jsonStream",
  "Position.z.json",
  "Position.z.jsonStream",
];

const FAST_FEEDS = [
  "SessionStatus.json",
  "SessionStatus.jsonStream",
  "SessionInfo.json",
  "DriverList.json",
  "DriverList.jsonStream",
  "TimingData.json",
  "TimingData.jsonStream",
  "TimingAppData.json",
  "LapCount.json",
  "TrackStatus.json",
  "WeatherData.json",
  "RaceControlMessages.json",
  "CarData.z.json",
];

function endpoint(path) {
  return `${F1_BASE}/${String(path || "").replace(/^\/+/, "")}`;
}

function jsonNoStore(payload, init = {}) {
  return Response.json(payload, {
    ...init,
    headers: {
      "Cache-Control": "no-store",
      ...(init.headers || {}),
    },
  });
}

function timingCacheKey(request) {
  const url = new URL(request.url);
  const keys = ["year", "meeting", "session", "fast"];
  return keys
    .map(
      (key) =>
        `${key}=${normalizedSelector(url.searchParams.get(key), key === "year" ? String(new Date().getUTCFullYear()) : key === "fast" ? "0" : "latest")}`,
    )
    .join("&");
}

function timingCacheTtl(payload) {
  const mode = String(
    payload?.timing_mode || payload?.session_state || "",
  ).toLowerCase();
  if (payload?.is_genuinely_live || mode === "live") return 3000;
  if (mode.includes("delayed") || mode.includes("recent")) return 30000;
  if (mode.includes("archive")) return 21600000;
  return 15000;
}

function cachedTimingResponse(cacheKey) {
  const cached = TIMING_RESPONSE_CACHE.get(cacheKey);
  if (!cached || cached.expiresAt <= Date.now()) {
    if (cached) TIMING_RESPONSE_CACHE.delete(cacheKey);
    return null;
  }
  return {
    ...cached.payload,
    timing_cache_status: "hit",
    server_fetched_at: cached.serverFetchedAt,
    cache_expires_at: new Date(cached.expiresAt).toISOString(),
  };
}

function cacheTimingPayload(cacheKey, payload) {
  const serverFetchedAt = new Date().toISOString();
  const enriched = {
    ...payload,
    timing_cache_status: "miss",
    server_fetched_at: serverFetchedAt,
    source_packet_at: payload?.timing_last_updated_at || null,
  };
  const ttl = cacheKey.includes("latest")
    ? Math.min(15000, timingCacheTtl(enriched))
    : timingCacheTtl(enriched);
  if (TIMING_RESPONSE_CACHE.size >= 100)
    TIMING_RESPONSE_CACHE.delete(TIMING_RESPONSE_CACHE.keys().next().value);
  TIMING_RESPONSE_CACHE.set(cacheKey, {
    payload: enriched,
    serverFetchedAt,
    expiresAt: Date.now() + ttl,
  });
  return jsonNoStore(enriched, {
    headers: { "X-PitWall-Timing-Cache": "miss" },
  });
}

function normalizedYear(value) {
  const year = Number(String(value || "").trim());
  const current = new Date().getUTCFullYear();
  if (
    !Number.isInteger(year) ||
    year < 2018 ||
    year > Math.max(2030, current + 1)
  )
    return null;
  return String(year);
}

function normalizedSelector(value, fallback = "latest") {
  const raw = String(value || fallback).trim();
  if (!raw) return fallback;
  return raw
    .replace(/[^\w\s./:-]/g, " ")
    .replace(/\s+/g, " ")
    .slice(0, 120);
}

async function getText(url, timeoutMs = 12000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      signal: controller.signal,
      headers: {
        Accept: "application/json,text/plain,*/*",
        "User-Agent": "BestHTTP",
        "Accept-Encoding": "gzip, identity",
      },
      cache: "no-store",
    });
    const reader = res.body?.getReader();
    if (!reader) return { ok: false, status: res.status, text: "", url };
    const chunks = [];
    let length = 0;
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      length += value.length;
      if (length > 12_000_000) {
        await reader.cancel();
        throw new Error("Timing feed exceeds size limit");
      }
      chunks.push(value);
    }
    const text = Buffer.concat(chunks).toString("utf8");
    return { ok: res.ok, status: res.status, text, url };
  } catch (error) {
    console.warn(
      "PitWall timing request failed",
      new URL(url).hostname,
      error?.name,
    );
    return {
      ok: false,
      status: 0,
      text: "",
      url,
      error: "Provider request failed",
    };
  } finally {
    clearTimeout(timeout);
  }
}

function requestIp(request) {
  const forwarded = request.headers.get("x-forwarded-for") || "";
  const first = forwarded.split(",")[0]?.trim();
  return first || request.headers.get("x-real-ip") || "local";
}

function checkRateLimit(request) {
  const key = requestIp(request);
  const now = Date.now();
  const previous = RATE_LIMIT_BUCKET.get(key) || 0;
  const waitMs = RATE_LIMIT_MS - (now - previous);
  if (waitMs > 0) {
    return {
      limited: true,
      retryAfterSeconds: Math.max(1, Math.ceil(waitMs / 1000)),
      key,
    };
  }
  RATE_LIMIT_BUCKET.set(key, now);
  for (const [bucketKey, timestamp] of RATE_LIMIT_BUCKET.entries()) {
    if (now - timestamp > Math.max(60000, RATE_LIMIT_MS * 12))
      RATE_LIMIT_BUCKET.delete(bucketKey);
  }
  return { limited: false, retryAfterSeconds: 0, key };
}

function readValue(value, fallback = "") {
  if (value === null || value === undefined || value === "") return fallback;

  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return value;
  }

  if (typeof value === "object") {
    return (
      value.Value ??
      value.value ??
      value.Time ??
      value.time ??
      value.Gap ??
      value.gap ??
      value.Interval ??
      value.interval ??
      value.Status ??
      value.status ??
      value.Message ??
      value.message ??
      fallback
    );
  }

  return fallback;
}

function readNumber(value, fallback = "") {
  const clean = readValue(value, "");
  if (clean === "" || clean === null || clean === undefined) return fallback;
  const number = Number(clean);
  return Number.isFinite(number) ? number : fallback;
}

function decompressFormula1Payload(value) {
  if (typeof value !== "string") return value;
  try {
    const buffer = Buffer.from(value, "base64");
    const inflated = inflateRawSync(buffer, {
      maxOutputLength: 2_000_000,
    }).toString("utf8");
    return safeJson(inflated, inflated);
  } catch {
    return value;
  }
}

function parseJsonStream(text, zipped = false) {
  const entries = [];
  for (const rawLine of String(text || "").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;
    const jsonStartCandidates = [line.indexOf("{"), line.indexOf("[")].filter(
      (idx) => idx >= 0,
    );
    if (!jsonStartCandidates.length) continue;
    const jsonStart = Math.min(...jsonStartCandidates);
    const stamp = line.slice(0, jsonStart).trim().replace(/^,|,$/g, "");
    const jsonPart = line.slice(jsonStart);
    const parsed = safeJson(jsonPart, null);
    if (parsed === null) continue;
    entries.push({
      time: stamp,
      data: zipped ? decompressFormula1Payload(parsed) : parsed,
    });
  }
  return entries;
}

function latestByMerge(entries) {
  const merged = {};
  for (const entry of entries || []) {
    const data = entry?.data;
    if (!data || typeof data !== "object" || Array.isArray(data)) continue;
    Object.assign(merged, data);
  }
  return merged;
}

function entriesWithKeyframe(streamEntries, keyframeJson) {
  const entries = Array.isArray(streamEntries) ? [...streamEntries] : [];
  if (keyframeJson && typeof keyframeJson === "object") {
    entries.unshift({
      time: keyframeJson.Utc || keyframeJson.utc || "",
      data: keyframeJson,
    });
  }
  return entries;
}

function pickMeetings(yearIndex) {
  return (
    yearIndex?.Meetings ||
    yearIndex?.meetings ||
    yearIndex?.Races ||
    yearIndex?.races ||
    []
  );
}

function pickSessions(meeting) {
  const sessions = meeting?.Sessions || meeting?.sessions;
  return Array.isArray(sessions) ? sessions : [];
}

function sessionStart(session) {
  return sessionDate(
    session?.StartDate ||
      session?.startDate ||
      session?.Date ||
      session?.date_start,
    session?.GmtOffset,
  );
}

function sessionEnd(session) {
  return sessionDate(
    session?.EndDate ||
      session?.endDate ||
      session?.DateEnd ||
      session?.date_end,
    session?.GmtOffset,
  );
}

function sessionLifecycle(selected, hasUsefulF1Data = false) {
  const now = Date.now();
  const start =
    selected?.start?.getTime?.() ||
    sessionStart(selected?.session)?.getTime?.() ||
    0;
  const end =
    selected?.end?.getTime?.() ||
    sessionEnd(selected?.session)?.getTime?.() ||
    (start ? start + 3 * 60 * 60 * 1000 : 0);
  const preWindow = 90 * 60 * 1000;

  if (!start) {
    return { state: "unknown", is_live: false, refresh_after_ms: 60000 };
  }
  if (now < start - preWindow) {
    return { state: "upcoming", is_live: false, refresh_after_ms: 60000 };
  }
  if (now < start) {
    return { state: "pre-session", is_live: false, refresh_after_ms: 15000 };
  }
  if (now <= end) {
    return {
      state: hasUsefulF1Data ? "active" : "active_without_live_data",
      is_live: Boolean(hasUsefulF1Data),
      refresh_after_ms: hasUsefulF1Data ? 5000 : 30000,
    };
  }
  return { state: "archive", is_live: false, refresh_after_ms: 90000 };
}

function timingFreshness(lifecycle, hasData, source, packetAt = null) {
  const enabled =
    process.env.DISABLE_LIVE_MODE !== "true" &&
    process.env.LIVE_TIMING_ENABLED !== "false";
  return freshness(lifecycle, hasData, source, packetAt, Date.now(), enabled);
}

function safeNormalizedTimingPayload(value) {
  const normalized =
    value && typeof value === "object" && !Array.isArray(value) ? value : {};
  return {
    session:
      normalized.session && typeof normalized.session === "object"
        ? normalized.session
        : {},
    drivers: Array.isArray(normalized.drivers) ? normalized.drivers : [],
    leaderboard: Array.isArray(normalized.leaderboard)
      ? normalized.leaderboard
      : [],
    intervals: Array.isArray(normalized.intervals) ? normalized.intervals : [],
    laps: Array.isArray(normalized.laps) ? normalized.laps : [],
    stints: Array.isArray(normalized.stints) ? normalized.stints : [],
    pits: Array.isArray(normalized.pits) ? normalized.pits : [],
    raceControl: Array.isArray(normalized.raceControl)
      ? normalized.raceControl
      : [],
    weather: normalized.weather || null,
    carData: Array.isArray(normalized.carData) ? normalized.carData : [],
    radio: Array.isArray(normalized.radio) ? normalized.radio : [],
    trackStatus: normalized.trackStatus || null,
    lapCount:
      normalized.lapCount && typeof normalized.lapCount === "object"
        ? normalized.lapCount
        : {},
    source: normalized.source || "",
  };
}

function selectionResolution(
  selected,
  requestedSession,
  requestedMeeting,
  hasUsefulF1Data = false,
  fallback = "",
) {
  if (!selected) {
    return {
      strategy: "fallback",
      requested_meeting: requestedMeeting,
      requested_session: requestedSession,
      selected_meeting: null,
      selected_session: null,
      reason:
        fallback ||
        "No matching Formula 1 timing session was listed for this selection.",
    };
  }
  const selectedSessionName = normalizeSessionName(
    selected.session?.Name ||
      selected.session?.name ||
      selected.session?.SessionName ||
      selected.session?.session_name,
  );
  const selectedMeetingName = meetingName(selected.meeting);
  const autoSelected =
    requestedMeeting === "latest" || requestedSession === "latest";
  return {
    strategy: autoSelected ? "auto_best_available" : "manual_safe_selection",
    requested_meeting: requestedMeeting,
    requested_session: requestedSession,
    selected_meeting: selectedMeetingName,
    selected_session: selectedSessionName,
    selected_session_key: String(
      selected.session?.Key ||
        selected.session?.key ||
        selected.session?.session_key ||
        selected.session?.Path ||
        selected.session?.path ||
        "",
    ),
    selected_meeting_key: meetingKey(selected.meeting),
    has_useful_timing_data: Boolean(hasUsefulF1Data),
    reason: autoSelected
      ? "Selected the best available live, completed, upcoming, or cached timing session."
      : "Manual session selection was normalized and guarded before fetch.",
  };
}

function normalizeSessionName(name) {
  return String(name || "")
    .replace(/_/g, " ")
    .trim();
}

function normalizeToken(value) {
  return String(value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(
      /formula 1|grand prix|gp|prix|airways|aramco|aws|lenovo|emirates|msc|crypto.com/g,
      " ",
    )
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function meetingName(meeting) {
  return normalizeSessionName(
    meeting?.Name ||
      meeting?.name ||
      meeting?.MeetingName ||
      meeting?.meeting_name ||
      meeting?.Location ||
      meeting?.location ||
      meeting?.Path ||
      meeting?.path,
  );
}

function meetingKey(meeting) {
  return String(
    meeting?.Key ||
      meeting?.key ||
      meeting?.MeetingKey ||
      meeting?.meeting_key ||
      meeting?.Path ||
      meeting?.path ||
      meetingName(meeting),
  );
}

function meetingMatches(meeting, requestedMeeting) {
  const requested = normalizeToken(requestedMeeting);
  if (!requested || requested === "latest" || requested === "current")
    return true;
  const haystack = normalizeToken(
    [
      meetingName(meeting),
      meeting?.Location,
      meeting?.Country?.Name,
      meeting?.Country?.Code,
      meeting?.Path,
      meetingKey(meeting),
    ]
      .filter(Boolean)
      .join(" "),
  );
  return requested.split(/\s+/).every((part) => haystack.includes(part));
}

function isRealSession(session) {
  const name = normalizeSessionName(
    session?.Name ||
      session?.name ||
      session?.SessionName ||
      session?.session_name,
  ).toLowerCase();
  return Boolean(name) && !name.includes("test");
}

function isGrandPrixMeeting(meeting) {
  const name = meetingName(meeting).toLowerCase();
  const path = String(meeting?.Path || meeting?.path || "").toLowerCase();
  const text = `${name} ${path}`;
  if (!name) return false;
  if (
    text.includes("pre-season") ||
    text.includes("preseason") ||
    text.includes("testing") ||
    text.includes("test")
  )
    return false;
  return pickSessions(meeting).some(isRealSession);
}

function chooseSession(
  meetings,
  requestedSession,
  requestedMeeting = "latest",
) {
  const sessions = [];
  for (const meeting of meetings) {
    if (!meetingMatches(meeting, requestedMeeting)) continue;
    for (const session of pickSessions(meeting)) {
      if (!isRealSession(session)) continue;
      sessions.push({
        meeting,
        session,
        start: sessionStart(session),
        end: sessionEnd(session),
      });
    }
  }

  sessions.sort(
    (a, b) => (a.start?.getTime() || 0) - (b.start?.getTime() || 0),
  );

  if (requestedSession && requestedSession !== "latest") {
    const exact = sessions.find(
      (item) =>
        String(
          item.session?.Path ||
            item.session?.path ||
            item.session?.Key ||
            item.session?.session_key,
        ) === requestedSession,
    );
    if (exact) return exact;

    const byName = [...sessions].reverse().find((item) =>
      normalizeSessionName(item.session?.Name || item.session?.name)
        .toLowerCase()
        .includes(requestedSession.toLowerCase()),
    );
    if (byName) return byName;
    return null;
  }

  const now = Date.now();
  const preWindow = 90 * 60 * 1000;

  if (TIMING_AUTO_SELECT_ENABLED) {
    // Prefer a session that is currently active or about to start.
    const active = sessions.find((item) => {
      if (!item.start) return false;
      const start = item.start.getTime();
      const end = item.end?.getTime() || start + 3 * 60 * 60 * 1000;
      return now >= start - preWindow && now <= end;
    });
    if (active) return active;
  }

  // If nothing is live, show the latest completed/started session.
  const completedOrStarted = sessions.filter(
    (item) => item.start && item.start.getTime() <= now,
  );
  if (completedOrStarted.length)
    return completedOrStarted[completedOrStarted.length - 1];

  // Before the season/weekend starts, show the next upcoming session.
  return sessions[0] || null;
}

function meetingOptions(meetings) {
  return (meetings || [])
    .filter(isGrandPrixMeeting)
    .map((meeting) => ({
      key: meetingKey(meeting),
      name: meetingName(meeting),
      path: meeting?.Path || meeting?.path || "",
      country: meeting?.Country?.Name || meeting?.country || "",
      location: meeting?.Location || meeting?.location || "",
      date_start:
        meeting?.DateStart ||
        meeting?.date_start ||
        pickSessions(meeting)?.[0]?.StartDate ||
        "",
    }))
    .filter((meeting) => meeting.name);
}

function sessionOptions(meeting) {
  return pickSessions(meeting)
    .filter(isRealSession)
    .map((session) => ({
      key: String(
        session?.Path ||
          session?.path ||
          session?.Key ||
          session?.session_key ||
          normalizeSessionName(session?.Name || session?.name),
      ),
      name: normalizeSessionName(
        session?.Name ||
          session?.name ||
          session?.SessionName ||
          session?.session_name,
      ),
      type: session?.Type || session?.type || "",
      date_start: session?.StartDate || session?.startDate || "",
    }));
}

function normalizeMiniSectorTone(value) {
  const text = String(readValue(value, value) || "").toLowerCase();
  if (
    text.includes("2048") ||
    text.includes("purple") ||
    text.includes("overall") ||
    text.includes("fastest")
  )
    return "purple";
  if (
    text.includes("2049") ||
    text.includes("green") ||
    text.includes("personal")
  )
    return "green";
  if (text.includes("2051") || text.includes("yellow")) return "yellow";
  if (text.includes("2064") || text.includes("pit")) return "pit";
  if (text.includes("0") || text.includes("normal")) return "neutral";
  return "neutral";
}

function normalizeMiniSectors(rawSectors) {
  const sectors = Array.isArray(rawSectors)
    ? rawSectors
    : rawSectors && typeof rawSectors === "object"
      ? Object.values(rawSectors)
      : [];

  const output = [];
  sectors.forEach((sector, sectorIndex) => {
    const sectorNumber = readValue(
      sector?.Number ||
        sector?.number ||
        sector?.SectorNumber ||
        sector?.sector_number,
      sectorIndex + 1,
    );
    const rawSegments =
      sector?.Segments ||
      sector?.segments ||
      sector?.MiniSectors ||
      sector?.mini_sectors ||
      [];
    const segments = Array.isArray(rawSegments)
      ? rawSegments
      : rawSegments && typeof rawSegments === "object"
        ? Object.values(rawSegments)
        : [];

    if (segments.length) {
      segments.forEach((segment, segmentIndex) => {
        const status = readValue(
          segment?.Status ||
            segment?.status ||
            segment?.Value ||
            segment?.value ||
            segment,
          "",
        );
        output.push({
          sector: sectorNumber,
          segment: readValue(
            segment?.Number || segment?.number || segmentIndex + 1,
            segmentIndex + 1,
          ),
          status,
          tone: normalizeMiniSectorTone(status),
        });
      });
      return;
    }

    const status = readValue(
      sector?.Status ||
        sector?.status ||
        sector?.Value ||
        sector?.value ||
        sector,
      "",
    );
    if (status !== "") {
      output.push({
        sector: sectorNumber,
        segment: 1,
        status,
        tone: normalizeMiniSectorTone(status),
      });
    }
  });

  return output;
}

function sessionPath(meeting, session) {
  const year = String(meeting?.Year || meeting?.year || "").trim();
  const meetingPath = String(meeting?.Path || meeting?.path || "").replace(
    /^\/+|\/+$/g,
    "",
  );
  const sessionPath = String(session?.Path || session?.path || "").replace(
    /^\/+|\/+$/g,
    "",
  );

  if (sessionPath.startsWith("20"))
    return sessionPath.endsWith("/") ? sessionPath : `${sessionPath}/`;
  if (meetingPath && sessionPath)
    return `${year}/${meetingPath}/${sessionPath}/`.replace(/\/+/g, "/");
  return "";
}

function driverDisplay(raw, num = "") {
  const firstLast = [
    raw?.FirstName || raw?.first_name || raw?.givenName,
    raw?.LastName || raw?.last_name || raw?.familyName,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    raw?.FullName ||
    raw?.full_name ||
    raw?.BroadcastName ||
    raw?.broadcast_name ||
    firstLast ||
    raw?.Tla ||
    raw?.tla ||
    raw?.Code ||
    raw?.code ||
    raw?.RacingNumber ||
    num ||
    "-"
  );
}

function driverRowsFromMap(lines) {
  return Object.entries(lines || {})
    .filter(
      ([key, raw]) =>
        raw &&
        typeof raw === "object" &&
        !["_kf", "timestamp", "Utc"].includes(key),
    )
    .map(([num, raw]) => {
      const racingNumber = Number(
        raw?.RacingNumber || raw?.racing_number || raw?.DriverNumber || num,
      );
      return {
        driver_number: Number.isFinite(racingNumber) ? racingNumber : num,
        full_name: driverDisplay(raw, num),
        name_acronym: raw?.Tla || raw?.tla || raw?.Code || raw?.code || "",
        team_name:
          raw?.TeamName || raw?.team_name || raw?.Team || raw?.team || "",
        team_colour: raw?.TeamColour || raw?.team_colour || "e10600",
        headshot_url: raw?.HeadshotUrl || raw?.headshot_url || "",
      };
    });
}

function normalizeDrivers(driverList) {
  const merged = latestByMerge(driverList);
  const lines = merged?.Drivers || merged?.drivers || merged || {};
  return driverRowsFromMap(lines);
}

function normalizeDriverKeyframe(driverJson) {
  const lines = driverJson?.Drivers || driverJson?.drivers || driverJson || {};
  return driverRowsFromMap(lines);
}

function mergeDriverSources(primary, fallbackMap) {
  const map = new Map();
  for (const driver of primary || []) {
    map.set(String(driver.driver_number), driver);
  }
  for (const [num, fallback] of fallbackMap || []) {
    const current = map.get(String(num));
    if (!current || !current.full_name || current.full_name === "-") {
      map.set(String(num), fallback);
    } else if (!current.team_name && fallback.team_name) {
      map.set(String(num), { ...current, team_name: fallback.team_name });
    }
  }
  return Array.from(map.values());
}

function objectList(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter(Boolean);
  if (typeof value === "object") return Object.values(value).filter(Boolean);
  return [];
}

function latestStint(rawStints) {
  // Do not substitute an older compound when the current stint is incomplete.
  return objectList(rawStints).at(-1) || null;
}

function stintCompound(stint) {
  return readValue(
    stint?.Compound ||
      stint?.compound ||
      stint?.Tyre ||
      stint?.tyre ||
      stint?.tyre_compound ||
      stint?.compound_name,
    "",
  );
}

function stintTyreAge(stint) {
  return readValue(
    stint?.TotalLaps ??
      stint?.total_laps ??
      stint?.TyreAge ??
      stint?.tyre_age ??
      stint?.tyre_age_at_start ??
      stint?.LapCount ??
      stint?.lap_count ??
      stint?.StartLaps ??
      stint?.start_laps,
    "",
  );
}

function normalizeTiming(timingData, drivers, timingAppData, carData) {
  const driverMap = new Map(
    (drivers || []).map((d) => [String(d.driver_number), d]),
  );
  const lines = {};
  const appLines = {};

  for (const entry of timingData || []) {
    const data = entry?.data?.Lines || entry?.data?.lines || {};
    for (const [num, update] of Object.entries(data)) {
      lines[num] = mergeTimingLine(lines[num] || {}, update);
    }
  }

  for (const entry of timingAppData || []) {
    const data = entry?.data?.Lines || entry?.data?.lines || {};
    for (const [num, update] of Object.entries(data)) {
      appLines[num] = mergeTimingLine(appLines[num] || {}, update);
    }
  }

  const latestCar = {};
  for (const entry of carData || []) {
    const data =
      entry?.data?.Entries || entry?.data?.entries || entry?.data || {};
    for (const item of Array.isArray(data) ? data : Object.values(data)) {
      const cars = item?.Cars || item?.cars || {};
      for (const [num, car] of Object.entries(cars)) {
        latestCar[num] = { ...(latestCar[num] || {}), ...car };
      }
    }
  }

  const rows = Object.entries(lines).map(([num, raw]) => {
    const driver =
      driverMap.get(String(Number(num))) || driverMap.get(String(num)) || {};
    const stint =
      latestStint(appLines[num]?.Stints || appLines[num]?.stints) ||
      appLines[num]?.Stint ||
      appLines[num]?.stint ||
      {};
    const channels = latestCar[num]?.Channels || latestCar[num]?.channels || {};
    const lastLap = readValue(raw?.LastLapTime, "");
    const interval = readValue(raw?.IntervalToPositionAhead, "");
    const gapToLeader = readValue(raw?.GapToLeader, "");

    return {
      driver_number: Number(num),
      position: readNumber(raw?.Position ?? raw?.position, null),
      interval,
      gap_to_leader: gapToLeader,
      status: readValue(raw?.Status || raw?.status, ""),
      lap_duration: lastLap,
      compound: stintCompound(stint),
      tyre_age: stintTyreAge(stint),
      speed: readValue(
        channels?.[2] ?? latestCar[num]?.Speed ?? latestCar[num]?.speed,
        "",
      ),
      n_gear: readValue(
        channels?.[3] ?? latestCar[num]?.Gear ?? latestCar[num]?.gear,
        "",
      ),
      rpm: readValue(
        channels?.[0] ?? latestCar[num]?.Rpm ?? latestCar[num]?.rpm,
        "",
      ),
      brake: readValue(
        channels?.[5] ?? latestCar[num]?.Brake ?? latestCar[num]?.brake,
        "",
      ),
      sectors: raw?.Sectors || raw?.sectors || [],
      mini_sectors: normalizeMiniSectors(raw?.Sectors || raw?.sectors || []),
      driver,
    };
  });

  return rows.sort(
    (a, b) =>
      (a.position ?? Infinity) - (b.position ?? Infinity) ||
      a.driver_number - b.driver_number,
  );
}

function normalizeWeather(weatherEntries) {
  const latest = weatherEntries?.slice(-1)?.[0]?.data || null;
  if (!latest) return null;
  return {
    air_temperature: latest.AirTemp ?? latest.air_temperature ?? "",
    track_temperature: latest.TrackTemp ?? latest.track_temperature ?? "",
    humidity: latest.Humidity ?? latest.humidity ?? "",
    rainfall: latest.Rainfall ?? latest.rainfall ?? "",
    wind_speed: latest.WindSpeed ?? latest.wind_speed ?? "",
    wind_direction: latest.WindDirection ?? latest.wind_direction ?? "",
  };
}

function normalizeRaceControl(entries) {
  const messages = [];
  for (const entry of entries || []) {
    const data = entry?.data || {};
    const candidates =
      data.Messages ||
      data.messages ||
      data.RaceControlMessages ||
      data.raceControlMessages ||
      data.Message ||
      data.message ||
      data;
    const list = Array.isArray(candidates)
      ? candidates
      : typeof candidates === "object"
        ? Object.values(candidates)
        : [{ Message: candidates }];

    for (const raw of list) {
      if (!raw) continue;
      const item = typeof raw === "object" ? raw : { Message: raw };
      messages.push({
        date: messageTimestamp(item),
        lap: readValue(item.Lap || item.lap, ""),
        category:
          item.Category ||
          item.category ||
          item.Flag ||
          item.flag ||
          item.Scope ||
          item.scope ||
          item.Type ||
          item.type ||
          "Race control",
        status: item.Status || item.status || item.Mode || item.mode || "",
        racing_number:
          item.RacingNumber || item.racing_number || item.DriverNumber || "",
        message:
          item.Message ||
          item.message ||
          item.Text ||
          item.text ||
          JSON.stringify(item),
      });
    }
  }

  return messages
    .filter((message) => message.message && message.message !== "{}")
    .slice(-40)
    .reverse();
}

function normalizeLapCount(entries) {
  const latest = entries?.slice(-1)?.[0]?.data || {};
  return {
    current_lap: latest.CurrentLap || latest.current_lap || "",
    total_laps: latest.TotalLaps || latest.total_laps || "",
  };
}

function normalizeTeamRadio(entries, basePath) {
  const captures = [];
  for (const entry of entries || []) {
    const data = entry?.data || {};
    const list = Array.isArray(data.Captures || data.captures)
      ? data.Captures || data.captures
      : Array.isArray(data.Radio || data.radio)
        ? data.Radio || data.radio
        : [data];
    for (const item of list) {
      captures.push({ time: entry.time, data: item });
    }
  }

  return captures
    .map((entry) => {
      const data = entry?.data || {};
      const path =
        data.Path ||
        data.path ||
        data.Url ||
        data.url ||
        data.RecordingUrl ||
        data.recording_url ||
        data.AudioUrl ||
        "";
      const recordingUrl = path
        ? path.startsWith("http")
          ? path
          : endpoint(`${basePath}${String(path).replace(/^\/+/, "")}`)
        : "";

      return {
        date: messageTimestamp(data),
        driver_number: Number(
          data.RacingNumber || data.driver_number || data.DriverNumber || 0,
        ),
        recording_url: recordingUrl,
        message: data.Message || data.message || data.Text || data.text || "",
        raw: data,
      };
    })
    .filter((item) => item.recording_url || item.message)
    .slice(-30)
    .reverse();
}

async function fetchFeeds(basePath, { fast = false } = {}) {
  const feeds = {};
  const feedList = fast ? FAST_FEEDS : FEEDS;
  const timeoutMs = fast ? 4200 : 7000;
  await Promise.all(
    feedList.map(async (feed) => {
      const url = endpoint(`${basePath}${feed}`);
      const response = await getText(url, timeoutMs);
      const zipped = feed.includes(".z.");
      const json = feed.endsWith(".json")
        ? decompressFormula1Payload(safeJson(response.text, response.text))
        : null;
      const stream = feed.endsWith(".jsonStream")
        ? parseJsonStream(response.text, zipped)
        : [];
      feeds[feed] = {
        ...response,
        text: undefined,
        entries: stream,
        json,
        count: stream.length,
      };
    }),
  );
  return feeds;
}

export async function GET(request) {
  const params = new URL(request.url).searchParams;
  const year = normalizedYear(
    params.get("year") || String(new Date().getUTCFullYear()),
  );
  if (!year)
    return jsonNoStore(
      {
        ok: false,
        error: "Invalid year. Choose a supported Formula 1 season.",
        normalized: null,
        meeting_options: [],
        session_options: [],
      },
      { status: 400 },
    );
  const requestedSession = normalizedSelector(params.get("session"), "latest");
  const requestedMeeting = normalizedSelector(params.get("meeting"), "latest");
  const fast = params.get("fast") === "1" || params.get("fast") === "true";
  const cacheKey = timingCacheKey(request);
  const cached = cachedTimingResponse(cacheKey);
  if (cached)
    return jsonNoStore(cached, {
      headers: { "X-PitWall-Timing-Cache": "hit" },
    });
  const rate = checkRateLimit(request);
  if (rate.limited)
    return jsonNoStore(
      {
        ok: false,
        error: "Timing endpoint rate limit exceeded.",
        retry_after_seconds: rate.retryAfterSeconds,
      },
      {
        status: 429,
        headers: { "Retry-After": String(rate.retryAfterSeconds) },
      },
    );
  const index = await getText(endpoint(`${year}/Index.json`));
  const indexMeetings = pickMeetings(safeJson(index.text, null));
  const meetings = Array.isArray(indexMeetings) ? indexMeetings : [];
  const selected = chooseSession(meetings, requestedSession, requestedMeeting);
  if (!selected)
    return cacheTimingPayload(cacheKey, {
      ok: false,
      source: "Formula1LiveTiming",
      reason: index.ok
        ? "No matching timing session is available. No other race has been substituted."
        : "The Formula 1 session index is unavailable. Try again later.",
      timing_mode: "unavailable",
      is_genuinely_live: false,
      is_live: false,
      source_packet_at: null,
      server_time: new Date().toISOString(),
      normalized: null,
      meeting_options: meetingOptions(meetings),
      session_options: [],
      session_resolution: selectionResolution(
        null,
        requestedSession,
        requestedMeeting,
      ),
      session_state: "unavailable",
      refresh_after_ms: 60000,
    });
  const basePath = sessionPath(selected.meeting, selected.session);
  const feeds = basePath ? await fetchFeeds(basePath, { fast }) : {};
  const keyframeDrivers = normalizeDriverKeyframe(
    feeds["DriverList.json"]?.json || {},
  );
  const streamDrivers = normalizeDrivers(
    feeds["DriverList.jsonStream"]?.entries || [],
  );
  const drivers = mergeDriverSources(
    keyframeDrivers,
    new Map(streamDrivers.map((d) => [String(d.driver_number), d])),
  );
  const entries = (name) =>
    entriesWithKeyframe(
      feeds[`${name}.jsonStream`]?.entries || [],
      feeds[`${name}.json`]?.json,
    );
  const leaderboard = normalizeTiming(
    entries("TimingData"),
    drivers,
    entries("TimingAppData"),
    entries("CarData.z"),
  );
  const normalized = {
    session: {
      meeting_name: meetingName(selected.meeting),
      meeting_key: meetingKey(selected.meeting),
      session_name: selected.session.Name || selected.session.name,
      session_type: selected.session.Type || selected.session.type,
      session_path: selected.session.Path || selected.session.path,
      date_start: sessionStart(selected.session)?.toISOString() || null,
      base_path: basePath,
    },
    drivers,
    leaderboard,
    intervals: leaderboard,
    laps: leaderboard.map((r) => ({
      driver_number: r.driver_number,
      lap_duration: r.lap_duration,
    })),
    stints: leaderboard.map((r) => ({
      driver_number: r.driver_number,
      compound: r.compound,
      tyre_age: r.tyre_age,
    })),
    carData: leaderboard.map((r) => ({
      driver_number: r.driver_number,
      speed: r.speed,
      n_gear: r.n_gear,
      rpm: r.rpm,
      brake: r.brake,
    })),
    weather: normalizeWeather(entries("WeatherData")),
    raceControl: normalizeRaceControl(entries("RaceControlMessages")),
    lapCount: normalizeLapCount(entries("LapCount")),
    trackStatus: entries("TrackStatus").slice(-1)[0]?.data || null,
    pits: [],
    radio: normalizeTeamRadio(entries("TeamRadio"), basePath),
  };
  const hasData = leaderboard.length > 0;
  const sessionStatus = entries("SessionStatus").at(-1)?.data?.Status || null;
  // Finished can close Q1/Q2; only Finalised/Ends establish whole-session completion.
  const lifecycle = applySessionStatus(
    sessionLifecycle(selected, hasData),
    sessionStatus,
  );
  const timing = timingFreshness(
    lifecycle,
    hasData,
    "Formula1LiveTiming",
    packetTimestamp(feeds),
  );
  return cacheTimingPayload(cacheKey, {
    ok: hasData,
    source: "Formula1LiveTiming",
    source_note:
      "Formula 1 static session feeds. A missing packet timestamp cannot establish live timing.",
    ...timing,
    is_live: timing.is_genuinely_live,
    server_time: new Date().toISOString(),
    base_path: basePath,
    session_state: lifecycle.state,
    session_status: sessionStatus,
    completion_verified: lifecycle.completion_verified,
    refresh_after_ms: lifecycle.refresh_after_ms,
    session_resolution: selectionResolution(
      selected,
      requestedSession,
      requestedMeeting,
      hasData,
    ),
    auto_selected_session: selectionResolution(
      selected,
      requestedSession,
      requestedMeeting,
      hasData,
    ),
    warnings: hasData
      ? []
      : [
          "Timing data is unavailable for this session. No other event has been substituted.",
        ],
    meeting_options: meetingOptions(meetings),
    session_options: sessionOptions(selected.meeting),
    feed_status: Object.fromEntries(
      Object.entries(feeds).map(([key, value]) => [
        key,
        { ok: value.ok, status: value.status, count: value.count || 0 },
      ]),
    ),
    normalized: safeNormalizedTimingPayload(normalized),
  });
}
