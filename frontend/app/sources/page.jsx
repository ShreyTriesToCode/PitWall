"use client";

import { AnimatedTicker, AppShell, DataStateBadge, EmptyState, InlineNotice, LoadingSkeleton, Metric, PageHeader, SectionTitle, SourceHealthCard, StatusBadge, statusTone, usePitWallData } from "../components/PitWallComponents";

export default function SourcesPage() {
  const predictions = usePitWallData("/api/predictions");
  const sourceHealth = usePitWallData("/api/source-health");
  const latest = predictions.data?.latest;
  const health = sourceHealth.data || latest?.source_health || latest?.source_status;
  const sources = health?.sources || [];
  const conflicts = sourceHealth.data?.source_conflicts || predictions.data?.source_conflicts || latest?.source_conflicts || [];
  const fiaDocument = predictions.data?.fia_latest_document || latest?.fia_latest_document || null;
  const fiaTrustRows = [
    ["Source authority", fiaDocument?.source_authority],
    ["Source status", fiaDocument?.source_status],
    ["Official", fiaDocument ? (fiaDocument.is_official ? "Yes" : "No") : null],
    ["Verified", fiaDocument ? (fiaDocument.is_verified ? "Yes" : "No") : null],
    ["Stale", fiaDocument ? (fiaDocument.is_stale ? "Yes" : "No") : null],
    ["Fetched", fiaDocument?.fetched_at],
    ["SHA256", fiaDocument?.sha256],
  ];
  return (
    <AppShell active="/sources">
      <AnimatedTicker latest={latest} />
      <PageHeader eyebrow="Sources" title="Data Source Health" description="Truthful status for timing, OpenF1, FIA, Jolpica, FastF1, weather, cache, and fallback data." actions={<StatusBadge label={health?.status || "Pending"} tone={statusTone(health?.status, health?.overall_score ?? health?.score)} />} />
      {(predictions.loading || sourceHealth.loading) && <LoadingSkeleton />}
      {sourceHealth.error && <InlineNotice title="Source health unavailable" body={sourceHealth.error} tone="error" action={<button className="control-btn" onClick={sourceHealth.refetch}>Retry</button>} />}
      {health && (
        <>
          <SourceHealthCard health={health} />
          <section className="panel reveal">
            <SectionTitle
              title="FIA Document Trust"
              action={<DataStateBadge status={fiaDocument?.source_status || predictions.data?.fia_source_discovery_status || "unavailable"} />}
            />
            {fiaDocument ? (
              <>
                <div className="metric-grid compact">
                  {fiaTrustRows.map(([label, value]) => <Metric label={label} value={value || "Unavailable"} key={label} />)}
                </div>
                <p className="panel-note">
                  {fiaDocument.title || "Latest FIA document"} is labelled from resolver metadata. Third-party summaries are never displayed here as official documents.
                </p>
                <div className="tag-row">
                  {fiaDocument.source_url && <a href={fiaDocument.source_url} target="_blank" rel="noopener noreferrer">Source URL</a>}
                  {fiaDocument.download_url && <a href={fiaDocument.download_url} target="_blank" rel="noopener noreferrer">Download URL</a>}
                </div>
              </>
            ) : (
              <EmptyState title="No trusted FIA document row" body="FIA document metadata will appear only after a verified official, archive, third-party document-index, or cache source is available." />
            )}
          </section>
          <section className="panel reveal">
            <SectionTitle title="Source Conflicts" action={<StatusBadge label={`${conflicts.length} conflicts`} tone={conflicts.length ? "amber" : "green"} />} />
            {conflicts.length ? (
              <div className="archive-grid">
                {conflicts.map((conflict, index) => (
                  <article className="panel archive-card" key={`${conflict.conflict_type}-${index}`}>
                    <SectionTitle title={conflict.conflict_type?.replaceAll?.("_", " ") || "Source conflict"} action={<StatusBadge label={conflict.confidence || "medium"} tone={conflict.confidence === "high" ? "red" : "amber"} />} />
                    <p className="panel-note">{conflict.reason}</p>
                    <div className="metric-grid compact">
                      <Metric label="Preferred source" value={conflict.preferred_source || "Pending"} />
                      <Metric label="Affected fields" value={(conflict.affected_fields || []).join(", ") || "Pending"} />
                    </div>
                    <p className="panel-note">{conflict.action_needed}</p>
                  </article>
                ))}
              </div>
            ) : <EmptyState title="No source conflicts reported" body="PitWall did not detect stale, missing, or conflicting source states in the latest contract." />}
          </section>
          <section className="panel reveal">
            <SectionTitle title="Source Details" />
            {sources.length ? (
              <div className="archive-grid">
                {sources.map((source) => (
                  <article className="panel archive-card" key={source.source}>
                    <SectionTitle title={source.source} action={<StatusBadge label={source.status || "Unknown"} tone={statusTone(source.status, source.score)} />} />
                    <div className="metric-grid">
                      <Metric label="Confidence" value={source.score !== undefined ? `${source.score}%` : "Pending"} />
                      <Metric label="Last checked" value={source.last_checked_at || source.generated_at || "Pending"} />
                      <Metric label="Last success" value={source.last_success_at || "Pending"} />
                      <Metric label="Auth restricted" value={source.auth_restricted ? "Yes" : "No"} />
                    </div>
                    {source.detail && <p className="panel-note">{source.detail}</p>}
                  </article>
                ))}
              </div>
            ) : <EmptyState title="No source rows" body="The generated source-health contract did not include individual source rows." />}
          </section>
        </>
      )}
    </AppShell>
  );
}
