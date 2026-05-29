"use client";

import { AnimatedTicker, AppShell, EmptyState, InlineNotice, LoadingSkeleton, Metric, PageHeader, SectionTitle, SourceHealthCard, StatusBadge, usePitWallData } from "../components/PitWallComponents";

export default function SourcesPage() {
  const predictions = usePitWallData("/api/predictions");
  const sourceHealth = usePitWallData("/api/source-health");
  const latest = predictions.data?.latest;
  const health = sourceHealth.data || latest?.source_health || latest?.source_status;
  const sources = health?.sources || [];
  const conflicts = sourceHealth.data?.source_conflicts || predictions.data?.source_conflicts || latest?.source_conflicts || [];
  return (
    <AppShell active="/sources">
      <AnimatedTicker latest={latest} />
      <PageHeader eyebrow="Sources" title="Data Source Health" description="Truthful status for timing, OpenF1, FIA, Jolpica, FastF1, weather, cache, and fallback data." actions={<StatusBadge label={health?.status || "Pending"} tone={health?.status === "Available" ? "green" : "amber"} />} />
      {(predictions.loading || sourceHealth.loading) && <LoadingSkeleton />}
      {sourceHealth.error && <InlineNotice title="Source health unavailable" body={sourceHealth.error} tone="error" action={<button className="control-btn" onClick={sourceHealth.refetch}>Retry</button>} />}
      {health && (
        <>
          <SourceHealthCard health={health} />
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
                    <SectionTitle title={source.source} action={<StatusBadge label={source.status || "Unknown"} tone={(source.score || 0) >= 70 ? "green" : (source.score || 0) >= 40 ? "amber" : "red"} />} />
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
