"use client";

import Link from "next/link";
import Image from "next/image";
import { sessionStatus } from "../lib/session-status";
import { formatISTDateTime } from "../lib/time";
import { useState } from "react";
import {
  AppShell,
  EmptyState,
  InlineNotice,
  LoadingSkeleton,
  StatusBadge,
  usePitWallData,
} from "./PitWallComponents";

const value = (n, digits = 2) =>
  n === null || n === undefined || !Number.isFinite(Number(n))
    ? "Unavailable"
    : Number(n).toFixed(digits);

function Section({ title, children, aside }) {
  return (
    <section className="product-section">
      <div className="section-heading">
        <h2>{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}
function State({ children }) {
  return <p className="product-note">{children}</p>;
}
function ResultTable({ rows = [], ranking = false }) {
  if (!rows.length)
    return (
      <EmptyState
        title="No matching drivers"
        body="Try a different name or constructor."
      />
    );
  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label={ranking ? "Predicted classification" : "Race classification"}
    >
      <table className="product-table">
        <caption className="sr-only">
          {ranking ? "Predicted classification" : "Race classification"}
        </caption>
        <thead>
          <tr>
            <th scope="col">{ranking ? "Rank" : "Pos"}</th>
            <th scope="col">Driver</th>
            <th scope="col">Constructor</th>
            <th scope="col">{ranking ? "Qualifying" : "Status"}</th>
            {!ranking && <th scope="col">Points</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.driver_id}>
              <td className="position">{ranking ? r.rank : r.position}</td>
              <th scope="row">{r.name}</th>
              <td>{r.team}</td>
              <td>
                {ranking
                  ? (r.qualifying_position ?? "Unavailable")
                  : r.status || "Unavailable"}
              </td>
              {!ranking && <td>{r.points ?? "Unavailable"}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EventHeader({ data, compact = false }) {
  const current = data.current || {},
    event = current.event;
  return (
    <section className={`event-focus${compact ? " event-focus-compact" : ""}`}>
      <div className="event-copy">
        <div className="event-kicker">
          <StatusBadge
            label={current.state || "UNAVAILABLE"}
            tone={
              current.state === "UPCOMING"
                ? "amber"
                : current.state === "LIVE"
                  ? "green"
                  : "neutral"
            }
          />
          <span>
            {event
              ? `${event.season} · Round ${event.round}`
              : "Calendar status"}
          </span>
        </div>
        <h2>{event?.name || "Race schedule unavailable"}</h2>
        <p>
          {event
            ? `${event.circuit}${event.location ? ` · ${event.location}` : ""}`
            : current.reason ||
              "The calendar provider could not be verified. Try refreshing."}
        </p>
        {event && (
          <p className="event-date">{formatISTDateTime(event.start_at)}</p>
        )}
        <div className="event-links">
          {!compact && (
            <Link prefetch={false} href="/predictions">
              View ranking <span aria-hidden="true">↗</span>
            </Link>
          )}
          <Link prefetch={false} href="/live">
            Open timing <span aria-hidden="true">↗</span>
          </Link>
        </div>
      </div>
      {event && (
        <div className="round-plate" aria-hidden="true">
          <span className="round-plate-label">Grand Prix / {event.season}</span>
          <div className="round-plate-number">
            <span>R</span>
            {String(event.round).padStart(2, "0")}
          </div>
        </div>
      )}
    </section>
  );
}
function Prediction({ data, preview = false, target = "race" }) {
  const p = data.prediction;
  const [full, setFull] = useState(false);
  const [query, setQuery] = useState("");
  if (target !== "race")
    return (
      <Section title="Sprint ranking">
        <EmptyState
          title="Sprint prediction unavailable"
          body="The validated production baseline currently covers Grand Prix races only. Sprint session times and timing remain available when supplied by the provider."
        />
      </Section>
    );
  if (!p)
    return (
      <Section title="Race ranking">
        <EmptyState
          title="Prediction unavailable"
          body={
            data.current?.state === "UPCOMING"
              ? "A ranking will be available after qualifying is published and a forecast is captured before the race starts."
              : "A pre-race ranking cannot be generated for an event that has started or whose schedule is unverified."
          }
        />
        <State>
          PitWall uses qualifying order as a transparent baseline. It does not
          publish win probabilities or confidence percentages.{" "}
          <Link prefetch={false} href="/model">
            Read the methodology
          </Link>
          .
        </State>
      </Section>
    );
  const rows = (
    preview ? p.full_grid.slice(0, 3) : full ? p.full_grid : p.top10
  ).filter((r) =>
    `${r.name} ${r.team}`.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <Section
      title={preview ? "Leading ranks" : "Predicted classification"}
      aside={<span className="muted">Post qualifying</span>}
    >
      <State>
        {p.event.name} · {p.model_version} · Captured{" "}
        {formatISTDateTime(p.generated_at)}
      </State>
      {!preview && (
        <div className="product-controls">
          <label>
            Find driver
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Name or constructor"
            />
          </label>
          <button
            className="control-btn"
            aria-pressed={full}
            onClick={() => setFull(!full)}
          >
            {full ? "Show top 10" : "Show full grid"}
          </button>
        </div>
      )}
      {rows.length ? (
        <ResultTable rows={rows} ranking />
      ) : (
        <EmptyState
          title="No matching drivers"
          body="Try a different name or constructor."
        />
      )}
      <State>
        Classification estimate based on qualifying order. Penalties, race pace,
        weather and reliability are not modeled.
      </State>
      {!preview && (
        <details className="product-details">
          <summary>Prediction provenance</summary>
          <dl className="provenance">
            <dt>Model</dt>
            <dd>{p.model_version}</dd>
            <dt>Features</dt>
            <dd>{p.feature_version}</dd>
            <dt>Data cutoff</dt>
            <dd>{formatISTDateTime(p.data_cutoff)}</dd>
            <dt>Race ID</dt>
            <dd>{p.race_id}</dd>
            <dt>Input SHA-256</dt>
            <dd>{p.input_hash}</dd>
          </dl>
        </details>
      )}
    </Section>
  );
}
function Schedule({ data }) {
  const { data: timing } = usePitWallData("/api/f1timing?fast=1");
  const event = data.current?.event;
  return (
    <Section
      title="Weekend schedule"
      aside={<span className="muted">All times IST (UTC+05:30)</span>}
    >
      {event ? (
        <ul className="session-list">
          {event.sessions.map((s, i) => (
            <li key={`${s.name}-${i}`}>
              <span className="session-heading">
                {s.name}
                <StatusBadge {...sessionStatus(s, event, data, timing)} />
              </span>
              <time dateTime={s.start_at || undefined}>
                {formatISTDateTime(s.start_at)}
              </time>
            </li>
          ))}
        </ul>
      ) : (
        <State>No verified upcoming weekend is available.</State>
      )}
      <State>
        Schedule supplied by{" "}
        <a
          href="https://api.jolpi.ca/ergast/f1/"
          target="_blank"
          rel="noreferrer"
        >
          Jolpica
        </a>
        . Sessions can change. Past scheduled starts remain unconfirmed until
        results or session evidence establish completion.
      </State>
    </Section>
  );
}
function LatestResult({ data, compact = false }) {
  const result = data.latest_result;
  return (
    <Section
      title="Latest available race result"
      aside={<StatusBadge label="COMPLETED" tone="red" />}
    >
      {result ? (
        <>
          <h3>{result.event.name}</h3>
          <State>
            {formatISTDateTime(result.event.start_at)} · Source retrieved{" "}
            {formatISTDateTime(result.source?.retrieved_at)}
          </State>
          <ResultTable rows={compact ? result.rows.slice(0, 5) : result.rows} />
          {compact && (
            <Link prefetch={false} className="text-link" href="/drivers">
              Full classification →
            </Link>
          )}
        </>
      ) : (
        <EmptyState
          title="Results unavailable"
          body="No validated race classification is available from the provider."
        />
      )}
    </Section>
  );
}
function Calendar({ data }) {
  const [all, setAll] = useState(false);
  const events = data.calendar || [];
  const currentIndex = events.findIndex(
    (e) => e.id === data.current?.event?.id,
  );
  const visible = all || currentIndex < 0 ? events : events.slice(currentIndex);
  return (
    <Section
      title="Season calendar"
      aside={
        <button
          className="control-btn"
          aria-pressed={all}
          onClick={() => setAll(!all)}
        >
          {all ? "Show remaining" : "Show full season"}
        </button>
      }
    >
      <div className="calendar-list">
        {visible.map((e) => (
          <article
            key={e.id}
            className={e.id === data.current?.event?.id ? "selected" : ""}
          >
            <span className="muted">
              R{e.round} · {e.season}
            </span>
            <strong>{e.name}</strong>
            <span>{formatISTDateTime(e.start_at)}</span>
            <small>
              {e.sessions.some((s) => s.name === "Sprint")
                ? "Sprint weekend"
                : ""}
            </small>
          </article>
        ))}
      </div>
      {!data.calendar?.length && (
        <State>Calendar unavailable. No static fallback is used.</State>
      )}
    </Section>
  );
}
function Drivers({ data }) {
  const [query, setQuery] = useState("");
  const result = data.latest_result;
  return (
    <>
      <Section title="Driver classification">
        <State>
          {result
            ? `${result.event.name} · ${formatISTDateTime(result.event.start_at)} · Historical result`
            : "Results unavailable"}
          . Final classified positions include non-finishers and
          disqualifications as supplied by the provider.
        </State>
        <label className="search-label">
          Find driver or team
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search classification"
          />
        </label>
        {result?.rows.length ? (
          <ResultTable
            rows={result.rows.filter((r) =>
              `${r.name} ${r.team}`.toLowerCase().includes(query.toLowerCase()),
            )}
          />
        ) : (
          <EmptyState
            title="Driver data unavailable"
            body="The result provider has not returned a valid classification."
          />
        )}
      </Section>
    </>
  );
}
function Teams({ data }) {
  const result = data.latest_result;
  const grouped = new Map();
  for (const row of result?.rows || []) {
    if (!grouped.has(row.team)) grouped.set(row.team, []);
    grouped.get(row.team).push(row);
  }
  return (
    <Section title="Constructor race results">
      <State>
        {result
          ? `${result.event.name} · Historical classification`
          : "No race classification available"}
        . Points below are the sum of the published driver points for this race;
        they are not season standings.
      </State>
      {[...grouped].map(([team, rows]) => (
        <details className="product-details" key={team}>
          <summary>
            {team}
            <span>
              {rows.every(
                (r) =>
                  r.points !== null &&
                  r.points !== undefined &&
                  Number.isFinite(Number(r.points)),
              )
                ? `${rows.reduce((n, r) => n + Number(r.points), 0)} pts`
                : "Points unavailable"}
            </span>
          </summary>
          <ResultTable rows={rows} />
        </details>
      ))}
      {!grouped.size && (
        <EmptyState
          title="Constructor data unavailable"
          body="No team names or statistics are substituted when results are missing."
        />
      )}
    </Section>
  );
}
function Metrics({ report }) {
  const b = report?.baseline,
    c = report?.candidate;
  if (report?.status !== "AVAILABLE")
    return (
      <EmptyState
        title="Backtest unavailable"
        body="No verified chronological evaluation report has been published."
      />
    );
  return (
    <>
      <State>
        {report.test_period} reserved test period · {b.races} eligible races.
        Lower MAE is better; rank correlation closer to 1 is better. Both
        methods use the same races.
      </State>
      <div
        className="table-scroll"
        tabIndex={0}
        role="region"
        aria-label="Backtest comparison"
      >
        <table className="product-table">
          <thead>
            <tr>
              <th>Method</th>
              <th>MAE (places)</th>
              <th>Rank correlation</th>
              <th>Winner first</th>
              <th>Winner in top 3</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["Qualifying order · production", b],
              ["Qualifying + recent form · candidate", c],
            ].map(([name, m]) => (
              <tr key={name}>
                <th scope="row">{name}</th>
                <td>{value(m.mae)}</td>
                <td>{value(m.spearman, 3)}</td>
                <td>
                  {m.winner_hit == null
                    ? "Unavailable"
                    : `${value(m.winner_hit * 100, 1)}%`}
                </td>
                <td>
                  {m.winner_top3 == null
                    ? "Unavailable"
                    : `${value(m.winner_top3 * 100, 1)}%`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <State>
        These are measured frequencies from a retrospective reconstruction. They
        are not probabilities for the upcoming race.
      </State>
    </>
  );
}
function Model({ data }) {
  const report = data.backtest;
  return (
    <>
      <Section title="Methodology">
        <h3>Qualifying order, with a measurable baseline</h3>
        <p>
          The production ranking predicts final classification order using the
          published qualifying positions. It has no trained parameters, random
          simulation, or confidence score. A simple candidate combines
          qualifying rank with a driver’s mean finish over their previous five
          races.
        </p>
        <dl className="provenance">
          <dt>Production version</dt>
          <dd>{data.model?.version || "Unavailable"}</dd>
          <dt>Feature version</dt>
          <dd>{data.model?.feature_version || "Unavailable"}</dd>
          <dt>Forecasts captured</dt>
          <dd>{data.predictions.length}</dd>
          <dt>Evaluations recorded</dt>
          <dd>{data.evaluations.length}</dd>
        </dl>
        <State>
          No original legacy forecast has adequate immutable provenance to count
          toward genuine forecast performance.
        </State>
      </Section>
      <Section title="Chronological comparison">
        <Metrics report={report} />
        {report?.promotion && (
          <InlineNotice
            title={
              report.promotion.eligible_for_review
                ? "Candidate eligible for review"
                : "Candidate not promoted"
            }
            body={report.promotion.reason}
          />
        )}
        <State>
          The development period is 2019–2023; the reserved test period is
          2024–2025. Prior race results are appended only after each simulated
          forecast. Historical qualification records can contain later
          corrections.
        </State>
      </Section>
      <Section title="Limits and improvement process">
        <ol className="method-list">
          <li>
            Capture a forecast with its model, feature version, input hash and
            data cutoff before the race.
          </li>
          <li>
            Retrieve the published classification. Keep the forecast unchanged;
            save a separate evaluation revision.
          </li>
          <li>
            Develop a candidate using older races. Compare it with the baseline
            on the same unseen races.
          </li>
          <li>
            Require at least 30 test races across two seasons, 5% lower MAE, no
            season regression and no rank-correlation regression before review.
          </li>
          <li>
            Promote through a reviewed version change. Repeated tuning requires
            a new untouched test period.
          </li>
        </ol>
        <ul className="method-list">
          {report?.limitations?.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      </Section>
      {report?.races?.length > 0 && (
        <Section title="Race-level evidence">
          <details className="product-details">
            <summary>
              Inspect {report.races.length} reconstructed races and{" "}
              {report.excluded.length} exclusions
            </summary>
            <div
              className="table-scroll"
              tabIndex={0}
              role="region"
              aria-label="Backtest comparison"
            >
              <table className="product-table">
                <thead>
                  <tr>
                    <th>Race</th>
                    <th>Split</th>
                    <th>Baseline MAE</th>
                    <th>Candidate MAE</th>
                  </tr>
                </thead>
                <tbody>
                  {report.races.map((r) => (
                    <tr key={r.race_id}>
                      <th scope="row">
                        {r.season} · {r.name}
                      </th>
                      <td>{r.split}</td>
                      <td>{value(r.baseline.mae)}</td>
                      <td>{value(r.candidate.mae)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ul className="method-list">
              {report.excluded.map((r, i) => (
                <li key={i}>
                  {r.race_id || r.file}: {r.reason}
                </li>
              ))}
            </ul>
          </details>
        </Section>
      )}
    </>
  );
}
function Archive({ data }) {
  return (
    <>
      <LatestResult data={data} />
      <Section title="Captured forecasts">
        <State>
          {new Set(data.predictions.map((p) => p.race_id)).size} races with
          pre-race captures ·{" "}
          {data.evaluated_races ??
            new Set(data.evaluations.map((e) => e.race_id)).size}{" "}
          evaluated races. Captures are immutable; corrected results create new
          evaluation revisions. Retrospective backtests do not count toward this
          history.
        </State>
        {data.predictions.length ? (
          data.predictions.map((p) => (
            <details key={p.prediction_id} className="product-details">
              <summary>
                {p.event.name} · {formatISTDateTime(p.generated_at)}
              </summary>
              <State>
                {p.model_version} · Data cutoff{" "}
                {formatISTDateTime(p.data_cutoff)}
              </State>
              <ResultTable rows={p.full_grid} ranking />
              {data.evaluations
                .filter((e) => e.prediction_id === p.prediction_id)
                .map((e) => (
                  <div key={e.evaluation_id}>
                    <h3>Evaluation · {formatISTDateTime(e.evaluated_at)}</h3>
                    <State>
                      MAE {value(e.metrics.mae)} places · Rank correlation{" "}
                      {value(e.metrics.spearman, 3)}
                    </State>
                    <ResultTable rows={e.actual} />
                  </div>
                ))}
              {!data.evaluations.some(
                (e) => e.prediction_id === p.prediction_id,
              ) && (
                <State>
                  Evaluation pending: a complete matching classification has not
                  been recorded.
                </State>
              )}
            </details>
          ))
        ) : (
          <EmptyState
            title="No verified forecasts captured yet"
            body="New forecasts are recorded after qualifying, before the scheduled race start. Historical backtests are shown separately in Methodology."
          />
        )}
      </Section>
      <Section title="Legacy prediction archive">
        <State>
          These rankings were saved by an earlier implementation. Their input
          cutoff and immutable model provenance are missing, so they are
          excluded from validated performance. Unsupported probabilities have
          been withdrawn.
        </State>
        {data.legacy_archive?.map((p, i) => (
          <details className="product-details" key={`${p.generated_at}-${i}`}>
            <summary>
              {p.title || "Legacy briefing"}
              <span>{formatISTDateTime(p.generated_at)}</span>
            </summary>
            <State>
              UNVERIFIED LEGACY · Recorded event start{" "}
              {formatISTDateTime(p.start_at)}
            </State>
            <ResultTable rows={p.rows} ranking />
          </details>
        ))}
      </Section>
    </>
  );
}
function Sources({ data }) {
  const unique = [
    ...new Map([...data.sources].reverse().map((s) => [s.url, s])).values(),
  ];
  return (
    <>
      <Section title="Retrieval evidence">
        <State>
          Retrieval time is when PitWall received a response. It is not the
          provider’s publication time. Cached or historical data never
          establishes a live session.
        </State>
        <div className="source-list">
          {unique.map((s) => (
            <article key={s.url}>
              <StatusBadge label={s.status} />
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.url}
              </a>
              <span>{formatISTDateTime(s.retrieved_at)}</span>
            </article>
          ))}
        </div>
        {!unique.length && (
          <EmptyState
            title="Sources unavailable"
            body="No successful retrieval evidence is available."
          />
        )}
      </Section>
      <Section title="FIA document archive">
        <State>
          Saved document metadata, checked{" "}
          {formatISTDateTime(data.fia_archive?.checked_at)}. These links have
          not been reverified by the current request. Original authority,
          verification and error fields are retained below; they do not
          establish current availability.
        </State>
        {data.fia_archive?.documents?.length ? (
          <details className="product-details">
            <summary>
              Inspect {data.fia_archive.documents.length} saved document records
            </summary>
            {data.fia_archive.documents.map((doc, i) => (
              <article className="fia-record" key={doc.document_id || i}>
                <h3>
                  {/^https:\/\//.test(doc.source_url || "") ? (
                    <a href={doc.source_url} target="_blank" rel="noreferrer">
                      {doc.title}
                    </a>
                  ) : (
                    doc.title
                  )}
                </h3>
                <State>
                  Published {formatISTDateTime(doc.published_at)} · Retrieved{" "}
                  {formatISTDateTime(doc.fetched_at)}
                </State>
                <dl className="provenance">
                  <dt>Source authority</dt>
                  <dd>{doc.source_authority || "Unknown"}</dd>
                  <dt>Saved source status</dt>
                  <dd>{doc.source_status || "Unknown"}</dd>
                  <dt>Verification status</dt>
                  <dd>{doc.verification_status || "Unknown"}</dd>
                  <dt>Saved flags</dt>
                  <dd>
                    Official: {String(doc.is_official)} · Verified:{" "}
                    {String(doc.is_verified)} · Stale: {String(doc.is_stale)}
                  </dd>
                  <dt>Errors</dt>
                  <dd>
                    {doc.error_summary || doc.parse_error || "None recorded"}
                  </dd>
                </dl>
              </article>
            ))}
          </details>
        ) : (
          <State>Document metadata unavailable.</State>
        )}
        {data.fia_archive?.errors?.length > 0 && (
          <State>
            {data.fia_archive.errors
              .map((e) => (typeof e === "string" ? e : JSON.stringify(e)))
              .join("; ")}
          </State>
        )}
      </Section>
      <Section title="Data providers">
        <dl className="provider-list">
          <dt>
            <a href="https://github.com/jolpica/jolpica-f1">Jolpica F1</a>
          </dt>
          <dd>
            Community-maintained calendar, qualifying and classified results.
            Data may be delayed or revised. The calendar is refreshed at most
            every five minutes; no result is assumed from elapsed time.
          </dd>
          <dt>
            <a href="https://livetiming.formula1.com/static/Index.json">
              Formula 1 timing
            </a>
          </dt>
          <dd>
            Timing session index, timing packets, weather, race control and team
            radio where available. This is an undocumented service with no
            availability guarantee. Historical sessions are labeled archive.
          </dd>
          <dt>
            <a href="https://www.fia.com/documents">FIA documents</a>
          </dt>
          <dd>
            Official classifications and decisions are authoritative for
            sporting disputes. PitWall’s numerical model does not interpret
            regulations or infer performance from document titles.
          </dd>
        </dl>
        <State>
          PitWall is an independent project, unaffiliated with Formula 1 or the
          FIA. Provider content retains its owners’ rights; availability does
          not grant redistribution rights. No paid OpenF1 access is required for
          the published ranking.
        </State>
      </Section>
    </>
  );
}
const TITLES = {
  home: [
    "Race overview",
    "Schedule, classifications and traceable race rankings.",
  ],
  predictions: [
    "Race ranking",
    "Qualifying-based rankings, with the evidence behind each forecast.",
  ],
  drivers: [
    "Drivers",
    "Published race classifications, including finish status.",
  ],
  teams: [
    "Constructors",
    "Results grouped by the constructor recorded for the race.",
  ],
  strategy: ["Strategy", "Observed context and the limits of prediction."],
  model: [
    "Methodology & evaluation",
    "How rankings are made, tested and retained.",
  ],
  archive: [
    "Results & history",
    "Race results, captured forecasts and the legacy archive.",
  ],
  sources: ["Data sources", "Provider status and retrieval evidence."],
  assistant: ["About PitWall", "An independent Formula 1 data project."],
};
export default function ProductView({
  view = "home",
  initialData,
  target = "race",
}) {
  const { data, loading, error, refetch, refreshing } = usePitWallData(
    "/api/predictions",
    { initialData },
  );
  const [title, description] = TITLES[view];
  const isRaceView = view === "home" || view === "predictions";
  return (
    <AppShell active={view === "home" ? "/" : `/${view}`}>
      <div className={isRaceView ? "race-intro" : "product-intro"}>
        {isRaceView && (
          <div className="event-art" aria-hidden="true">
            <Image
              src="/pitwall-racing-hero.png"
              alt=""
              fill
              sizes="(max-width: 900px) 100vw, (max-width: 1760px) calc(100vw - 224px), 1536px"
              preload
            />
          </div>
        )}
        <header className="product-header">
          <div>
            <span className="eyebrow">
              PITWALL / {view === "home" ? "OVERVIEW" : view.toUpperCase()}
            </span>
            <h1>
              {view === "predictions" && target === "sprint"
                ? "Sprint ranking"
                : title}
            </h1>
            <p>{description}</p>
          </div>
          <button
            className="control-btn"
            onClick={refetch}
            disabled={refreshing}
          >
            {refreshing ? "Refreshing…" : "Refresh data"}
          </button>
        </header>
        {loading && <LoadingSkeleton />}
        {error && (
          <InlineNotice
            title="Data request failed"
            body={error}
            tone="error"
            action={
              <button onClick={refetch} className="control-btn">
                Retry
              </button>
            }
          />
        )}
        {data?.warnings
          ?.filter((s) => !s.startsWith("Prediction unavailable:"))
          .map((s) => (
            <InlineNotice key={s} title="Data notice" body={s} tone="warning" />
          ))}
        {data && isRaceView && (
          <EventHeader data={data} compact={view === "predictions"} />
        )}
      </div>
      {data && (
        <>
          {view === "home" && (
            <>
              <div className="overview-columns">
                <div>
                  <Prediction data={data} preview />
                  <LatestResult data={data} compact />
                </div>
                <Schedule data={data} />
              </div>
              <Calendar data={data} />
            </>
          )}
          {view === "predictions" && (
            <>
              <Prediction data={data} target={target} />
            </>
          )}
          {view === "drivers" && <Drivers data={data} />}{" "}
          {view === "teams" && <Teams data={data} />}{" "}
          {view === "model" && <Model data={data} />}{" "}
          {view === "archive" && <Archive data={data} />}{" "}
          {view === "sources" && <Sources data={data} />}{" "}
          {view === "assistant" && (
            <Section title="Evidence first">
              <p>
                PitWall presents published Formula 1 data and deterministic race
                rankings. A conversational or machine-learning assistant is not
                currently enabled.
              </p>
              <Link prefetch={false} href="/model">
                Read the methodology →
              </Link>
            </Section>
          )}
          <p className="freshness-note">
            Calendar and results are checked separately from the saved analysis
            snapshot. Last successful retrieval:{" "}
            {formatISTDateTime(data.current_data_retrieved_at)}. Retrieval time
            is not a live session timestamp.
          </p>
          <footer className="product-footer">
            <span>Independent Formula 1 analysis</span>
            <span>
              Analysis snapshot: {formatISTDateTime(data.generated_at)}
            </span>
            <Link prefetch={false} href="/sources">
              Sources & limitations
            </Link>
          </footer>
        </>
      )}
    </AppShell>
  );
}
