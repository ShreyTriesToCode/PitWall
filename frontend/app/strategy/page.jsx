"use client";

import { useState } from "react";
import { AnimatedTicker, AppShell, EmptyState, InlineNotice, LoadingSkeleton, Metric, PageHeader, RaceControlTimeline, ScenarioCards, SectionTitle, StatusBadge, StrategyPanel, usePitWallData } from "../components/PitWallComponents";

export default function StrategyLabPage() {
  const { loading, data, error, warning, refetch, refreshing } = usePitWallData("/api/predictions");
  const [rain, setRain] = useState(40);
  const [safety, setSafety] = useState(45);
  const [deg, setDeg] = useState(55);
  const [temp, setTemp] = useState(32);
  const strategy = data?.latest?.strategy || {};
  const rainRisk = data?.latest?.weather?.rain || data?.latest?.race_factors?.rain_impact;
  const rainUnavailable = !rainRisk || String(rainRisk).toLowerCase().includes("unavailable");
  const scenarios = { ...(data?.latest?.scenarios || {}) };
  if (rainUnavailable && scenarios.rain) {
    scenarios.rain = {
      ...scenarios.rain,
      notes: `${scenarios.rain.notes || "Rain scenario uses weather adaptation and reliability component scores."} Live rain-risk source is unavailable, so this is a simulated sensitivity view, not official weather output.`,
    };
  }
  const visualOutput = Math.round((Number(rain) * 0.25) + (Number(safety) * 0.25) + (Number(deg) * 0.30) + (Number(temp) * 0.20));
  return (
    <AppShell active="/strategy">
      <AnimatedTicker latest={data?.latest} />
      <PageHeader eyebrow="Strategy Lab" title="PitWall Strategy Lab" description="Scenario comparison, chaos timeline, pit windows, tyre degradation, and 2026 Boost / Overtake Mode Intelligence." />
      {loading && <LoadingSkeleton />}
      {error && <InlineNotice title="Strategy data sync failed" body={error} tone="error" action={<button className="control-btn" onClick={refetch}>Retry</button>} />}
      {warning && <InlineNotice title="Fallback strategy data" body={warning} tone="warning" />}
      {data?.latest && (
        <>
          <section className="toolbar panel compact-toolbar reveal">
            <button className="control-btn" onClick={refetch} disabled={refreshing}>{refreshing ? "Refreshing" : "Refresh strategy data"}</button>
            <button className="control-btn" onClick={() => { setRain(40); setSafety(45); setDeg(55); setTemp(32); }}>Reset simulator</button>
            <StatusBadge label="scenario output simulated" tone="amber" />
          </section>
          <section className="dashboard-grid compact-dashboard">
            <StrategyPanel strategy={strategy} />
            <section className="panel reveal">
              <SectionTitle title="PitWall Decision Log" />
              <RaceControlTimeline items={strategy.decision_log} />
            </section>
            <section className="panel reveal">
              <SectionTitle title="Active Aero Mode Panel" />
              <div className="metric-grid">
                <Metric label="Straight Mode" value={strategy.active_aero?.straight_mode} />
                <Metric label="Corner Mode" value={strategy.active_aero?.corner_mode} />
                <Metric label="Suitability" value={`${strategy.active_aero?.average_suitability ?? "Pending"}%`} />
                <Metric label="Boost Advantage" value={`${strategy.energy_deployment?.average_boost_advantage ?? "Pending"}%`} />
              </div>
            </section>
            <section className="panel simulator reveal">
              <SectionTitle title="What-if Simulator" />
              {[
                ["Rain risk", rain, setRain],
                ["Safety-car probability", safety, setSafety],
                ["Tyre degradation", deg, setDeg],
                ["Track temperature", temp, setTemp],
              ].map(([label, value, setter]) => (
                <label key={label}><span>{label}</span><input type="range" min="0" max="100" value={value} onChange={(e) => setter(Number(e.target.value))} /><b>{value}</b></label>
              ))}
              <Metric label="Visual scenario output" value={`${visualOutput}% chaos`} />
              <p>This simulator output is a visual scenario aid, not an official final model output.</p>
            </section>
          </section>
          {rainUnavailable && <InlineNotice title="Rain scenario is simulated" body="Rain risk is unavailable from trusted live weather data, so rain rankings are generated from model component sensitivities and labelled as simulated." tone="warning" />}
          {Object.keys(scenarios).length ? <ScenarioCards scenarios={scenarios} /> : <EmptyState title="No scenario rankings" body="Scenario output appears when the generated prediction contract includes ranked scenario rows." />}
        </>
      )}
    </AppShell>
  );
}
