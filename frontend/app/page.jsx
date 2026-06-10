"use client";

import Link from "next/link";
import {
  AnimatedTicker,
  AppShell,
  DataFreshnessBadge,
  EmptyState,
  Icons,
  InlineNotice,
  LoadingSkeleton,
  Metric,
  OfficialCalendarStrip,
  PageHeader,
  pct,
  RaceControlTimeline,
  RaceHero,
  ScenarioCards,
  SectionTitle,
  SourceHealthCard,
  StatusBadge,
  StrategyPanel,
  usePitWallData,
} from "./components/PitWallComponents";

export default function HomePage() {
  const { loading, data, error, warning, refetch, refreshing } = usePitWallData("/api/predictions");
  const latest = data?.latest;
  return (
    <AppShell active="/">
      <AnimatedTicker latest={latest} />
      <PageHeader
        eyebrow="Home / Race Control"
        title="PitWall"
        description="A race-control dashboard for prediction confidence, source health, strategy risk, and model readiness."
        actions={latest && <DataFreshnessBadge value={latest.generated_iso} />}
      />
      {loading && <LoadingSkeleton />}
      {error && <InlineNotice title="Prediction JSON unavailable" body={error} tone="error" action={<button className="control-btn" onClick={refetch}>Retry</button>} />}
      {warning && <InlineNotice title="Fallback race-control data" body={warning} tone="warning" action={<button className="control-btn" onClick={refetch} disabled={refreshing}>{refreshing ? "Refreshing" : "Refresh"}</button>} />}
      {!loading && !error && data && !latest && <EmptyState title="No generated race briefing yet" body="Run the backend briefing generator to create the frontend prediction contract." />}
      {latest && (
        <>
          <RaceHero latest={latest} />
          <section className="dashboard-grid compact-dashboard">
            <div className="panel reveal">
              <SectionTitle icon={Icons.Sparkles} title="Race Intelligence Summary" action={<StatusBadge label={(data.ai_features || latest.ai_features)?.provider || "deterministic"} tone="green" />} />
              <p className="panel-note">{(data.race_intelligence_summary || latest.race_intelligence_summary)?.headline || "Race intelligence summary pending."}</p>
              <RaceControlTimeline items={[
                (data.race_intelligence_summary || latest.race_intelligence_summary)?.race_week_summary || "Deterministic summary uses local contract data only.",
                ...((data.race_intelligence_summary || latest.race_intelligence_summary)?.key_uncertainties || []).slice(0, 3),
              ]} />
            </div>
            <div className="panel reveal">
              <SectionTitle icon={Icons.ShieldAlert} title="Prediction Trust" action={<StatusBadge label={data.event_trust_label || latest.event_trust_label || latest.prediction_trust_label || "Trust pending"} tone={(Number(data.event_trust_score ?? latest.event_trust_score ?? latest.prediction_trust_score) || 0) >= 75 ? "green" : (Number(data.event_trust_score ?? latest.event_trust_score ?? latest.prediction_trust_score) || 0) >= 50 ? "amber" : "red"} />} />
              <div className="metric-grid compact">
                <Metric label="Event trust" value={pct(data.event_trust_score ?? latest.event_trust_score ?? latest.prediction_trust_score)} />
                <Metric label="High disagreements" value={latest.confidence_breakdown?.high_disagreement_count ?? 0} />
                <Metric label="Source conflicts" value={(data.source_conflicts || latest.source_conflicts || []).length} />
                <Metric label="AI mode" value={(data.ai_features || latest.ai_features)?.free_mode === false ? "Configured" : "Free deterministic"} />
              </div>
            </div>
            <div className="panel reveal">
              <SectionTitle icon={Icons.LineChart} title="What Changed Since Last Run" />
              <p className="panel-note">{(data.changed_since_last_run || latest.changed_since_last_run || latest.change_summary)?.summary || "No previous valid contract available."}</p>
              <RaceControlTimeline items={[
                `${(data.changed_since_last_run || latest.changed_since_last_run || latest.change_summary)?.rank_changes?.length ?? 0} rank changes`,
                `${(data.changed_since_last_run || latest.changed_since_last_run || latest.change_summary)?.probability_changes?.length ?? 0} probability changes`,
                `${(data.changed_since_last_run || latest.changed_since_last_run || latest.change_summary)?.trust_changes?.length ?? 0} trust changes`,
              ]} />
            </div>
          </section>
          <section className="dashboard-grid compact-dashboard">
            <div className="panel reveal">
              <SectionTitle icon={Icons.Trophy} title="Top 3 Prediction Preview" action={<StatusBadge label={latest.prediction_stage || latest.stage} tone="red" />} />
              <div className="podium-list">
                {latest.top10?.slice(0, 3).map((item) => (
                  <article key={item.driver_id}>
                    <span>P{item.rank}</span>
                    <strong>{item.name}</strong>
                    <small>{item.team} · {item.confidence === null || item.confidence === undefined ? "confidence pending" : `${item.confidence}% confidence`}</small>
                  </article>
                ))}
              </div>
            </div>
            <StrategyPanel strategy={latest.strategy} />
            <SourceHealthCard health={latest.source_health || latest.source_status} />
            <div className="panel reveal">
              <SectionTitle icon={Icons.CalendarDays} title="Race Weekend Timeline" />
              <RaceControlTimeline items={[
                `${latest.target_type || "Race"} target selected`,
                `${latest.stage || "pre_weekend"} model stage`,
                `${latest.circuit || "Circuit"} profile loaded`,
                "Official result audit pending until final result gate",
              ]} />
            </div>
            <div className="panel reveal">
              <SectionTitle icon={Icons.Timer} title="Official 2026 Calendar" />
              <OfficialCalendarStrip latest={latest} generatedTargets={data.generated_targets || []} />
            </div>
            <div className="panel reveal">
              <SectionTitle icon={Icons.Zap} title="Quick Links" />
              <div className="quick-links">
                {[
                  ["/predictions", "Predictions"],
                  ["/live", "Timing"],
                  ["/strategy", "Strategy Lab"],
                  ["/model", "Model Center"],
                  ["/archive", "Archive"],
                ].map(([href, label]) => <Link href={href} key={href}>{label}<Icons.ChevronRight size={16} /></Link>)}
              </div>
            </div>
          </section>

          <ScenarioCards scenarios={Object.fromEntries(Object.entries(latest.scenarios || {}).slice(0, 3))} />

          <details className="home-footer reveal compact-details">
            <summary>How PitWall Works</summary>
            <p>PitWall checks structured race, timing, weather, model-history, source-health, and post-race result data. Predictions are probabilistic and update when trusted source data changes.</p>
            <div className="metric-grid compact">
              <Metric label="Model Version" value={latest.model_version} />
              <Metric label="Circuit" value={latest.circuit} />
              <Metric label="Source State" value={(latest.source_health || latest.source_status)?.status || "Pending"} />
              <Metric label="Stage" value={latest.stage} />
              <Metric label="Timing Mode" value={latest.timing_mode || "unavailable"} />
              <Metric label="FIA Docs" value={latest.fia_source_discovery_status || "pending"} />
            </div>
          </details>
        </>
      )}
    </AppShell>
  );
}
