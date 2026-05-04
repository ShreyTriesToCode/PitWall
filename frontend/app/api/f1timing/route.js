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

function driverDisplay(raw) {
  return raw?.FullName || raw?.full_name || raw?.BroadcastName || raw?.Tla || raw?.RacingNumber || "-";
}

function normalizeDrivers(driverList) {
  const lines = latestByMerge(driverList)?.Drivers || latestByMerge(driverList) || {};
  return Object.entries(lines).map(([num, raw]) => ({
    driver_number: Number(raw?.RacingNumber || num),
    full_name: driverDisplay(raw),
    name_acronym: raw?.Tla || raw?.tla || "",
    team_name: raw?.TeamName || raw?.team_name || "",
    team_colour: raw?.TeamColour || raw?.team_colour || "e10600",
    headshot_url: raw?.HeadshotUrl || ""
  }));
}

function normalizeTiming(timingData, drivers, timingAppData, carData) {
  const driverMap = new Map(drivers.map((d) => [String(d.driver_number), d]));
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
      for (const [num, car] of Object.entries(cars)) latestCar[num] = { ...(latestCar[num] || {}), ...car };
    }
  }

  return Object.entries(lines).map(([num, raw]) => {
    const driver = driverMap.get(String(num)) || {};
    const stint = appLines[num]?.Stints ? Object.values(appLines[num].Stints).slice(-1)[0] : appLines[num]?.Stint || {};
    const lastLap = raw?.LastLapTime?.Value || raw?.LastLapTime || raw?.Sectors?.[2]?.Value || "";
    return {
      driver_number: Number(num),
      position: Number(raw?.Position || raw?.position || 999),
      interval: raw?.IntervalToPositionAhead?.Value || raw?.IntervalToPositionAhead || raw?.GapToLeader || raw?.GapToLeader?.Value || "",
      gap_to_leader: raw?.GapToLeader?.Value || raw?.GapToLeader || "",
      lap_duration: lastLap,
      compound: stint?.Compound || stint?.compound || "",
      tyre_age: stint?.TotalLaps || stint?.StartLaps || "",
      speed: latestCar[num]?.Channels?.[2] || latestCar[num]?.Speed || "",
      n_gear: latestCar[num]?.Channels?.[3] || latestCar[num]?.Gear || "",
      rpm: latestCar[num]?.Channels?.[0] || latestCar[num]?.Rpm || "",
      drs: latestCar[num]?.Channels?.[45] || latestCar[num]?.Drs || "",
      brake: latestCar[num]?.Channels?.[5] || latestCar[num]?.Brake || "",
      driver
    };
  }).sort((a, b) => a.position - b.position || a.driver_number - b.driver_number);
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
  const drivers = normalizeDrivers(feeds["DriverList.jsonStream"]?.entries || []);
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

  const hasUsefulF1Data = drivers.length > 0 || leaderboard.length > 0 || normalized.weather || normalized.raceControl.length > 0;

  const jolpicaFallback = hasUsefulF1Data ? null : await fetchJolpicaFallback();

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
    jolpica_fallback: jolpicaFallback,
    normalized_fallback: jolpicaFallback ? normalizeJolpicaFallback(jolpicaFallback) : null
  }, { headers: { "Cache-Control": "no-store" } });
}
