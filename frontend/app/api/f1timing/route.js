export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { inflateRawSync } from "node:zlib";

const F1_BASE = "https://livetiming.formula1.com/static";
const JOLPICA_BASE = "https://api.jolpi.ca/ergast/f1";
const OPENF1_BASE = "https://api.openf1.org/v1";
const OPENF1_ACCESS_TOKEN = (process.env.OPENF1_ACCESS_TOKEN || process.env.OPENF1_TOKEN || "").trim();
const OPENF1_USERNAME = (process.env.OPENF1_USERNAME || "").trim();
const OPENF1_PASSWORD = (process.env.OPENF1_PASSWORD || "").trim();
const RATE_LIMIT_MS = Math.max(1000, Number(process.env.F1_TIMING_RATE_LIMIT_MS || 5000));
const TIMING_AUTO_SELECT_ENABLED = String(process.env.PITWALL_TIMING_AUTO_SELECT || "true").toLowerCase() !== "false";
const OFFICIAL_VISUAL_CACHE = new Map();
const RATE_LIMIT_BUCKET = globalThis.__pitwallF1TimingRateLimit || new Map();
globalThis.__pitwallF1TimingRateLimit = RATE_LIMIT_BUCKET;

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
  "Position.z.jsonStream"
];

const FAST_FEEDS = [
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
  "CarData.z.json"
];

function endpoint(path) {
  return `${F1_BASE}/${String(path || "").replace(/^\/+/, "")}`;
}

function jsonNoStore(payload, init = {}) {
  return Response.json(payload, {
    ...init,
    headers: {
      "Cache-Control": "no-store",
      ...(init.headers || {})
    }
  });
}

function normalizedYear(value) {
  const year = Number(String(value || "").trim());
  const current = new Date().getUTCFullYear();
  if (!Number.isInteger(year) || year < 2018 || year > Math.max(2030, current + 1)) return null;
  return String(year);
}

function normalizedSelector(value, fallback = "latest") {
  const raw = String(value || fallback).trim();
  if (!raw) return fallback;
  return raw.replace(/[^\w\s./:-]/g, " ").replace(/\s+/g, " ").slice(0, 120);
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
        "Accept-Encoding": "gzip, identity"
      },
      cache: "no-store"
    });
    const text = await res.text();
    return { ok: res.ok, status: res.status, text, url };
  } catch (error) {
    return { ok: false, status: 0, text: "", url, error: error?.name === "AbortError" ? "timeout" : String(error?.message || error) };
  } finally {
    clearTimeout(timeout);
  }
}

function safeJson(text, fallback = null) {
  try { return JSON.parse(text); } catch { return fallback; }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
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
      key
    };
  }
  RATE_LIMIT_BUCKET.set(key, now);
  for (const [bucketKey, timestamp] of RATE_LIMIT_BUCKET.entries()) {
    if (now - timestamp > Math.max(60000, RATE_LIMIT_MS * 12)) RATE_LIMIT_BUCKET.delete(bucketKey);
  }
  return { limited: false, retryAfterSeconds: 0, key };
}

async function getJson(url, timeoutMs = 12000) {
  const response = await getText(url, timeoutMs);
  return { ...response, data: safeJson(response.text, null), text: undefined };
}

