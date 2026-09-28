"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AudioLines,
  BadgeInfo,
  CloudRain,
  Eye,
  EyeOff,
  Flag,
  Gauge,
  MapPinned,
  Pause,
  Play,
  RefreshCcw,
  Search,
  Settings2,
  ShieldAlert,
  Trophy,
  Waves,
} from "lucide-react";
import { expireLivePayload, trackStateLabel } from "../api/_lib/timing";
import ObservedStrategy from "./ObservedStrategy";
import { AppShell } from "./PitWallComponents";
import {
  formatISTTime as time,
  formatISTDateTime as dateTime,
} from "../lib/time";

const DEFAULT_SETTINGS = {
  leaderboard: true,
  tyres: true,
  sectors: true,
  raceControl: true,
  weather: true,
  trackStatus: true,
  carMetrics: true,
  teamRadio: true,
  oled: false,
  safetyCarColors: true,
  metric: "kmh",
};

function cx(...parts) {
  return parts.filter(Boolean).join(" ");
}

function primitive(value) {
  if (value === null || value === undefined || value === "") return null;

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

function measured(value, unit = "") {
  const raw = primitive(value);
  return raw === null ? "Unavailable" : `${raw}${unit}`;
}

function color(teamColour) {
  const raw = String(teamColour || "")
    .replace("#", "")
    .trim();
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
    [
      driver.first_name || driver.givenName,
      driver.last_name || driver.familyName,
    ]
      .filter(Boolean)
      .join(" ") ||
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
  if (!Number.isFinite(n) || n < 0) return "-";
  if (metric === "mph") return `${Math.round(n * 0.621371)} mph`;
  return `${Math.round(n)} km/h`;
}

function gap(row) {
  return fmt(row?.interval);
}

function raceControlTone(message) {
  const text =
    `${message?.category || ""} ${message?.status || ""} ${message?.message || ""}`.toLowerCase();
  if (text.includes("red")) return "red";
  if (text.includes("safety") || text.includes("vsc")) return "safety";
  if (text.includes("yellow")) return "yellow";
  if (text.includes("green") || text.includes("clear")) return "green";
  if (
    text.includes("investig") ||
    text.includes("noted") ||
    text.includes("penalty")
  )
    return "warning";
  return "";
}

async function fetchF1Timing(signal, controls = {}) {
  const url = new URL("/api/f1timing", window.location.origin);
  url.searchParams.set(
    "year",
    String(controls.year || new Date().getUTCFullYear()),
  );
  url.searchParams.set("meeting", String(controls.meeting || "latest"));
  url.searchParams.set("session", String(controls.session || "latest"));
  if (controls.fast) url.searchParams.set("fast", "1");
  const res = await fetch(url.toString(), { cache: "no-store", signal });
  const payload = await res.json().catch(() => null);
  if (!res.ok)
    throw new Error(
      payload?.error || `Live timing API returned HTTP ${res.status}`,
    );
  return payload;
}

function f1TimingStreamUrl(controls = {}) {
  const url = new URL("/api/f1timing/stream", window.location.origin);
  url.searchParams.set(
    "year",
    String(controls.year || new Date().getUTCFullYear()),
  );
  url.searchParams.set("meeting", String(controls.meeting || "latest"));
  url.searchParams.set("session", String(controls.session || "latest"));
  return url.toString();
}

function validateLiveControls(controls = {}) {
  const year = Number(String(controls.year || "").trim());
  const current = new Date().getUTCFullYear();
  if (
    !Number.isInteger(year) ||
    year < 2018 ||
    year > Math.max(2030, current + 1)
  ) {
    return "Choose a valid F1 timing year between 2018 and the next listed season.";
  }
  if (
    String(controls.meeting || "").length > 120 ||
    String(controls.session || "").length > 120
  ) {
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
      if (stored) {
        const parsed = JSON.parse(stored);
        const valid = Object.fromEntries(
          Object.entries(DEFAULT_SETTINGS).map(([key, fallback]) => [
            key,
            typeof fallback === "boolean" && typeof parsed?.[key] === "boolean"
              ? parsed[key]
              : fallback,
          ]),
        );
        if (["kmh", "mph"].includes(parsed?.metric))
          valid.metric = parsed.metric;
        setSettings(valid);
      }
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
  const containerRef = useRef(null);
  const triggerRef = useRef(null);
  useEffect(() => {
    if (!open) return;
    function close(event) {
      if (event.type === "keydown" && event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      } else if (
        event.type === "pointerdown" &&
        !containerRef.current?.contains(event.target)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("keydown", close);
    document.addEventListener("pointerdown", close);
    return () => {
      document.removeEventListener("keydown", close);
      document.removeEventListener("pointerdown", close);
    };
  }, [open]);
  const toggles = [
    ["leaderboard", "Show leaderboard"],
    ["tyres", "Show tyres and stints"],
    ["sectors", "Show mini sectors"],
    ["weather", "Show weather"],
    ["raceControl", "Show race control"],
    ["trackStatus", "Show track status"],
    ["carMetrics", "Show car metrics if available"],
    ["teamRadio", "Show team radio"],
    ["oled", "OLED mode"],
    ["safetyCarColors", "Use safety car colors"],
  ];

  return (
    <div className="dash-settings" ref={containerRef}>
      <button
        className="dash-btn"
        ref={triggerRef}
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls="live-settings-panel"
      >
        <Settings2 size={16} /> Settings
      </button>

      {open && (
        <div className="dash-settings-panel" id="live-settings-panel">
          <div className="dash-field">
            <label htmlFor="timing-speed-unit">Speed</label>
            <select
              id="timing-speed-unit"
              value={settings.metric}
              onChange={(event) => patch({ metric: event.target.value })}
            >
              <option value="kmh">km/h</option>
              <option value="mph">mph</option>
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

function StatusPill({ payload }) {
  if (!payload)
    return (
      <div className="dash-status-pill">
        <span>Checking timing source…</span>
      </div>
    );
  const live = Boolean(payload?.is_genuinely_live);
  const sourceOk = payload?.source === "Formula1LiveTiming" && payload?.ok;
  const state = String(payload?.session_state || "").replace("-", " ");
  const archived =
    !live &&
    ["archive", "archived", "completed"].some((word) =>
      String(payload?.timing_mode || payload?.session_state || "")
        .toLowerCase()
        .includes(word),
    );
  const mode = archived
    ? "Historical session timing"
    : String(
        payload?.timing_mode ||
          (live ? "live" : sourceOk ? state : "unavailable"),
      ).replace("-", " ");
  return (
    <div
      className={cx(
        "dash-status-pill",
        live
          ? "live"
          : payload?.completion_verified
            ? "completed"
            : payload?.session_state === "upcoming"
              ? "upcoming"
              : "fallback",
      )}
    >
      <span>{live ? "Live timing" : mode || "Timing data"}</span>
      <strong>
        {live
          ? "Recent source activity verified"
          : archived
            ? "Archived observations"
            : "Awaiting verified session activity"}
      </strong>
    </div>
  );
}

function Card({ id, title, icon, show = true, children, empty }) {
  if (!show) return null;
  return (
    <section className="dash-card" id={id}>
      <div className="dash-card-head">
        <h2>
          {icon}
          {title}
        </h2>
      </div>
      {empty ? <p className="dash-empty">{empty}</p> : children}
    </section>
  );
}

function MiniSectors({ row }) {
  const values = Array.isArray(row?.mini_sectors) ? row.mini_sectors : [];
  if (!values.length) return null;

  return (
    <div className="mini-sectors">
      {values.map((sector, index) => {
        const cls = sector?.tone || "neutral";
        const label = `S${sector?.sector || "?"}.${sector?.segment || index + 1}: ${sector?.status ?? "unavailable"}`;
        return (
          <i
            className={cls}
            key={`${index}-${label}`}
            title={label}
            aria-label={label}
            role="img"
          />
        );
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
  const rawAge = primitive(row?.tyre_age);
  const age = rawAge === null ? null : Number(rawAge);
  const hasAge = age !== null && Number.isFinite(age) && age >= 0;
  const tone = tyreTone(row?.compound);
  const hasCompound = Boolean(fmt(row?.compound, "") !== "");
  return (
    <div className={cx("tyre-visual", compact && "compact", tone)}>
      <div>
        <strong>{fmt(row?.compound, "Awaiting tyre feed")}</strong>
        <span>
          {hasAge ? `${age} lap${age === 1 ? "" : "s"}` : "Age unavailable"}
        </span>
      </div>
      {!compact && !hasCompound && (
        <em>Compound appears when Formula 1 stint data is available.</em>
      )}
    </div>
  );
}

function TeamRadioPlayer({ item }) {
  const [failed, setFailed] = useState(false);
  const url = item?.recording_url;
  if (!url)
    return <span className="radio-missing">No recording available</span>;
  return (
    <div className="radio-player">
      {failed ? (
        <span className="radio-missing">Audio unavailable from provider</span>
      ) : (
        <audio
          controls
          preload="none"
          src={`/api/audio?url=${encodeURIComponent(url)}`}
          onError={() => setFailed(true)}
        />
      )}
      <a href={url} target="_blank" rel="noreferrer">
        Open source
      </a>
    </div>
  );
}

function rowHasUsefulCarMetrics(row) {
  const values = [row?.speed, row?.n_gear, row?.rpm, row?.throttle];
  return values.some((value) => {
    const primitiveValue = primitive(value);
    if (
      primitiveValue === null ||
      primitiveValue === undefined ||
      primitiveValue === ""
    )
      return false;
    if (typeof primitiveValue === "number")
      return Number.isFinite(primitiveValue) && primitiveValue >= 0;
    const text = String(primitiveValue).trim();
    return Boolean(text) && text !== "-";
  });
}

export default function SessionTiming({ strategy = false }) {
  const [expanded, setExpanded] = useState(false);
  const [settings, patchSettings] = useSettings();
  const [controls, setControls] = useState({
    year: new Date().getUTCFullYear(),
    meeting: "latest",
    session: "latest",
  });
  const [rawPayload, setPayload] = useState(null);
  const [clock, setClock] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const payload = expireLivePayload(rawPayload, clock);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [loading, setLoading] = useState(true);
  const [auto, setAuto] = useState(true);
  const [error, setError] = useState("");
  const [streamState, setStreamState] = useState("idle");
  const [meetingQuery, setMeetingQuery] = useState("");
  const [selectionPending, setSelectionPending] = useState(false);
  const requestIdRef = useRef(0);
  const controllerRef = useRef(null);
  const streamRef = useRef(null);
  const controlError = useMemo(
    () => validateLiveControls(controls),
    [controls],
  );

  function updateControls(update) {
    setSelectionPending(true);
    setPayload(null);
    requestIdRef.current += 1;
    controllerRef.current?.abort?.();
    streamRef.current?.close?.();
    setControls((prev) => ({ ...prev, ...update }));
  }

  const loadLiveData = useCallback(
    async (options = {}) => {
      const nextControls = sanitizedLiveControls(options.controls || controls);
      const nextControlError = validateLiveControls(nextControls);
      if (nextControlError) {
        setError(nextControlError);
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
        const data = await fetchF1Timing(controller.signal, {
          ...nextControls,
          fast: Boolean(options.fast),
        });
        if (requestId !== requestIdRef.current) return;
        setPayload(data);
        setLastUpdated(new Date());
        setSelectionPending(false);
      } catch (err) {
        if (requestId === requestIdRef.current && err?.name !== "AbortError") {
          setPayload(null);
          setError(
            "Timing could not be retrieved for the selected session. Try again.",
          );
          setSelectionPending(false);
        }
      } finally {
        if (requestId === requestIdRef.current) setLoading(false);
      }
    },
    [controls],
  );

  useEffect(() => {
    const id = setTimeout(
      () =>
        loadLiveData({
          fast: controls.meeting === "latest" && controls.session === "latest",
        }),
      150,
    );
    return () => {
      clearTimeout(id);
      requestIdRef.current += 1;
      controllerRef.current?.abort();
    };
  }, [controls, loadLiveData]);

  const refreshMs = Math.max(3000, Number(payload?.refresh_after_ms || 15000));

  useEffect(() => {
    streamRef.current?.close?.();
    streamRef.current = null;
    if (!auto || controlError || typeof EventSource === "undefined") {
      setStreamState(
        auto && typeof EventSource === "undefined" ? "unsupported" : "idle",
      );
      return;
    }

    const source = new EventSource(
      f1TimingStreamUrl(sanitizedLiveControls(controls)),
    );
    streamRef.current = source;
    setStreamState("connecting");

    source.onopen = () => setStreamState("connected");
    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setPayload(data);
        setLastUpdated(new Date());
        setSelectionPending(false);
        setError("");
        setStreamState("connected");
      } catch {
        setStreamState("error");
      }
    };
    source.onerror = () => {
      setStreamState("reconnecting");
    };

    return () => source.close();
  }, [auto, controlError, controls]);

  const normalized = useMemo(() => {
    if (payload?.normalized)
      return {
        ...payload.normalized,
        source: payload?.is_genuinely_live
          ? "Formula 1 live timing"
          : payload?.source || "Latest timing data",
      };
    return {};
  }, [payload]);

  const session = normalized.session || {};
  const drivers = normalized.drivers || [];
  const leaderboard = normalized.leaderboard || [];
  const weather = normalized.weather || null;
  const raceControl = normalized.raceControl || [];
  const radio = normalized.radio || [];
  const playableRadio = radio.filter((item) => item.recording_url);
  const trackStatus = normalized.trackStatus || null;
  const trackCode = String(
    primitive(trackStatus?.Status ?? trackStatus?.status) ?? "",
  );
  const lapCount = normalized.lapCount || {};
  const meetingOptions = useMemo(
    () => payload?.meeting_options || [],
    [payload?.meeting_options],
  );
  const sessionOptions = useMemo(
    () => payload?.session_options || [],
    [payload?.session_options],
  );
  const activeMeeting = meetingOptions.find(
    (meeting) => (meeting.key || meeting.name) === controls.meeting,
  );
  const selectedMeetingLabel =
    controls.meeting === "latest"
      ? "Latest / current event"
      : [
          activeMeeting?.name || controls.meeting,
          activeMeeting?.location,
          activeMeeting?.country,
        ]
          .filter(Boolean)
          .join(" · ");
  const filteredMeetingOptions = useMemo(() => {
    const q = meetingQuery.trim().toLowerCase();
    const rows = q
      ? meetingOptions.filter((meeting) =>
          [meeting.name, meeting.location, meeting.country, meeting.key]
            .filter(Boolean)
            .join(" ")
            .toLowerCase()
            .includes(q),
        )
      : meetingOptions;
    return rows;
  }, [meetingOptions, meetingQuery]);
  const sessionChoices = useMemo(() => {
    const seenKeys = new Set(["latest"]);
    const seenNames = new Set(["latest / current"]);
    return [
      { key: "latest", name: "Latest / current" },
      ...sessionOptions.filter((session) => {
        const key = String(session.key || session.name || "").toLowerCase();
        const name = String(session.name || session.key || "")
          .trim()
          .toLowerCase();
        if (!key || !name || seenKeys.has(key) || seenNames.has(name))
          return false;
        seenKeys.add(key);
        seenNames.add(name);
        return true;
      }),
    ];
  }, [sessionOptions]);
  const hasMiniSectors = leaderboard.some(
    (row) => Array.isArray(row.mini_sectors) && row.mini_sectors.length,
  );
  const carMetricRows = leaderboard.filter(rowHasUsefulCarMetrics);
  const carMetricsMostlyMissing = !carMetricRows.length;
  const timingModeLabel = payload?.is_genuinely_live
    ? "Live timing"
    : payload?.timing_mode === "archive"
      ? "Historical session timing"
      : "Session timing";
  const oledClass = settings.oled ? "oled" : "";
  const refreshSeconds = Math.round(refreshMs / 1000);

  return (
    <AppShell active={strategy ? "/strategy" : "/live"}>
      <section
        className={cx(
          "f1dash-shell",
          "f1dash-main",
          oledClass,
          strategy && "strategy-desk",
          expanded ? "timing-expanded" : "timing-compact",
        )}
      >
        <header className="f1dash-topbar">
          <div>
            <p>
              {strategy ? "Strategy / observed session data" : timingModeLabel}
            </p>
            <h1>
              {strategy
                ? "Strategy desk"
                : fmt(session.meeting_name, "Session timing")}
            </h1>
            {strategy && <p>{fmt(session.meeting_name, "Checking event")}</p>}
            <span>
              {fmt(
                session.session_name || session.session_type,
                "Auto-selected event",
              )}{" "}
              · {dateTime(session.date_start)}
            </span>
          </div>

          <div className="topbar-actions">
            <StatusPill payload={payload} normalized={normalized} />
            <button
              className="dash-btn"
              onClick={() => loadLiveData()}
              disabled={loading || Boolean(controlError)}
            >
              <RefreshCcw size={16} /> {loading ? "Syncing" : "Refresh"}
            </button>
            <button
              className={cx("dash-btn", auto && "active")}
              onClick={() => setAuto(!auto)}
            >
              {auto ? <Pause size={16} /> : <Play size={16} />}{" "}
              {auto ? "Auto sync" : "Manual"}
            </button>
            <SettingsPanel settings={settings} patch={patchSettings} />
          </div>
        </header>

        <details className="product-details session-selector">
          <summary>
            Choose a session <span>Season, Grand Prix & session</span>
          </summary>
          <section
            className={cx(
              "live-control-panel",
              "live-selector-flow",
              selectionPending && "selecting",
            )}
          >
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
                  onChange={(event) =>
                    updateControls({
                      year: event.target.value,
                      meeting: "latest",
                      session: "latest",
                    })
                  }
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
                    <strong>
                      {selectionPending || loading
                        ? "Syncing selection"
                        : selectedMeetingLabel}
                    </strong>
                  </div>
                  <span className={cx("stream-badge", streamState)}>
                    {auto
                      ? `Refresh connection: ${streamState.replace("-", " ") || "checking"}`
                      : `manual · ${refreshSeconds}s suggested`}
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
                      onChange={(event) =>
                        updateControls({
                          meeting: event.target.value,
                          session: "latest",
                        })
                      }
                      aria-label="Choose Grand Prix"
                    >
                      <option value="latest">Latest / current event</option>
                      {filteredMeetingOptions.map((meeting, index) => {
                        const key =
                          meeting.key || meeting.name || `meeting-${index}`;
                        const label = [
                          meeting.name || key,
                          meeting.location,
                          meeting.country,
                        ]
                          .filter(Boolean)
                          .join(" · ");
                        return (
                          <option value={key} key={`${key}-${index}`}>
                            {label}
                          </option>
                        );
                      })}
                    </select>
                  </label>
                </div>

                {!filteredMeetingOptions.length && (
                  <p className="race-picker-empty">
                    {loading
                      ? "Loading events…"
                      : meetingOptions.length
                        ? `No event matches this filter for ${controls.year}.`
                        : "Event list unavailable. Refresh to retry."}
                  </p>
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
                  onChange={(event) =>
                    updateControls({ session: event.target.value })
                  }
                  aria-label="Choose session"
                >
                  {sessionChoices.map((choice) => {
                    const key = choice.key || choice.name;
                    return (
                      <option value={key} key={key}>
                        {choice.name || key}
                      </option>
                    );
                  })}
                </select>
              </label>
            </div>

            <div className="selector-sync-row">
              <button
                className="dash-btn live"
                onClick={() => loadLiveData()}
                disabled={loading || Boolean(controlError)}
              >
                <RefreshCcw size={16} />{" "}
                {loading ? "Syncing selected session" : "Sync selected session"}
              </button>
            </div>
          </section>
        </details>

        {controlError && (
          <section className="dash-warning" role="alert">
            <BadgeInfo size={18} />
            <div>
              <strong>Check timing controls.</strong>
              <p>{controlError}</p>
            </div>
          </section>
        )}

        {error && (
          <section className="dash-warning" role="alert">
            <BadgeInfo size={18} />
            <div>
              <strong>Auto-sync could not complete.</strong>
              <p>{error}</p>
            </div>
          </section>
        )}

        {loading && !payload && (
          <section className="dash-warning">
            <RefreshCcw size={18} />
            <div>
              <strong>Syncing selected timing session.</strong>
              <p>
                PitWall is checking the selected season, Grand Prix, and session
                before showing source status.
              </p>
            </div>
          </section>
        )}

        {payload && payload.ok === false && (
          <section className="dash-warning" role="alert">
            <BadgeInfo size={18} />
            <div>
              <strong>Timing unavailable for this selection.</strong>
              <p>
                {payload.reason ||
                  "The selected session could not be retrieved. Try refreshing or choose another session."}
              </p>
            </div>
          </section>
        )}

        {strategy && (
          <ObservedStrategy
            rows={leaderboard}
            available={Boolean(payload?.ok)}
            loading={loading && !payload}
          />
        )}
        {!strategy && (
          <div className="timing-density">
            <button
              className="dash-btn"
              aria-pressed={expanded}
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? "Compact timing" : "All timing details"}
            </button>
            <span>
              Phone view prioritises position, driver and interval. Expand for
              laps, tyres and telemetry.
            </span>
          </div>
        )}
        <section className="f1dash-grid">
          <Card
            id="leaderboard"
            title="Leaderboard"
            icon={<Trophy size={18} />}
            show={!strategy && settings.leaderboard}
            empty={
              !leaderboard.length &&
              "No timing rows available for this session."
            }
          >
            <div
              className="table-scroll"
              role="region"
              aria-label="Session leaderboard"
              tabIndex={0}
            >
              <table className="product-table timing-table">
                <caption className="sr-only">Session leaderboard</caption>
                <thead>
                  <tr>
                    <th scope="col">Pos</th>
                    <th scope="col">Driver</th>
                    <th scope="col">Interval</th>
                    <th scope="col">Last lap</th>
                    <th scope="col">Tyre / age</th>
                    <th scope="col">Speed</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((row, index) => (
                    <tr key={`${row.driver_number}-${index}`}>
                      <td className="position">{fmt(row.position)}</td>
                      <th scope="row">
                        <span className="driver-name">
                          <i
                            style={{
                              background: color(row.driver?.team_colour),
                            }}
                          />
                          <strong>{driverName(row)}</strong>
                          <small>
                            {fmt(row.driver?.team_name || row.team, "")}
                          </small>
                        </span>
                      </th>
                      <td>{gap(row)}</td>
                      <td>{fmt(row.lap_duration)}</td>
                      <td>
                        <TyreAgeVisual row={row} compact />
                      </td>
                      <td>{speed(row.speed, settings.metric)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card
            id="tyres"
            title="Tyres and stints"
            icon={<Waves size={18} />}
            show={!strategy && settings.tyres}
            empty={!leaderboard.length && "No tyre data available."}
          >
            <div
              className="compact-stack"
              role="region"
              aria-label="Tyre compounds and observed ages"
              tabIndex={0}
            >
              {leaderboard.map((row) => (
                <div key={`${row.driver_number}-tyre`}>
                  <strong>{driverName(row)}</strong>
                  <TyreAgeVisual row={row} />
                </div>
              ))}
            </div>
          </Card>

          <Card
            id="sectors"
            title="Mini sectors"
            icon={<MapPinned size={18} />}
            show={!strategy && settings.sectors && hasMiniSectors}
            empty={
              !leaderboard.length
                ? "Mini-sector style data is unavailable for this feed."
                : !hasMiniSectors &&
                  "This selected session does not expose mini-sector segment data in the available feed."
            }
          >
            <div
              className="sector-list"
              role="region"
              aria-label="Driver mini sectors"
              tabIndex={0}
            >
              {leaderboard
                .filter(
                  (row) =>
                    Array.isArray(row.mini_sectors) && row.mini_sectors.length,
                )
                .map((row) => (
                  <div key={`${row.driver_number}-sector`}>
                    <strong>{driverName(row)}</strong>
                    <MiniSectors row={row} />
                  </div>
                ))}
            </div>
          </Card>

          <Card
            id="weather"
            title="Weather"
            icon={<CloudRain size={18} />}
            show={settings.weather}
            empty={!weather && "No timing-feed weather data available."}
          >
            <div className="fact-grid">
              <div>
                <span>Air</span>
                <strong>{measured(weather?.air_temperature, "°C")}</strong>
              </div>
              <div>
                <span>Track</span>
                <strong>{measured(weather?.track_temperature, "°C")}</strong>
              </div>
              <div>
                <span>Humidity</span>
                <strong>{measured(weather?.humidity, "%")}</strong>
              </div>
              <div>
                <span>Rain indicator</span>
                <strong>{measured(weather?.rainfall)}</strong>
              </div>
              <div>
                <span>Wind</span>
                <strong>{measured(weather?.wind_speed, " m/s")}</strong>
              </div>
              <div>
                <span>Direction</span>
                <strong>{measured(weather?.wind_direction, "°")}</strong>
              </div>
            </div>
          </Card>

          <Card
            id="track-status"
            title="Track status"
            icon={<Activity size={18} />}
            show={settings.trackStatus}
          >
            <div
              className={cx(
                "track-status",
                settings.safetyCarColors && `track-code-${trackCode}`,
              )}
            >
              <Flag size={20} />
              <div>
                <strong>{trackStateLabel(trackCode)}</strong>
                <span>
                  {fmt(
                    trackStatus?.Message ||
                      trackStatus?.message ||
                      "No active track-status message",
                  )}
                </span>
              </div>
            </div>
          </Card>

          <Card
            id="car-metrics"
            title="Car metrics"
            icon={<Gauge size={18} />}
            show={!strategy && settings.carMetrics}
            empty={
              carMetricsMostlyMissing &&
              "Telemetry unavailable for this session."
            }
          >
            <p className="product-note">
              Latest values retained by this session feed. Archived readings are
              not race averages. Brake is the raw provider value, not a
              percentage.
            </p>
            <div
              className="table-scroll"
              role="region"
              aria-label="Car metrics"
              tabIndex={0}
            >
              <table className="product-table">
                <caption className="sr-only">Available car metrics</caption>
                <thead>
                  <tr>
                    <th scope="col">Driver</th>
                    <th scope="col">Speed</th>
                    <th scope="col">Gear</th>
                    <th scope="col">RPM</th>
                    <th scope="col">Brake (raw)</th>
                  </tr>
                </thead>
                <tbody>
                  {carMetricRows.map((row) => (
                    <tr key={`${row.driver_number}-car`}>
                      <th scope="row">{driverName(row)}</th>
                      <td>{speed(row.speed, settings.metric)}</td>
                      <td>{fmt(row.n_gear)}</td>
                      <td>{fmt(row.rpm)}</td>
                      <td>{fmt(row.brake)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card
            id="race-control"
            title="Race control"
            icon={<ShieldAlert size={18} />}
            show={settings.raceControl}
            empty={!raceControl.length && "No race-control messages available."}
          >
            <div
              className="race-control-stack"
              role="region"
              aria-label="Race control messages"
              tabIndex={0}
            >
              {raceControl.map((message, index) => (
                <article
                  className={raceControlTone(message)}
                  key={`${message.date}-${index}`}
                >
                  <div className="race-control-meta">
                    <time>{time(message.date)}</time>
                    {message.lap && <span>Lap {fmt(message.lap)}</span>}
                    {message.racing_number && (
                      <span>#{fmt(message.racing_number)}</span>
                    )}
                    {message.status && <span>{fmt(message.status)}</span>}
                  </div>
                  <strong>{fmt(message.category)}</strong>
                  <p>{fmt(message.message)}</p>
                </article>
              ))}
            </div>
          </Card>

          <Card
            id="team-radio"
            title="Team radio"
            icon={<AudioLines size={18} />}
            show={!strategy && settings.teamRadio}
            empty={
              !radio.length &&
              "No team-radio recordings available for this session."
            }
          >
            <div
              className="radio-stack"
              role="region"
              aria-label="Team radio recordings"
              tabIndex={0}
            >
              {radio.map((item, index) => {
                const row = leaderboard.find(
                  (driver) =>
                    Number(driver.driver_number) === Number(item.driver_number),
                );
                const radioDriver = row || {
                  driver_number: item.driver_number,
                  driver:
                    drivers.find(
                      (driver) =>
                        Number(driver.driver_number) ===
                        Number(item.driver_number),
                    ) || {},
                };
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

        <details className="product-details timing-provenance">
          <summary>Timing provenance & refresh details</summary>
          <div className="sync-strip">
            <span>
              Screen refreshed:{" "}
              <strong>
                {lastUpdated ? time(lastUpdated.toISOString()) : "-"}
              </strong>
            </span>
            <span>
              Mode:{" "}
              <strong>
                {payload?.timing_mode ||
                  (auto ? `auto ${streamState}` : "manual")}
              </strong>
            </span>
            <span>
              Source:{" "}
              <strong>
                {payload?.timing_source || payload?.source || "-"}
              </strong>
            </span>
            <span>
              Server fetched:{" "}
              <strong>
                {payload?.server_fetched_at
                  ? time(payload.server_fetched_at)
                  : "-"}
              </strong>
            </span>
            <span>
              Packet:{" "}
              <strong>
                {payload?.source_packet_at
                  ? dateTime(payload.source_packet_at)
                  : "-"}
              </strong>
            </span>
            <span>
              Lap:{" "}
              <strong>
                {fmt(lapCount.current_lap)}/{fmt(lapCount.total_laps)}
              </strong>
            </span>
            <span>
              Track:{" "}
              <strong>
                {fmt(
                  trackStatus?.Status ||
                    trackStatus?.Message ||
                    trackStatus?.status,
                )}
              </strong>
            </span>
          </div>
        </details>
        <details className="product-details">
          <summary>Session feed details</summary>
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
              <span>Drivers in feed</span>
              <strong>{payload ? leaderboard.length : "Checking"}</strong>
            </div>
            <div>
              <span>Radio clips</span>
              <strong>
                {playableRadio.length
                  ? `${playableRadio.length}/${radio.length}`
                  : "Unavailable"}
              </strong>
            </div>
            <div>
              <span>Selected session</span>
              <strong>
                {payload?.auto_selected_session?.session_name ||
                  payload?.session_resolution?.selected_session ||
                  fmt(session.session_name)}
              </strong>
            </div>
            <div>
              <span>Data status</span>
              <strong>
                {payload?.reason ||
                  payload?.live_fallback_reason ||
                  payload?.session_resolution?.reason ||
                  "None"}
              </strong>
            </div>
          </section>
        </details>
        <footer className="dash-footer">
          Inspired by f1-dash layout principles, but implemented independently.
          Data comes from Formula 1 timing feeds; archived or stale data is
          labelled accordingly. This site does not stream video.
        </footer>
      </section>
    </AppShell>
  );
}
