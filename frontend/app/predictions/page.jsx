"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AnimatedTicker,
  AppShell,
  CopySummaryButton,
  DriverExplainabilityDrawer,
  EmptyState,
  InlineNotice,
  LoadingSkeleton,
  Metric,
  PageHeader,
  PredictionCard,
  PredictionTable,
  ScenarioCards,
  SearchBox,
  SectionTitle,
  StatusBadge,
  useFilteredDrivers,
  usePitWallData,
} from "../components/PitWallComponents";

export default function PredictionsPage() {
  const { loading, data, error, warning, refetch, refreshing } = usePitWallData("/api/predictions");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [view, setView] = useState("table");
  const [detailMode, setDetailMode] = useState("expert");
  const [requestedTarget, setRequestedTarget] = useState("race");
  const [compareA, setCompareA] = useState("");
  const [compareB, setCompareB] = useState("");
  const latest = data?.latest;
  const generatedTargets = data?.generated_targets || [];
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setRequestedTarget(params.get("target") || latest?.target_type || generatedTargets[0]?.target_type || "race");
    const onPop = () => {
      const next = new URLSearchParams(window.location.search).get("target");
      setRequestedTarget(next || latest?.target_type || generatedTargets[0]?.target_type || "race");
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [latest?.target_type, generatedTargets]);
  const targetMap = useMemo(() => {
    const map = new Map(generatedTargets.map((target) => [target.target_type, target]));
    if (latest?.target_type && !map.has(latest.target_type)) {
      map.set(latest.target_type, {
        ...latest,
        title: latest.title || latest.race_name,
        top10: data?.top10 || latest.top10 || [],
        full_grid: data?.full_grid || latest.full_grid || latest.all_predictions || latest.top10 || [],
        target_type: latest.target_type,
        stage: latest.stage,
      });
    }
    return map;
  }, [data?.full_grid, data?.top10, generatedTargets, latest]);
  const selectedTarget = targetMap.get(requestedTarget) || (!generatedTargets.length && latest ? {
    ...latest,
    title: latest.title || latest.race_name,
    top10: data?.top10 || [],
    full_grid: data?.full_grid || data?.all_predictions || data?.top10 || [],
    target_type: latest.target_type,
    stage: latest.stage,
  } : null);
  const targetPending = Boolean(requestedTarget && !targetMap.has(requestedTarget) && generatedTargets.length);
  const selectedPayload = targetPending ? {} : selectedTarget || latest || {};
  const selectedTop10 = targetPending ? [] : selectedTarget?.top10?.length ? selectedTarget.top10 : data?.top10 || [];
  const selectedFullGrid = targetPending
    ? []
    : selectedTarget?.full_grid?.length
      ? selectedTarget.full_grid
      : selectedTarget?.all_predictions?.length
        ? selectedTarget.all_predictions
        : data?.full_grid?.length
          ? data.full_grid
          : data?.all_predictions?.length
            ? data.all_predictions
            : selectedTop10;
  const top10Rows = useFilteredDrivers(selectedTop10, query);
  const fullGridRows = useFilteredDrivers(selectedFullGrid, query);
  const predictions = fullGridRows.length ? fullGridRows : top10Rows;
  const generatedTargetTypes = useMemo(() => {
    const values = new Set(generatedTargets.map((target) => target.target_type).filter(Boolean));
    if (latest?.target_type) values.add(latest.target_type);
    return values;
  }, [generatedTargets, latest?.target_type]);
  const summary = useMemo(() => {
    const top = top10Rows.slice(0, 3).map((p) => `P${p.rank} ${p.name} (${p.team})`).join(", ");
    return `${selectedPayload?.title || selectedPayload?.race_name || "PitWall"}: ${top || "No prediction rows available"}. Stage: ${selectedPayload?.stage || "pending"}.`;
  }, [top10Rows, selectedPayload]);

  useEffect(() => {
    if (!predictions.length) {
      setCompareA("");
      setCompareB("");
      return;
    }
    setCompareA((current) => predictions.some((item) => item.driver_id === current) ? current : predictions[0]?.driver_id || "");
    setCompareB((current) => predictions.some((item) => item.driver_id === current) ? current : predictions[1]?.driver_id || predictions[0]?.driver_id || "");
    setSelected((current) => current && predictions.some((item) => item.driver_id === current.driver_id) ? current : null);
  }, [predictions]);

  function selectTarget(type) {
    setRequestedTarget(type);
    setSelected(null);
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("target", type);
      window.history.pushState({}, "", url.toString());
    } catch {}
  }

  return (
    <AppShell active="/predictions">
      <AnimatedTicker latest={latest} />
      <PageHeader eyebrow="Prediction Intelligence" title="Predictions" description="Race overview, top-10 probabilities, full-grid ranking, and source-aware driver explanations." actions={<CopySummaryButton text={summary} />} />
      {loading && <LoadingSkeleton />}
      {error && <InlineNotice title="Prediction sync failed" body={error} tone="error" action={<button className="control-btn" onClick={refetch}>Retry</button>} />}
      {warning && <InlineNotice title="Fallback prediction data" body={warning} tone="warning" />}
      {data?.contract_recovered_from_debug && <InlineNotice title="Recovered prediction contract" body={data.contract_recovery_warning || "PitWall rebuilt this response from latest-model-debug.json because the primary contract was unusable."} tone="warning" />}
      {data?.contract_recovered_from_previous && <InlineNotice title="Using previous valid contract" body="The latest prediction contract was unusable, so PitWall served the last valid rollback contract." tone="warning" />}
      {latest && (
        <>
          <section className="toolbar panel reveal">
            <SearchBox value={query} onChange={setQuery} placeholder="Search drivers or teams" />
            <TargetTabs active={requestedTarget} available={generatedTargetTypes} onSelect={selectTarget} />
            <button className={view === "table" ? "control-btn active" : "control-btn"} onClick={() => setView("table")} disabled={!predictions.length}>Table</button>
            <button className={view === "cards" ? "control-btn active" : "control-btn"} onClick={() => setView("cards")} disabled={!predictions.length}>Cards</button>
            {["simple", "expert", "debug"].map((mode) => <button className={detailMode === mode ? "control-btn active" : "control-btn"} onClick={() => setDetailMode(mode)} type="button" key={mode}>{mode[0].toUpperCase() + mode.slice(1)}</button>)}
            <button className="control-btn" onClick={refetch} disabled={refreshing}>{refreshing ? "Refreshing" : "Refresh data"}</button>
            <StatusBadge label={targetPending ? `${requestedTarget} pending` : selectedTarget?.stage || latest.stage} tone="red" />
          </section>
          <section className="panel reveal prediction-overview">
            <SectionTitle title="Race Overview" />
            <div className="metric-grid">
              <Metric label="Prediction ID" value={targetPending ? "Pending generation" : selectedPayload.prediction_id || latest.prediction_id} />
              <Metric label="Target" value={targetPending ? requestedTarget : selectedPayload.target_type || latest.target_type} />
              <Metric label="Model Agreement Leader" value={`${predictions[0]?.model_agreement_score ?? "Pending"}%`} />
              <Metric label="Event Trust" value={`${selectedPayload.prediction_trust_score ?? latest.prediction_trust_score ?? "Pending"}${selectedPayload.prediction_trust_score || latest.prediction_trust_score ? "%" : ""}`} />
              <Metric label="High Disagreements" value={selectedPayload.confidence_breakdown?.high_disagreement_count ?? latest.confidence_breakdown?.high_disagreement_count ?? "Pending"} />
              <Metric label="Dark Horse" value={predictions.find((p) => p.dark_horse_flag)?.name || "Not flagged"} />
              <Metric label="Stage" value={selectedPayload.prediction_stage || selectedPayload.stage || latest.prediction_stage || "pending"} />
              <Metric label="Avg Uncertainty" value={`${selectedPayload.confidence_breakdown?.average_uncertainty ?? latest.confidence_breakdown?.average_uncertainty ?? "Pending"}%`} />
              <Metric label="Safety Car Risk" value={`${selectedPayload.race_factors?.safety_car_probability ?? latest.race_factors?.safety_car_probability ?? "Pending"}%`} />
              <Metric label="Rain Impact" value={selectedPayload.race_factors?.rain_impact || latest.race_factors?.rain_impact || "Pending"} />
              <Metric label="FIA Documents" value={selectedPayload.fia_document_count ?? latest.fia_document_count ?? 0} />
              <Metric label="Timing Mode" value={selectedPayload.timing_mode || latest.timing_mode || "unavailable"} />
            </div>
          </section>
          {!predictions.length && <EmptyState title={targetPending ? `${requestedTarget} prediction pending` : "No prediction rows match"} body={targetPending ? "That target has not been generated yet. The next backend run will expose it when the data exists." : "Clear the search or try another driver/team."} />}
          {top10Rows.length > 0 && (
            <section className="panel reveal prediction-section">
              <SectionTitle title="Top 10 Prediction" action={<StatusBadge label={`${top10Rows.length} drivers`} tone="green" />} />
              <div className="card-grid top10-grid">
                {top10Rows.slice(0, 10).map((item) => <PredictionCard item={item} key={item.driver_id} onOpen={setSelected} compact={detailMode === "simple"} />)}
              </div>
            </section>
          )}
          {fullGridRows.length > 0 && (
            <section className="panel reveal prediction-section">
              <SectionTitle title="Full Grid Prediction" action={<StatusBadge label={`${fullGridRows.length} drivers`} tone="red" />} />
              {view === "table"
                ? <PredictionTable predictions={fullGridRows} onOpen={setSelected} />
                : <div className="card-grid">{fullGridRows.map((item) => <PredictionCard item={item} key={item.driver_id} onOpen={setSelected} compact={detailMode === "simple"} />)}</div>}
            </section>
          )}
          {detailMode === "debug" && predictions.length > 0 && (
            <section className="panel reveal">
              <SectionTitle title="Debug Contract Signals" />
              <div className="metric-grid">
                <Metric label="Contract schema" value={data.schema_version} />
                <Metric label="Prediction data" value={data.prediction_data_version} />
                <Metric label="Recovered from debug" value={data.contract_recovered_from_debug ? "Yes" : "No"} />
                <Metric label="Source conflicts" value={data.source_conflicts?.length ?? 0} />
              </div>
              <div className="podium-list">
                {predictions.slice(0, 5).map((p) => <article key={`debug-${p.driver_id}`}><span>P{p.rank}</span><strong>{p.name}</strong><small>{(p.missing_feature_groups || []).length} missing · {(p.source_warnings || []).length} source warnings · {p.model_disagreement_level || "low"} disagreement</small></article>)}
              </div>
            </section>
          )}
          {predictions.length > 1 && <DriverComparePanel predictions={predictions} aId={compareA} bId={compareB} onA={setCompareA} onB={setCompareB} />}
          {predictions.length > 0 && <section className="dashboard-grid">
            <div className="panel reveal">
              <SectionTitle title="Constructor Prediction Summary" />
              <div className="podium-list">
                {Object.entries(Object.groupBy?.(predictions, (p) => p.team) || predictions.reduce((acc, p) => ((acc[p.team] ||= []).push(p), acc), {})).map(([team, rows]) => (
                  <article key={team}><span>{rows.length}</span><strong>{team}</strong><small>{rows.reduce((sum, row) => sum + Number(row.expected_points || 0), 0).toFixed(1)} expected points</small></article>
                ))}
              </div>
            </div>
            <div className="panel reveal">
              <SectionTitle title="Model Evidence Panel" />
              <div className="podium-list">
                {predictions.slice(0, 4).map((p) => <article key={p.driver_id}><span>P{p.rank}</span><strong>{p.name}</strong><small>{p.evidence_status?.available?.length || 0} signals · {p.evidence_status?.missing?.length || 0} missing</small></article>)}
              </div>
            </div>
            <div className="panel reveal">
              <SectionTitle title="Session And Source State" />
              <div className="podium-list">
                <article><span>{selectedPayload.pending_session_checks?.length ?? latest.pending_session_checks?.length ?? 0}</span><strong>Pending checks</strong><small>{selectedPayload.session_data_delay_status || latest.session_data_delay_status || "unknown"}</small></article>
                <article><span>{selectedPayload.fia_cache_hits ?? latest.fia_cache_hits ?? 0}</span><strong>FIA cache hits</strong><small>{selectedPayload.fia_source_discovery_status || latest.fia_source_discovery_status || "not checked"}</small></article>
                <article><span>{selectedPayload.source_conflicts?.length ?? latest.source_conflicts?.length ?? 0}</span><strong>Source conflicts</strong><small>{selectedPayload.source_health?.status || latest.source_health?.status || "Pending"}</small></article>
              </div>
            </div>
          </section>}
          {predictions.length > 0 && <ScenarioCards scenarios={selectedPayload.scenarios || latest.scenarios} />}
          <DriverExplainabilityDrawer driver={selected} onClose={() => setSelected(null)} />
        </>
      )}
    </AppShell>
  );
}