async function getOpenF1Json(path, timeoutMs = 12000) {
  const url = `${OPENF1_BASE}/${String(path || "").replace(/^\/+/, "")}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const headers = {
      Accept: "application/json",
      "User-Agent": "pitwall-live-dashboard/1.0"
    };
    if (OPENF1_ACCESS_TOKEN) {
      headers.Authorization = `Bearer ${OPENF1_ACCESS_TOKEN}`;
    } else if (OPENF1_USERNAME && OPENF1_PASSWORD) {
      headers.Authorization = `Basic ${Buffer.from(`${OPENF1_USERNAME}:${OPENF1_PASSWORD}`).toString("base64")}`;
    }
    const res = await fetch(url, { signal: controller.signal, headers, cache: "no-store" });
    const text = await res.text();
    const data = safeJson(text, null);
    const detail = data?.detail || data?.message || data?.error || text.slice(0, 280);
    const authRestricted = (res.status === 401 || res.status === 403) && /authenticated users|live f1 session|api key/i.test(String(detail || ""));
    return {
      ok: res.ok,
      status: res.status,
      data,
      auth_restricted: authRestricted,
      auth_configured: Boolean(OPENF1_ACCESS_TOKEN || (OPENF1_USERNAME && OPENF1_PASSWORD)),
      detail: authRestricted ? detail : ""
    };
  } catch (error) {
    return { ok: false, status: 0, data: null, auth_restricted: false, auth_configured: Boolean(OPENF1_ACCESS_TOKEN || (OPENF1_USERNAME && OPENF1_PASSWORD)), detail: String(error?.message || error) };
  } finally {
    clearTimeout(timeout);
  }
}

function readValue(value, fallback = "") {
  if (value === null || value === undefined || value === "") return fallback;

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
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
  const number = Number(clean);
  return Number.isFinite(number) ? number : fallback;
}

function lastObject(value) {
  if (!value) return {};
  if (Array.isArray(value)) return value[value.length - 1] || {};
  if (typeof value === "object") {
    const values = Object.values(value);
    return values[values.length - 1] || {};
  }
  return {};
}

function mergeIndexedCollection(previous, update) {
  if (!previous) return update;
  if (!update) return previous;

  if (Array.isArray(previous) || Array.isArray(update)) {
    const prevArray = Array.isArray(previous) ? previous : Object.values(previous || {});
    const updateArray = Array.isArray(update) ? update : Object.values(update || {});
    const max = Math.max(prevArray.length, updateArray.length);
    return Array.from({ length: max }, (_, index) => {
      const prevItem = prevArray[index];
      const updateItem = updateArray[index];
      if (prevItem && updateItem && typeof prevItem === "object" && typeof updateItem === "object") {
        return mergeTimingLine(prevItem, updateItem);
      }
      return updateItem ?? prevItem;
    });
  }

  if (typeof previous === "object" && typeof update === "object") {
    const merged = { ...previous };
    for (const [key, value] of Object.entries(update)) {
      const current = merged[key];
      merged[key] = current && value && typeof current === "object" && typeof value === "object"
        ? mergeTimingLine(current, value)
        : value;
    }
    return merged;
  }

  return update;
}

function mergeTimingLine(previous = {}, update = {}) {
  const merged = { ...previous, ...update };
  for (const key of ["Sectors", "sectors", "Segments", "segments", "Speeds", "speeds"]) {
    if (previous?.[key] || update?.[key]) {
      merged[key] = mergeIndexedCollection(previous?.[key], update?.[key]);
    }
  }
  return merged;
}

function decompressFormula1Payload(value) {
  if (typeof value !== "string") return value;
  try {
    const buffer = Buffer.from(value, "base64");
    const inflated = inflateRawSync(buffer).toString("utf8");
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
    const jsonStartCandidates = [line.indexOf("{"), line.indexOf("[")].filter((idx) => idx >= 0);
    if (!jsonStartCandidates.length) continue;
    const jsonStart = Math.min(...jsonStartCandidates);
    const stamp = line.slice(0, jsonStart).trim().replace(/^,|,$/g, "");
    const jsonPart = line.slice(jsonStart);
    const parsed = safeJson(jsonPart, null);
    if (parsed === null) continue;
    entries.push({ time: stamp, data: zipped ? decompressFormula1Payload(parsed) : parsed });
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
    entries.unshift({ time: keyframeJson.Utc || keyframeJson.utc || "", data: keyframeJson });
  }
  return entries;
}

function pickMeetings(yearIndex) {
  return yearIndex?.Meetings || yearIndex?.meetings || yearIndex?.Races || yearIndex?.races || [];
}

function pickSessions(meeting) {
  return meeting?.Sessions || meeting?.sessions || [];
}

function getDate(value) {
  const date = new Date(value || "");
  return Number.isNaN(date.getTime()) ? null : date;
}

function sessionStart(session) {
  return getDate(session?.StartDate || session?.startDate || session?.Date || session?.date_start || session?.GmtOffset);
}

function sessionEnd(session) {
  return getDate(session?.EndDate || session?.endDate || session?.DateEnd || session?.date_end);
}

function sessionLifecycle(selected, hasUsefulF1Data = false) {
  const now = Date.now();
  const start = selected?.start?.getTime?.() || sessionStart(selected?.session)?.getTime?.() || 0;
  const end = selected?.end?.getTime?.() || sessionEnd(selected?.session)?.getTime?.() || (start ? start + 3 * 60 * 60 * 1000 : 0);
  const preWindow = 90 * 60 * 1000;

  if (!start) {
    return { state: hasUsefulF1Data ? "active" : "unknown", is_live: Boolean(hasUsefulF1Data), refresh_after_ms: hasUsefulF1Data ? 7000 : 60000 };
  }
  if (now < start - preWindow) {
    return { state: "upcoming", is_live: false, refresh_after_ms: 60000 };
  }
  if (now < start) {
    return { state: "pre-session", is_live: false, refresh_after_ms: 15000 };
  }
  if (now <= end) {
    return { state: hasUsefulF1Data ? "active" : "active_without_live_data", is_live: Boolean(hasUsefulF1Data), refresh_after_ms: hasUsefulF1Data ? 5000 : 30000 };
  }
  return { state: "archive", is_live: false, refresh_after_ms: 90000 };
}

function timingFreshness(lifecycle, hasUsefulF1Data, source) {
  const liveDisabled = String(process.env.DISABLE_LIVE_MODE || "false").toLowerCase() === "true";
  const liveEnabled = String(process.env.LIVE_TIMING_ENABLED || "true").toLowerCase() === "true";
  const staleAfter = Number(process.env.LIVE_STALE_AFTER_SECONDS || 60);
  const lastUpdated = hasUsefulF1Data ? new Date() : null;
  const freshnessSeconds = lastUpdated ? Math.max(0, Math.round((Date.now() - lastUpdated.getTime()) / 1000)) : null;
  let timingMode = "unavailable";
  let reason = "No fresh timing packets are available for the selected session.";
  if (liveDisabled || !liveEnabled) {
    timingMode = "unavailable";
    reason = "Live timing is disabled by configuration.";
  } else if (lifecycle.state === "archive") {
    timingMode = "archive";
    reason = "The selected session has ended; this is archived/latest available timing data.";
  } else if (hasUsefulF1Data && lifecycle.is_live && freshnessSeconds <= staleAfter) {
    timingMode = "live";
    reason = "";
  } else if (hasUsefulF1Data) {
    timingMode = "stale";
    reason = "Timing data exists but is older than the freshness threshold.";
  } else {
    timingMode = source === "OpenF1Fallback" || source === "JolpicaFallback" ? "archive" : "unavailable";
  }
  return {
    live_timing_status: timingMode === "live" ? "Live" : timingMode.charAt(0).toUpperCase() + timingMode.slice(1),
    timing_mode: timingMode,
    timing_source: source,
    timing_last_updated_at: lastUpdated?.toISOString() || null,
    timing_freshness_seconds: freshnessSeconds,
    is_genuinely_live: timingMode === "live",
    live_fallback_reason: reason
  };
}

function safeNormalizedTimingPayload(value) {
  const normalized = value && typeof value === "object" && !Array.isArray(value) ? value : {};
  const fallbackLeaderboard = Array.isArray(normalized.results)
    ? normalized.results.map((result, index) => {
      const driver = result?.Driver || {};
      const constructor = result?.Constructor || {};
      const fullName = [driver.givenName, driver.familyName].filter(Boolean).join(" ") || driver.code || driver.driverId || `#${result?.number || index + 1}`;
      return {
        driver_number: Number(result?.number || index + 1),
        position: Number(result?.position || result?.positionOrder || index + 1),
        name: fullName,
        team: constructor.name || "",
        driver: {
          driver_number: Number(result?.number || index + 1),
          full_name: fullName,
          name_acronym: driver.code || "",
          team_name: constructor.name || "",
          team_colour: "e10600",
        },
        interval: result?.Time?.time || result?.status || "",
        gap_to_leader: result?.Time?.time || result?.status || "",
        lap_duration: "",
        compound: "",
        tyre_age: "",
        sectors: [],
      };
    })
    : [];
  return {
    session: normalized.session && typeof normalized.session === "object"
      ? normalized.session
      : normalized.race
        ? {
          meeting_name: normalized.race.raceName || "Latest completed Grand Prix",
          session_name: "Latest completed race",
          session_type: "Race result",
          date_start: [normalized.race.date, normalized.race.time].filter(Boolean).join(" "),
        }
        : {},
    drivers: Array.isArray(normalized.drivers) ? normalized.drivers : [],
    leaderboard: Array.isArray(normalized.leaderboard) ? normalized.leaderboard : fallbackLeaderboard,
    intervals: Array.isArray(normalized.intervals) ? normalized.intervals : fallbackLeaderboard,
    laps: Array.isArray(normalized.laps) ? normalized.laps : fallbackLeaderboard,
    stints: Array.isArray(normalized.stints) ? normalized.stints : [],
    pits: Array.isArray(normalized.pits) ? normalized.pits : [],
    raceControl: Array.isArray(normalized.raceControl) ? normalized.raceControl : [],
    weather: normalized.weather || null,
    carData: Array.isArray(normalized.carData) ? normalized.carData : [],
    radio: Array.isArray(normalized.radio) ? normalized.radio : [],
    trackStatus: normalized.trackStatus || null,
    lapCount: normalized.lapCount && typeof normalized.lapCount === "object" ? normalized.lapCount : {},
    source: normalized.source || "",
  };
}

