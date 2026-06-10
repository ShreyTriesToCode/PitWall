"use client";

import { useMemo, useState } from "react";
import { AnimatedTicker, AppShell, CompactTable, EmptyState, InlineNotice, LoadingSkeleton, Metric, normalizeQuery, PageHeader, SearchBox, SectionCard, StatusBadge, TagRow, usePitWallData } from "../components/PitWallComponents";

const fallbackConstructors = [
  "Mercedes",
  "Ferrari",
  "McLaren",
  "Red Bull",
  "Aston Martin",
  "Alpine",
  "Williams",
  "RB F1 Team",
  "Haas",
  "Audi",
  "Cadillac",
];

const constructorAliases = {
  "mercedes-amg petronas f1 team": "Mercedes",
  "mercedes-amg": "Mercedes",
  "scuderia ferrari": "Ferrari",
  "scuderia ferrari hp": "Ferrari",
  "mclaren mastercard f1 team": "McLaren",
  "mclaren f1 team": "McLaren",
  "oracle red bull racing": "Red Bull",
  "red bull racing": "Red Bull",
  "aston martin aramco formula one team": "Aston Martin",
  "aston martin": "Aston Martin",
  "racing point": "Aston Martin",
  "force india": "Aston Martin",
  "bwt alpine formula one team": "Alpine",
  "alpine f1 team": "Alpine",
  "renault": "Alpine",
  "atlassian williams f1 team": "Williams",
  "williams racing": "Williams",
  "visa cash app rb formula one team": "RB F1 Team",
  "visa cash app racing bulls formula one team": "RB F1 Team",
  "racing bulls": "RB F1 Team",
  "alphatauri": "RB F1 Team",
  "toro rosso": "RB F1 Team",
  "moneygram haas f1 team": "Haas",
  "tgr haas f1 team": "Haas",
  "haas f1 team": "Haas",
  "audi revolut f1 team": "Audi",
  "sauber": "Audi",
  "kick sauber": "Audi",
  "cadillac formula 1 team": "Cadillac",
  "cadillac f1 team": "Cadillac",
};