function TargetTabs({ active, available, onSelect }) {
  const items = [
    ["sprint", "Sprint"],
    ["race", "Race"],
  ];
  return (
    <div className="target-tabs-ui" aria-label="Prediction target">
      {items.map(([type, label]) => {
        const enabled = available.has(type);
        return enabled
          ? <button className={active === type ? "active" : ""} type="button" onClick={() => onSelect(type)} aria-pressed={active === type} key={type}>{label}</button>
          : <span className="disabled" key={type}>{label} pending</span>;
      })}
    </div>
  );
}

function DriverComparePanel({ predictions, aId, bId, onA, onB }) {
  const left = predictions.find((item) => item.driver_id === aId) || predictions[0];
  const right = predictions.find((item) => item.driver_id === bId) || predictions[1] || predictions[0];
  const rows = [
    ["Rank", `P${left?.rank ?? "-"}`, `P${right?.rank ?? "-"}`],
    ["Score", left?.score?.toFixed?.(1) ?? left?.score ?? "-", right?.score?.toFixed?.(1) ?? right?.score ?? "-"],
    ["Confidence", `${left?.confidence ?? "-"}%`, `${right?.confidence ?? "-"}%`],
    ["Expected Points", left?.expected_points ?? "-", right?.expected_points ?? "-"],
    ["Attack Potential", `${left?.attack_potential_score ?? "-"}%`, `${right?.attack_potential_score ?? "-"}%`],
    ["Defend Risk", `${left?.defend_risk_score ?? "-"}%`, `${right?.defend_risk_score ?? "-"}%`],
  ];
  return (
    <section className="panel reveal">
      <SectionTitle title="Driver Comparison" />
      <div className="compare-controls">
        <label>
          <span>Driver A</span>
          <select value={left?.driver_id || ""} onChange={(event) => onA(event.target.value)}>
            {predictions.map((item) => <option key={item.driver_id} value={item.driver_id}>{item.name}</option>)}
          </select>
        </label>
        <label>
          <span>Driver B</span>
          <select value={right?.driver_id || ""} onChange={(event) => onB(event.target.value)}>
            {predictions.map((item) => <option key={item.driver_id} value={item.driver_id}>{item.name}</option>)}
          </select>
        </label>
      </div>
      <div className="compare-table" role="table" aria-label="Driver comparison">
        {rows.map(([label, a, b]) => (
          <div role="row" key={label}>
            <span role="cell">{label}</span>
            <strong role="cell">{a}</strong>
            <strong role="cell">{b}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
