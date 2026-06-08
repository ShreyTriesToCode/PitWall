"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  Archive,
  BarChart3,
  Bot,
  CalendarDays,
  ChevronRight,
  Clock,
  Copy,
  Factory,
  Flag,
  Gauge,
  Heart,
  Home,
  LineChart,
  Radio,
  Search,
  ShieldAlert,
  SlidersHorizontal,
  Sparkles,
  Star,
  Timer,
  Trophy,
  Users,
  X,
  Zap,
} from "lucide-react";
import { F1_2026_CALENDAR, activeCalendarRound } from "../data/f1Calendar2026";

export const navItems = [
  { href: "/", label: "Command Center", icon: Home },
  { href: "/predictions", label: "Prediction Board", icon: Trophy },
  { href: "/drivers", label: "Driver Analysis", icon: Users },
  { href: "/teams", label: "Team Analysis", icon: Factory },
  { href: "/strategy", label: "Strategy Wall", icon: SlidersHorizontal },
  { href: "/live", label: "Timing Replay", icon: Radio },
  { href: "/sources", label: "Source Health", icon: Activity },
  { href: "/model", label: "System Config", icon: Bot },
  { href: "/archive", label: "Archive", icon: Archive },
];

const transitionLiveries = [
  {
    team: "Mercedes",
    fullName: "Mercedes-AMG PETRONAS Formula One Team",
    accent: "#00d2be",
    image: "https://media.formula1.com/image/upload/c_lfill%2Cw_3392/q_auto/v1740000001/common/f1/2026/mercedes/2026mercedescarright.webp",
    source: "https://www.formula1.com/en/teams/mercedes",
  },
  {
    team: "Ferrari",
    fullName: "Scuderia Ferrari HP",
    accent: "#e10600",
    image: "https://media.formula1.com/image/upload/c_lfill%2Cw_3392/q_auto/v1740000001/common/f1/2026/ferrari/2026ferraricarright.webp",
    source: "https://www.formula1.com/en/teams/ferrari",
  },
  {
    team: "McLaren",
    fullName: "McLaren Mastercard F1 Team",
    accent: "#ff8700",
    image: "https://media.formula1.com/image/upload/c_lfill%2Cw_3392/q_auto/v1740000001/common/f1/2026/mclaren/2026mclarencarright.webp",
    source: "https://www.formula1.com/en/teams/mclaren",
  },
  {
    team: "Red Bull",
    fullName: "Oracle Red Bull Racing",
    accent: "#ffcc00",
    image: "https://media.formula1.com/image/upload/c_lfill%2Cw_3392/q_auto/v1740000001/common/f1/2026/redbullracing/2026redbullracingcarright.webp",
    source: "https://www.formula1.com/en/teams/red-bull-racing",
  },
  {
    team: "Alpine",
    fullName: "BWT Alpine Formula One Team",
    accent: "#ff87bc",
    image: "https://media.formula1.com/image/upload/c_lfill%2Cw_3392/q_auto/v1740000001/common/f1/2026/alpine/2026alpinecarright.webp",
    source: "https://www.formula1.com/en/teams/alpine",
  },
  {
    team: "Haas",
    fullName: "TGR Haas F1 Team",
    accent: "#e10600",
    image: "https://media.formula1.com/image/upload/c_lfill%2Cw_3392/q_auto/v1740000001/common/f1/2026/haas/2026haascarright.webp",
    source: "https://www.formula1.com/en/teams/haas",
  },
  {
    team: "Racing Bulls",
    fullName: "Visa Cash App Racing Bulls Formula One Team",
    accent: "#1535d1",
    image: "https://media.formula1.com/image/upload/c_lfill%2Cw_3392/q_auto/v1740000001/common/f1/2026/racingbulls/2026racingbullscarright.webp",
    source: "https://www.formula1.com/en/teams/racing-bulls",
  },
  {
    team: "Williams",
    fullName: "Atlassian Williams F1 Team",
    accent: "#005aff",
    image: "https://media.formula1.com/image/upload/c_lfill%2Cw_3392/q_auto/v1740000001/common/f1/2026/williams/2026williamscarright.webp",
    source: "https://www.formula1.com/en/teams/williams",
  },
  {
    team: "Audi",
    fullName: "Audi Revolut F1 Team",
    accent: "#e4002b",
    image: "https://media.formula1.com/image/upload/c_lfill%2Cw_3392/q_auto/v1740000001/common/f1/2026/audi/2026audicarright.webp",
    source: "https://www.formula1.com/en/teams/audi",
  },
  {
    team: "Cadillac",
    fullName: "Cadillac Formula 1 Team",
    accent: "#b8b8b8",
    image: "https://media.formula1.com/image/upload/c_lfill%2Cw_3392/q_auto/v1740000001/common/f1/2026/cadillac/2026cadillaccarright.webp",
    source: "https://www.formula1.com/en/teams/cadillac",
  },
  {
    team: "Aston Martin",
    fullName: "Aston Martin Aramco Formula One Team",
    accent: "#b6ff00",
    image: "https://media.formula1.com/image/upload/c_lfill%2Cw_3392/q_auto/v1740000001/common/f1/2026/astonmartin/2026astonmartincarright.webp",
    source: "https://www.formula1.com/en/teams/aston-martin",
  },
];

