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
  const targetMap = useMemo(() => new Map(generatedTargets.map((target) => [target.target_type, target])), [generatedTargets]);
  const selectedTarget = targetMap.get(requestedTarget) || (!generatedTargets.length && latest ? {
    ...latest,
    title: latest.title || latest.race_name,
    top10: data?.top10 || [],
    target_type: latest.target_type,
    stage: latest.stage,
  } : null);
  const targetPending = Boolean(requestedTarget && !targetMap.has(requestedTarget) && generatedTargets.length);
  const selectedTop10 = targetPending ? [] : selectedTarget?.top10?.length ? selectedTarget.top10 : data?.top10 || [];
  const predictions = useFilteredDrivers(selectedTop10, query);
  const generatedTargetTypes = new Set(generatedTargets.map((target) => target.target_type));
  const summary = useMemo(() => {
    const top = predictions.slice(0, 3).map((p) => `P${p.rank} ${p.name} (${p.team})`).join(", ");
    return `${selectedTarget?.title || latest?.race_name || "PitWall"}: ${top || "No prediction rows available"}. Stage: ${selectedTarget?.stage || latest?.stage || "pending"}.`;
  }, [latest, predictions, selectedTarget]);

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
      <PageHeader eyebrow="Prediction Intelligence" title="Predictions" description="Grid-aware, practice-aware, scenario-adjusted top 10 model board." actions={<CopySummaryButton text={summary} />} />
      {loading && <LoadingSkeleton />}
      {error && <InlineNotice title="Prediction sync failed" body={error} tone="error" action={<button className="control-btn" onClick={refetch}>Retry</button>} />}
      {warning && <InlineNotice title="Fallback prediction data" body={warning} tone="warning" />}
      {latest && (
        <>
          <section className="toolbar panel reveal">
            <SearchBox value={query} onChange={setQuery} placeholder="Search drivers or teams" />
            <TargetTabs active={requestedTarget} available={generatedTargetTypes} onSelect={selectTarget} />
            <button className={view === "table" ? "control-btn active" : "control-btn"} onClick={() => setView("table")} disabled={!predictions.length}>Table</button>
            <button className={view === "cards" ? "control-btn active" : "control-btn"} onClick={() => setView("cards")} disabled={!predictions.length}>Cards</button>
            <button className="control-btn" onClick={refetch} disabled={refreshing}>{refreshing ? "Refreshing" : "Refresh data"}</button>
            <StatusBadge label={targetPending ? `${requestedTarget} pending` : selectedTarget?.stage || latest.stage} tone="red" />
          </section>
          <section className="metric-grid">
            <Metric label="Prediction ID" value={targetPending ? "Pending generation" : latest.prediction_id} />
            <Metric label="Target" value={targetPending ? requestedTarget : selectedTarget?.target_type || latest.target_type} />
            <Metric label="Model Agreement Leader" value={`${predictions[0]?.model_agreement_score ?? "Pending"}%`} />
            <Metric label="Dark Horse" value={predictions.find((p) => p.dark_horse_flag)?.name || "Not flagged"} />
          </section>
          {!predictions.length && <EmptyState title={targetPending ? `${requestedTarget} prediction pending` : "No prediction rows match"} body={targetPending ? "That target has not been generated yet. The next backend run will expose it when the data exists." : "Clear the search or try another driver/team."} />}
          {predictions.length > 0 && (view === "table" ? <PredictionTable predictions={predictions} onOpen={setSelected} /> : <div className="card-grid">{predictions.map((item) => <PredictionCard item={item} key={item.driver_id} onOpen={setSelected} />)}</div>)}
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
          </section>}
          {predictions.length > 0 && <ScenarioCards scenarios={selectedTarget?.scenarios || latest.scenarios} />}
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
