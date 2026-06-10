"use client";

import { useMemo, useState } from "react";
import {
  actualResultAvailable,
  AnimatedTicker,
  AppShell,
  CompactTable,
  DataStateBadge,
  DeveloperOnlyPanel,
  EmptyState,
  InlineNotice,
  LoadingSkeleton,
  Metric,
  normalizeQuery,
  PageHeader,
  SearchBox,
  SectionCard,
  StatusBadge,
  useDeveloperMode,
  usePitWallData,
} from "../components/PitWallComponents";

export default function ArchivePage() {
  const predictions = usePitWallData("/api/predictions");
  const archive = usePitWallData("/api/archive");
  const status = usePitWallData("/api/model-status");
  const [query, setQuery] = useState("");
  const [stageFilter, setStageFilter] = useState("all");
  const [actualFilter, setActualFilter] = useState("all");
  const [selectedIds, setSelectedIds] = useState([]);
  const [developerMode, toggleDeveloperMode] = useDeveloperMode();

  const rows = useMemo(() => {
    const q = normalizeQuery(query);
    return dedupeRows(archive.data?.archive || [])
      .filter((row) => normalizeQuery(`${row.title} ${row.race_name} ${row.top_pick} ${row.top_pick_team} ${row.model_version} ${row.stage}`).includes(q))
      .filter((row) => stageFilter === "all" || normalizeQuery(row.stage) === normalizeQuery(stageFilter))
      .filter((row) => actualFilter === "all" || comparisonForRow(row).status === actualFilter);
  }, [archive.data, query, stageFilter, actualFilter]);

  const grouped = useMemo(() => groupRows(rows), [rows]);
  const archiveStatus = archive.data?.model_status || status.data || {};
  const latestActualComparison = archive.data?.actual_result_comparison || {};
  const selectedRows = selectedIds.map((id) => rows.find((row) => archiveKey(row) === id)).filter(Boolean);
  const stages = useMemo(() => Array.from(new Set(dedupeRows(archive.data?.archive || []).map((row) => row.stage).filter(Boolean))).sort(), [archive.data]);

  function toggleSelected(row) {
    const id = archiveKey(row);
    setSelectedIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current.slice(-1), id]);
  }

  return (
    <AppShell active="/archive">
      <AnimatedTicker latest={predictions.data?.latest} />
      <PageHeader eyebrow="Archive" title="Race Archive" description="Race-grouped briefings, model versions, prediction-vs-actual state, and opt-in comparison." />
      {archive.loading && <LoadingSkeleton />}
      {archive.error && <InlineNotice title="Archive sync failed" body={archive.error} tone="error" action={<button className="control-btn" onClick={archive.refetch}>Retry</button>} />}
      {archive.data && (
        <>
          <section className="toolbar panel compact-toolbar reveal">
            <SearchBox value={query} onChange={setQuery} placeholder="Search race, driver, model, or stage" />
            <label className="compact-filter"><span>Stage</span><select value={stageFilter} onChange={(event) => setStageFilter(event.target.value)}><option value="all">All stages</option>{stages.map((stage) => <option value={stage} key={stage}>{stage}</option>)}</select></label>
            <label className="compact-filter"><span>Actual result</span><select value={actualFilter} onChange={(event) => setActualFilter(event.target.value)}><option value="all">Any status</option><option value="available">Available</option><option value="pending">Pending</option><option value="unavailable">Unavailable</option><option value="incomplete">Incomplete</option></select></label>
            <button className="control-btn" onClick={archive.refetch} disabled={archive.refreshing}>{archive.refreshing ? "Refreshing" : "Refresh"}</button>
          </section>

          <section className="dashboard-grid compact-dashboard">
            <SectionCard title="Archive Summary">
              <div className="metric-grid compact">
                <Metric label="Unique briefings" value={rows.length} />
                <Metric label="Races" value={grouped.length} />
                <Metric label="Corrections" value={archiveStatus.correction_log_summary?.count ?? "Pending"} />
                <Metric label="Latest actuals" value={latestActualComparison.status || "Pending"} />
              </div>
            </SectionCard>
            <SectionCard title="Post-Race Review">
              {archiveStatus.correction_log_summary?.post_race_ai_review?.best_call
                ? <p className="panel-note">{archiveStatus.correction_log_summary.post_race_ai_review.best_call}</p>
                : <EmptyState title="No completed post-race audit" body="PitWall only shows winner match and recall after trusted actual result rows are available." />}
            </SectionCard>
          </section>

          <div className="archive-race-list">
            {grouped.map(({ race, records }) => (
              <SectionCard key={race} title={race} className="archive-race-group" action={<DataStateBadge status={overallActualStatus(records)} label={overallActualStatus(records)} />}>
                <CompactTable
                  rows={records}
                  getKey={(row) => archiveKey(row)}
                  columns={[
                    { header: "Compare", render: (row) => <button className={selectedIds.includes(archiveKey(row)) ? "control-btn active mini" : "control-btn mini"} type="button" onClick={(event) => { event.stopPropagation(); toggleSelected(row); }}>{selectedIds.includes(archiveKey(row)) ? "Selected" : "Select"}</button> },
                    { header: "Stage", render: (row) => row.stage || row.target_type || "Pending" },
                    { header: "Model Version", render: (row) => shortModel(row.model_version) },
                    { header: "Top Pick", render: (row) => row.top_pick || "Pending" },
                    { header: "Confidence", render: (row) => formatPercentValue(row.confidence ?? row.top_pick_confidence) },
                    { header: "Actual Status", render: (row) => <DataStateBadge status={comparisonForRow(row).status} /> },
                    { header: "Actual Winner", render: (row) => actualResultAvailable(comparisonForRow(row)) ? comparisonForRow(row).actual_winner?.name : "Pending trusted result" },
                    { header: "Top 10 Recall", render: (row) => comparisonForRow(row).status === "available" ? formatRecall(comparisonForRow(row).top10_recall) : "Pending" },
                  ]}
                  onRow={toggleSelected}
                />
              </SectionCard>
            ))}
          </div>

          {selectedRows.length === 2 ? (
            <SectionCard title="Compare Selected Briefings" action={<StatusBadge label="2 selected" tone="green" />}>
              <div className="compare-grid compact-compare">
                {selectedRows.map((row) => {
                  const comparison = comparisonForRow(row);
                  return (
                    <article key={`compare-${archiveKey(row)}`}>
                      <h3>{row.race_name || row.title}</h3>
                      <Metric label="Selected Archive Race" value={row.race_name || row.title} />
                      <Metric label="Stage" value={row.stage || "Pending"} />
                      <Metric label="Model Version" value={row.model_version || "Pending"} />
                      <Metric label="Top Pick" value={row.top_pick || "Pending"} />
                      <Metric label="Actual Result Status" value={comparison.status || "pending"} />
                      <Metric label="Actual Winner" value={actualResultAvailable(comparison) ? comparison.actual_winner?.name : "Pending trusted result"} />
                      <Metric label="Top 10 Recall" value={comparison.status === "available" ? formatRecall(comparison.top10_recall) : "Pending"} />
                      <p>{comparisonNote(comparison)}</p>
                    </article>
                  );
                })}
              </div>
            </SectionCard>
          ) : (
            <SectionCard title="Comparison" className="compact-empty-panel">
              <EmptyState title="Select two briefings" body="Choose two race briefings or model versions from the grouped archive rows to compare them." />
            </SectionCard>
          )}

          <DeveloperOnlyPanel enabled={developerMode} toggle={toggleDeveloperMode} title="Archive developer links">
            <div className="podium-list compact">
              {rows.filter((row) => row.path).slice(0, 12).map((row) => (
                <article key={`dev-${archiveKey(row)}`}><strong>{row.race_name || row.title}</strong><a className="control-btn mini" href={`/api/local-data?path=${encodeURIComponent(row.path)}`} target="_blank" rel="noreferrer">Open briefing JSON</a></article>
              ))}
            </div>
          </DeveloperOnlyPanel>

          {!rows.length && <EmptyState title="No archive matches" body="Try a different race, model version, actual-result status, or stage." />}
        </>
      )}
    </AppShell>
  );
}