function selectionResolution(selected, requestedSession, requestedMeeting, hasUsefulF1Data = false, fallback = "") {
  if (!selected) {
    return {
      strategy: "fallback",
      requested_meeting: requestedMeeting,
      requested_session: requestedSession,
      selected_meeting: null,
      selected_session: null,
      reason: fallback || "No matching Formula 1 timing session was listed for this selection.",
    };
  }
  const selectedSessionName = normalizeSessionName(selected.session?.Name || selected.session?.name || selected.session?.SessionName || selected.session?.session_name);
  const selectedMeetingName = meetingName(selected.meeting);
  const autoSelected = requestedMeeting === "latest" || requestedSession === "latest";
  return {
    strategy: autoSelected ? "auto_best_available" : "manual_safe_selection",
    requested_meeting: requestedMeeting,
    requested_session: requestedSession,
    selected_meeting: selectedMeetingName,
    selected_session: selectedSessionName,
    selected_session_key: String(selected.session?.Key || selected.session?.key || selected.session?.session_key || selected.session?.Path || selected.session?.path || ""),
    selected_meeting_key: meetingKey(selected.meeting),
    has_useful_timing_data: Boolean(hasUsefulF1Data),
    reason: autoSelected
      ? "Selected the best available live, completed, upcoming, or cached timing session."
      : "Manual session selection was normalized and guarded before fetch.",
  };
}

function normalizeSessionName(name) {
  return String(name || "").replace(/_/g, " ").trim();
}

