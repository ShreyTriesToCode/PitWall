"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AudioLines,
  BadgeInfo,
  Car,
  CheckCircle2,
  ChevronRight,
  CloudRain,
  Eye,
  EyeOff,
  Flag,
  Gauge,
  MapPinned,
  Pause,
  Play,
  Radio,
  ExternalLink,
  RefreshCcw,
  Search,
  Settings2,
  ShieldAlert,
  Timer,
  Trophy,
  Waves
} from "lucide-react";
import { AppShell } from "../components/PitWallComponents";

const DEFAULT_SETTINGS = {
  leaderboard: true,
  tyres: true,
  sectors: true,
  raceControl: true,
  weather: true,
  trackStatus: true,
  carMetrics: true,
  teamRadio: true,
  fallbackResults: true,
  oled: false,
  safetyCarColors: true,
  metric: "kmh",
  delay: 0
};

const NAV_ITEMS = [
  ["leaderboard", "Leaderboard"],
  ["tyres", "Tyres"],
  ["sectors", "Sectors"],
  ["weather", "Weather"],
  ["race-control", "Race control"],
  ["team-radio", "Team radio"]
];

function cx(...parts) {
  return parts.filter(Boolean).join(" ");
}

function primitive(value) {
  if (value === null || value === undefined || value === "") return null;

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
      null
    );
  }

  return null;
}

function fmt(value, fallback = "-") {
  const clean = primitive(value);
  if (clean === null || clean === undefined || clean === "") return fallback;
  return String(clean);
}

