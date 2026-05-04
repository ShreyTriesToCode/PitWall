export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { inflateRawSync } from "node:zlib";

const F1_BASE = "https://livetiming.formula1.com/static";
const JOLPICA_BASE = "https://api.jolpi.ca/ergast/f1";

const FEEDS = [
  "SessionInfo.jsonStream",
  "DriverList.jsonStream",
  "TimingData.jsonStream",
  "TimingAppData.jsonStream",
  "LapCount.jsonStream",
  "TrackStatus.jsonStream",
  "SessionStatus.jsonStream",
  "WeatherData.jsonStream",
  "RaceControlMessages.jsonStream",
  "PitLaneTimeCollection.jsonStream",
  "TeamRadio.jsonStream",
  "CarData.z.jsonStream",
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

function normalizeDrivers(driverList) {
  const merged = latestByMerge(driverList);
  const lines = merged?.Drivers || merged?.drivers || merged || {};

  return Object.entries(lines)
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
  return (entries || []).map((entry) => ({
    date: entry.time,
    category: entry.data?.Category || entry.data?.Flag || entry.data?.Scope || "Message",
    message: entry.data?.Message || entry.data?.message || JSON.stringify(entry.data)
  })).slice(-30).reverse();
}

function normalizeLapCount(entries) {
  const latest = entries?.slice(-1)?.[0]?.data || {};
  return {
    current_lap: latest.CurrentLap || latest.current_lap || "",
    total_laps: latest.TotalLaps || latest.total_laps || ""
  };
}


function normalizeTeamRadio(entries, basePath) {
  return (entries || []).map((entry) => {
    const data = entry?.data || {};
    const path = data.Path || data.path || data.Url || data.url || data.RecordingUrl || data.recording_url || "";
    const recordingUrl = path
      ? path.startsWith("http")
        ? path
        : endpoint(`${basePath}${String(path).replace(/^\/+/, "")}`)
      : "";

    return {
      date: entry.time || data.Utc || data.utc || data.Date || data.date || "",
      driver_number: Number(data.RacingNumber || data.driver_number || data.DriverNumber || 0),
      recording_url: recordingUrl,
      message: data.Message || data.message || "",
      raw: data
    };
  }).filter((item) => item.recording_url || item.message).slice(-30).reverse();
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

async function fetchFeeds(basePath) {
  const feeds = {};
  await Promise.all(FEEDS.map(async (feed) => {
    const url = endpoint(`${basePath}${feed}`);
    const response = await getText(url, 12000);
    const zipped = feed.includes(".z.");
    const json = feed.endsWith(".json") ? safeJson(response.text, null) : null;
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
    return Response.json({
      ok: false,
      source: "Formula1LiveTiming",
      reason: "No F1 live timing session found for selected year.",
      root_status: rootIndex.status,
      year_status: yearIndexResponse.status,
      jolpica_fallback: await fetchJolpicaFallback()
    }, { headers: { "Cache-Control": "no-store" } });
  }

  const basePath = sessionPath(selected.meeting, selected.session);
  const feeds = basePath ? await fetchFeeds(basePath) : {};
  const jolpicaFallback = await fetchJolpicaFallback();
  const fallbackDriverMap = normalizeJolpicaDrivers(jolpicaFallback);
  const drivers = mergeDriverSources(
    normalizeDrivers(feeds["DriverList.jsonStream"]?.entries || []),
    fallbackDriverMap
  );
  const leaderboard = normalizeTiming(
    feeds["TimingData.jsonStream"]?.entries || [],
    drivers,
    feeds["TimingAppData.jsonStream"]?.entries || [],
    feeds["CarData.z.jsonStream"]?.entries || []
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
    weather: normalizeWeather(feeds["WeatherData.jsonStream"]?.entries || []),
    raceControl: normalizeRaceControl(feeds["RaceControlMessages.jsonStream"]?.entries || []),
    lapCount: normalizeLapCount(feeds["LapCount.jsonStream"]?.entries || []),
    trackStatus: feeds["TrackStatus.jsonStream"]?.entries?.slice(-1)?.[0]?.data || null,
    pits: [],
    radio: normalizeTeamRadio(feeds["TeamRadio.jsonStream"]?.entries || [], basePath)
  };

  const hasUsefulF1Data = leaderboard.length > 0 || normalized.weather || normalized.raceControl.length > 0;

  return Response.json({
    ok: hasUsefulF1Data || Boolean(jolpicaFallback?.latestResults?.ok),
    source: hasUsefulF1Data ? "Formula1LiveTiming" : "JolpicaFallback",
    source_note: hasUsefulF1Data
      ? "Primary source uses Formula 1 livetiming static feeds."
      : "Formula 1 live timing did not return useful data, so this response shows the latest public Jolpica event data.",
    base_path: basePath,
    selected,
    feed_status: Object.fromEntries(Object.entries(feeds).map(([key, value]) => [key, { ok: value.ok, status: value.status, count: value.count || (value.json ? 1 : 0) }])),
    normalized,
    jolpica_fallback: hasUsefulF1Data ? null : jolpicaFallback,
    normalized_fallback: hasUsefulF1Data ? null : normalizeJolpicaFallback(jolpicaFallback)
  }, { headers: { "Cache-Control": "no-store" } });
}
