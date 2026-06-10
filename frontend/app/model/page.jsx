"use client";

import { useMemo, useState } from "react";
import {
  actualResultAvailable,
  AnimatedTicker,
  AppShell,
  CompactTable,
  DataStateBadge,
  EmptyState,
  InlineNotice,
  LoadingSkeleton,
  Metric,
  MetricCard,
  PageHeader,
  RaceControlTimeline,
  SectionCard,
  SourceHealthCard,
  StatusBadge,
  usePitWallData,
} from "../components/PitWallComponents";
import { Activity, BarChart3, Bot, Database, GitBranch, ShieldCheck } from "lucide-react";

function formatValue(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "Pending";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return `${Number.isInteger(value) ? value : value.toFixed(3)}${suffix}`;
  return String(value);
}

function formatPercent(value) {
  if (value === null || value === undefined || value === "") return "Pending";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  return `${Math.abs(number) <= 1 ? (number * 100).toFixed(1) : number.toFixed(1)}%`;
}

export default function ModelCenterPage() {
  const predictions = usePitWallData("/api/predictions");
  const status = usePitWallData("/api/model-status");
  const backtest = usePitWallData("/api/backtest");
  const [tab, setTab] = useState("overview");
  const metrics = status.data?.metrics || {};
  const modelComparison = status.data?.model_comparison || predictions.data?.model_comparison || predictions.data?.latest?.model_comparison || {};
  const actualComparison = predictions.data?.actual_result_comparison || predictions.data?.latest?.actual_result_comparison || {};
  const comparisonMetrics = modelComparison.metrics || {};
  const actualMetrics = actualComparison.metrics || {};
  const actualAvailable = actualResultAvailable(actualComparison);
  const positionErrors = actualComparison.driver_position_errors || [];
  const metricGroups = useMemo(() => ({
    accuracy: [
      ["Winner Hit Rate", metrics.winner_hit_rate, ShieldCheck],
      ["Exact Position Accuracy", metrics.exact_position_accuracy, ShieldCheck],
      ["Win AUC", metrics.win_auc, BarChart3],
      ["Podium AUC", metrics.podium_auc, BarChart3],
      ["Top 10 AUC", metrics.top10_auc, BarChart3],
    ],
    ranking: [
      ["Top-3 Recall", metrics.top3_recall, ShieldCheck],
      ["Top-5 Recall", metrics.top5_recall, ShieldCheck],
      ["Top-10 Recall", metrics.top10_recall, ShieldCheck],
      ["Spearman", comparisonMetrics.spearman_rank_correlation, Activity],
      ["NDCG@3", comparisonMetrics.ndcg_at_3, Activity],
      ["NDCG@10", comparisonMetrics.ndcg_at_10, Activity],
    ],
    calibration: [
      ["Win Brier", metrics.win_brier, BarChart3],
      ["Podium Brier", metrics.podium_brier, BarChart3],
      ["Top 10 Brier", metrics.top10_brier ?? comparisonMetrics.brier?.top10, BarChart3],
    ],
    errors: [
      ["Finish MAE", metrics.finish_position_mae, Activity],
      ["Finish RMSE", metrics.finish_position_rmse, Activity],
      ["Mean Position Error", metrics.mean_position_error, Activity],
      ["Lap-time MAE", metrics.lap_time_mae, Activity],
      ["Lap-time RMSE", metrics.lap_time_rmse, Activity],
    ],
  }), [metrics, comparisonMetrics]);

  return (
    <AppShell active="/model">
      <AnimatedTicker latest={predictions.data?.latest} />
      <PageHeader eyebrow="Model Center" title="Model Center" description="Champion/challenger status, validation metrics, source health, and actual-result comparison." actions={<DataStateBadge status={status.data?.readiness_state?.status || "pending"} />} />
      {(status.loading || predictions.loading) && <LoadingSkeleton />}
      {status.error && <InlineNotice title="Model status sync failed" body={status.error} tone="error" action={<button className="control-btn" onClick={status.refetch}>Retry</button>} />}
      {status.warning && <InlineNotice title="Fallback model status" body={status.warning} tone="warning" />}
      {status.data && (
        <>
          <nav className="tab-bar" aria-label="Model center sections">
            {["overview", "metrics", "source health", "developer"].map((item) => (
              <button className={tab === item ? "active" : ""} type="button" onClick={() => setTab(item)} key={item}>{item}</button>
            ))}
          </nav>

          {tab === "overview" && (
            <>
              <section className="metric-grid compact">
                <MetricCard label="Model Version" value={status.data.model_version} helper="Current champion shown to users" />
                <MetricCard label="Winner Hit Rate" value={formatPercent(metrics.winner_hit_rate)} helper="Historical verified-race outcome" />
                <MetricCard label="Top-3 Recall" value={formatPercent(metrics.top3_recall)} />
                <MetricCard label="Top-5 Recall" value={formatPercent(metrics.top5_recall)} />
                <MetricCard label="Top-10 Recall" value={formatPercent(metrics.top10_recall)} />
                <MetricCard label="Position MAE" value={formatValue(metrics.finish_position_mae)} />
              </section>
              <section className="dashboard-grid compact-dashboard">
                <SectionCard title="Champion vs Challenger" action={<StatusBadge label={modelComparison.promotion_decision?.decision || status.data.promotion_decision?.decision || "pending"} tone="amber" />}>
                  <div className="metric-grid compact">
                    <Metric label="Champion" value={modelComparison.champion?.name || status.data.champion_challenger?.champion_model || status.data.model_version} />
                    <Metric label="Challenger" value={modelComparison.challenger?.name || status.data.champion_challenger?.challenger_model || "Pending"} />
                    <Metric label="Status" value={modelComparison.challenger?.status || status.data.champion_challenger?.status || "Pending"} />
                    <Metric label="Promotion Decision" value={modelComparison.promotion_decision?.decision || status.data.promotion_decision?.decision || "Pending"} />
                  </div>
                </SectionCard>
                <ActualComparisonCard comparison={actualComparison} metrics={actualMetrics} available={actualAvailable} />
              </section>
            </>
          )}

          {tab === "metrics" && (
            <div className="metric-group-stack">
              {Object.entries(metricGroups).map(([group, rows]) => (
                <SectionCard title={`${group[0].toUpperCase()}${group.slice(1)} Metrics`} key={group}>
                  <div className="metric-grid compact">
                    {rows.map(([label, value, Icon]) => <MetricCard label={label} value={formatPercent(value).includes("%") && !label.includes("MAE") && !label.includes("RMSE") && !label.includes("Error") ? formatPercent(value) : formatValue(value)} key={label} icon={Icon} />)}
                  </div>
                </SectionCard>
              ))}
              <SectionCard title="Model Comparison Metrics">
                <div className="compare-table" role="table" aria-label="Model comparison metrics">
                  {[
                    ["Winner hit rate", formatPercent(comparisonMetrics.winner_hit_rate)],
                    ["Podium recall", formatPercent(comparisonMetrics.podium_recall)],
                    ["Top 10 recall", formatPercent(comparisonMetrics.top10_recall)],
                    ["Position MAE", formatValue(comparisonMetrics.position_mae)],
                    ["Spearman", formatValue(comparisonMetrics.spearman_rank_correlation)],
                    ["NDCG@3", formatValue(comparisonMetrics.ndcg_at_3)],
                    ["NDCG@10", formatValue(comparisonMetrics.ndcg_at_10)],
                  ].map(([label, value]) => <div className="compare-row" role="row" key={label}><span>{label}</span><strong>{value}</strong></div>)}
                </div>
              </SectionCard>
            </div>
          )}

          {tab === "source health" && (
            <section className="dashboard-grid compact-dashboard">
              <SourceHealthCard health={status.data.source_health} />
              <SectionCard title="Backtest Timeline">
                {backtest.error && <InlineNotice title="Backtest history unavailable" body={backtest.error} tone="warning" />}
                {(backtest.data?.history || []).length
                  ? <RaceControlTimeline items={(backtest.data?.history || []).map((row) => `${row.race_name}: ${row.top_pick || "Pending top pick"}`)} />
                  : <EmptyState title="No backtest history yet" body="Backtest cards will appear after audited race results are generated." />}
              </SectionCard>
            </section>
          )}

          {tab === "developer" && (
            <section className="dashboard-grid compact-dashboard">
              <SectionCard title="Developer Contract Details">
                <div className="metric-grid compact">
                  <Metric label="Schema Version" value={status.data.schema_version} />
                  <Metric label="Bundle Size" value={status.data.model_bundle_size_mb ? `${status.data.model_bundle_size_mb} MB` : "Pending"} />
                  <Metric label="Contract Validation" value={status.data.contract_validation?.status || "Pending"} />
                  <Metric label="Validation Split" value={status.data.validation?.grouped_split_method || "Pending"} />
                  <Metric label="Feature Count" value={status.data.feature_count} />
                  <Metric label="FIA Ingestion" value={status.data.fia_ingestion?.fia_source_discovery_status || "Pending"} />
                  <Metric label="Local RAG" value={status.data.ai_features?.local_rag_available ? "Available" : "Not indexed"} />
                  <Metric label="Local LLM" value={status.data.ai_features?.local_llm_enabled ? "Enabled" : "Disabled"} />
                </div>
              </SectionCard>
              <SectionCard title="Model Limitations">
                <RaceControlTimeline items={status.data.limitations} />
              </SectionCard>
              <SectionCard title="Baselines and Calibration">
                <RaceControlTimeline items={[
                  `Grid baseline: ${status.data.baseline_comparison?.grid_order_baseline?.status || "pending"}`,
                  `Constructor baseline: ${status.data.baseline_comparison?.constructor_standings_baseline?.status || "pending"}`,
                  `Calibration: ${status.data.calibration?.method || "pending"}`,
                  `Feature ablation: ${status.data.feature_ablation?.status || "manual only"}`,
                ]} />
              </SectionCard>
              <SectionCard title="Driver Position Errors" show={actualAvailable && positionErrors.length > 0} emptyTitle="No actual error table" emptyBody="Driver-level actual errors appear only after trusted actual result rows are available.">
                <CompactTable
                  rows={positionErrors.slice(0, 12)}
                  getKey={(row) => row.driver_id || row.name}
                  columns={[
                    { header: "Driver", render: (row) => row.name || row.driver_id },
                    { header: "Predicted", render: (row) => `P${row.predicted_position}` },
                    { header: "Actual", render: (row) => `P${row.actual_position}` },
                    { header: "Error", render: (row) => row.position_error },
                  ]}
                />
              </SectionCard>
            </section>
          )}
        </>
      )}
    </AppShell>
  );
}

function ActualComparisonCard({ comparison, metrics, available }) {
  return (
    <SectionCard title="Actual Result Comparison" action={<DataStateBadge status={comparison.status || "pending"} />}>
      {available ? (
        <>
          <div className="metric-grid compact">
            <Metric label="Predicted Winner" value={comparison.predicted_winner?.name || "Pending"} />
            <Metric label="Actual Winner" value={comparison.actual_winner?.name || "Unavailable"} />
            <Metric label="Winner Hit" value={comparison.winner_hit ? "Yes" : "No"} />
            <Metric label="Podium Recall" value={formatPercent(comparison.podium_recall ?? metrics.podium_recall)} />
            <Metric label="Top 10 Recall" value={formatPercent(comparison.top10_recall ?? metrics.top10_recall)} />
            <Metric label="Position MAE" value={formatValue(metrics.mae)} />
          </div>
          <p className="panel-note">Prediction-vs-actual metrics are shown only for trusted completed race classifications.</p>
        </>
      ) : (
        <EmptyState title="Pending actual result" body={(comparison.warnings || [])[0] || "Trusted actual race classification is not available yet. Winner match and recall stay hidden until verified results exist."} />
      )}
    </SectionCard>
  );
}