export function cx(...parts) {
  return parts.filter(Boolean).join(" ");
}

export function fmt(value, suffix = "") {
  const n = Number(value);
  if (!Number.isFinite(n)) return "Not enough data";
  return `${n.toFixed(n >= 10 ? 1 : 2)}${suffix}`;
}

export function pct(value) {
  return fmt(value, "%");
}

export function stageLabel(value) {
  return String(value || "pending").replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

function friendlyFetchError(error, timedOut = false) {
  if (timedOut) return "The data request timed out. Check your connection and try again.";
  const message = String(error?.message || error || "");
  if (message.includes("Failed to fetch")) return "The data source could not be reached. Try refreshing in a moment.";
  return message || "Unable to load data.";
}

export function normalizeQuery(value) {
  return String(value || "").trim().toLowerCase().replace(/\s+/g, " ");
}

export function usePitWallData(endpoint = "/api/predictions", options = {}) {
  const timeoutMs = Number(options.timeoutMs || 15000);
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState({ loading: true, data: null, error: "", warning: "", refreshing: false });
  useEffect(() => {
    const controller = new AbortController();
    let didTimeout = false;
    const timeout = setTimeout(() => {
      didTimeout = true;
      controller.abort();
    }, timeoutMs);
    setState((prev) => ({ ...prev, loading: !prev.data, refreshing: Boolean(prev.data), error: "", warning: "" }));
    fetch(endpoint, { cache: "no-store", signal: controller.signal })
      .then(async (res) => {
        const payload = await res.json().catch(() => null);
        if (!res.ok) throw new Error(payload?.error || payload?.message || `HTTP ${res.status}`);
        return payload;
      })
      .then((data) => {
        const warning = data?.ok === false
          ? data?.error || data?.reason || "This data source returned a fallback response."
          : "";
        setState({ loading: false, refreshing: false, data, error: "", warning });
      })
      .catch((error) => {
        if (error.name !== "AbortError" || didTimeout) {
          setState((prev) => ({
            loading: false,
            refreshing: false,
            data: prev.data,
            error: friendlyFetchError(error, didTimeout),
            warning: "",
          }));
        }
      })
      .finally(() => {
        clearTimeout(timeout);
      });
    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, [endpoint, reloadKey, timeoutMs]);
  return { ...state, refetch: () => setReloadKey((value) => value + 1) };
}

export function AppShell({ children, active = "/" }) {
  const [showLaunchText, setShowLaunchText] = useState(false);
  const activeItem = navItems.find((item) => item.href === active) || navItems[0];

  useEffect(() => {
    try {
      if (!sessionStorage.getItem("pitwall-lights-out-seen")) {
        setShowLaunchText(true);
        sessionStorage.setItem("pitwall-lights-out-seen", "1");
      }
    } catch {
      setShowLaunchText(true);
    }
  }, []);

  return (
    <div className="race-app">
      <Preloader label="PitWall Ready" showLaunchText={showLaunchText} />
      <DesktopSidebar active={active} />
      <div className="race-viewport">
        <div className="digital-gutter left" aria-hidden="true" />
        <div className="digital-gutter right" aria-hidden="true" />
        <ShellTopBar activeItem={activeItem} />
        <main className="race-main">
          {children}
        </main>
      </div>
      <MobileBottomNav active={active} />
    </div>
  );
}

export function ShellTopBar({ activeItem }) {
  const [clock, setClock] = useState("--:--:--");
  const Icon = activeItem?.icon || Activity;

  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="shell-topbar">
      <div className="shell-context">
        <span><Icon size={16} /> PitWall</span>
        <strong>{activeItem?.label || "Command Center"}</strong>
      </div>
      <div className="shell-telemetry" aria-label="System status">
        <span className="header-lights" aria-hidden="true">{[0, 1, 2, 3, 4].map((n) => <i key={n} />)}</span>
        <span><i className="live-dot mini" /> Timing-aware</span>
        <span>Local {clock}</span>
        <span>2026 Boost</span>
      </div>
    </header>
  );
}

export function DesktopSidebar({ active }) {
  return (
    <aside className="desktop-sidebar" aria-label="PitWall navigation">
      <Link className="brand-tile" href="/">
        <span>PITWALL</span>
        <strong>Formula 1 intelligence</strong>
        <small>V01-BETA</small>
      </Link>
      <nav>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link className={cx("side-link", active === item.href && "active")} href={item.href} key={item.href}>
              <Icon size={18} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <Link className="sidebar-scan-btn" href="/model">Initiate scans</Link>
    </aside>
  );
}

export function MobileBottomNav({ active }) {
  return (
    <nav className="mobile-bottom-nav" aria-label="Mobile navigation">
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <Link className={cx(active === item.href && "active")} href={item.href} key={item.href}>
            <Icon size={19} />
            <span>{item.label.replace("Command Center", "Command").replace("Prediction Board", "Predict").replace("Timing Replay", "Timing").replace("System Config", "Model").replace("Strategy Wall", "Strategy")}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <header className="page-header reveal">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="header-actions">{actions}</div>}
    </header>
  );
}

