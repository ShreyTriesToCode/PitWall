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
          <section className="dashboard-grid">
            <div className="panel reveal">
              <SectionTitle icon={Icons.Trophy} title="Top 3 Prediction Preview" action={<StatusBadge label={latest.prediction_stage || latest.stage} tone="red" />} />
              <div className="podium-list">
                {latest.top10?.slice(0, 3).map((item) => (
                  <article key={item.driver_id}>
                    <span>P{item.rank}</span>
                    <strong>{item.name}</strong>
                    <small>{item.team} · {item.confidence}% confidence</small>
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
              <SectionTitle icon={Icons.LineChart} title="What Changed Since Last Run" />
              <RaceControlTimeline items={[
                `${latest.change_summary?.rank_changes?.length ?? 0} notable rank changes`,
                `${latest.change_summary?.probability_changes?.length ?? 0} win-probability changes`,
                `${latest.change_summary?.trust_changes?.length ?? 0} trust-score changes`,
                latest.change_summary?.source_changed ? "Source health changed" : "Source health unchanged",
              ]} />
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

          <footer className="home-footer reveal">
            <span className="eyebrow">How PitWall Works</span>
            <h2>From race data to readable predictions</h2>
            <p>
              PitWall checks race data, timing data, weather, model history, source health, and post-race results.
              It creates predictions, shows confidence, explains each ranking, and updates after new race data arrives.
            </p>
            <div className="metric-grid">
              <Metric label="Model Version" value={latest.model_version} />
              <Metric label="Circuit" value={latest.circuit} />
              <Metric label="Source State" value={(latest.source_health || latest.source_status)?.status || "Pending"} />
              <Metric label="Stage" value={latest.stage} />
              <Metric label="Timing Mode" value={latest.timing_mode || "unavailable"} />
              <Metric label="FIA Docs" value={latest.fia_source_discovery_status || "pending"} />
            </div>
          </footer>
        </>
      )}
    </AppShell>
  );
}
