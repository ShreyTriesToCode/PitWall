"use client";

import { useMemo } from "react";
import { AnimatedTicker, AppShell, EmptyState, InlineNotice, LoadingSkeleton, ModelMetricCard, PageHeader, RaceControlTimeline, SectionTitle, SourceHealthCard, StatusBadge, usePitWallData } from "../components/PitWallComponents";
import { Activity, BarChart3, Bot, Database, GitBranch, ShieldCheck } from "lucide-react";

export default function ModelCenterPage() {
  const predictions = usePitWallData("/api/predictions");
  const status = usePitWallData("/api/model-status");
  const backtest = usePitWallData("/api/backtest");
  const metrics = status.data?.metrics || {};
  const cards = useMemo(() => [
    ["Win AUC", metrics.win_auc, BarChart3],
    ["Win Brier", metrics.win_brier, BarChart3],
    ["Podium AUC", metrics.podium_auc, BarChart3],
    ["Podium Brier", metrics.podium_brier, BarChart3],
    ["Top 10 AUC", metrics.top10_auc, BarChart3],
    ["Top 10 Brier", metrics.top10_brier, BarChart3],
    ["Finish MAE", metrics.finish_position_mae, Activity],
    ["Finish RMSE", metrics.finish_position_rmse, Activity],
    ["Winner Hit Rate", metrics.winner_hit_rate, ShieldCheck],
    ["Top-3 Recall", metrics.top3_recall, ShieldCheck],
    ["Top-5 Recall", metrics.top5_recall, ShieldCheck],
    ["Top-10 Recall", metrics.top10_recall, ShieldCheck],
    ["Exact Position Accuracy", metrics.exact_position_accuracy, ShieldCheck],
    ["Mean Position Error", metrics.mean_position_error, Activity],
    ["Lap-time MAE", metrics.lap_time_mae, Activity],
    ["Lap-time RMSE", metrics.lap_time_rmse, Activity],
  ], [metrics]);
  return (
    <AppShell active="/model">
      <AnimatedTicker latest={predictions.data?.latest} />
      <PageHeader eyebrow="Model Center" title="Model Intelligence" description="Accuracy audit, source reliability, correction status, champion/challenger gate, and backtest history." actions={<StatusBadge label={status.data?.readiness_state?.status || "Readiness pending"} tone="green" />} />
      {(status.loading || predictions.loading) && <LoadingSkeleton />}
      {status.error && <InlineNotice title="Model status sync failed" body={status.error} tone="error" action={<button className="control-btn" onClick={status.refetch}>Retry</button>} />}
      {status.warning && <InlineNotice title="Fallback model status" body={status.warning} tone="warning" />}
      {status.data && (
        <>
          <section className="metric-grid">
            <ModelMetricCard label="Model Version" value={status.data.model_version} icon={Bot} />
            <ModelMetricCard label="Schema Version" value={status.data.schema_version} icon={Database} />
            <ModelMetricCard label="Trained At" value={status.data.trained_at || "Pending"} icon={Activity} />
            <ModelMetricCard label="Feature Count" value={status.data.feature_count} icon={Database} />
            <ModelMetricCard label="Bundle Size" value={status.data.model_bundle_size_mb ? `${status.data.model_bundle_size_mb} MB` : "Pending"} icon={Database} />
            <ModelMetricCard label="Promotion" value={status.data.promotion_decision?.decision} icon={GitBranch} />
            <ModelMetricCard label="Validation" value={status.data.validation?.grouped_split_method || "Pending"} icon={ShieldCheck} />
            <ModelMetricCard label="Contract Validation" value={status.data.contract_validation?.status || "Pending"} icon={ShieldCheck} />
            <ModelMetricCard label="FIA Ingestion" value={status.data.fia_ingestion?.fia_source_discovery_status || "Pending"} icon={Database} />
          </section>
          <section className="metric-grid">{cards.map(([label, value, Icon]) => <ModelMetricCard label={label} value={value ?? "Pending"} icon={Icon} key={label} />)}</section>
          <section className="dashboard-grid">
            <SourceHealthCard health={status.data.source_health} />
            <section className="panel reveal">
              <SectionTitle title="Prediction Audit Timeline" />
              {backtest.error && <InlineNotice title="Backtest history unavailable" body={backtest.error} tone="warning" />}
              {(backtest.data?.history || []).length
                ? <RaceControlTimeline items={(backtest.data?.history || []).map((row) => `${row.race_name}: ${row.top_pick || "Pending top pick"}`)} />
                : <EmptyState title="No backtest history yet" body="Backtest cards will appear after audited race results are generated." />}
            </section>
            <section className="panel reveal">
              <SectionTitle title="Model Limitations" />
              <RaceControlTimeline items={status.data.limitations} />
            </section>
            <section className="panel reveal">
              <SectionTitle title="Champion vs Challenger Model Status" />
              <div className="metric-grid">
                <ModelMetricCard label="Champion" value={status.data.champion_challenger?.champion_model} icon={Bot} />
                <ModelMetricCard label="Challenger" value={status.data.champion_challenger?.challenger_model} icon={GitBranch} />
                <ModelMetricCard label="Status" value={status.data.champion_challenger?.status} icon={ShieldCheck} />
                <ModelMetricCard label="Corrections" value={status.data.correction_log_summary?.status} icon={Activity} />
              </div>
            </section>
            <section className="panel reveal">
              <SectionTitle title="Baselines And Calibration" />
              <RaceControlTimeline items={[
                `Grid baseline: ${status.data.baseline_comparison?.grid_order_baseline?.status || "pending"}`,
                `Constructor baseline: ${status.data.baseline_comparison?.constructor_standings_baseline?.status || "pending"}`,
                `Calibration: ${status.data.calibration?.method || "pending"}`,
                `Feature ablation: ${status.data.feature_ablation?.status || "manual only"}`,
              ]} />
            </section>
          </section>
        </>
      )}
    </AppShell>
  );
}