function normalizeToken(value) {
  return String(value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/formula 1|grand prix|gp|prix|airways|aramco|aws|lenovo|emirates|msc|crypto.com/g, " ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function meetingName(meeting) {
  return normalizeSessionName(meeting?.Name || meeting?.name || meeting?.MeetingName || meeting?.meeting_name || meeting?.Location || meeting?.location || meeting?.Path || meeting?.path);
}

function meetingKey(meeting) {
  return String(meeting?.Key || meeting?.key || meeting?.MeetingKey || meeting?.meeting_key || meeting?.Path || meeting?.path || meetingName(meeting));
}

function meetingMatches(meeting, requestedMeeting) {
  const requested = normalizeToken(requestedMeeting);
  if (!requested || requested === "latest" || requested === "current") return true;
  const haystack = normalizeToken([
    meetingName(meeting),
    meeting?.Location,
    meeting?.Country?.Name,
    meeting?.Country?.Code,
    meeting?.Path,
    meetingKey(meeting),
  ].filter(Boolean).join(" "));
  return requested.split(/\s+/).every((part) => haystack.includes(part));
}

function isRealSession(session) {
  const name = normalizeSessionName(session?.Name || session?.name || session?.SessionName || session?.session_name).toLowerCase();
  return Boolean(name) && !name.includes("test");
}

function isGrandPrixMeeting(meeting) {
  const name = meetingName(meeting).toLowerCase();
  const path = String(meeting?.Path || meeting?.path || "").toLowerCase();
  const text = `${name} ${path}`;
  if (!name) return false;
  if (text.includes("pre-season") || text.includes("preseason") || text.includes("testing") || text.includes("test")) return false;
  return pickSessions(meeting).some(isRealSession);
}

function chooseSession(meetings, requestedSession, requestedMeeting = "latest") {
  const sessions = [];
  for (const meeting of meetings) {
    if (!meetingMatches(meeting, requestedMeeting)) continue;
    for (const session of pickSessions(meeting)) {
      if (!isRealSession(session)) continue;
      sessions.push({
        meeting,
        session,
        start: sessionStart(session),
        end: sessionEnd(session)
      });
    }
  }

  sessions.sort((a, b) => (a.start?.getTime() || 0) - (b.start?.getTime() || 0));

  if (requestedSession && requestedSession !== "latest") {
    const exact = sessions.find((item) => String(item.session?.Path || item.session?.path || item.session?.Key || item.session?.session_key) === requestedSession);
    if (exact) return exact;

    const byName = sessions.find((item) =>
      normalizeSessionName(item.session?.Name || item.session?.name)
        .toLowerCase()
        .includes(requestedSession.toLowerCase())
    );
    if (byName) return byName;
  }

  const now = Date.now();
  const preWindow = 90 * 60 * 1000;
  const postWindow = 3 * 60 * 60 * 1000;

  if (TIMING_AUTO_SELECT_ENABLED) {
    // Prefer a session that is currently active or about to start.
    const active = sessions.find((item) => {
      if (!item.start) return false;
      const start = item.start.getTime();
      const end = item.end?.getTime() || start + 3 * 60 * 60 * 1000;
      return now >= start - preWindow && now <= end + postWindow;
    });
    if (active) return active;
  }

  // If nothing is live, show the latest completed/started session.
  const completedOrStarted = sessions.filter((item) => item.start && item.start.getTime() <= now);
  if (completedOrStarted.length) return completedOrStarted[completedOrStarted.length - 1];

  // Before the season/weekend starts, show the next upcoming session.
  return sessions[0] || null;
}

function meetingOptions(meetings) {
  return (meetings || []).filter(isGrandPrixMeeting).map((meeting) => ({
    key: meetingKey(meeting),
    name: meetingName(meeting),
    path: meeting?.Path || meeting?.path || "",
    country: meeting?.Country?.Name || meeting?.country || "",
    location: meeting?.Location || meeting?.location || "",
    date_start: meeting?.DateStart || meeting?.date_start || pickSessions(meeting)?.[0]?.StartDate || "",
  })).filter((meeting) => meeting.name);
}

function sessionOptions(meeting) {
  return pickSessions(meeting).filter(isRealSession).map((session) => ({
    key: String(session?.Path || session?.path || session?.Key || session?.session_key || normalizeSessionName(session?.Name || session?.name)),
    name: normalizeSessionName(session?.Name || session?.name || session?.SessionName || session?.session_name),
    type: session?.Type || session?.type || "",
    date_start: session?.StartDate || session?.startDate || "",
  }));
}

const OFFICIAL_RACE_SLUGS = {
  australia: "australia",
  melbourne: "australia",
  china: "china",
  shanghai: "china",
  japan: "japan",
  suzuka: "japan",
  bahrain: "bahrain",
  saudi: "saudi-arabia",
  jeddah: "saudi-arabia",
  miami: "miami",
  canada: "canada",
  montreal: "canada",
  monaco: "monaco",
  spain: "spain",
  barcelona: "spain",
  austria: "austria",
  britain: "great-britain",
  silverstone: "great-britain",
  belgium: "belgium",
  spa: "belgium",
  hungary: "hungary",
  zandvoort: "netherlands",
  dutch: "netherlands",
  netherlands: "netherlands",
  italy: "italy",
  monza: "italy",
  madrid: "spain",
  azerbaijan: "azerbaijan",
  baku: "azerbaijan",
  singapore: "singapore",
  "united states": "united-states",
  austin: "united-states",
  mexico: "mexico",
  "mexico city": "mexico",
  brazil: "brazil",
  "sao paulo": "brazil",
  vegas: "las-vegas",
  "las vegas": "las-vegas",
  qatar: "qatar",
  lusail: "qatar",
  abu: "abu-dhabi",
  "abu dhabi": "abu-dhabi",
};

const TRACK_IMAGE_SLUGS = {
  australia: "melbourne",
  china: "shanghai",
  japan: "suzuka",
  bahrain: "bahrain",
  "saudi-arabia": "jeddah",
  miami: "miami",
  canada: "montreal",
  monaco: "monaco",
  spain: "barcelona",
  austria: "austria",
  "great-britain": "silverstone",
  belgium: "spa",
  hungary: "hungary",
  netherlands: "zandvoort",
  italy: "monza",
  azerbaijan: "baku",
  singapore: "singapore",
  "united-states": "austin",
  mexico: "mexico",
  brazil: "interlagos",
  "las-vegas": "lasvegas",
  qatar: "lusail",
  "abu-dhabi": "abudhabi",
};

const TRACK_IMAGE_EXAMPLES = [
  "https://media.formula1.com/image/upload/c_fit,h_704/q_auto/v1740000001/common/f1/2026/track/2026trackmontrealdetailed.webp",
  "https://media.formula1.com/image/upload/c_fit,h_704/q_auto/v1740000001/common/f1/2026/track/2026trackmontecarlodetailed.webp",
];

const OFFICIAL_CIRCUIT_MAP_ASSETS = {
  australia: "Australia_Circuit",
  china: "China_Circuit",
  japan: "Japan_Circuit",
  bahrain: "Bahrain_Circuit",
  "saudi-arabia": "Saudi_Arabia_Circuit",
  miami: "Miami_Circuit",
  canada: "Canada_Circuit",
  monaco: "Monaco_Circuit",
  spain: "Spain_Circuit",
  austria: "Austria_Circuit",
  "great-britain": "Great_Britain_Circuit",
  belgium: "Belgium_Circuit",
  hungary: "Hungary_Circuit",
  netherlands: "Netherlands_Circuit",
  italy: "Italy_Circuit",
  azerbaijan: "Azerbaijan_Circuit",
  singapore: "Singapore_Circuit",
  "united-states": "United_States_Circuit",
  mexico: "Mexico_Circuit",
  brazil: "Brazil_Circuit",
  "las-vegas": "Las_Vegas_Circuit",
  qatar: "Qatar_Circuit",
  "abu-dhabi": "Abu_Dhabi_Circuit",
};

function officialRaceSlug(meeting) {
  const text = normalizeToken([meetingName(meeting), meeting?.Location, meeting?.Country?.Name, meeting?.Path].filter(Boolean).join(" "));
  const match = Object.entries(OFFICIAL_RACE_SLUGS)
    .sort((a, b) => b[0].length - a[0].length)
    .find(([needle]) => text.includes(needle));
  return match?.[1] || "";
}

function seasonTrackImageUrl(cleanYear, trackSlug) {
  return `https://media.formula1.com/image/upload/c_fit,h_704/q_auto/v1740000001/common/f1/${cleanYear}/track/${cleanYear}track${trackSlug}detailed.webp`;
}

async function officialRaceVisual(year, meeting) {
  const raceSlug = officialRaceSlug(meeting);
  if (!raceSlug) return null;
  const trackSlug = TRACK_IMAGE_SLUGS[raceSlug] || raceSlug.replace(/-/g, "");
  const circuitAsset = OFFICIAL_CIRCUIT_MAP_ASSETS[raceSlug] || `${raceSlug.split("-").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join("_")}_Circuit`;
  const cleanYear = String(year || new Date().getUTCFullYear());
  const pageUrl = `https://www.formula1.com/en/racing/${cleanYear}/${raceSlug}/`;
  const cacheKey = `${cleanYear}:${raceSlug}`;
  if (OFFICIAL_VISUAL_CACHE.has(cacheKey)) return OFFICIAL_VISUAL_CACHE.get(cacheKey);

  const visual = {
    source: "Formula 1",
    page_url: pageUrl,
    image_url: seasonTrackImageUrl(cleanYear, trackSlug),
    fallback_image_url: `https://media.formula1.com/image/upload/c_fit,h_704/q_auto/v1740000001/content/dam/fom-website/2018-redesign-assets/Circuit%20maps%2016x9/${circuitAsset}.webp`,
    image_status: "season-track-detailed",
    alt: `${meetingName(meeting)} official circuit and grid visual`,
  };
  OFFICIAL_VISUAL_CACHE.set(cacheKey, visual);
  return visual;
}

function normalizeMiniSectorTone(value) {
  const text = String(readValue(value, value) || "").toLowerCase();
  if (text.includes("2048") || text.includes("purple") || text.includes("overall") || text.includes("fastest")) return "purple";
  if (text.includes("2049") || text.includes("green") || text.includes("personal")) return "green";
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
    const sectorNumber = readValue(sector?.Number || sector?.number || sector?.SectorNumber || sector?.sector_number, sectorIndex + 1);
    const rawSegments = sector?.Segments || sector?.segments || sector?.MiniSectors || sector?.mini_sectors || [];
    const segments = Array.isArray(rawSegments)
      ? rawSegments
      : rawSegments && typeof rawSegments === "object"
        ? Object.values(rawSegments)
        : [];

    if (segments.length) {
      segments.forEach((segment, segmentIndex) => {
        const status = readValue(segment?.Status || segment?.status || segment?.Value || segment?.value || segment, "");
        output.push({
          sector: sectorNumber,
          segment: readValue(segment?.Number || segment?.number || segmentIndex + 1, segmentIndex + 1),
          status,
          tone: normalizeMiniSectorTone(status),
        });
      });
      return;
    }

    const status = readValue(sector?.Status || sector?.status || sector?.Value || sector?.value || sector, "");
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
  const meetingPath = String(meeting?.Path || meeting?.path || "").replace(/^\/+|\/+$/g, "");
  const sessionPath = String(session?.Path || session?.path || "").replace(/^\/+|\/+$/g, "");

  if (sessionPath.startsWith("20")) return sessionPath.endsWith("/") ? sessionPath : `${sessionPath}/`;
  if (meetingPath && sessionPath) return `${year}/${meetingPath}/${sessionPath}/`.replace(/\/+/g, "/");
  return "";
}

function driverDisplay(raw, num = "") {
  const firstLast = [raw?.FirstName || raw?.first_name || raw?.givenName, raw?.LastName || raw?.last_name || raw?.familyName]
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
    .filter(([key, raw]) => raw && typeof raw === "object" && !["_kf", "timestamp", "Utc"].includes(key))
    .map(([num, raw]) => {
      const racingNumber = Number(raw?.RacingNumber || raw?.racing_number || raw?.DriverNumber || num);
      return {
        driver_number: Number.isFinite(racingNumber) ? racingNumber : num,
        full_name: driverDisplay(raw, num),
        name_acronym: raw?.Tla || raw?.tla || raw?.Code || raw?.code || "",
        team_name: raw?.TeamName || raw?.team_name || raw?.Team || raw?.team || "",
        team_colour: raw?.TeamColour || raw?.team_colour || "e10600",
        headshot_url: raw?.HeadshotUrl || raw?.headshot_url || ""
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

function normalizeJolpicaDrivers(fallback) {
  const standings = fallback?.driverStandings?.data?.MRData?.StandingsTable?.StandingsLists?.[0]?.DriverStandings || [];
  const latestResults = fallback?.latestResults?.data?.MRData?.RaceTable?.Races?.[0]?.Results || [];
  const map = new Map();

  function add(driver, constructor = {}) {
    if (!driver) return;
    const number = Number(driver.permanentNumber || driver.number);
    if (!Number.isFinite(number)) return;
    const name = [driver.givenName, driver.familyName].filter(Boolean).join(" ") || driver.code || driver.driverId || `#${number}`;
    map.set(String(number), {
      driver_number: number,
      full_name: name,
      name_acronym: driver.code || "",
      team_name: constructor.name || "",
      team_colour: "e10600",
      headshot_url: ""
    });
  }

  for (const row of standings) add(row.Driver, row.Constructors?.[0] || {});
  for (const row of latestResults) add(row.Driver, row.Constructor || {});

  return map;
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
  const stints = objectList(rawStints);
  return [...stints].reverse().find((stint) => readValue(stint?.Compound || stint?.compound || stint?.tyre_compound, "")) || stints[stints.length - 1] || {};
}

function stintCompound(stint) {
  return readValue(
    stint?.Compound ||
    stint?.compound ||
    stint?.Tyre ||
    stint?.tyre ||
    stint?.tyre_compound ||
    stint?.compound_name,
    ""
  );
}

function stintTyreAge(stint) {
  return readValue(
    stint?.TotalLaps ||
    stint?.total_laps ||
    stint?.TyreAge ||
    stint?.tyre_age ||
    stint?.tyre_age_at_start ||
    stint?.LapCount ||
    stint?.lap_count ||
    stint?.StartLaps ||
    stint?.start_laps,
    ""
  );
}

function normalizeTiming(timingData, drivers, timingAppData, carData) {
  const driverMap = new Map((drivers || []).map((d) => [String(d.driver_number), d]));
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
    const data = entry?.data?.Entries || entry?.data?.entries || entry?.data || {};
    for (const item of Array.isArray(data) ? data : Object.values(data)) {
      const cars = item?.Cars || item?.cars || {};
      for (const [num, car] of Object.entries(cars)) {
        latestCar[num] = { ...(latestCar[num] || {}), ...car };
      }
    }
  }

  const rows = Object.entries(lines).map(([num, raw]) => {
    const driver = driverMap.get(String(Number(num))) || driverMap.get(String(num)) || {};
    const stint = latestStint(appLines[num]?.Stints || appLines[num]?.stints) || appLines[num]?.Stint || appLines[num]?.stint || {};
    const channels = latestCar[num]?.Channels || latestCar[num]?.channels || {};
    const lastLap = readValue(raw?.LastLapTime, readValue(raw?.Sectors?.[2], ""));
    const interval = readValue(raw?.IntervalToPositionAhead, readValue(raw?.GapToLeader, readValue(raw?.Status, "")));
    const gapToLeader = readValue(raw?.GapToLeader, interval);

    return {
      driver_number: Number(num),
      position: readNumber(raw?.Position || raw?.position, 999),
      interval,
      gap_to_leader: gapToLeader,
      status: readValue(raw?.Status || raw?.status, ""),
      lap_duration: lastLap,
      compound: stintCompound(stint),
      tyre_age: stintTyreAge(stint),
      speed: readValue(channels?.[2] || latestCar[num]?.Speed || latestCar[num]?.speed, ""),
      n_gear: readValue(channels?.[3] || latestCar[num]?.Gear || latestCar[num]?.gear, ""),
      rpm: readValue(channels?.[0] || latestCar[num]?.Rpm || latestCar[num]?.rpm, ""),
      aero_mode: readValue(channels?.[45] || latestCar[num]?.Drs || latestCar[num]?.drs, ""),
      brake: readValue(channels?.[5] || latestCar[num]?.Brake || latestCar[num]?.brake, ""),
      sectors: raw?.Sectors || raw?.sectors || [],
      mini_sectors: normalizeMiniSectors(raw?.Sectors || raw?.sectors || []),
      driver
    };
  });

  return rows
    .filter((row) => Number.isFinite(row.position) && row.position < 999)
    .sort((a, b) => a.position - b.position || a.driver_number - b.driver_number);
}

function normalizeWeather(weatherEntries) {
  const latest = weatherEntries?.slice(-1)?.[0]?.data || null;
  if (!latest) return null;
  return {
    air_temperature: latest.AirTemp || latest.air_temperature || "",
    track_temperature: latest.TrackTemp || latest.track_temperature || "",
    humidity: latest.Humidity || latest.humidity || "",
    rainfall: latest.Rainfall || latest.rainfall || "",
    wind_speed: latest.WindSpeed || latest.wind_speed || "",
    wind_direction: latest.WindDirection || latest.wind_direction || ""
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
        date: item.Utc || item.utc || item.Date || item.date || item.Time || item.time || entry.time,
        lap: readValue(item.Lap || item.lap, ""),
        category: item.Category || item.category || item.Flag || item.flag || item.Scope || item.scope || item.Type || item.type || "Race control",
        status: item.Status || item.status || item.Mode || item.mode || "",
        racing_number: item.RacingNumber || item.racing_number || item.DriverNumber || "",
        message: item.Message || item.message || item.Text || item.text || JSON.stringify(item)
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
    total_laps: latest.TotalLaps || latest.total_laps || ""
  };
}


function normalizeTeamRadio(entries, basePath) {
  const captures = [];
  for (const entry of entries || []) {
    const data = entry?.data || {};
    const list = Array.isArray(data.Captures || data.captures)
      ? (data.Captures || data.captures)
      : Array.isArray(data.Radio || data.radio)
        ? (data.Radio || data.radio)
        : [data];
    for (const item of list) {
      captures.push({ time: entry.time, data: item });
    }
  }

  return captures.map((entry) => {
    const data = entry?.data || {};
    const path = data.Path || data.path || data.Url || data.url || data.RecordingUrl || data.recording_url || data.AudioUrl || "";
    const recordingUrl = path
      ? path.startsWith("http")
        ? path
        : endpoint(`${basePath}${String(path).replace(/^\/+/, "")}`)
      : "";

    return {
      date: entry.time || data.Utc || data.utc || data.Date || data.date || "",
      driver_number: Number(data.RacingNumber || data.driver_number || data.DriverNumber || 0),
      recording_url: recordingUrl,
      message: data.Message || data.message || data.Text || data.text || "",
      raw: data
    };
  }).filter((item) => item.recording_url || item.message).slice(-30).reverse();
}

async function fetchOpenF1TeamRadio(sessionKey) {
  if (!sessionKey) return { ok: false, status: "no_session_key", rows: [] };
  const response = await getOpenF1Json(`team_radio?session_key=${encodeURIComponent(sessionKey)}`);
  const rows = Array.isArray(response.data) ? response.data : [];
  return {
    ok: response.ok && rows.length > 0,
    status: response.status,
    auth_restricted: response.auth_restricted,
    auth_configured: response.auth_configured,
    detail: response.detail,
    rows
  };
}

function normalizeOpenF1TeamRadio(rows, drivers = []) {
  const driverMap = new Map((drivers || []).map((driver) => [String(driver.driver_number), driver]));
  return (rows || [])
    .map((row) => {
      const driver = driverMap.get(String(row.driver_number)) || {};
      return {
        date: row.date || "",
        driver_number: Number(row.driver_number || 0),
        driver_name: driver.full_name || driver.broadcast_name || "",
        recording_url: row.recording_url || "",
        source: "OpenF1",
        raw: row
      };
    })
    .filter((item) => item.recording_url)
    .sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")))
    .slice(0, 30);
}

async function fetchJolpicaFallback() {
  const endpoints = {
    currentSchedule: "/current.json",
    latestResults: "/current/last/results.json",
    driverStandings: "/current/driverStandings.json",
    constructorStandings: "/current/constructorStandings.json"
  };

  const result = {};
  await Promise.all(Object.entries(endpoints).map(async ([key, path]) => {
    try {
      const res = await fetch(`${JOLPICA_BASE}${path}`, {
        cache: "no-store",
        headers: {
          Accept: "application/json",
          "User-Agent": "pitwall-live-dashboard/1.0"
        }
      });
      const data = await res.json().catch(() => null);
      result[key] = { ok: res.ok, status: res.status, data };
    } catch (error) {
      result[key] = { ok: false, error: String(error?.message || error), data: null };
    }
  }));

  return result;
}

function normalizeJolpicaFallback(fallback) {
  const races = fallback?.latestResults?.data?.MRData?.RaceTable?.Races || [];
  const latestRace = races[0] || null;
  const results = latestRace?.Results || [];
  const driverStandings =
    fallback?.driverStandings?.data?.MRData?.StandingsTable?.StandingsLists?.[0]?.DriverStandings || [];
  const constructorStandings =
    fallback?.constructorStandings?.data?.MRData?.StandingsTable?.StandingsLists?.[0]?.ConstructorStandings || [];

  return {
    race: latestRace,
    results,
    driverStandings,
    constructorStandings
  };
}

async function fetchOpenF1Fallback() {
  const sessions = await getOpenF1Json("sessions?session_key=latest");
  const session = Array.isArray(sessions.data) ? sessions.data[0] : null;
  if (sessions.auth_restricted) {
    return {
      ok: false,
      status: "auth_required_during_live_session",
      auth_restricted: true,
      auth_configured: sessions.auth_configured,
      detail: sessions.detail,
      session: null,
      drivers: [],
      results: []
    };
  }
  if (!session?.session_key) {
    return { ok: false, sessions_status: sessions.status, session: null, drivers: [], results: [] };
  }
  await sleep(380);
  const drivers = await getOpenF1Json(`drivers?session_key=${encodeURIComponent(session.session_key)}`);
  await sleep(380);
  const results = await getOpenF1Json(`session_result?session_key=${encodeURIComponent(session.session_key)}`);
  await sleep(380);
  const pits = await getOpenF1Json(`pit?session_key=${encodeURIComponent(session.session_key)}`);
  await sleep(380);
  const stints = await getOpenF1Json(`stints?session_key=${encodeURIComponent(session.session_key)}`);
  await sleep(380);
  const teamRadio = await fetchOpenF1TeamRadio(session.session_key);
  const authRestricted = [drivers, results, pits, stints, teamRadio].some((item) => item?.auth_restricted);
  return {
    ok: sessions.ok && drivers.ok && Array.isArray(drivers.data) && !authRestricted,
    auth_restricted: authRestricted,
    auth_configured: Boolean(OPENF1_ACCESS_TOKEN || (OPENF1_USERNAME && OPENF1_PASSWORD)),
    detail: [drivers, results, pits, stints, teamRadio].find((item) => item?.auth_restricted)?.detail || "",
    session,
    drivers: Array.isArray(drivers.data) ? drivers.data : [],
    results: Array.isArray(results.data) ? results.data : [],
    pits: Array.isArray(pits.data) ? pits.data : [],
    stints: Array.isArray(stints.data) ? stints.data : [],
    team_radio: teamRadio.rows,
    status: {
      sessions: sessions.status,
      drivers: drivers.status,
      session_result: results.status,
      pit: pits.status,
      stints: stints.status,
      team_radio: teamRadio.status
    }
  };
}

function normalizeOpenF1Fallback(openf1) {
  if (!openf1?.ok) return null;
  const driverMap = new Map((openf1.drivers || []).map((driver) => [String(driver.driver_number), driver]));
  const drivers = (openf1.drivers || []).map((driver) => ({
    driver_number: Number(driver.driver_number),
    full_name: driver.full_name || `${driver.first_name || ""} ${driver.last_name || ""}`.trim(),
    name_acronym: driver.name_acronym || "",
    team_name: driver.team_name || "",
    team_colour: driver.team_colour || "",
    headshot_url: driver.headshot_url || ""
  }));
  const latestStints = new Map();
  for (const stint of openf1.stints || []) {
    const driverNumber = Number(stint.driver_number);
    if (!Number.isFinite(driverNumber)) continue;
    const current = latestStints.get(driverNumber);
    const stintNumber = Number(stint.stint_number || stint.stint || 0);
    const currentNumber = Number(current?.stint_number || current?.stint || 0);
    if (!current || stintNumber >= currentNumber) latestStints.set(driverNumber, stint);
  }
  const leaderboard = (openf1.results || []).map((row) => {
    const driver = driverMap.get(String(row.driver_number)) || {};
    const position = Number(row.position);
    const stint = latestStints.get(Number(row.driver_number)) || {};
    return {
      position: Number.isFinite(position) ? position : "",
      driver_number: Number(row.driver_number),
      driver,
      driver_name: driver.full_name || driver.broadcast_name || `#${row.driver_number}`,
      team_name: driver.team_name || "",
      gap_to_leader: row.gap_to_leader ?? "",
      interval: row.gap_to_leader ?? "",
      lap_duration: "",
      compound: stintCompound(stint),
      tyre_age: stintTyreAge(stint),
      speed: "",
      status: row.dnf ? "DNF" : row.dns ? "DNS" : row.dsq ? "DSQ" : "",
      points: row.points ?? ""
    };
  }).sort((a, b) => {
    const pa = Number(a.position || 999);
    const pb = Number(b.position || 999);
    return pa - pb;
  });
  const pits = (openf1.pits || []).map((pit) => ({
    driver_number: Number(pit.driver_number),
    lap_number: pit.lap_number,
    pit_duration: pit.pit_duration ?? pit.lane_duration ?? pit.stop_duration ?? ""
  }));
  return {
    session: {
      meeting_name: `${openf1.session.country_name || ""} ${openf1.session.session_name || ""}`.trim(),
      session_name: openf1.session.session_name || "",
      session_type: openf1.session.session_type || "",
      session_path: "",
      date_start: openf1.session.date_start || "",
      base_path: ""
    },
    drivers,
    leaderboard,
    intervals: leaderboard,
    laps: [],
    carData: [],
    weather: null,
    raceControl: [],
    lapCount: { current_lap: Math.max(0, ...leaderboard.map((row) => Number((openf1.results || []).find((item) => Number(item.driver_number) === row.driver_number)?.number_of_laps || 0))), total_laps: "" },
    trackStatus: null,
    pits,
    stints: Array.from(latestStints.entries()).map(([driverNumber, stint]) => ({
      driver_number: driverNumber,
      compound: stintCompound(stint),
      tyre_age_at_start: stintTyreAge(stint),
      raw: stint
    })),
    radio: normalizeOpenF1TeamRadio(openf1.team_radio || [], drivers)
  };
}

async function fetchFeeds(basePath, { fast = false } = {}) {
  const feeds = {};
  const feedList = fast ? FAST_FEEDS : FEEDS;
  const timeoutMs = fast ? 4200 : 7000;
  await Promise.all(feedList.map(async (feed) => {
    const url = endpoint(`${basePath}${feed}`);
    const response = await getText(url, timeoutMs);
    const zipped = feed.includes(".z.");
    const json = feed.endsWith(".json") ? decompressFormula1Payload(safeJson(response.text, response.text)) : null;
    const stream = feed.endsWith(".jsonStream") ? parseJsonStream(response.text, zipped) : [];
    feeds[feed] = { ...response, text: undefined, entries: stream, json, count: stream.length };
  }));
  return feeds;
}

export async function GET(request) {
  const rateLimit = checkRateLimit(request);
  if (rateLimit.limited) {
    return jsonNoStore({
      ok: false,
      error: "Timing endpoint rate limit exceeded.",
      retry_after_seconds: rateLimit.retryAfterSeconds,
      reason: "PitWall limits timing proxy requests to protect upstream Formula 1 and fallback data sources."
    }, {
      status: 429,
      headers: {
        "Retry-After": String(rateLimit.retryAfterSeconds)
      }
    });
  }
  const { searchParams } = new URL(request.url);
  const year = normalizedYear(searchParams.get("year") || String(new Date().getUTCFullYear()));
  if (!year) {
    return jsonNoStore({
      ok: false,
      error: "Invalid year. Choose a season between 2018 and the next available F1 season.",
      normalized: null,
      meeting_options: [],
      session_options: [],
    }, { status: 400 });
  }
  const requestedSession = normalizedSelector(searchParams.get("session"), "latest");
  const requestedMeeting = normalizedSelector(searchParams.get("meeting"), "latest");
  const fast = searchParams.get("fast") === "1" || searchParams.get("fast") === "true";

  const rootIndex = await getText(endpoint("Index.json"));
  const yearIndexResponse = await getText(endpoint(`${year}/Index.json`));
  const yearIndex = safeJson(yearIndexResponse.text, null);
  const meetings = pickMeetings(yearIndex);
  const selected = chooseSession(meetings, requestedSession, requestedMeeting);

  if (!selected) {
    const openf1Fallback = await fetchOpenF1Fallback();
    const openf1AuthReason = openf1Fallback?.auth_restricted
      ? `OpenF1 requires authentication right now: ${openf1Fallback.detail || "live-session restriction"}`
      : "";
    const timing = timingFreshness({ state: "unavailable", ended: true }, false, openf1Fallback?.ok ? "OpenF1Fallback" : "Formula1LiveTiming");
    const fallbackWarnings = [
      "No live/current F1 timing session matched the request.",
      openf1AuthReason,
    ].filter(Boolean);
    return jsonNoStore({
      ok: Boolean(openf1Fallback?.ok),
      source: openf1Fallback?.ok ? "OpenF1Fallback" : "Formula1LiveTiming",
      reason: openf1Fallback?.ok ? "No F1 live timing session found, using latest OpenF1 free historical session." : (openf1AuthReason || "No F1 live timing session found for selected year."),
      server_time: new Date().toISOString(),
      is_live: false,
      ...timing,
      auto_selected_session: null,
      session_resolution: selectionResolution(null, requestedSession, requestedMeeting, false, openf1AuthReason),
      warnings: fallbackWarnings,
      session_state: openf1Fallback?.ok ? "openf1-fallback" : "unavailable",
      refresh_after_ms: 60000,
      root_status: rootIndex.status,
      year_status: yearIndexResponse.status,
      meeting_options: meetingOptions(meetings),
      session_options: [],
      official_visual: null,
      normalized: safeNormalizedTimingPayload(normalizeOpenF1Fallback(openf1Fallback)),
      openf1_fallback: openf1Fallback,
      jolpica_fallback: await fetchJolpicaFallback()
    });
  }

  const basePath = sessionPath(selected.meeting, selected.session);
  const feeds = basePath ? await fetchFeeds(basePath, { fast }) : {};
  let jolpicaFallback = null;
  let fallbackDriverMap = new Map();
  const keyframeDrivers = normalizeDriverKeyframe(feeds["DriverList.json"]?.json || {});
  const streamDrivers = normalizeDrivers(feeds["DriverList.jsonStream"]?.entries || []);
  let drivers = mergeDriverSources(keyframeDrivers, new Map(streamDrivers.map((driver) => [String(driver.driver_number), driver])));
  if (!drivers.length) {
    jolpicaFallback = await fetchJolpicaFallback();
    fallbackDriverMap = normalizeJolpicaDrivers(jolpicaFallback);
    drivers = mergeDriverSources(drivers, fallbackDriverMap);
  }
  const leaderboard = normalizeTiming(
    entriesWithKeyframe(feeds["TimingData.jsonStream"]?.entries || [], feeds["TimingData.json"]?.json),
    drivers,
    entriesWithKeyframe(feeds["TimingAppData.jsonStream"]?.entries || [], feeds["TimingAppData.json"]?.json),
    entriesWithKeyframe(feeds["CarData.z.jsonStream"]?.entries || [], feeds["CarData.z.json"]?.json)
  );

  const normalized = {
    session: {
      meeting_name: selected.meeting?.Name || selected.meeting?.name || "",
      meeting_key: meetingKey(selected.meeting),
      meeting_path: selected.meeting?.Path || selected.meeting?.path || "",
      session_name: selected.session?.Name || selected.session?.name || "",
      session_type: selected.session?.Type || selected.session?.type || "",
      session_path: selected.session?.Path || selected.session?.path || "",
      date_start: selected.session?.StartDate || selected.session?.startDate || "",
      base_path: basePath
    },
    drivers,
    leaderboard,
    intervals: leaderboard,
    laps: leaderboard.map((row) => ({ driver_number: row.driver_number, lap_duration: row.lap_duration })),
    stints: leaderboard.map((row) => ({ driver_number: row.driver_number, compound: row.compound, tyre_age_at_start: row.tyre_age })),
    carData: leaderboard.map((row) => ({ driver_number: row.driver_number, speed: row.speed, n_gear: row.n_gear, rpm: row.rpm, aero_mode: row.aero_mode, brake: row.brake })),
    weather: normalizeWeather(entriesWithKeyframe(feeds["WeatherData.jsonStream"]?.entries || [], feeds["WeatherData.json"]?.json)),
    raceControl: normalizeRaceControl(entriesWithKeyframe(feeds["RaceControlMessages.jsonStream"]?.entries || [], feeds["RaceControlMessages.json"]?.json)),
    lapCount: normalizeLapCount(entriesWithKeyframe(feeds["LapCount.jsonStream"]?.entries || [], feeds["LapCount.json"]?.json)),
    trackStatus: feeds["TrackStatus.jsonStream"]?.entries?.slice(-1)?.[0]?.data || feeds["TrackStatus.json"]?.json || null,
    pits: [],
    radio: normalizeTeamRadio(entriesWithKeyframe(feeds["TeamRadio.jsonStream"]?.entries || [], feeds["TeamRadio.json"]?.json), basePath)
  };
  const openf1Radio = normalized.radio.length
    ? { ok: false, status: "formula1_team_radio_used", rows: [] }
    : await fetchOpenF1TeamRadio(selected.session?.Key || selected.session?.key || selected.session?.session_key);
  if (!normalized.radio.length && openf1Radio.rows.length) {
    normalized.radio = normalizeOpenF1TeamRadio(openf1Radio.rows, drivers);
  }

  const hasUsefulF1Data = leaderboard.length > 0 || normalized.weather || normalized.raceControl.length > 0;
  const lifecycle = sessionLifecycle(selected, hasUsefulF1Data);
  if (!hasUsefulF1Data && !jolpicaFallback) {
    jolpicaFallback = await fetchJolpicaFallback();
  }
  const openf1Fallback = hasUsefulF1Data || fast ? null : await fetchOpenF1Fallback();
  const normalizedOpenF1 = normalizeOpenF1Fallback(openf1Fallback);
  const normalizedJolpica = normalizeJolpicaFallback(jolpicaFallback);
  const outputNormalized = safeNormalizedTimingPayload(hasUsefulF1Data ? normalized : normalizedOpenF1 || normalizedJolpica || normalized);
  const outputOk = hasUsefulF1Data || Boolean(normalizedOpenF1?.leaderboard?.length) || Boolean(jolpicaFallback?.latestResults?.ok);
  const officialVisual = await officialRaceVisual(year, selected.meeting);
  const source = hasUsefulF1Data ? "Formula1LiveTiming" : normalizedOpenF1 ? "OpenF1Fallback" : "JolpicaFallback";
  const timing = timingFreshness(lifecycle, hasUsefulF1Data, source);
  const openf1AuthReason = openf1Fallback?.auth_restricted
    ? `OpenF1 requires authentication right now: ${openf1Fallback.detail || "live-session restriction"}`
    : "";
  const warnings = [
    !basePath ? "Selected session is missing a Formula 1 timing base path." : "",
    !hasUsefulF1Data ? "Formula 1 timing did not return usable live rows for this session." : "",
    openf1AuthReason,
    !outputOk ? "No live timing, OpenF1 fallback, or Jolpica fallback data was usable." : "",
  ].filter(Boolean);

  return jsonNoStore({
    ok: outputOk,
    source,
    source_note: hasUsefulF1Data
      ? "Primary source uses Formula 1 livetiming static feeds."
      : normalizedOpenF1
        ? "Formula 1 live timing did not return useful data, so this response uses the latest OpenF1 free historical session."
        : openf1AuthReason
          ? `${openf1AuthReason}. Showing Jolpica fallback data instead.`
          : "Formula 1 live timing did not return useful data, so this response shows the latest public Jolpica event data.",
    base_path: basePath,
    server_time: new Date().toISOString(),
    is_live: timing.is_genuinely_live,
    ...timing,
    auto_selected_session: selectionResolution(selected, requestedSession, requestedMeeting, hasUsefulF1Data),
    session_resolution: selectionResolution(selected, requestedSession, requestedMeeting, hasUsefulF1Data),
    warnings,
    session_state: hasUsefulF1Data ? lifecycle.state : normalizedOpenF1 ? "openf1-fallback" : "fallback",
    refresh_after_ms: hasUsefulF1Data ? lifecycle.refresh_after_ms : 60000,
    fast_sync: fast,
    selected,
    meeting_options: meetingOptions(meetings),
    session_options: sessionOptions(selected.meeting),
    official_visual: officialVisual,
    feed_status: {
      ...Object.fromEntries(Object.entries(feeds).map(([key, value]) => [key, { ok: value.ok, status: value.status, count: value.count || (value.json ? 1 : 0) }])),
      OpenF1TeamRadio: { ok: openf1Radio.ok, status: openf1Radio.status, count: openf1Radio.rows.length },
      OpenF1: openf1Fallback ? {
        ok: openf1Fallback.ok,
        status: openf1Fallback.status,
        auth_restricted: Boolean(openf1Fallback.auth_restricted),
        auth_configured: Boolean(openf1Fallback.auth_configured),
        detail: openf1Fallback.auth_restricted ? openf1Fallback.detail : ""
      } : { ok: false, status: "not_used_primary_f1_available" }
    },
    normalized: outputNormalized,
    openf1_fallback: openf1Fallback,
    jolpica_fallback: hasUsefulF1Data ? null : jolpicaFallback,
    normalized_fallback: hasUsefulF1Data ? null : normalizedJolpica
  });
}
