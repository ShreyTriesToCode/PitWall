"use client";

import { useMemo } from "react";
import { AnimatedTicker, AppShell, EmptyState, InlineNotice, LoadingSkeleton, ModelMetricCard, PageHeader, RaceControlTimeline, SectionTitle, SourceHealthCard, StatusBadge, usePitWallData } from "../components/PitWallComponents";
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
  const metrics = status.data?.metrics || {};
  const modelComparison = status.data?.model_comparison || predictions.data?.model_comparison || predictions.data?.latest?.model_comparison || {};
  const actualComparison = predictions.data?.actual_result_comparison || predictions.data?.latest?.actual_result_comparison || {};
  const comparisonMetrics = modelComparison.metrics || {};
  const actualMetrics = actualComparison.metrics || {};
  const actualWarnings = actualComparison.warnings || [];
  const positionErrors = actualComparison.driver_position_errors || [];
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
                <ModelMetricCard label="Champion" value={modelComparison.champion?.name || status.data.champion_challenger?.champion_model} icon={Bot} />
                <ModelMetricCard label="Challenger" value={modelComparison.challenger?.name || status.data.champion_challenger?.challenger_model} icon={GitBranch} />
                <ModelMetricCard label="Status" value={modelComparison.challenger?.status || status.data.champion_challenger?.status} icon={ShieldCheck} />
                <ModelMetricCard label="Promotion Decision" value={modelComparison.promotion_decision?.decision || status.data.promotion_decision?.decision} icon={GitBranch} />
                <ModelMetricCard label="Corrections" value={status.data.correction_log_summary?.status} icon={Activity} />
              </div>
              <div className="compare-table" role="table" aria-label="Model comparison metrics">
                {[
                  ["Winner hit rate", formatPercent(comparisonMetrics.winner_hit_rate)],
                  ["Podium recall", formatPercent(comparisonMetrics.podium_recall)],
                  ["Top 10 recall", formatPercent(comparisonMetrics.top10_recall)],
                  ["Position MAE", formatValue(comparisonMetrics.position_mae)],
                  ["Spearman", formatValue(comparisonMetrics.spearman_rank_correlation)],
                  ["NDCG@3", formatValue(comparisonMetrics.ndcg_at_3)],
                  ["NDCG@10", formatValue(comparisonMetrics.ndcg_at_10)],
                  ["Top 10 Brier", formatValue(comparisonMetrics.brier?.top10)],
                ].map(([label, value]) => (
                  <div className="compare-row" role="row" key={label}>
                    <span>{label}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
              </div>
              {(modelComparison.warnings || []).length > 0 && <InlineNotice title="Model comparison note" body={modelComparison.warnings[0]} tone="warning" />}
            </section>
            <section className="panel reveal">
              <SectionTitle title="Actual Result Comparison" action={<StatusBadge label={actualComparison.status || "pending"} tone={actualComparison.status === "available" ? "green" : "amber"} />} />
              <div className="metric-grid">
                <ModelMetricCard label="Predicted Winner" value={actualComparison.predicted_winner?.name || "Pending"} icon={Bot} />
                <ModelMetricCard label="Actual Winner" value={actualComparison.actual_winner?.name || "Unavailable"} icon={ShieldCheck} />
                <ModelMetricCard label="Winner Hit" value={formatValue(actualComparison.winner_hit)} icon={ShieldCheck} />
                <ModelMetricCard label="Top 10 Recall" value={formatPercent(actualComparison.top10_recall ?? actualMetrics.top10_recall)} icon={BarChart3} />
              </div>
              {actualComparison.status === "available" ? (
                <>
                  <div className="compare-table" role="table" aria-label="Actual result comparison metrics">
                    {[
                      ["Podium recall", formatPercent(actualComparison.podium_recall ?? actualMetrics.podium_recall)],
                      ["Position MAE", formatValue(actualMetrics.mae)],
                      ["Position RMSE", formatValue(actualMetrics.rmse)],
                      ["Exact position accuracy", formatPercent(actualMetrics.exact_position_accuracy)],
                      ["Spearman", formatValue(actualMetrics.spearman_rank_correlation)],
                      ["NDCG@3", formatValue(actualMetrics.ndcg_at_3)],
                      ["NDCG@10", formatValue(actualMetrics.ndcg_at_10)],
                    ].map(([label, value]) => (
                      <div className="compare-row" role="row" key={label}>
                        <span>{label}</span>
                        <strong>{value}</strong>
                      </div>
                    ))}
                  </div>
                  {positionErrors.length > 0 && (
                    <div className="table-wrap">
                      <table className="data-table">
                        <thead>
                          <tr><th>Driver</th><th>Predicted</th><th>Actual</th><th>Error</th></tr>
                        </thead>
                        <tbody>
                          {positionErrors.slice(0, 10).map((row) => (
                            <tr key={row.driver_id || row.name}>
                              <td>{row.name || row.driver_id}</td>
                              <td>P{row.predicted_position}</td>
                              <td>P{row.actual_position}</td>
                              <td>{row.position_error}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              ) : (
                <EmptyState title="Pending actual result" body={(actualWarnings[0] || "Trusted actual race classification is not available yet. The comparison will update after verified result rows are cached.")} />
              )}
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
            <section className="panel reveal">
              <SectionTitle title="AI-Style Model Review" />
              <p className="panel-note">{status.data.ai_model_review?.summary || "Deterministic model review pending."}</p>
              <RaceControlTimeline items={[
                status.data.ai_model_review?.numeric_guardrail || "AI text cannot change numeric predictions.",
                `Local RAG: ${status.data.ai_features?.local_rag_available ? "available" : "not indexed"}`,
                `Local LLM: ${status.data.ai_features?.local_llm_enabled ? "enabled locally" : "disabled"}`,
              ]} />
            </section>
            <section className="panel reveal">
              <SectionTitle title="Post-Race Failure Themes" />
              <RaceControlTimeline items={[
                status.data.correction_log_summary?.post_race_ai_review?.best_call || "No actual result audit is available yet.",
                status.data.correction_log_summary?.post_race_ai_review?.worst_miss || "No worst miss available yet.",
                ...((status.data.correction_log_summary?.post_race_ai_review?.feature_improvement_suggestions || []).slice(0, 3)),
              ]} />
            </section>
          </section>
        </>
      )}
    </AppShell>
  );
}