function canonicalConstructorName(value) {
  const raw = String(value || "").trim();
  if (!raw) return "Unknown";
  const key = raw.toLowerCase().replace(/&/g, "and").replace(/\s+/g, " ");
  return constructorAliases[key] || raw
    .replace(/\bF1 Team\b/gi, "")
    .replace(/\bFormula One Team\b/gi, "")
    .replace(/\s+/g, " ")
    .trim();
}

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
  const [selectedTeam, setSelectedTeam] = useState("");
  const teams = useMemo(() => {
    const latest = data?.latest || {};
    const predictionRows = data?.full_grid || data?.all_predictions || latest.full_grid || latest.all_predictions || data?.top10 || [];
    const grouped = predictionRows.reduce((acc, item) => {
      const team = canonicalConstructorName(item.team);
      (acc[team] ||= []).push({ ...item, team });
      return acc;
    }, {});
    const traitTeams = Object.keys(latest.upgrade_context?.team_traits || {}).map(canonicalConstructorName);
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
      ...pitRows.map((row) => canonicalConstructorName(row.team)).filter(Boolean),
      ...scenarioRows.map((row) => canonicalConstructorName(row.team)).filter(Boolean),
    ].map(canonicalConstructorName)));
    const q = normalizeQuery(query);
    return teamNames.map((team) => {
      const drivers = grouped[team] || [];
      const teamPitRows = pitRows.filter((row) => canonicalConstructorName(row.team) === team);
      const scenarioMentions = scenarioRows.filter((row) => canonicalConstructorName(row.team) === team).length;
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
  const activeTeam = teams.find((team) => team.team === selectedTeam) || teams[0];
  const columns = [
    { header: "Team", render: (team) => <><strong>{team.team}</strong><small>{team.drivers.map((driver) => driver.name).join(" / ") || "Driver rows pending"}</small></> },
    { header: "Expected Points", render: (team) => formatMetric(team.expected) },
    { header: "Team Score", render: (team) => formatMetric(team.score) },
    { header: "Pit Execution", render: (team) => formatMetric(team.pit, "%") },
    { header: "Active Aero", render: (team) => formatMetric(team.aero, "%") },
    { header: "Energy Deployment", render: (team) => formatMetric(team.boost, "%") },
    { header: "Top-10 Safety", render: (team) => formatMetric(team.top10Safety, "%") },
  ];
  return (
    <AppShell active="/teams">
      <AnimatedTicker latest={data?.latest} />
      <PageHeader eyebrow="Team Analysis" title="Constructor Intelligence" description="Team points, strategy risk, tyre management, pit execution, reliability threats, and teammate battles." />
      {loading && <LoadingSkeleton />}
      {error && <InlineNotice title="Team data sync failed" body={error} tone="error" action={<button className="control-btn" onClick={refetch}>Retry</button>} />}
      {warning && <InlineNotice title="Fallback team data" body={warning} tone="warning" />}
      {data?.latest && (
        <>
          <section className="toolbar panel compact-toolbar reveal">
            <SearchBox value={query} onChange={setQuery} placeholder="Search constructors" />
            <button className="control-btn" onClick={refetch} disabled={refreshing}>{refreshing ? "Refreshing" : "Refresh data"}</button>
          </section>
          <SectionCard title="Constructor Comparison" action={<StatusBadge label={`${teams.length} constructors`} tone="green" />}>
            <CompactTable columns={columns} rows={teams} getKey={(team) => team.team} onRow={(team) => setSelectedTeam(team.team)} emptyTitle="No constructor matches" emptyBody="Clear the search or try a team or driver name from the current prediction board." />
          </SectionCard>
          {activeTeam && (
            <SectionCard title={`${activeTeam.team} Details`} action={<StatusBadge label={activeTeam.hasPredictionRows ? "prediction evidence" : "limited evidence"} tone={activeTeam.hasPredictionRows ? "green" : "amber"} />}>
              <div className="metric-grid compact">
                <Metric label="Expected Points" value={formatMetric(activeTeam.expected)} />
                <Metric label="Team Score" value={formatMetric(activeTeam.score)} />
                <Metric label="Pit Execution" value={formatMetric(activeTeam.pit, "%")} />
                <Metric label="Active Aero" value={formatMetric(activeTeam.aero, "%")} />
                <Metric label="Energy Deployment" value={formatMetric(activeTeam.boost, "%")} />
                <Metric label="Top-10 Safety" value={formatMetric(activeTeam.top10Safety, "%")} />
                <Metric label="Tyre Management" value={data.latest.strategy?.tyre_degradation_model?.label || "Pending"} />
              </div>
              <div className="constructor-battle compact">
                {activeTeam.drivers.length ? activeTeam.drivers.map((driver) => (
                  <article key={driver.driver_id}>
                    <strong>{driver.name}</strong>
                    <span>P{driver.rank}</span>
                    <small>{driver.teammate_prediction_gap ?? "No teammate gap"} score gap</small>
                  </article>
                )) : (
                  <article>
                    <strong>Full constructor listed</strong>
                    <span>Pending driver row</span>
                    <small>No prediction row for this team in the current generated contract.</small>
                  </article>
                )}
              </div>
              <TagRow tags={[
                activeTeam.hasPredictionRows ? "prediction evidence available" : "not enough driver evidence yet",
                activeTeam.scenarioMentions ? `${activeTeam.scenarioMentions} scenario mentions` : "scenario watchlist pending",
                "constructor aliases normalized",
              ]} />
            </SectionCard>
          )}
          {!teams.length && <EmptyState title="No constructor matches" body="Clear the search or try a team or driver name from the current prediction board." />}
        </>
      )}
    </AppShell>
  );
}