function archiveKey(row) {
  return [
    row?.race_name || row?.title,
    row?.target_type,
    row?.stage || row?.prediction_stage,
    row?.model_version,
    row?.prediction_id || row?.path || row?.generated_at,
  ].filter(Boolean).map((value) => String(value).toLowerCase()).join("::");
}

function dedupeRows(rows) {
  const map = new Map();
  rows.forEach((row) => {
    const key = [
      row?.race_name || row?.title,
      row?.target_type,
      row?.stage || row?.prediction_stage,
      row?.model_version,
    ].filter(Boolean).map((value) => String(value).toLowerCase()).join("::");
    const current = map.get(key);
    if (!current || scoreRow(row) > scoreRow(current)) map.set(key || archiveKey(row), row);
  });
  return Array.from(map.values());
}

function scoreRow(row) {
  const comparison = comparisonForRow(row);
  return (comparison.status === "available" ? 100 : 0) + (row?.path ? 10 : 0) + (Date.parse(row?.generated_at || row?.generated || "") || 0) / 1000000000000;
}

function groupRows(rows) {
  const groups = rows.reduce((acc, row) => {
    const race = row?.race_name || row?.title || "Unknown race";
    (acc[race] ||= []).push(row);
    return acc;
  }, {});
  return Object.entries(groups).map(([race, records]) => ({ race, records })).sort((a, b) => a.race.localeCompare(b.race));
}

function comparisonForRow(row) {
  return row?.actual_result_comparison || row?.briefing?.actual_result_comparison || {
    status: row?.actual_winner ? "available" : "pending",
    actual_winner: row?.actual_winner ? { name: row.actual_winner } : {},
    top10_recall: null,
    warnings: ["Trusted actual-result comparison is pending or unavailable for this archive row."],
  };
}

function comparisonNote(comparison) {
  if (comparison?.status === "available" && actualResultAvailable(comparison)) {
    const winner = comparison.winner_hit ? "Predicted winner matched the trusted result." : "Predicted winner did not match the trusted result.";
    return `${winner} Position MAE: ${comparison.metrics?.mae ?? "pending"}.`;
  }
  return comparison?.warnings?.[0] || "Trusted actual classification is pending or unavailable.";
}

function overallActualStatus(records) {
  if (records.some((row) => comparisonForRow(row).status === "available")) return "available";
  if (records.some((row) => comparisonForRow(row).status === "incomplete")) return "incomplete";
  if (records.some((row) => comparisonForRow(row).status === "unavailable")) return "unavailable";
  return "pending";
}

function shortModel(value) {
  const text = String(value || "Pending");
  return text.length > 36 ? `${text.slice(0, 33)}...` : text;
}

function formatRecall(value) {
  if (value === null || value === undefined || value === "") return "Pending";
  const number = Number(value);
  if (!Number.isFinite(number)) return "Pending";
  return `${Math.abs(number) <= 1 ? (number * 100).toFixed(1) : number.toFixed(1)}%`;
}

function formatPercentValue(value) {
  if (value === null || value === undefined || value === "") return "Pending";
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(1)}%` : "Pending";
}
