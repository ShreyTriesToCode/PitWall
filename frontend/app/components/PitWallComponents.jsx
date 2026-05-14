"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
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
  { href: "/live", label: "Live Telemetry", icon: Radio },
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
        <span><i className="live-dot mini" /> Live-ready</span>
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
            <span>{item.label.replace("Command Center", "Command").replace("Prediction Board", "Predict").replace("Live Telemetry", "Live").replace("System Config", "Model").replace("Strategy Wall", "Strategy")}</span>
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

export function DataFreshnessBadge({ value }) {
  const date = new Date(value || "");
  const label = Number.isNaN(date.getTime()) ? "Freshness pending" : `Updated ${date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}`;
  return <StatusBadge label={label} tone="green" />;
}

export function SourceHealthCard({ health }) {
  const sources = health?.sources || [];
  return (
    <section className="panel reveal">
      <SectionTitle icon={Activity} title="Source Health" action={<StatusBadge label={health?.status || "Pending"} tone="green" />} />
      <div className="source-list">
        {sources.length ? sources.map((source) => (
          <div className="source-row" key={source.source}>
            <span>{source.source}</span>
            <ConfidenceBar value={source.score} />
            <small>{source.status}</small>
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

export function PredictionCard({ item, onOpen, compact = false }) {
  return (
    <article className={cx("prediction-card reveal", compact && "compact")}>
      <button className="prediction-open-hitbox" type="button" onClick={() => onOpen?.(item)} aria-label={`Open ${item.name} prediction detail`} />
      <div className="rank-chip">P{item.rank}</div>
      <div className="prediction-card-title">
        <h3>{item.name}</h3>
        <p>{item.team}</p>
      </div>
      <FavoriteButton id={item.driver_id} />
      <ConfidenceBar value={item.confidence} label="Confidence" />
      <div className="prediction-grid">
        <Metric label="Score" value={fmt(item.score)} />
        <Metric label="Win" value={pct(item.win_probability)} />
        <Metric label="Podium" value={pct(item.podium_probability)} />
        <Metric label="Top 10" value={pct(item.top10_probability)} />
      </div>
      <p className="card-reason">{item.reason_tags?.[0] || item.reason || "Model estimate"}</p>
      {!compact && <TagRow tags={[...(item.reason_tags || []), ...(item.weakness_tags || []).slice(0, 2)]} />}
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
              <th>Rank</th><th>Driver</th><th>Team</th><th>Score</th><th>Confidence</th><th>Win</th><th>Podium</th><th>Top 10</th><th>Range</th><th>2026 Boost</th>
            </tr>
          </thead>
          <tbody>
            {predictions.map((item) => (
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
                <td>{pct(item.win_probability)}</td>
                <td>{pct(item.podium_probability)}</td>
                <td>{pct(item.top10_probability)}</td>
                <td>{item.best_case_finish}-{item.worst_case_finish}</td>
                <td>{pct(item.energy_boost_advantage_score)}</td>
              </tr>
            ))}
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
  useEffect(() => {
    if (!driver) return undefined;
    const onKey = (event) => {
      if (event.key === "Escape") onClose?.();
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKey);
    };
  }, [driver, onClose]);

  if (!driver) return null;
  return (
    <>
      <button className="drawer-backdrop" aria-label="Close driver details" onClick={onClose} />
      <aside className="detail-drawer" role="dialog" aria-modal="true" aria-labelledby="driver-detail-title">
        <button className="icon-btn close" onClick={onClose} aria-label="Close"><X size={18} /></button>
        <span className="eyebrow">Prediction Detail</span>
        <h2 id="driver-detail-title">{driver.name}</h2>
        <p>{driver.team} · P{driver.rank} · {driver.best_case_finish}-{driver.worst_case_finish} finish range</p>
        <div className="prediction-grid">
          <Metric label="Agreement" value={pct(driver.model_agreement_score)} />
          <Metric label="Attack" value={pct(driver.attack_potential_score)} />
          <Metric label="Defend Risk" value={pct(driver.defend_risk_score)} />
          <Metric label="Active Aero" value={pct(driver.active_aero_suitability_score)} />
        </div>
        <ComponentScoreBars scores={driver.component_scores} />
        <TagRow tags={driver.reason_tags || []} />
        <TagRow tags={driver.weakness_tags || []} tone="warning" />
        <p className="drawer-note">{driver.short_explanation || driver.reason}</p>
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

export const Icons = { CalendarDays, ChevronRight, Clock, Flag, Gauge, LineChart, Timer, Trophy, Zap };
