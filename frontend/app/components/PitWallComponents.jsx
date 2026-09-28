"use client";

import Link from "next/link";
import { expireLivePayload } from "../api/_lib/timing";
import { useEffect, useRef, useState } from "react";
import {
  Flag,
  ListOrdered,
  Users,
  Wrench,
  Radio,
  Database,
  ChartNoAxesCombined,
  Archive,
  CalendarDays,
} from "lucide-react";

export const navItems = [
  { href: "/", label: "Race overview", icon: CalendarDays },
  { href: "/predictions", label: "Race ranking", icon: ListOrdered },
  { href: "/drivers", label: "Drivers", icon: Users },
  { href: "/teams", label: "Constructors", icon: Flag },
  { href: "/strategy", label: "Strategy", icon: Wrench },
  { href: "/live", label: "Session timing", icon: Radio },
  { href: "/sources", label: "Data sources", icon: Database },
  { href: "/model", label: "Methodology", icon: ChartNoAxesCombined },
  { href: "/archive", label: "Results & history", icon: Archive },
];

export function AppShell({ children, active = "/" }) {
  const [menu, setMenu] = useState(false);
  const menuButton = useRef(null);
  useEffect(() => {
    if (!menu) return;
    const close = (event) => {
      if (event.key === "Escape") {
        setMenu(false);
        menuButton.current?.focus();
      }
    };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [menu]);
  return (
    <div className="race-app">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <aside className="desktop-sidebar" aria-label="PitWall navigation">
        <Link className="brand-tile" href="/" prefetch={false}>
          <span>PITWALL</span>
          <strong>Formula 1 analysis</strong>
        </Link>
        <button
          className="mobile-menu control-btn"
          ref={menuButton}
          aria-expanded={menu}
          aria-controls="primary-navigation"
          onClick={() => setMenu(!menu)}
        >
          {menu ? "Close menu" : "Menu"}
        </button>
        <nav id="primary-navigation" className={menu ? "menu-open" : ""}>
          {navItems.map(({ href, label, icon: Icon }, index) => (
            <Link
              className={`side-link ${active === href ? "active" : ""}`}
              aria-current={active === href ? "page" : undefined}
              href={href}
              prefetch={false}
              key={href}
              onClick={() => setMenu(false)}
            >
              <Icon size={18} />
              <span>{label}</span>
              <small className="nav-index" aria-hidden="true">
                {String(index + 1).padStart(2, "0")}
              </small>
            </Link>
          ))}
        </nav>
        <div className="sidebar-foot">
          Independent F1 data
          <br />
          <Link href="/sources" prefetch={false}>
            Sources & limitations
          </Link>
        </div>
      </aside>
      <div className="race-viewport">
        <header className="paddock-masthead">
          <span className="paddock-title">
            <i className="grid-mark" aria-hidden="true" />
            Formula 1 <span>/ Race centre</span>
          </span>
          <span className="paddock-caption">
            Timing. Classification. Analysis.
          </span>
        </header>
        <main id="main-content" className="race-main" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}

function expire(data) {
  data = expireLivePayload(data);
  if (!data?.current?.event || data.current.state !== "UPCOMING") return data;
  if (Date.parse(data.current.event.start_at) > Date.now()) return data;
  return {
    ...data,
    prediction: null,
    current: {
      ...data.current,
      state: "UPDATING",
      reason: "Scheduled start has passed. Refreshing session status.",
    },
  };
}
export function usePitWallData(endpoint = "/api/predictions", options = {}) {
  const [data, setData] = useState(options.initialData || null);
  const [loading, setLoading] = useState(!options.initialData);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let timedOut = false,
      active = true;
    const timeout = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 15000);
    setRefreshing(true);
    fetch(endpoint, { cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok)
          throw new Error(`Data service returned HTTP ${response.status}.`);
        const payload = await response.json();
        if (payload.ok === false)
          throw new Error("The data service is unavailable.");
        if (active) {
          setData(expire(payload));
          setError("");
        }
      })
      .catch(() => {
        if (active) {
          setData(null);
          setError(
            timedOut
              ? "The request timed out. Try again."
              : "The data service could not be reached. Try again.",
          );
        }
      })
      .finally(() => {
        clearTimeout(timeout);
        if (active) {
          setLoading(false);
          setRefreshing(false);
        }
      });
    return () => {
      active = false;
      clearTimeout(timeout);
      controller.abort();
    };
  }, [endpoint, revision]);
  useEffect(() => {
    const refresh = setInterval(() => setRevision((n) => n + 1), 60000);
    const expiry = setInterval(
      () => setData((current) => expire(current)),
      1000,
    );
    return () => {
      clearInterval(refresh);
      clearInterval(expiry);
    };
  }, []);
  return {
    data,
    loading,
    error,
    refreshing,
    refetch: () => setRevision((n) => n + 1),
  };
}
export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <header className="product-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions}
    </header>
  );
}
export function EmptyState({ title = "Data unavailable", body }) {
  return (
    <div className="product-empty">
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}
export function InlineNotice({ title, body, tone = "info", action }) {
  return (
    <div
      className={`product-notice ${tone}`}
      role={tone === "error" ? "alert" : "status"}
    >
      <strong>{title}</strong>
      <p>{body}</p>
      {action}
    </div>
  );
}
export function LoadingSkeleton() {
  return (
    <div className="product-loading" role="status" aria-live="polite">
      <span>Loading race data…</span>
      <div />
      <div />
      <div />
    </div>
  );
}
export function StatusBadge({ label, tone = "neutral" }) {
  return (
    <span className={`status-badge ${tone}`}>{label || "UNAVAILABLE"}</span>
  );
}