export function AnimatedTicker({ latest }) {
  const top = latest?.top10?.[0];
  const source = latest?.source_health || latest?.source_status;
  const items = [
    `Current race: ${latest?.race_name || latest?.event_title || "Waiting for briefing"}`,
    `Next session: ${latest?.target_type || "race"}`,
    `Top prediction: ${top?.name || "Pending"}`,
    `Rain risk: ${latest?.weather?.rain || "Not enough data"}`,
    `Safety-car risk: ${latest?.safety_car || "Pending"}`,
    `Model: ${latest?.model_version || "Unavailable"}`,
    `Sources: ${source?.status || "Checking"}`,
    `Updated: ${latest?.generated || latest?.generated_iso || "Pending"}`,
  ];
  return (
    <section className="ticker" aria-label="Race control ticker">
      <div className="ticker-track">
        {[...items, ...items].map((item, index) => <span key={`${item}-${index}`}>{item}</span>)}
      </div>
    </section>
  );
}

export function Preloader({ label = "Initializing PitWall", showLaunchText = false }) {
  const [hidden, setHidden] = useState(false);
  const [livery, setLivery] = useState(transitionLiveries[0]);
  useEffect(() => {
    setLivery(transitionLiveries[Math.floor(Math.random() * transitionLiveries.length)]);
  }, []);
  useEffect(() => {
    const id = setTimeout(() => setHidden(true), showLaunchText ? 2450 : 1550);
    return () => clearTimeout(id);
  }, [showLaunchText]);
  if (hidden) return null;
  return (
    <div className={cx("preloader", showLaunchText && "launch-copy")} aria-live="polite">
      <div className="race-lights">{[0, 1, 2, 3, 4].map((n) => <span key={n} />)}</div>
      <TransitionCar livery={livery} />
      <strong>{label}</strong>
      {showLaunchText && <p>It's lights out and away we go</p>}
    </div>
  );
}

function TransitionCar({ livery }) {
  return (
    <div
      className="transition-car"
      style={{
        "--car-accent": livery.accent,
      }}
      aria-hidden="true"
      data-livery-source={livery.source}
    >
      <img src={livery.image} alt="" loading="eager" decoding="async" />
    </div>
  );
}

export function Countdown({ startIso }) {
  const [time, setTime] = useState(["--", "--", "--"]);
  useEffect(() => {
    const target = new Date(startIso || "");
    if (Number.isNaN(target.getTime())) return;
    const tick = () => {
      const diff = Math.max(0, target.getTime() - Date.now());
      const sec = Math.floor(diff / 1000);
      setTime([
        String(Math.floor(sec / 86400)).padStart(2, "0"),
        String(Math.floor((sec % 86400) / 3600)).padStart(2, "0"),
        String(Math.floor((sec % 3600) / 60)).padStart(2, "0"),
      ]);
    };
    tick();
    const id = setInterval(tick, 30000);
    return () => clearInterval(id);
  }, [startIso]);
  return (
    <div className="countdown-grid" aria-label="Countdown">
      {["Days", "Hours", "Minutes"].map((label, i) => <div key={label}><strong>{time[i]}</strong><span>{label}</span></div>)}
    </div>
  );
}

export function RaceHero({ latest }) {
  const top = latest?.top10?.slice(0, 3) || [];
  return (
    <section className="race-hero reveal">
      <div className="speed-lines" />
      <div className="hero-copy">
        <span className="active-mode-tag">{stageLabel(latest?.stage)} · {latest?.target_type || "Race"}</span>
        <span className="eyebrow">Race Control</span>
        <h2>{latest?.race_name || latest?.event_title || "PitWall"}</h2>
        <p>{latest?.circuit || "Circuit pending"} · {latest?.city || "City pending"}, {latest?.country || "Country pending"}</p>
        <div className="hero-badges">
          <StatusBadge label={latest?.model_version || "Model pending"} tone="red" />
          <DataFreshnessBadge value={latest?.generated_iso} />
        </div>
      </div>
      <div className="hero-panel">
        <Countdown startIso={latest?.start_iso} />
        <div className="top-three">
          {top.map((item) => <PredictionMini key={item.driver_id} item={item} />)}
        </div>
      </div>
    </section>
  );
}

export function OfficialCalendarStrip({ latest, generatedTargets = [] }) {
  const active = activeCalendarRound();
  const targetTypes = new Set(generatedTargets.map((target) => target.target_type));
  return (
    <div className="official-calendar">
      <div className="calendar-current">
        <span className="eyebrow">Official 2026 Calendar</span>
        <strong>Round {active.round}: {active.name}</strong>
        <small>{active.circuit} · {active.city}, {active.country}</small>
      </div>
      <div className="official-calendar-strip" aria-label="Official F1 2026 calendar">
        {F1_2026_CALENDAR.map((race) => {
          const isActive = race.round === active.round || latest?.race_name?.toLowerCase?.().includes(race.name.replace("Grand Prix", "").trim().toLowerCase());
          return (
            <article className={cx("calendar-race", isActive && "active")} key={`${race.round}-${race.name}`}>
              <span>R{race.round}</span>
              <strong>{race.name}</strong>
              <small>{dateRange(race.start, race.end)} · {race.city}</small>
              {race.sprint && <b>Sprint Weekend</b>}
              <div className="calendar-actions">
                {race.sprint && <PredictionTargetLink type="sprint" enabled={targetTypes.has("sprint")} />}
                <PredictionTargetLink type="race" enabled={targetTypes.has("race") || latest?.target_type === "race"} />
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function PredictionTargetLink({ type, enabled }) {
  const label = type === "sprint" ? "Sprint prediction" : "Race prediction";
  if (!enabled) return <span className="target-link disabled">{label} pending</span>;
  return <Link className="target-link" href={`/predictions?target=${type}`}>{label}</Link>;
}

function dateRange(start, end) {
  const a = new Date(`${start}T00:00:00Z`);
  const b = new Date(`${end}T00:00:00Z`);
  if (Number.isNaN(a.getTime()) || Number.isNaN(b.getTime())) return "Date pending";
  return `${a.toLocaleDateString([], { month: "short", day: "numeric" })}-${b.toLocaleDateString([], { day: "numeric" })}`;
}

export function PredictionMini({ item }) {
  return (
    <article className="mini-prediction">
      <span>P{item.rank}</span>
      <strong>{item.name}</strong>
      <small>{item.team} · {pct(item.confidence)}</small>
    </article>
  );
}

export function StatusBadge({ label, tone = "neutral" }) {
  return <span className={cx("status-badge", tone)}>{label}</span>;
}

export function statusTone(status, score) {
  const text = String(status || "").toLowerCase();
  if (["available", "healthy", "fresh", "ok", "success"].some((word) => text.includes(word))) return "green";
  if (["fallback", "stale", "partial", "degraded", "delayed", "waiting", "limited"].some((word) => text.includes(word))) return "amber";
  if (["missing", "unavailable", "error", "fail", "auth", "forbidden", "invalid"].some((word) => text.includes(word))) return "red";
  const numericScore = Number(score);
  if (Number.isFinite(numericScore)) {
    if (numericScore >= 70) return "green";
    if (numericScore >= 40) return "amber";
    return "red";
  }
  return "neutral";
}

export function DataFreshnessBadge({ value }) {
  const date = new Date(value || "");
  const label = Number.isNaN(date.getTime()) ? "Freshness pending" : `Updated ${date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}`;
  return <StatusBadge label={label} tone="green" />;
}

export function SourceHealthCard({ health }) {
  const sources = health?.sources || [];
  const overallScore = Number(health?.overall_score ?? health?.score ?? health?.confidence);
  const generatedAt = health?.generated_at || health?.last_checked_at || health?.last_success_at;
  const openf1 = sources.find((source) => normalizeQuery(source.source).includes("openf1")) || health?.openf1 || health?.OpenF1;
  const warnings = [
    health?.fallback_reason,
    health?.live_fallback_reason,
    openf1?.auth_restricted ? "OpenF1 authenticated access required; using fallback timing/session sources." : "",
    health?.fia_source_discovery_status ? `FIA: ${stageLabel(health.fia_source_discovery_status)}` : "",
  ].filter(Boolean);
  return (
    <section className="panel reveal">
      <SectionTitle icon={Activity} title="Source Health" action={<StatusBadge label={health?.status || "Pending"} tone={statusTone(health?.status, overallScore)} />} />
      <div className="metric-grid compact">
        <Metric label="Overall Score" value={Number.isFinite(overallScore) ? pct(overallScore) : "Pending"} />
        <Metric label="Generated" value={generatedAt ? new Date(generatedAt).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "Pending"} />
      </div>
      {warnings.length > 0 && <div className="tag-row warning">{warnings.slice(0, 3).map((warning) => <span key={warning}>{warning}</span>)}</div>}
      <div className="source-list">
        {sources.length ? sources.map((source) => (
          <div className="source-row" key={source.source}>
            <span>{source.source}</span>
            <ConfidenceBar value={source.score} />
            <small><StatusBadge label={source.status || "Unknown"} tone={statusTone(source.status, source.score)} /></small>
          </div>
        )) : <EmptyState title="Source data unavailable" body="The UI is waiting for generated source-health JSON." />}
      </div>
    </section>
  );
}

export function SectionTitle({ icon: Icon = Flag, title, action }) {
  return (
    <div className="section-title">
      <h2><Icon size={18} /> {title}</h2>
      {action}
    </div>
  );
}

export function ConfidenceBar({ value, label }) {
  const n = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <div className="confidence">
      {label && <span>{label}</span>}
      <i style={{ width: `${n}%` }} />
      <b>{fmt(n, "%")}</b>
    </div>
  );
}

export function ComponentScoreBars({ scores = {}, limit = 8 }) {
  const rows = Object.entries(scores)
    .filter(([, value]) => Number.isFinite(Number(value)))
    .sort((a, b) => Number(b[1]) - Number(a[1]))
    .slice(0, limit);
  return <div className="component-bars">{rows.map(([key, value]) => <ConfidenceBar key={key} value={value} label={key.replaceAll("_", " ")} />)}</div>;
}

function trustTone(item) {
  const label = String(item?.prediction_trust_label || "").toLowerCase();
  const score = Number(item?.prediction_trust_score);
  if (label.includes("high") || score >= 72) return "green";
  if (label.includes("low") || score < 48) return "red";
  return "amber";
}

function disagreementTone(item) {
  const level = String(item?.model_disagreement_level || "low").toLowerCase();
  if (level === "high") return "red";
  if (level === "medium") return "amber";
  return "green";
}

export function PredictionCard({ item, onOpen, compact = false }) {
  return (
    <article className={cx("prediction-card reveal", compact && "compact")}>
      <button className="prediction-open-hitbox" type="button" onClick={() => onOpen?.(item)} aria-label={`Open ${item.name} prediction detail`} />
      <div className="rank-chip">P{item.rank}</div>
      <div className="prediction-card-title">
        <h3>{item.name}</h3>
        <p>{item.team}</p>
      </div>
      <div className="prediction-badges">
        <StatusBadge label={item.prediction_trust_label || "Trust pending"} tone={trustTone(item)} />
        <StatusBadge label={`${stageLabel(item.model_disagreement_level || "low")} disagreement`} tone={disagreementTone(item)} />
      </div>
      <FavoriteButton id={item.driver_id} />
      <ConfidenceBar value={item.confidence} label="Confidence" />
      <div className="prediction-grid">
        <Metric label="Score" value={fmt(item.score)} />
        <Metric label="Trust" value={pct(item.prediction_trust_score)} />
        <Metric label="Win" value={pct(item.win_probability)} />
        <Metric label="Podium" value={pct(item.podium_probability)} />
        <Metric label="Top 10" value={pct(item.top10_probability)} />
        <Metric label="Expected" value={`P${item.predicted_finish_position ?? item.predicted_finish ?? item.likely_finish ?? item.rank}`} />
      </div>
      <p className="card-reason">{item.ai_explanation?.simple_explanation || item.reason_tags?.[0] || item.reason || "Model estimate"}</p>
      {!compact && <TagRow tags={[...(item.reason_tags || []), ...(item.weakness_tags || []).slice(0, 2), ...(item.model_disagreement_reasons || []).slice(0, 2)]} />}
    </article>
  );
}

export function PredictionTable({ predictions, onOpen }) {
  return (
    <>
      <div className="timing-table-wrap">
        <table className="timing-table">
          <thead>
            <tr>
              <th>Rank</th><th>Driver</th><th>Team</th><th>Score</th><th>Confidence</th><th>Trust</th><th>Disagreement</th><th>Win</th><th>Podium</th><th>Top 10</th><th>Range</th>
            </tr>
          </thead>
          <tbody>
            {predictions.map((item) => {
              const range = Array.isArray(item.position_range) ? item.position_range : [item.best_case_finish, item.worst_case_finish];
              return (
              <tr key={item.driver_id} onClick={() => onOpen?.(item)} tabIndex={0} onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onOpen?.(item);
                }
              }}>
                <td>P{item.rank}</td>
                <td><strong>{item.name}</strong><small>{item.reason_tags?.[0]}</small></td>
                <td>{item.team}</td>
                <td>{fmt(item.score)}</td>
                <td>{pct(item.confidence)}</td>
                <td>{pct(item.prediction_trust_score)}<small>{item.prediction_trust_label}</small></td>
                <td><StatusBadge label={item.model_disagreement_level || "low"} tone={disagreementTone(item)} /></td>
                <td>{pct(item.win_probability)}</td>
                <td>{pct(item.podium_probability)}</td>
                <td>{pct(item.top10_probability)}</td>
                <td>{range.filter((value) => value !== undefined && value !== null).join("-") || "Pending"}</td>
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="mobile-prediction-list">
        {predictions.map((item) => <PredictionCard item={item} key={item.driver_id} onOpen={onOpen} compact />)}
      </div>
    </>
  );
}

export function DriverExplainabilityDrawer({ driver, onClose }) {
  const closeRef = useRef(null);
  const drawerRef = useRef(null);

  useEffect(() => {
    if (!driver) return undefined;
    const previousFocus = document.activeElement;
    const onKey = (event) => {
      if (event.key === "Escape") {
        onClose?.();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(drawerRef.current?.querySelectorAll("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])") || [])
        .filter((element) => !element.hasAttribute("disabled"));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    window.setTimeout(() => closeRef.current?.focus?.(), 0);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKey);
      previousFocus?.focus?.();
    };
  }, [driver, onClose]);

  if (!driver) return null;
  const strategy = driver.expected_strategy || {};
  const explanation = driver.explanation || {};
  const aiExplanation = driver.ai_explanation || {};
  const freshness = driver.data_freshness || {};
  const sourceNotes = driver.source_notes || {};
  const sourceWarnings = Array.isArray(sourceNotes.warnings) ? sourceNotes.warnings : [];
  const missingSignals = driver.missing_feature_groups?.length ? driver.missing_feature_groups : driver.evidence_status?.missing || [];
  const availableSignals = driver.available_feature_groups?.length ? driver.available_feature_groups : driver.evidence_status?.available || [];
  const details = [
    ["Predicted finish", `P${driver.predicted_finish_position ?? driver.predicted_finish ?? driver.rank ?? "-"}`],
    ["Top 10 probability", pct(driver.top10_probability ?? driver.points_probability)],
    ["Win probability", pct(driver.win_probability)],
    ["Podium probability", pct(driver.podium_probability)],
    ["Points probability", pct(driver.points_probability ?? driver.top10_probability)],
    ["DNF risk", pct(driver.dnf_probability)],
    ["Fastest lap", pct(driver.fastest_lap_probability)],
    ["Recent form", pct(driver.component_scores?.driver_form ?? driver.component_scores?.current_season_recent_form)],
    ["Qualifying strength", pct(driver.component_scores?.qualifying ?? driver.component_scores?.timing_starting_grid)],
    ["Race pace strength", pct(driver.component_scores?.race_pace ?? driver.component_scores?.timing_lap_pace)],
    ["Teammate comparison", driver.teammate_reference ? `${driver.teammate_reference} · ${fmt(driver.teammate_prediction_gap)}` : "Not enough data"],
    ["Weather sensitivity", pct(driver.component_scores?.weather_adaptation)],
  ];
  const explanationRows = [
    ["Pace", explanation.pace],
    ["Strategy", explanation.strategy],
    ["Tyres", explanation.tyres],
    ["Weather", explanation.weather],
    ["Risk", explanation.risk],
    ["Qualifying", explanation.qualifying],
  ].filter(([, value]) => value);

  return (
    <>
      <button className="drawer-backdrop" aria-label="Close driver details" onClick={onClose} />
      <aside className="detail-drawer" role="dialog" aria-modal="true" aria-labelledby="driver-detail-title" ref={drawerRef}>
        <button ref={closeRef} className="icon-btn close" onClick={onClose} aria-label="Close"><X size={18} /></button>
        <div className="driver-detail-content">
          <span className="eyebrow">Driver Detail</span>
          <h2 id="driver-detail-title">{driver.name}</h2>
          <p>{driver.team} · P{driver.rank} · {(driver.position_range || [driver.best_case_finish, driver.worst_case_finish]).join("-")} finish range</p>

          <div className="prediction-grid">
            <Metric label="Agreement" value={pct(driver.model_agreement_score)} />
            <Metric label="Trust" value={`${pct(driver.prediction_trust_score)} · ${driver.prediction_trust_label || "Trust pending"}`} />
            <Metric label="Disagreement" value={stageLabel(driver.model_disagreement_level || "low")} />
            <Metric label="Attack" value={pct(driver.attack_potential_score)} />
            <Metric label="Defend Risk" value={pct(driver.defend_risk_score)} />
            <Metric label="Confidence" value={driver.confidence_label || pct(driver.confidence)} />
          </div>

          <section className="detail-section">
            <h3>AI-style explanation</h3>
            <div className="drawer-list">
              <p><strong>Simple</strong><span>{aiExplanation.simple_explanation || driver.simple_explanation || "Deterministic explanation unavailable."}</span></p>
              <p><strong>Expert</strong><span>{aiExplanation.expert_explanation || driver.expert_explanation || "Not enough structured evidence for expert explanation."}</span></p>
              <p><strong>Risk</strong><span>{aiExplanation.risk_summary || "No deterministic risk summary available."}</span></p>
              <p><strong>Upside</strong><span>{aiExplanation.upside_case || "Upside case unavailable."}</span></p>
              <p><strong>Downside</strong><span>{aiExplanation.downside_case || "Downside case unavailable."}</span></p>
            </div>
          </section>

          <section className="detail-section">
            <h3>Prediction probabilities</h3>
            <div className="detail-metric-grid">
              {details.map(([label, value]) => <Metric label={label} value={value} key={label} />)}
            </div>
          </section>

          <section className="detail-section">
            <h3>Expected strategy</h3>
            <div className="detail-strategy">
              <Metric label="Stops" value={strategy.stops ?? "Pending"} />
              <Metric label="First pit lap" value={strategy.first_pit_lap ?? "Pending"} />
              <Metric label="Compound sequence" value={(strategy.compound_sequence || []).join(" > ") || "Pending"} />
            </div>
            {strategy.basis && <p className="drawer-note">{strategy.basis}</p>}
          </section>

          <section className="detail-section">
            <h3>Why the model ranked this driver here</h3>
            <ComponentScoreBars scores={driver.component_scores} />
            <TagRow tags={driver.reason_tags || []} />
            <TagRow tags={driver.weakness_tags || []} tone="warning" />
            <TagRow tags={driver.model_disagreement_reasons || []} tone="warning" />
            <div className="drawer-list">
              {explanationRows.map(([label, value]) => <p key={label}><strong>{label}</strong><span>{value}</span></p>)}
              <p><strong>Model agreement</strong><span>{aiExplanation.model_agreement_note || driver.trust_explanation || "Agreement note unavailable."}</span></p>
              <p><strong>Scenario impact</strong><span>{aiExplanation.scenario_note || "Scenario note unavailable."}</span></p>
            </div>
          </section>

          <section className="detail-section">
            <h3>Missing and available signals</h3>
            <div className="prediction-grid">
              <Metric label="Available groups" value={availableSignals.length} />
              <Metric label="Missing groups" value={missingSignals.length} />
              <Metric label="Missing penalty" value={fmt(driver.missing_data_penalty_total)} />
              <Metric label="Stage limits" value={driver.stage_limitations?.length || 0} />
            </div>
            <TagRow tags={missingSignals} tone="warning" />
            <TagRow tags={driver.stage_limitations || []} tone="warning" />
            <p className="drawer-note">{aiExplanation.missing_data_note || "Missing-data note unavailable."}</p>
          </section>

          <section className="detail-section">
            <h3>Risk notes</h3>
            <p className="drawer-note">{driver.short_explanation || driver.reason || "Model estimate based on currently available race data."}</p>
            <TagRow tags={(driver.strategy_annotations || []).map((item) => item.label)} tone="warning" />
          </section>

          <section className="detail-section">
            <h3>Source notes</h3>
            <div className="drawer-list">
              <p><strong>Generated</strong><span>{freshness.generated_at || driver.generated_at || "Pending"}</span></p>
              <p><strong>Stage</strong><span>{freshness.stage || driver.stage || "Pending"}</span></p>
              <p><strong>Source health</strong><span>{sourceNotes.source_health || freshness.source_health_status || "Pending"}</span></p>
            </div>
            <TagRow tags={sourceWarnings} tone="warning" />
            <p className="drawer-note">{aiExplanation.source_health_note || "Source health note unavailable."}</p>
          </section>
        </div>
      </aside>
    </>
  );
}

export function MobileBottomSheet({ item, onClose }) {
  return <DriverExplainabilityDrawer driver={item} onClose={onClose} />;
}

export function StrategyPanel({ strategy }) {
  return (
    <section className="panel reveal">
      <SectionTitle icon={Gauge} title="Strategy Risk" action={<StatusBadge label={`${fmt(strategy?.risk_meter, "%")} risk`} tone="amber" />} />
      <div className="metric-grid">
        <Metric label="Chaos" value={pct(strategy?.strategy_chaos_score)} />
        <Metric label="Circuit Difficulty" value={pct(strategy?.circuit_difficulty_score)} />
        <Metric label="Qualifying Importance" value={pct(strategy?.qualifying_importance_score)} />
        <Metric label="Track Evolution" value={strategy?.track_evolution_indicator || "Pending"} />
      </div>
      <p className="panel-note">{strategy?.pit_window || "Pit window unavailable until more stint history is available."}</p>
    </section>
  );
}

export function ScenarioCards({ scenarios = {} }) {
  return (
    <section className="scenario-grid">
      {Object.entries(scenarios).map(([key, scenario]) => (
        <article className="panel scenario-card reveal" key={key}>
          <SectionTitle icon={Sparkles} title={scenario.label || stageLabel(key)} />
          <ol>
            {(scenario.top10 || []).slice(0, 5).map((row) => <li key={`${key}-${row.driver_id}`}><span>P{row.rank}</span><strong>{row.name}</strong><small>{fmt(row.scenario_score)}</small></li>)}
          </ol>
          <p>{scenario.notes}</p>
        </article>
      ))}
    </section>
  );
}

export function ModelMetricCard({ label, value, icon: Icon = BarChart3 }) {
  return <article className="metric-card reveal"><Icon size={18} /><span>{label}</span><strong>{value ?? "Pending"}</strong></article>;
}

export function RaceControlTimeline({ items = [] }) {
  const rows = items.length ? items : ["Data contract generated", "Source health checked", "Prediction board normalized", "Waiting for official result audit"];
  return <div className="timeline">{rows.map((item, i) => <div key={`${item}-${i}`}><span>{String(i + 1).padStart(2, "0")}</span><p>{typeof item === "string" ? item : item.message}</p></div>)}</div>;
}

export function TeamRadioTimeline({ rows = [] }) {
  return <RaceControlTimeline items={rows.length ? rows : ["Team radio unavailable for this session"]} />;
}

export function EmptyState({ title = "No data yet", body = "The next generated briefing will populate this panel." }) {
  return <div className="empty-state" role="status"><span><ShieldAlert size={22} /></span><strong>{title}</strong><p>{body}</p></div>;
}

export function InlineNotice({ title = "Heads up", body, tone = "info", action }) {
  return (
    <div className={cx("inline-notice", tone)} role={tone === "error" ? "alert" : "status"}>
      <ShieldAlert size={18} />
      <div>
        <strong>{title}</strong>
        {body && <p>{body}</p>}
      </div>
      {action}
    </div>
  );
}

export function LoadingSkeleton() {
  return <div className="skeleton-grid" aria-label="Loading content">{Array.from({ length: 6 }).map((_, i) => <span className="skeleton" key={i} />)}</div>;
}

export function Metric({ label, value }) {
  return <div className="metric"><span>{label}</span><strong>{value ?? "Pending"}</strong></div>;
}

export function TagRow({ tags = [], tone = "" }) {
  if (!tags.length) return null;
  return <div className={cx("tag-row", tone)}>{tags.slice(0, 8).map((tag) => <span key={tag}>{tag}</span>)}</div>;
}

export function SearchBox({ value, onChange, placeholder = "Search" }) {
  const hasValue = Boolean(String(value || "").length);
  return (
    <label className="search-box">
      <Search size={17} />
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} aria-label={placeholder} />
      {hasValue && <button type="button" aria-label="Clear search" onClick={() => onChange("")}><X size={15} /></button>}
    </label>
  );
}

export function CopySummaryButton({ text }) {
  const [state, setState] = useState("idle");
  return (
    <button className="control-btn" onClick={async () => {
      const value = text || "PitWall summary unavailable";
      try {
        if (!navigator.clipboard?.writeText) throw new Error("Clipboard permission unavailable");
        await navigator.clipboard.writeText(value);
        setState("copied");
      } catch {
        setState("failed");
      } finally {
        setTimeout(() => setState("idle"), 1600);
      }
    }}>
      <Copy size={16} /> {state === "copied" ? "Copied" : state === "failed" ? "Copy unavailable" : "Copy analyst summary"}
    </button>
  );
}

function readPinnedIds() {
  try {
    const ids = JSON.parse(localStorage.getItem("pitwall-pins") || "[]");
    return Array.isArray(ids) ? ids.filter(Boolean) : [];
  } catch {
    return [];
  }
}

function writePinnedIds(ids) {
  try {
    localStorage.setItem("pitwall-pins", JSON.stringify([...new Set(ids.filter(Boolean))]));
    window.dispatchEvent(new CustomEvent("pitwall-pins-change", { detail: ids }));
  } catch {}
}

export function usePinnedIds() {
  const [pins, setPins] = useState([]);
  useEffect(() => {
    setPins(readPinnedIds());
    const sync = () => setPins(readPinnedIds());
    const custom = (event) => setPins(Array.isArray(event.detail) ? event.detail : readPinnedIds());
    window.addEventListener("storage", sync);
    window.addEventListener("pitwall-pins-change", custom);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("pitwall-pins-change", custom);
    };
  }, []);
  return pins;
}

export function FavoriteButton({ id, label = "Pin favorite" }) {
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    setSaved(readPinnedIds().includes(id));
  }, [id]);
  return (
    <button className={cx("icon-btn", saved && "active")} onClick={(event) => {
      event.stopPropagation();
      const pins = new Set(readPinnedIds());
      saved ? pins.delete(id) : pins.add(id);
      const next = [...pins];
      writePinnedIds(next);
      setSaved(!saved);
    }} aria-label={label} aria-pressed={saved} type="button">
      {saved ? <Star size={17} /> : <Heart size={17} />}
    </button>
  );
}

export function useFilteredDrivers(predictions, query) {
  return useMemo(() => {
    const q = normalizeQuery(query);
    if (!q) return predictions || [];
    return (predictions || []).filter((item) => normalizeQuery(`${item.name} ${item.team} ${item.driver_id}`).includes(q));
  }, [predictions, query]);
}

export const Icons = { CalendarDays, ChevronRight, Clock, Flag, Gauge, LineChart, ShieldAlert, Sparkles, Timer, Trophy, Zap };
