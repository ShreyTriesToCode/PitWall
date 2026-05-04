export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { inflateRawSync } from "node:zlib";

const F1_BASE = "https://livetiming.formula1.com/static";
const JOLPICA_BASE = "https://api.jolpi.ca/ergast/f1";
const OPENF1_BASE = "https://api.openf1.org/v1";

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

function endpoint(path) {
  return `${F1_BASE}/${String(path || "").replace(/^\/+/, "")}`;
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

async function getJson(url, timeoutMs = 12000) {
  const response = await getText(url, timeoutMs);
  return { ...response, data: safeJson(response.text, null), text: undefined };
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
  const postWindow = 3 * 60 * 60 * 1000;

  if (!start) {
    return { state: hasUsefulF1Data ? "active" : "unknown", is_live: Boolean(hasUsefulF1Data), refresh_after_ms: hasUsefulF1Data ? 7000 : 60000 };
  }
  if (now < start - preWindow) {
    return { state: "upcoming", is_live: false, refresh_after_ms: 60000 };
  }
  if (now < start) {
    return { state: "pre-session", is_live: false, refresh_after_ms: 15000 };
  }
  if (now <= end + postWindow) {
    return { state: "active", is_live: true, refresh_after_ms: 5000 };
  }
  return { state: "archive", is_live: false, refresh_after_ms: 90000 };
}

function normalizeSessionName(name) {
  return String(name || "").replace(/_/g, " ").trim();
}

function isRealSession(session) {
  const name = normalizeSessionName(session?.Name || session?.name || session?.SessionName || session?.session_name).toLowerCase();
  return Boolean(name) && !name.includes("test");
}

function chooseSession(meetings, requestedSession) {
  const sessions = [];
  for (const meeting of meetings) {
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

  // Prefer a session that is currently active or about to start.
  const active = sessions.find((item) => {
    if (!item.start) return false;
    const start = item.start.getTime();
    const end = item.end?.getTime() || start + 3 * 60 * 60 * 1000;
    return now >= start - preWindow && now <= end + postWindow;
  });
  if (active) return active;

  // If nothing is live, show the latest completed/started session.
  const completedOrStarted = sessions.filter((item) => item.start && item.start.getTime() <= now);
  if (completedOrStarted.length) return completedOrStarted[completedOrStarted.length - 1];

  // Before the season/weekend starts, show the next upcoming session.
  return sessions[0] || null;
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

function normalizeTiming(timingData, drivers, timingAppData, carData) {
  const driverMap = new Map((drivers || []).map((d) => [String(d.driver_number), d]));
  const lines = {};
  const appLines = {};

  for (const entry of timingData || []) {
    const data = entry?.data?.Lines || entry?.data?.lines || {};
    for (const [num, update] of Object.entries(data)) {
      lines[num] = { ...(lines[num] || {}), ...update };
    }
  }

  for (const entry of timingAppData || []) {
    const data = entry?.data?.Lines || entry?.data?.lines || {};
    for (const [num, update] of Object.entries(data)) {
      appLines[num] = { ...(appLines[num] || {}), ...update };
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
    const stint = lastObject(appLines[num]?.Stints || appLines[num]?.stints) || appLines[num]?.Stint || appLines[num]?.stint || {};
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
      compound: readValue(stint?.Compound || stint?.compound, ""),
      tyre_age: readValue(stint?.TotalLaps || stint?.StartLaps || stint?.LapCount || stint?.tyre_age, ""),
      speed: readValue(channels?.[2] || latestCar[num]?.Speed || latestCar[num]?.speed, ""),
      n_gear: readValue(channels?.[3] || latestCar[num]?.Gear || latestCar[num]?.gear, ""),
      rpm: readValue(channels?.[0] || latestCar[num]?.Rpm || latestCar[num]?.rpm, ""),
      drs: readValue(channels?.[45] || latestCar[num]?.Drs || latestCar[num]?.drs, ""),
      brake: readValue(channels?.[5] || latestCar[num]?.Brake || latestCar[num]?.brake, ""),
      sectors: raw?.Sectors || raw?.sectors || [],
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
  const response = await getJson(`${OPENF1_BASE}/team_radio?session_key=${encodeURIComponent(sessionKey)}`);
  const rows = Array.isArray(response.data) ? response.data : [];
  return {
    ok: response.ok && rows.length > 0,
    status: response.status,
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
          "User-Agent": "f1-race-intel-live-dashboard/1.0"
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
  const sessions = await getJson(`${OPENF1_BASE}/sessions?session_key=latest`);
  const session = Array.isArray(sessions.data) ? sessions.data[0] : null;
  if (!session?.session_key) {
    return { ok: false, sessions_status: sessions.status, session: null, drivers: [], results: [] };
  }
  await sleep(380);
  const drivers = await getJson(`${OPENF1_BASE}/drivers?session_key=${encodeURIComponent(session.session_key)}`);
  await sleep(380);
  const results = await getJson(`${OPENF1_BASE}/session_result?session_key=${encodeURIComponent(session.session_key)}`);
  await sleep(380);
  const pits = await getJson(`${OPENF1_BASE}/pit?session_key=${encodeURIComponent(session.session_key)}`);
  await sleep(380);
  const teamRadio = await fetchOpenF1TeamRadio(session.session_key);
  return {
    ok: sessions.ok && drivers.ok && Array.isArray(drivers.data),
    session,
    drivers: Array.isArray(drivers.data) ? drivers.data : [],
    results: Array.isArray(results.data) ? results.data : [],
    pits: Array.isArray(pits.data) ? pits.data : [],
    team_radio: teamRadio.rows,
    status: {
      sessions: sessions.status,
      drivers: drivers.status,
      session_result: results.status,
      pit: pits.status,
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
  const leaderboard = (openf1.results || []).map((row) => {
    const driver = driverMap.get(String(row.driver_number)) || {};
    const position = Number(row.position);
    return {
      position: Number.isFinite(position) ? position : "",
      driver_number: Number(row.driver_number),
      driver,
      driver_name: driver.full_name || driver.broadcast_name || `#${row.driver_number}`,
      team_name: driver.team_name || "",
      gap_to_leader: row.gap_to_leader ?? "",
      interval: row.gap_to_leader ?? "",
      lap_duration: "",
      compound: "",
      tyre_age: "",
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
    stints: [],
    carData: [],
    weather: null,
    raceControl: [],
    lapCount: { current_lap: Math.max(0, ...leaderboard.map((row) => Number((openf1.results || []).find((item) => Number(item.driver_number) === row.driver_number)?.number_of_laps || 0))), total_laps: "" },
    trackStatus: null,
    pits,
    radio: normalizeOpenF1TeamRadio(openf1.team_radio || [], drivers)
  };
}

async function fetchFeeds(basePath) {
  const feeds = {};
  await Promise.all(FEEDS.map(async (feed) => {
    const url = endpoint(`${basePath}${feed}`);
    const response = await getText(url, 12000);
    const zipped = feed.includes(".z.");
    const json = feed.endsWith(".json") ? decompressFormula1Payload(safeJson(response.text, response.text)) : null;
    const stream = feed.endsWith(".jsonStream") ? parseJsonStream(response.text, zipped) : [];
    feeds[feed] = { ...response, text: undefined, entries: stream, json, count: stream.length };
  }));
  return feeds;
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const year = searchParams.get("year") || String(new Date().getUTCFullYear());
  const requestedSession = searchParams.get("session") || "latest";

  const rootIndex = await getText(endpoint("Index.json"));
  const yearIndexResponse = await getText(endpoint(`${year}/Index.json`));
  const yearIndex = safeJson(yearIndexResponse.text, null);
  const meetings = pickMeetings(yearIndex);
  const selected = chooseSession(meetings, requestedSession);

  if (!selected) {
    const openf1Fallback = await fetchOpenF1Fallback();
    return Response.json({
      ok: Boolean(openf1Fallback?.ok),
      source: openf1Fallback?.ok ? "OpenF1Fallback" : "Formula1LiveTiming",
      reason: openf1Fallback?.ok ? "No F1 live timing session found, using latest OpenF1 free historical session." : "No F1 live timing session found for selected year.",
      server_time: new Date().toISOString(),
      is_live: false,
      session_state: openf1Fallback?.ok ? "openf1-fallback" : "unavailable",
      refresh_after_ms: 60000,
      root_status: rootIndex.status,
      year_status: yearIndexResponse.status,
      normalized: normalizeOpenF1Fallback(openf1Fallback),
      openf1_fallback: openf1Fallback,
      jolpica_fallback: await fetchJolpicaFallback()
    }, { headers: { "Cache-Control": "no-store" } });
  }

  const basePath = sessionPath(selected.meeting, selected.session);
  const feeds = basePath ? await fetchFeeds(basePath) : {};
  const jolpicaFallback = await fetchJolpicaFallback();
  const fallbackDriverMap = normalizeJolpicaDrivers(jolpicaFallback);
  const keyframeDrivers = normalizeDriverKeyframe(feeds["DriverList.json"]?.json || {});
  const streamDrivers = normalizeDrivers(feeds["DriverList.jsonStream"]?.entries || []);
  const drivers = mergeDriverSources(
    mergeDriverSources(keyframeDrivers, new Map(streamDrivers.map((driver) => [String(driver.driver_number), driver]))),
    fallbackDriverMap
  );
  const leaderboard = normalizeTiming(
    entriesWithKeyframe(feeds["TimingData.jsonStream"]?.entries || [], feeds["TimingData.json"]?.json),
    drivers,
    entriesWithKeyframe(feeds["TimingAppData.jsonStream"]?.entries || [], feeds["TimingAppData.json"]?.json),
    entriesWithKeyframe(feeds["CarData.z.jsonStream"]?.entries || [], feeds["CarData.z.json"]?.json)
  );

  const normalized = {
    session: {
      meeting_name: selected.meeting?.Name || selected.meeting?.name || "",
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
    carData: leaderboard.map((row) => ({ driver_number: row.driver_number, speed: row.speed, n_gear: row.n_gear, rpm: row.rpm, drs: row.drs, brake: row.brake })),
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
  const openf1Fallback = hasUsefulF1Data ? null : await fetchOpenF1Fallback();
  const normalizedOpenF1 = normalizeOpenF1Fallback(openf1Fallback);
  const outputNormalized = hasUsefulF1Data ? normalized : normalizedOpenF1 || normalized;
  const outputOk = hasUsefulF1Data || Boolean(normalizedOpenF1?.leaderboard?.length) || Boolean(jolpicaFallback?.latestResults?.ok);

  return Response.json({
    ok: outputOk,
    source: hasUsefulF1Data ? "Formula1LiveTiming" : normalizedOpenF1 ? "OpenF1Fallback" : "JolpicaFallback",
    source_note: hasUsefulF1Data
      ? "Primary source uses Formula 1 livetiming static feeds."
      : normalizedOpenF1
        ? "Formula 1 live timing did not return useful data, so this response uses the latest OpenF1 free historical session."
        : "Formula 1 live timing did not return useful data, so this response shows the latest public Jolpica event data.",
    base_path: basePath,
    server_time: new Date().toISOString(),
    is_live: lifecycle.is_live && hasUsefulF1Data,
    session_state: hasUsefulF1Data ? lifecycle.state : normalizedOpenF1 ? "openf1-fallback" : "fallback",
    refresh_after_ms: hasUsefulF1Data ? lifecycle.refresh_after_ms : 60000,
    selected,
    feed_status: {
      ...Object.fromEntries(Object.entries(feeds).map(([key, value]) => [key, { ok: value.ok, status: value.status, count: value.count || (value.json ? 1 : 0) }])),
      OpenF1TeamRadio: { ok: openf1Radio.ok, status: openf1Radio.status, count: openf1Radio.rows.length },
      OpenF1: openf1Fallback ? { ok: openf1Fallback.ok, status: openf1Fallback.status } : { ok: false, status: "not_used_primary_f1_available" }
    },
    normalized: outputNormalized,
    openf1_fallback: openf1Fallback,
    jolpica_fallback: hasUsefulF1Data ? null : jolpicaFallback,
    normalized_fallback: hasUsefulF1Data ? null : normalizeJolpicaFallback(jolpicaFallback)
  }, { headers: { "Cache-Control": "no-store" } });
}