function time(value) {
  const date = new Date(value || "");
  if (Number.isNaN(date.getTime())) return fmt(value);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function dateTime(value) {
  const date = new Date(value || "");
  if (Number.isNaN(date.getTime())) return fmt(value);
  return date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function color(teamColour) {
  const raw = String(teamColour || "").replace("#", "").trim();
  return /^[0-9a-fA-F]{6}$/.test(raw) ? `#${raw}` : "#e10600";
}

function driverName(row) {
  const driver = row?.driver || {};
  const fullName =
    row?.name ||
    driver.full_name ||
    driver.FullName ||
    driver.BroadcastName ||
    driver.broadcast_name ||
    [driver.first_name || driver.givenName, driver.last_name || driver.familyName].filter(Boolean).join(" ") ||
    driver.name_acronym ||
    driver.Tla ||
    driver.code;

  if (fullName) return fullName;
  if (row?.driver_number) return `#${row.driver_number}`;
  return "-";
}

function speed(value, metric) {
  const clean = primitive(value);
  if (clean === null || clean === undefined || clean === "") return "-";

  const n = Number(clean);
  if (!Number.isFinite(n) || n <= 0) return fmt(clean);
  if (metric === "mph") return `${Math.round(n * 0.621371)} mph`;
  return `${Math.round(n)} km/h`;
}

function gap(row) {
  return fmt(row?.interval ?? row?.gap_to_leader ?? row?.status);
}

function raceControlTone(message) {
  const text = `${message?.category || ""} ${message?.status || ""} ${message?.message || ""}`.toLowerCase();
  if (text.includes("red")) return "red";
  if (text.includes("safety") || text.includes("vsc")) return "safety";
  if (text.includes("yellow")) return "yellow";
  if (text.includes("green") || text.includes("clear")) return "green";
  if (text.includes("investig") || text.includes("noted") || text.includes("penalty")) return "warning";
  return "";
}

function normalizeJolpicaFallback(fallback) {
  if (!fallback) return null;

  if (Array.isArray(fallback.results)) {
    const race = fallback.race || {};
    const leaderboard = fallback.results.map((result, index) => {
      const driver = result.Driver || {};
      const constructor = result.Constructor || {};
      const name = [driver.givenName, driver.familyName].filter(Boolean).join(" ") || driver.code || driver.driverId || "-";
      return {
        driver_number: Number(result.number || index + 1),
        position: Number(result.position || index + 1),
        name,
        team: constructor.name || "",
        driver: {
          driver_number: Number(result.number || index + 1),
          full_name: name,
          name_acronym: driver.code || "",
          team_name: constructor.name || "",
          team_colour: "e10600"
        },
        interval: result.Time?.time || result.status || "",
        gap_to_leader: result.Time?.time || result.status || "",
        lap_duration: "",
        compound: "",
        tyre_age: "",
        speed: "",
        n_gear: "",
        rpm: "",
        aero_mode: "",
        brake: "",
        sectors: []
      };
    });

    return {
      session: {
        meeting_name: race.raceName || "Latest completed Grand Prix",
        session_name: "Latest completed race",
        session_type: "Race result",
        date_start: [race.date, race.time].filter(Boolean).join(" ")
      },
      drivers: leaderboard.map((row) => row.driver),
      leaderboard,
      intervals: leaderboard,
      laps: leaderboard,
      stints: [],
      pits: [],
      raceControl: [],
      weather: null,
      carData: leaderboard,
      radio: [],
      trackStatus: null,
      lapCount: {},
      source: "Jolpica latest completed event"
    };
  }

  return null;
}

async function fetchF1Timing(signal, controls = {}) {
  const url = new URL("/api/f1timing", window.location.origin);
  url.searchParams.set("year", String(controls.year || new Date().getUTCFullYear()));
  url.searchParams.set("meeting", String(controls.meeting || "latest"));
  url.searchParams.set("session", String(controls.session || "latest"));
  if (controls.fast) url.searchParams.set("fast", "1");
  const res = await fetch(url.toString(), { cache: "no-store", signal });
  const payload = await res.json().catch(() => null);
  if (!res.ok) throw new Error(payload?.error || `Live timing API returned HTTP ${res.status}`);
  return payload;
}

function f1TimingStreamUrl(controls = {}) {
  const url = new URL("/api/f1timing/stream", window.location.origin);
  url.searchParams.set("year", String(controls.year || new Date().getUTCFullYear()));
  url.searchParams.set("meeting", String(controls.meeting || "latest"));
  url.searchParams.set("session", String(controls.session || "latest"));
  return url.toString();
}

function validateLiveControls(controls = {}) {
  const year = Number(String(controls.year || "").trim());
  const current = new Date().getUTCFullYear();
  if (!Number.isInteger(year) || year < 2018 || year > Math.max(2030, current + 1)) {
    return "Choose a valid F1 timing year between 2018 and the next listed season.";
  }
  if (String(controls.meeting || "").length > 120 || String(controls.session || "").length > 120) {
    return "The selected race or session value is too long. Choose an option from the list.";
  }
  return "";
}

function sanitizedLiveControls(controls = {}) {
  return {
    year: Number(String(controls.year || new Date().getUTCFullYear()).trim()),
    meeting: String(controls.meeting || "latest").trim() || "latest",
    session: String(controls.session || "latest").trim() || "latest",
  };
}

function useSettings() {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("f1-live-settings");
      if (stored) setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(stored) });
    } catch {}
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("f1-live-settings", JSON.stringify(settings));
    } catch {}
  }, [settings]);

  function patch(update) {
    setSettings((prev) => ({ ...prev, ...update }));
  }

  return [settings, patch];
}

