"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatedTicker, AppShell, EmptyState, InlineNotice, LoadingSkeleton, Metric, normalizeQuery, PageHeader, SearchBox, SectionTitle, StatusBadge, usePitWallData } from "../components/PitWallComponents";

export default function ArchivePage() {
  const predictions = usePitWallData("/api/predictions");
  const archive = usePitWallData("/api/archive");
  const [query, setQuery] = useState("");
  const [left, setLeft] = useState(0);
  const [right, setRight] = useState(1);
  const rows = useMemo(() => {
    const q = normalizeQuery(query);
    return (archive.data?.archive || []).filter((row) => normalizeQuery(`${row.title} ${row.race_name} ${row.top_pick} ${row.top_pick_team} ${row.model_version} ${row.stage}`).includes(q));
  }, [archive.data, query]);
  useEffect(() => {
    setLeft(0);
    setRight(rows.length > 1 ? 1 : 0);
  }, [query, rows.length]);
  const a = rows[left];
  const b = rows[right] || rows[0];
  return (
    <AppShell active="/archive">
      <AnimatedTicker latest={predictions.data?.latest} />
      <PageHeader eyebrow="Archive" title="Race Archive" description="Generated briefings, model cards, prediction-vs-actual audit state, and race-to-race comparison." />
      {archive.loading && <LoadingSkeleton />}
      {archive.error && <InlineNotice title="Archive sync failed" body={archive.error} tone="error" action={<button className="control-btn" onClick={archive.refetch}>Retry</button>} />}
      {archive.data && (
        <>
          <section className="toolbar panel reveal">
            <SearchBox value={query} onChange={setQuery} placeholder="Search by race, driver, team, model, or stage" />
            <button className="control-btn" onClick={archive.refetch} disabled={archive.refreshing}>{archive.refreshing ? "Refreshing" : "Refresh archive"}</button>
          </section>
          <div className="archive-grid">
            {rows.map((row, index) => (
              <article className="panel archive-card reveal" key={archiveKey(row, index)}>
                <SectionTitle title={row.race_name || row.title} action={<StatusBadge label={row.stage} tone="red" />} />
                <div className="metric-grid">
                  <Metric label="Top Pick" value={row.top_pick || "Pending"} />
                  <Metric label="Confidence" value={row.confidence ? `${row.confidence}%` : "Pending"} />
                  <Metric label="Actual Winner" value={row.actual_winner || "No actual result yet"} />
                  <Metric label="Accuracy" value={formatAccuracy(row.accuracy)} />
                </div>
                <div className="row-actions">
                  <button className={left === index ? "control-btn active" : "control-btn"} onClick={() => setLeft(index)}>Compare left</button>
                  <button className={right === index ? "control-btn active" : "control-btn"} onClick={() => setRight(index)}>Compare right</button>
                  {row.path && <a className="control-btn" href={`/api/local-data?path=${encodeURIComponent(row.path)}`} target="_blank" rel="noreferrer">Open briefing</a>}
                </div>
              </article>
            ))}
          </div>
          {a && b && (
            <section className="panel reveal">
              <SectionTitle title="Compare Two Race Briefings" />
              <div className="compare-grid">
                {[a, b].map((row, index) => (
                  <article key={`compare-${archiveKey(row, index)}`}>
                    <h3>{row.race_name || row.title}</h3>
                    <Metric label="Stage" value={row.stage} />
                    <Metric label="Model" value={row.model_version} />
                    <Metric label="Top Pick" value={row.top_pick || "Pending"} />
                    <Metric label="Actual Winner" value={row.actual_winner || "No actual result yet"} />
                    <p>{row.correction_summary?.learning_notes || "Model correction pending."}</p>
                  </article>
                ))}
              </div>
            </section>
          )}
          {!rows.length && <EmptyState title="No archive matches" body="Try a different race, driver, team, model version, or stage." />}
        </>
      )}
    </AppShell>
  );
}

function archiveKey(row, index) {
  return [
    row?.prediction_id,
    row?.path,
    row?.target_type,
    row?.generated_at,
    index,
  ].filter(Boolean).join("::") || `archive-row-${index}`;
}

function formatAccuracy(value) {
  if (value === null || value === undefined || value === "") return "Pending";
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(1)}%` : "Pending";
}
