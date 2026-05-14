"use client";

import { useMemo, useState } from "react";
import { AnimatedTicker, AppShell, EmptyState, InlineNotice, LoadingSkeleton, Metric, normalizeQuery, PageHeader, SearchBox, SectionTitle, TagRow, usePitWallData } from "../components/PitWallComponents";

const fallbackConstructors = [
  "Mercedes",
  "Ferrari",
  "McLaren",
  "Red Bull",
  "Aston Martin",
  "Alpine F1 Team",
  "Williams",
  "Racing Bulls",
  "Haas F1 Team",
  "Audi",
  "Cadillac F1 Team",
];

function avg(rows, pick) {
  const values = rows.map(pick).map(Number).filter(Number.isFinite);
  if (!values.length) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function formatMetric(value, suffix = "") {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(1)}${suffix}` : "Not enough data";
}

export default function TeamAnalysisPage() {
  const { loading, data, error, warning, refetch, refreshing } = usePitWallData("/api/predictions");
  const [query, setQuery] = useState("");
  const teams = useMemo(() => {
    const latest = data?.latest || {};
    const predictionRows = data?.full_grid || data?.all_predictions || latest.full_grid || latest.all_predictions || data?.top10 || [];
    const grouped = predictionRows.reduce((acc, item) => ((acc[item.team] ||= []).push(item), acc), {});
    const traitTeams = Object.keys(latest.upgrade_context?.team_traits || {});
    const pitRows = latest.strategy?.pit_execution_model || [];
    const scenarioRows = [
      ...(latest.strategy?.rain_beneficiaries || []),
      ...(latest.strategy?.safety_car_beneficiaries || []),
      ...Object.values(latest.scenarios || {}).flatMap((scenario) => Array.isArray(scenario?.ranking) ? scenario.ranking : []),
    ];
    const teamNames = Array.from(new Set([
      ...fallbackConstructors,
      ...traitTeams,
      ...Object.keys(grouped),
      ...pitRows.map((row) => row.team).filter(Boolean),
      ...scenarioRows.map((row) => row.team).filter(Boolean),
    ]));
    const q = normalizeQuery(query);
    return teamNames.map((team) => {
      const drivers = grouped[team] || [];
      const teamPitRows = pitRows.filter((row) => row.team === team);
      const scenarioMentions = scenarioRows.filter((row) => row.team === team).length;
      return {
        team,
        drivers,
        expected: avg(drivers, (d) => d.expected_points),
        score: avg(drivers, (d) => d.score),
        pit: avg(drivers, (d) => d.component_scores?.pit_execution) ?? avg(teamPitRows, (row) => row.score),
        aero: avg(drivers, (d) => d.active_aero_suitability_score),
        boost: avg(drivers, (d) => d.energy_boost_advantage_score),
        top10Safety: avg(drivers, (d) => d.top10_safety_score),
        scenarioMentions,
        hasPredictionRows: drivers.length > 0,
      };
    }).filter((t) => normalizeQuery(`${t.team} ${t.drivers.map((driver) => driver.name).join(" ")}`).includes(q)).sort((a, b) => {
      const scoreA = Number.isFinite(Number(a.expected)) ? Number(a.expected) : -1;
      const scoreB = Number.isFinite(Number(b.expected)) ? Number(b.expected) : -1;
      return scoreB - scoreA || b.scenarioMentions - a.scenarioMentions || a.team.localeCompare(b.team);
    });
  }, [data, query]);
  return (
    <AppShell active="/teams">
      <AnimatedTicker latest={data?.latest} />
      <PageHeader eyebrow="Team Analysis" title="Constructor Intelligence" description="Team points, strategy risk, tyre management, pit execution, reliability threats, and teammate battles." />
      {loading && <LoadingSkeleton />}
      {error && <InlineNotice title="Team data sync failed" body={error} tone="error" action={<button className="control-btn" onClick={refetch}>Retry</button>} />}
      {warning && <InlineNotice title="Fallback team data" body={warning} tone="warning" />}
      {data?.latest && (
        <>
          <section className="toolbar panel reveal">
            <SearchBox value={query} onChange={setQuery} placeholder="Search constructors" />
            <button className="control-btn" onClick={refetch} disabled={refreshing}>{refreshing ? "Refreshing" : "Refresh data"}</button>
          </section>
          <div className="team-grid">
            {teams.map((team) => (
              <section className="panel team-card reveal" key={team.team}>
                <SectionTitle title={team.team} />
                <div className="metric-grid">
                  <Metric label="Expected Points" value={formatMetric(team.expected)} />
                  <Metric label="Team Score" value={formatMetric(team.score)} />
                  <Metric label="Pit Execution" value={formatMetric(team.pit, "%")} />
                  <Metric label="Active Aero" value={formatMetric(team.aero, "%")} />
                  <Metric label="Energy Deployment" value={formatMetric(team.boost, "%")} />
                  <Metric label="Top-10 Safety" value={formatMetric(team.top10Safety, "%")} />
                  <Metric label="Tyre Management" value={data.latest.strategy?.tyre_degradation_model?.label || "Pending"} />
                </div>
                <div className="constructor-battle">
                  {team.drivers.length ? team.drivers.map((driver) => (
                    <article key={driver.driver_id}>
                      <strong>{driver.name}</strong>
                      <span>P{driver.rank}</span>
                      <small>{driver.teammate_prediction_gap ?? "No teammate gap"} score gap</small>
                    </article>
                  )) : (
                    <article>
                      <strong>Full constructor listed</strong>
                      <span>Pending driver row</span>
                      <small>No top-10 prediction row for this team in the current generated contract.</small>
                    </article>
                  )}
                </div>
                <TagRow tags={[
                  team.hasPredictionRows ? "prediction evidence available" : "not enough driver evidence yet",
                  team.scenarioMentions ? `${team.scenarioMentions} scenario mentions` : "scenario watchlist pending",
                  "strategy risk ranking",
                  "reliability threat board",
                  "track fit",
                  "weather fit",
                ]} />
              </section>
            ))}
          </div>
          {!teams.length && <EmptyState title="No constructor matches" body="Clear the search or try a team or driver name from the current prediction board." />}
        </>
      )}
    </AppShell>
  );
}