function SettingsPanel({ settings, patch }) {
  const [open, setOpen] = useState(false);
  const toggles = [
    ["leaderboard", "Show leaderboard"],
    ["tyres", "Show tyres and stints"],
    ["sectors", "Show sectors/mini-sector style data"],
    ["weather", "Show weather"],
    ["raceControl", "Show race control"],
    ["trackStatus", "Show track status"],
    ["carMetrics", "Show car metrics if available"],
    ["teamRadio", "Show team radio"],
    ["fallbackResults", "Show fallback results"],
    ["oled", "OLED mode"],
    ["safetyCarColors", "Use safety car colors"]
  ];

  return (
    <div className="dash-settings">
      <button className="dash-btn" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="live-settings-panel">
        <Settings2 size={16} /> Settings
      </button>

      {open && (
        <div className="dash-settings-panel" id="live-settings-panel">
          <div className="dash-field">
            <label>Delay</label>
            <input
              type="number"
              min="0"
              value={settings.delay}
              onChange={(event) => patch({ delay: Math.max(0, Number(event.target.value) || 0) })}
            />
            <span>seconds</span>
          </div>

          <div className="dash-field">
            <label>Speed</label>
            <select value={settings.metric} onChange={(event) => patch({ metric: event.target.value })}>
              <option value="kmh">km/h</option>
              <option value="mph">mp/h</option>
            </select>
          </div>

          {toggles.map(([key, label]) => (
            <label className="dash-toggle" key={key}>
              <input
                type="checkbox"
                checked={Boolean(settings[key])}
                onChange={(event) => patch({ [key]: event.target.checked })}
              />
              <span>{label}</span>
              {settings[key] ? <Eye size={14} /> : <EyeOff size={14} />}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusPill({ payload, normalized }) {
  const live = Boolean(payload?.is_genuinely_live);
  const sourceOk = payload?.source === "Formula1LiveTiming" && payload?.ok;
  const state = String(payload?.session_state || "").replace("-", " ");
  const mode = String(payload?.timing_mode || (live ? "live" : sourceOk ? state : "archive")).replace("-", " ");
  return (
    <div className={cx("dash-status-pill", live ? "live" : sourceOk ? "synced" : "fallback")}>
      <span>{live ? "Live timing" : mode || "Timing data"}</span>
      <strong>{normalized?.source || payload?.source || "Loading"}</strong>
    </div>
  );
}

function Card({ id, title, icon, show = true, children, empty }) {
  if (!show) return null;
  return (
    <section className="dash-card" id={id}>
      <div className="dash-card-head">
        <h2>{icon}{title}</h2>
      </div>
      {empty ? <p className="dash-empty">{empty}</p> : children}
    </section>
  );
}

function MiniSectors({ row }) {
  const values = Array.isArray(row?.mini_sectors) ? row.mini_sectors.slice(0, 36) : [];
  if (!values.length) return <span className="mini-sector-missing">No mini-sector feed</span>;

  return (
    <div className="mini-sectors">
      {values.map((sector, index) => {
        const cls = sector?.tone || "neutral";
        const label = `S${sector?.sector || "?"}.${sector?.segment || index + 1}: ${sector?.status || "normal"}`;
        return <i className={cls} key={`${index}-${label}`} title={label} aria-label={label} />;
      })}
    </div>
  );
}

function tyreTone(compound) {
  const value = String(compound || "").toLowerCase();
  if (value.includes("soft")) return "soft";
  if (value.includes("medium")) return "medium";
  if (value.includes("hard")) return "hard";
  if (value.includes("inter")) return "inter";
  if (value.includes("wet")) return "wet";
  return "unknown";
}

function TyreAgeVisual({ row, compact = false }) {
  const age = Number(primitive(row?.tyre_age));
  const pct = Number.isFinite(age) ? Math.max(4, Math.min(100, (age / 35) * 100)) : 0;
  const tone = tyreTone(row?.compound);
  const hasCompound = Boolean(fmt(row?.compound, "") !== "");
  return (
    <div className={cx("tyre-visual", compact && "compact", tone)}>
      <div>
        <strong>{fmt(row?.compound, "Awaiting tyre feed")}</strong>
        <span>{Number.isFinite(age) ? `${age} lap${age === 1 ? "" : "s"}` : "Age unavailable"}</span>
      </div>
      <i><b style={{ width: `${pct}%` }} /></i>
      {!compact && !hasCompound && <em>Compound appears when live TimingAppData or OpenF1 stint data is available.</em>}
    </div>
  );
}

function OfficialRaceVisual({ visual, session }) {
  const [activeSrc, setActiveSrc] = useState("");
  const hasImage = Boolean(activeSrc);

  useEffect(() => {
    setActiveSrc(visual?.image_url || "");
  }, [visual?.image_url]);

  return (
    <section className="official-race-visual">
      <div className="official-race-media">
        {hasImage ? (
          <img
            src={activeSrc}
            alt={visual?.alt || `${fmt(session?.meeting_name)} circuit visual`}
            onError={() => setActiveSrc(activeSrc !== visual?.fallback_image_url ? visual?.fallback_image_url || "" : "")}
          />
        ) : (
          <div className="official-race-placeholder">
            <MapPinned size={30} />
            <span>Official visual unavailable</span>
          </div>
        )}
      </div>
      <div className="official-race-copy">
        <p>Selected event</p>
        <h2>{fmt(session?.meeting_name, "Latest Formula 1 event")}</h2>
        <span>{fmt(session?.session_name || session?.session_type, "Latest / current session")}</span>
        {visual?.page_url && (
          <a href={visual.page_url} target="_blank" rel="noreferrer">
            <ExternalLink size={15} /> Open official F1 race page
          </a>
        )}
      </div>
    </section>
  );
}

function TeamRadioPlayer({ item }) {
  const [proxy, setProxy] = useState(true);
  const url = item?.recording_url || item?.RecordingUrl || item?.url;
  if (!url) return <span className="radio-missing">No recording available</span>;

  const src = proxy ? `/api/audio?url=${encodeURIComponent(url)}` : url;

  return (
    <div className="radio-player">
      <audio controls preload="none" src={src} />
      <button onClick={() => setProxy(!proxy)}>{proxy ? "Proxy" : "Direct"}</button>
      <a href={url} target="_blank" rel="noreferrer">Open</a>
    </div>
  );
}

export default function LivePage() {
  const [settings, patchSettings] = useSettings();
  const [controls, setControls] = useState({
    year: new Date().getUTCFullYear(),
    meeting: "latest",
    session: "latest",
  });
  const [payload, setPayload] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [loading, setLoading] = useState(false);
  const [auto, setAuto] = useState(true);
  const [error, setError] = useState("");
  const [streamState, setStreamState] = useState("idle");
  const [meetingQuery, setMeetingQuery] = useState("");
  const [selectionPending, setSelectionPending] = useState(false);
  const requestIdRef = useRef(0);
  const controllerRef = useRef(null);
  const streamRef = useRef(null);
  const controlError = useMemo(() => validateLiveControls(controls), [controls]);

  function updateControls(update) {
    setSelectionPending(true);
    setControls((prev) => ({ ...prev, ...update }));
  }

  async function loadLiveData(options = {}) {
    if (controlError) {
      setError(controlError);
      setLoading(false);
      setSelectionPending(false);
      return;
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    controllerRef.current?.abort?.();
    const controller = new AbortController();
    controllerRef.current = controller;
    setLoading(true);
    setError("");
    try {
      const data = await fetchF1Timing(controller.signal, { ...sanitizedLiveControls(controls), fast: Boolean(options.fast) });
      if (requestId !== requestIdRef.current) return;
      setPayload(data);
      setLastUpdated(new Date());
      setSelectionPending(false);
    } catch (err) {
      if (requestId === requestIdRef.current && err?.name !== "AbortError") {
        setError(String(err?.message || err || "Live timing sync failed"));
        setSelectionPending(false);
      }
    } finally {
      if (requestId === requestIdRef.current) setLoading(false);
    }
  }

  useEffect(() => {
    loadLiveData({ fast: controls.meeting === "latest" && controls.session === "latest" });
    return () => {
      controllerRef.current?.abort?.();
      streamRef.current?.close?.();
    };
  }, []);

  useEffect(() => {
    if (!payload) return;
    const id = setTimeout(() => loadLiveData({ fast: controls.meeting === "latest" && controls.session === "latest" }), 250);
    return () => clearTimeout(id);
  }, [controls.year, controls.meeting, controls.session]);

  const refreshMs = Math.max(3000, Number(payload?.refresh_after_ms || 15000) + (Number(settings.delay) || 0) * 1000);

  useEffect(() => {
    streamRef.current?.close?.();
    streamRef.current = null;
    if (!auto || controlError || typeof EventSource === "undefined") {
      setStreamState(auto && typeof EventSource === "undefined" ? "unsupported" : "idle");
      return;
    }

    const source = new EventSource(f1TimingStreamUrl(sanitizedLiveControls(controls)));
    streamRef.current = source;
    setStreamState("connecting");

    source.onopen = () => setStreamState("live");
    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setPayload(data);
        setLastUpdated(new Date());
        setSelectionPending(false);
        setError("");
        setStreamState("live");
      } catch {
        setStreamState("error");
      }
    };
    source.onerror = () => {
      setStreamState("reconnecting");
    };

    return () => source.close();
  }, [auto, controlError, controls.year, controls.meeting, controls.session]);

  const normalized = useMemo(() => {
    if (payload?.ok && payload.normalized) return { ...payload.normalized, source: payload?.is_genuinely_live ? "Formula 1 live timing" : payload?.source || "Latest timing data" };
    if (!settings.fallbackResults) return {};
    return normalizeJolpicaFallback(payload?.normalized_fallback || payload?.jolpica_fallback) || {};
  }, [payload, settings.fallbackResults]);
  const openf1AuthRestricted = Boolean(payload?.feed_status?.OpenF1?.auth_restricted || payload?.openf1_fallback?.auth_restricted);

  const session = normalized.session || {};
  const drivers = normalized.drivers || [];
  const leaderboard = normalized.leaderboard || [];
  const weather = normalized.weather || null;
  const raceControl = normalized.raceControl || [];
  const radio = normalized.radio || [];
  const trackStatus = normalized.trackStatus || null;
  const lapCount = normalized.lapCount || {};
  const meetingOptions = payload?.meeting_options || [];
  const sessionOptions = payload?.session_options || [];
  const activeMeeting = meetingOptions.find((meeting) => (meeting.key || meeting.name) === controls.meeting);
  const selectedMeetingLabel = controls.meeting === "latest"
    ? "Latest / current event"
    : [activeMeeting?.name || controls.meeting, activeMeeting?.location, activeMeeting?.country].filter(Boolean).join(" · ");
  const filteredMeetingOptions = useMemo(() => {
    const q = meetingQuery.trim().toLowerCase();
    const rows = q
      ? meetingOptions.filter((meeting) => [meeting.name, meeting.location, meeting.country, meeting.key].filter(Boolean).join(" ").toLowerCase().includes(q))
      : meetingOptions;
    return rows;
  }, [meetingOptions, meetingQuery]);
  const sessionChoices = useMemo(() => {
    const fallback = [
      { key: "race", name: "Race" },
      { key: "qualifying", name: "Qualifying" },
      { key: "sprint qualifying", name: "Sprint qualifying" },
      { key: "sprint", name: "Sprint" },
      { key: "practice", name: "Practice" },
    ];
    const seenKeys = new Set(["latest"]);
    const seenNames = new Set(["latest / current"]);
    return [
      { key: "latest", name: "Latest / current" },
      ...[...sessionOptions, ...fallback].filter((session) => {
        const key = String(session.key || session.name || "").toLowerCase();
        const name = String(session.name || session.key || "").trim().toLowerCase();
        if (!key || !name || seenKeys.has(key) || seenNames.has(name)) return false;
        seenKeys.add(key);
        seenNames.add(name);
        return true;
      }),
    ];
  }, [sessionOptions]);
  const hasMiniSectors = leaderboard.some((row) => Array.isArray(row.mini_sectors) && row.mini_sectors.length);
  const oledClass = settings.oled ? "oled" : "";
  const refreshSeconds = Math.round(refreshMs / 1000);
  const sessionProgress = (() => {
    const start = new Date(session.date_start || "").getTime();
    if (!Number.isFinite(start)) return payload?.is_live ? 52 : 12;
    const duration = 2 * 60 * 60 * 1000;
    return Math.max(0, Math.min(100, ((Date.now() - start) / duration) * 100));
  })();

  return (
    <AppShell active="/live">
      <section className={cx("f1dash-shell", "f1dash-main", oledClass)}>
        <header className="f1dash-topbar">
          <div>
            <p>{payload?.is_genuinely_live ? "Live timing" : "Timing replay"}</p>
            <h1>{fmt(session.meeting_name, "F1 timing dashboard")}</h1>
            <span>{fmt(session.session_name || session.session_type, "Auto-selected event")} · {dateTime(session.date_start)}</span>
          </div>

          <div className="topbar-actions">
            <StatusPill payload={payload} normalized={normalized} />
            <button className="dash-btn" onClick={() => loadLiveData()} disabled={loading || Boolean(controlError)}>
              <RefreshCcw size={16} /> {loading ? "Syncing" : "Refresh"}
            </button>
            <button className={cx("dash-btn", auto && "active")} onClick={() => setAuto(!auto)}>
              {auto ? <Pause size={16} /> : <Play size={16} />} {auto ? "Auto sync" : "Manual"}
            </button>
            <SettingsPanel settings={settings} patch={patchSettings} />
          </div>
        </header>

        <section className={cx("live-control-panel", "live-selector-flow", selectionPending && "selecting")}>
          <div className="selector-step season-step">
            <div className="selector-step-label">
              <span>01</span>
              <strong>Season</strong>
            </div>
            <label className="season-input">
              <span>Year</span>
              <input
                type="number"
                min="2018"
                max="2030"
                value={controls.year}
                onChange={(event) => updateControls({ year: event.target.value, meeting: "latest", session: "latest" })}
                aria-invalid={Boolean(controlError)}
              />
            </label>
          </div>

          <div className="selector-step grand-prix-step">
            <div className="selector-step-label">
              <span>02</span>
              <strong>Grand Prix</strong>
            </div>
            <div className="live-race-picker compact">
              <div className="race-picker-head compact">
                <div>
                  <span>Selected event</span>
                  <strong>{selectionPending || loading ? "Syncing selection" : selectedMeetingLabel}</strong>
                </div>
                <span className={cx("stream-badge", streamState)}>
                  {auto ? streamState.replace("-", " ") || "stream" : `manual · ${refreshSeconds}s suggested`}
                </span>
              </div>

              <div className="selector-fields">
                <label className="race-picker-search">
                  <Search size={15} />
                  <input
                    value={meetingQuery}
                    onChange={(event) => setMeetingQuery(event.target.value)}
                    placeholder="Filter Grand Prix"
                    aria-label="Filter Grand Prix list"
                  />
                </label>

                <label className="select-shell">
                  <span>Grand Prix</span>
                  <select
                    value={controls.meeting}
                    onChange={(event) => updateControls({ meeting: event.target.value, session: "latest" })}
                    aria-label="Choose Grand Prix"
                  >
                    <option value="latest">Latest / current event</option>
                    {filteredMeetingOptions.map((meeting, index) => {
                      const key = meeting.key || meeting.name || `meeting-${index}`;
                      const label = [meeting.name || key, meeting.location, meeting.country].filter(Boolean).join(" · ");
                      return <option value={key} key={`${key}-${index}`}>{label}</option>;
                    })}
                  </select>
                </label>
              </div>

              {!filteredMeetingOptions.length && (
                <p className="race-picker-empty">No Grand Prix matches this filter for {controls.year}.</p>
              )}
            </div>
          </div>

          <div className="selector-step session-step">
            <div className="selector-step-label">
              <span>03</span>
              <strong>Session</strong>
            </div>
            <label className="select-shell">
              <span>Timing feed</span>
              <select
                value={controls.session}
                onChange={(event) => updateControls({ session: event.target.value })}
                aria-label="Choose session"
              >
                {sessionChoices.map((choice) => {
                  const key = choice.key || choice.name;
                  return <option value={key} key={key}>{choice.name || key}</option>;
                })}
              </select>
            </label>
          </div>

          <div className="selector-sync-row">
            <button className="dash-btn live" onClick={() => loadLiveData()} disabled={loading || Boolean(controlError)}>
              <RefreshCcw size={16} /> {loading ? "Syncing selected session" : "Sync selected session"}
            </button>
            <div className="session-progress">
              <span>Session progress</span>
              <i><b style={{ width: `${sessionProgress}%` }} /></i>
            </div>
          </div>
        </section>

        {controlError && (
          <section className="dash-warning" role="alert">
            <BadgeInfo size={18} />
            <div>
              <strong>Check timing controls.</strong>
              <p>{controlError}</p>
            </div>
          </section>
        )}

        <div className="sync-strip">
          <span>Updated: <strong>{lastUpdated ? lastUpdated.toLocaleTimeString() : "-"}</strong></span>
          <span>Mode: <strong>{payload?.timing_mode || (auto ? `auto ${streamState}` : "manual")}</strong></span>
          <span>Source: <strong>{payload?.timing_source || payload?.source || "-"}</strong></span>
          <span>Delay: <strong>{settings.delay}s</strong></span>
          <span>Lap: <strong>{fmt(lapCount.current_lap)}/{fmt(lapCount.total_laps)}</strong></span>
          <span>Track: <strong>{fmt(trackStatus?.Status || trackStatus?.Message || trackStatus?.status)}</strong></span>
        </div>

        <OfficialRaceVisual visual={payload?.official_visual} session={session} />

        {error && (
          <section className="dash-warning">
            <BadgeInfo size={18} />
            <div>
              <strong>Auto-sync could not complete.</strong>
              <p>{error}</p>
            </div>
          </section>
        )}

        {!payload?.ok && (
          <section className="dash-warning">
            <BadgeInfo size={18} />
            <div>
              <strong>Fresh live timing is not available right now.</strong>
              <p>The page is showing latest available timing or completed event data where possible. It only shows Live when fresh timing packets are present during an active session.</p>
            </div>
          </section>
        )}

        {openf1AuthRestricted && (
          <section className="dash-warning">
            <ShieldAlert size={18} />
            <div>
              <strong>OpenF1 authenticated access is required for this live-session request.</strong>
              <p>{payload?.feed_status?.OpenF1?.detail || payload?.openf1_fallback?.detail || "PitWall is using Formula 1 timing, FastF1, Jolpica, and cached fallbacks instead of inventing live data."}</p>
            </div>
          </section>
        )}

        <section className="live-summary-grid">
          <div>
            <span>Primary source</span>
            <strong>{fmt(payload?.source, "Checking")}</strong>
          </div>
          <div>
            <span>State</span>
            <strong>{fmt(payload?.session_state, "Pending")}</strong>
          </div>
          <div>
            <span>Rows</span>
            <strong>{leaderboard.length}</strong>
          </div>
          <div>
            <span>Radio clips</span>
            <strong>{radio.length}</strong>
          </div>
        </section>

        <section className="f1dash-grid">
          <Card id="leaderboard" title="Leaderboard" icon={<Trophy size={18} />} show={settings.leaderboard} empty={!leaderboard.length && "No timing or fallback result rows available."}>
            <div className="dash-table">
              <div className="dash-row head">
                <span>Pos</span><span>Driver</span><span>Gap</span><span>Last lap</span><span>Tyre / age</span><span>Speed</span>
              </div>
              {leaderboard.map((row, index) => (
                <div className="dash-row" key={`${row.driver_number}-${index}`}>
                  <span>{fmt(row.position || index + 1)}</span>
                  <span className="driver-name">
                    <i style={{ background: color(row.driver?.team_colour) }} />
                    <strong>{driverName(row)}</strong>
                    <small>{fmt(row.driver?.team_name || row.team, "")}</small>
                  </span>
                  <span>{gap(row)}</span>
                  <span>{fmt(row.lap_duration)}</span>
                  <span><TyreAgeVisual row={row} compact /></span>
                  <span>{speed(row.speed, settings.metric)}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card id="tyres" title="Tyres and stints" icon={<Waves size={18} />} show={settings.tyres} empty={!leaderboard.length && "No tyre data available."}>
            <div className="compact-stack">
              {leaderboard.slice(0, 20).map((row) => (
                <div key={`${row.driver_number}-tyre`}>
                  <strong>{driverName(row)}</strong>
                  <TyreAgeVisual row={row} />
                </div>
              ))}
            </div>
          </Card>

          <Card id="sectors" title="Mini sectors" icon={<MapPinned size={18} />} show={settings.sectors} empty={!leaderboard.length ? "Mini-sector style data is unavailable for this feed." : !hasMiniSectors && "This selected session does not expose mini-sector segment data in the available feed."}>
            <div className="sector-list">
              {leaderboard.slice(0, 20).map((row) => (
                <div key={`${row.driver_number}-sector`}>
                  <strong>{driverName(row)}</strong>
                  <MiniSectors row={row} />
                </div>
              ))}
            </div>
          </Card>

          <Card id="weather" title="Weather" icon={<CloudRain size={18} />} show={settings.weather} empty={!weather && "No timing-feed weather data available."}>
            <div className="fact-grid">
              <div><span>Air</span><strong>{fmt(weather?.air_temperature)}°C</strong></div>
              <div><span>Track</span><strong>{fmt(weather?.track_temperature)}°C</strong></div>
              <div><span>Humidity</span><strong>{fmt(weather?.humidity)}%</strong></div>
              <div><span>Rain</span><strong>{fmt(weather?.rainfall)}</strong></div>
              <div><span>Wind</span><strong>{fmt(weather?.wind_speed)} km/h</strong></div>
              <div><span>Direction</span><strong>{fmt(weather?.wind_direction)}°</strong></div>
            </div>
          </Card>

          <Card id="track-status" title="Track status" icon={<Activity size={18} />} show={settings.trackStatus}>
            <div className={cx("track-status", settings.safetyCarColors && "safety")}>
              <Flag size={20} />
              <div>
                <strong>{fmt(trackStatus?.Status || trackStatus?.status || "Unknown")}</strong>
                <span>{fmt(trackStatus?.Message || trackStatus?.message || "No active track-status message")}</span>
              </div>
            </div>
          </Card>

          <Card id="car-metrics" title="Car metrics" icon={<Gauge size={18} />} show={settings.carMetrics} empty={!leaderboard.some((row) => row.speed || row.rpm || row.n_gear) && "Car metrics may be restricted or unavailable for this session."}>
            <div className="dash-table compact">
              <div className="dash-row head">
                <span>Driver</span><span>Speed</span><span>Gear</span><span>RPM</span><span>Aero / Boost</span><span>Brake</span>
              </div>
              {leaderboard.slice(0, 20).map((row) => (
                <div className="dash-row" key={`${row.driver_number}-car`}>
                  <span>{driverName(row)}</span>
                  <span>{speed(row.speed, settings.metric)}</span>
                  <span>{fmt(row.n_gear)}</span>
                  <span>{fmt(row.rpm)}</span>
                  <span>{fmt(row.aero_mode)}</span>
                  <span>{fmt(row.brake)}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card id="race-control" title="Race control" icon={<ShieldAlert size={18} />} show={settings.raceControl} empty={!raceControl.length && "No race-control messages available."}>
            <div className="race-control-stack">
              {raceControl.map((message, index) => (
                <article className={raceControlTone(message)} key={`${message.date}-${index}`}>
                  <div className="race-control-meta">
                    <time>{time(message.date)}</time>
                    {message.lap && <span>Lap {fmt(message.lap)}</span>}
                    {message.racing_number && <span>#{fmt(message.racing_number)}</span>}
                    {message.status && <span>{fmt(message.status)}</span>}
                  </div>
                  <strong>{fmt(message.category)}</strong>
                  <p>{fmt(message.message)}</p>
                </article>
              ))}
            </div>
          </Card>

          <Card id="team-radio" title="Team radio" icon={<AudioLines size={18} />} show={settings.teamRadio} empty={!radio.length && "No team-radio recordings available for this session."}>
            <div className="radio-stack">
              {radio.map((item, index) => {
                const row = leaderboard.find((driver) => Number(driver.driver_number) === Number(item.driver_number));
                const radioDriver = row || { driver_number: item.driver_number, driver: drivers.find((driver) => Number(driver.driver_number) === Number(item.driver_number)) || {} };
                return (
                  <article key={`${item.date}-${item.driver_number}-${index}`}>
                    <div>
                      <strong>{driverName(radioDriver)}</strong>
                      <span>{time(item.date)}</span>
                    </div>
                    {item.message && <p>{fmt(item.message)}</p>}
                    <TeamRadioPlayer item={item} />
                  </article>
                );
              })}
            </div>
          </Card>
        </section>

        <footer className="dash-footer">
          Inspired by f1-dash layout principles, but implemented independently. Data comes from Formula 1 timing feeds, OpenF1, and Jolpica fallback; archived or stale data is labelled accordingly. This site does not stream video.
        </footer>
      </section>
    </AppShell>
  );
}
