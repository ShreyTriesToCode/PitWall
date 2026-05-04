"use client";

import { useEffect, useMemo, useState } from "react";
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
  RefreshCcw,
  Settings2,
  ShieldAlert,
  Timer,
  Trophy,
  Waves
} from "lucide-react";

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

function fmt(value, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
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
  return row?.name || row?.driver?.full_name || row?.driver?.name_acronym || row?.driver_number || "-";
}

function speed(value, metric) {
  const n = Number(value);
  if (!Number.isFinite(n)) return fmt(value);
  if (metric === "mph") return `${Math.round(n * 0.621371)} mph`;
  return `${Math.round(n)} km/h`;
}

function gap(row) {
  return fmt(row?.interval || row?.gap_to_leader || row?.status);
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
        drs: "",
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

async function fetchF1Timing() {
  const url = new URL("/api/f1timing", window.location.origin);
  url.searchParams.set("year", String(new Date().getUTCFullYear()));
  const res = await fetch(url.toString(), { cache: "no-store" });
  return res.json();
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
      <button className="dash-btn" onClick={() => setOpen(!open)}>
        <Settings2 size={16} /> Settings
      </button>

      {open && (
        <div className="dash-settings-panel">
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
  const live = payload?.source === "Formula1LiveTiming" && payload?.ok;
  return (
    <div className={cx("dash-status-pill", live ? "live" : "fallback")}>
      <span>{live ? "Live timing" : "Latest event"}</span>
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
  const sectors = row?.sectors || row?.Segments || [];
  const values = Array.isArray(sectors) && sectors.length ? sectors.slice(0, 18) : Array.from({ length: 12 }, (_, index) => index);
  return (
    <div className="mini-sectors">
      {values.map((sector, index) => {
        const raw = typeof sector === "object" ? sector.Status || sector.status || sector.Value || sector.value : sector;
        const name = String(raw || index);
        const cls = name.includes("2048") || name.toLowerCase().includes("purple")
          ? "purple"
          : name.includes("2049") || name.toLowerCase().includes("green")
            ? "green"
            : name.includes("2051") || name.toLowerCase().includes("yellow")
              ? "yellow"
              : "";
        return <i className={cls} key={`${index}-${name}`} />;
      })}
    </div>
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
  const [payload, setPayload] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [loading, setLoading] = useState(false);
  const [auto, setAuto] = useState(true);

  async function loadLiveData() {
    setLoading(true);
    try {
      const data = await fetchF1Timing();
      setPayload(data);
      setLastUpdated(new Date());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLiveData();
  }, []);

  useEffect(() => {
    if (!auto) return;
    const intervalMs = Math.max(5000, (Number(settings.delay) || 0) * 1000 + 15000);
    const id = setInterval(loadLiveData, intervalMs);
    return () => clearInterval(id);
  }, [auto, settings.delay]);

  const normalized = useMemo(() => {
    if (payload?.ok && payload.normalized) return { ...payload.normalized, source: "Formula 1 live timing" };
    return normalizeJolpicaFallback(payload?.normalized_fallback || payload?.jolpica_fallback) || {};
  }, [payload]);

  const session = normalized.session || {};
  const leaderboard = normalized.leaderboard || [];
  const weather = normalized.weather || null;
  const raceControl = normalized.raceControl || [];
  const radio = normalized.radio || [];
  const trackStatus = normalized.trackStatus || null;
  const lapCount = normalized.lapCount || {};
  const oledClass = settings.oled ? "oled" : "";

  return (
    <main className={cx("f1dash-shell", oledClass)}>
      <aside className="f1dash-sidebar">
        <a className="side-logo" href="/">F1</a>
        <nav>
          {NAV_ITEMS.map(([href, label]) => (
            <a href={`#${href}`} key={href}><ChevronRight size={14} />{label}</a>
          ))}
        </nav>
        <a href="/">Predictions</a>
      </aside>

      <section className="f1dash-main">
        <header className="f1dash-topbar">
          <div>
            <p>Live timing</p>
            <h1>{fmt(session.meeting_name, "F1 live dashboard")}</h1>
            <span>{fmt(session.session_name || session.session_type, "Auto-selected event")} · {dateTime(session.date_start)}</span>
          </div>

          <div className="topbar-actions">
            <StatusPill payload={payload} normalized={normalized} />
            <button className="dash-btn" onClick={loadLiveData} disabled={loading}>
              <RefreshCcw size={16} /> {loading ? "Syncing" : "Refresh"}
            </button>
            <button className={cx("dash-btn", auto && "active")} onClick={() => setAuto(!auto)}>
              {auto ? <Pause size={16} /> : <Play size={16} />} {auto ? "Auto" : "Manual"}
            </button>
            <SettingsPanel settings={settings} patch={patchSettings} />
          </div>
        </header>

        <div className="sync-strip">
          <span>Updated: <strong>{lastUpdated ? lastUpdated.toLocaleTimeString() : "-"}</strong></span>
          <span>Delay: <strong>{settings.delay}s</strong></span>
          <span>Lap: <strong>{fmt(lapCount.current_lap)}/{fmt(lapCount.total_laps)}</strong></span>
          <span>Track: <strong>{fmt(trackStatus?.Status || trackStatus?.Message || trackStatus?.status)}</strong></span>
        </div>

        {!payload?.ok && (
          <section className="dash-warning">
            <BadgeInfo size={18} />
            <div>
              <strong>Live timing is not available right now.</strong>
              <p>The page is showing latest completed event data from Jolpica where possible. During an active race weekend, Formula 1 live timing feeds are used automatically.</p>
            </div>
          </section>
        )}

        <section className="f1dash-grid">
          <Card id="leaderboard" title="Leaderboard" icon={<Trophy size={18} />} show={settings.leaderboard} empty={!leaderboard.length && "No timing or fallback result rows available."}>
            <div className="dash-table">
              <div className="dash-row head">
                <span>Pos</span><span>Driver</span><span>Gap</span><span>Last lap</span><span>Tyre</span><span>Age</span><span>Speed</span>
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
                  <span>{fmt(row.compound)}</span>
                  <span>{fmt(row.tyre_age)}</span>
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
                  <span>{fmt(row.compound)} · age {fmt(row.tyre_age)}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card id="sectors" title="Mini sectors" icon={<MapPinned size={18} />} show={settings.sectors} empty={!leaderboard.length && "Mini-sector style data is unavailable for this feed."}>
            <div className="sector-list">
              {leaderboard.slice(0, 20).map((row) => (
                <div key={`${row.driver_number}-sector`}>
                  <strong>{driverName(row)}</strong>
                  <MiniSectors row={row} />
                </div>
              ))}
            </div>
          </Card>

          <Card id="weather" title="Weather" icon={<CloudRain size={18} />} show={settings.weather} empty={!weather && "No live weather data available."}>
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
                <span>Driver</span><span>Speed</span><span>Gear</span><span>RPM</span><span>DRS</span><span>Brake</span>
              </div>
              {leaderboard.slice(0, 20).map((row) => (
                <div className="dash-row" key={`${row.driver_number}-car`}>
                  <span>{driverName(row)}</span>
                  <span>{speed(row.speed, settings.metric)}</span>
                  <span>{fmt(row.n_gear)}</span>
                  <span>{fmt(row.rpm)}</span>
                  <span>{fmt(row.drs)}</span>
                  <span>{fmt(row.brake)}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card id="race-control" title="Race control" icon={<ShieldAlert size={18} />} show={settings.raceControl} empty={!raceControl.length && "No race-control messages available."}>
            <div className="race-control-stack">
              {raceControl.map((message, index) => (
                <article key={`${message.date}-${index}`}>
                  <time>{time(message.date)}</time>
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
                return (
                  <article key={`${item.date}-${item.driver_number}-${index}`}>
                    <div>
                      <strong>{row ? driverName(row) : fmt(item.driver_number, "Radio")}</strong>
                      <span>{time(item.date)}</span>
                    </div>
                    <TeamRadioPlayer item={item} />
                  </article>
                );
              })}
            </div>
          </Card>
        </section>

        <footer className="dash-footer">
          Inspired by f1-dash layout principles, but implemented independently. Data comes from Formula 1 live timing feeds and Jolpica fallback. This site does not stream video.
        </footer>
      </section>
    </main>
  );
}
