"use client";

import { useMemo, useState } from "react";
import {
  AnimatedTicker,
  AppShell,
  CompactTable,
  DataStateBadge,
  DriverExplainabilityDrawer,
  EmptyState,
  FavoriteButton,
  InlineNotice,
  LoadingSkeleton,
  Metric,
  normalizeQuery,
  PageHeader,
  SearchBox,
  SectionCard,
  StatusBadge,
  useFilteredDrivers,
  usePinnedIds,
  usePitWallData,
} from "../components/PitWallComponents";

function pctValue(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(1)}%` : "Pending";
}

function sortDrivers(rows, key) {
  const copy = [...rows];
  const numeric = (row, field, fallback = -Infinity) => {
    const value = Number(row?.[field]);
    return Number.isFinite(value) ? value : fallback;
  };
  if (key === "confidence") return copy.sort((a, b) => numeric(b, "confidence") - numeric(a, "confidence"));
  if (key === "trust") return copy.sort((a, b) => numeric(b, "prediction_trust_score") - numeric(a, "prediction_trust_score"));
  if (key === "team") return copy.sort((a, b) => String(a.team || "").localeCompare(String(b.team || "")) || numeric(a, "rank", 999) - numeric(b, "rank", 999));
  return copy.sort((a, b) => numeric(a, "rank", 999) - numeric(b, "rank", 999));
}

export default function DriverAnalysisPage() {
  const { loading, data, error, warning, refetch, refreshing } = usePitWallData("/api/predictions");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [watchlistOnly, setWatchlistOnly] = useState(false);
  const [teamFilter, setTeamFilter] = useState("all");
  const [rankMax, setRankMax] = useState("22");
  const [minConfidence, setMinConfidence] = useState("0");
  const [sortKey, setSortKey] = useState("rank");
  const pins = usePinnedIds();
  const fullGrid = data?.full_grid || data?.all_predictions || data?.latest?.full_grid || data?.latest?.all_predictions || data?.top10 || [];
  const searchedDrivers = useFilteredDrivers(fullGrid, query);
  const teams = useMemo(() => Array.from(new Set(fullGrid.map((row) => row.team).filter(Boolean))).sort(), [fullGrid]);
  const drivers = useMemo(() => {
    const maxRank = Number(rankMax);
    const confidence = Number(minConfidence);
    return sortDrivers(searchedDrivers
      .filter((item) => !watchlistOnly || pins.includes(item.driver_id))
      .filter((item) => teamFilter === "all" || item.team === teamFilter)
      .filter((item) => !Number.isFinite(maxRank) || Number(item.rank || 999) <= maxRank)
      .filter((item) => !Number.isFinite(confidence) || Number(item.confidence || 0) >= confidence), sortKey);
  }, [searchedDrivers, watchlistOnly, pins, teamFilter, rankMax, minConfidence, sortKey]);
  const selectedRows = drivers.slice(0, 3);

  const columns = [
    { header: "Rank", render: (row) => <strong>P{row.rank}</strong> },
    { header: "Driver", render: (row) => <><strong>{row.name}</strong><small>{row.driver_id}</small></> },
    { header: "Team", render: (row) => row.team || "Unknown" },
    { header: "Confidence", render: (row) => <DataStateBadge status={Number(row.confidence) >= 40 ? "available" : "fallback"} label={pctValue(row.confidence)} /> },
    { header: "Trust", render: (row) => <><strong>{pctValue(row.prediction_trust_score)}</strong><small>{row.prediction_trust_label || "Trust pending"}</small></> },
    { header: "Top 10", render: (row) => pctValue(row.top10_probability) },
    { header: "Win", render: (row) => pctValue(row.win_probability) },
    { header: "Watch", render: (row) => <FavoriteButton id={row.driver_id} /> },
  ];

  return (
    <AppShell active="/drivers">
      <AnimatedTicker latest={data?.latest} />
      <PageHeader eyebrow="Driver Analysis" title="Driver Intelligence" description="Compact P1-P22 driver ranking, filters, watchlist state, and selected-driver evidence." />
      {loading && <LoadingSkeleton />}
      {error && <InlineNotice title="Driver data sync failed" body={error} tone="error" action={<button className="control-btn" onClick={refetch}>Retry</button>} />}
      {warning && <InlineNotice title="Fallback driver data" body={warning} tone="warning" />}
      {data?.latest && (
        <>
          <section className="toolbar panel compact-toolbar reveal">
            <SearchBox value={query} onChange={setQuery} placeholder="Search drivers or teams" />
            <label className="compact-filter"><span>Team</span><select value={teamFilter} onChange={(event) => setTeamFilter(event.target.value)}><option value="all">All teams</option>{teams.map((team) => <option value={team} key={team}>{team}</option>)}</select></label>
            <label className="compact-filter"><span>Rank</span><select value={rankMax} onChange={(event) => setRankMax(event.target.value)}><option value="22">P1-P22</option><option value="10">P1-P10</option><option value="6">P1-P6</option></select></label>
            <label className="compact-filter"><span>Confidence</span><select value={minConfidence} onChange={(event) => setMinConfidence(event.target.value)}><option value="0">Any</option><option value="10">10%+</option><option value="25">25%+</option><option value="40">40%+</option></select></label>
            <label className="compact-filter"><span>Sort</span><select value={sortKey} onChange={(event) => setSortKey(event.target.value)}><option value="rank">Rank</option><option value="confidence">Confidence</option><option value="trust">Trust</option><option value="team">Team</option></select></label>
            <button className={watchlistOnly ? "control-btn active" : "control-btn"} onClick={() => setWatchlistOnly((value) => !value)}>
              {watchlistOnly ? "Watchlist only" : `Watchlist (${pins.length})`}
            </button>
            <button className="control-btn" onClick={refetch} disabled={refreshing}>{refreshing ? "Refreshing" : "Refresh"}</button>
          </section>

          <SectionCard title="Driver Ranking Table" action={<StatusBadge label={`${drivers.length}/${fullGrid.length || 22} drivers`} tone="green" />}>
            <CompactTable columns={columns} rows={drivers} onRow={setSelected} getKey={(row) => row.driver_id} emptyTitle={watchlistOnly ? "No pinned drivers yet" : "No driver matches"} emptyBody={watchlistOnly ? "Pin drivers from the table to build a watchlist." : "Clear filters or try another team/driver."} />
          </SectionCard>

          <SectionCard title="Selected Driver Shortlist" show={selectedRows.length > 0}>
            <div className="metric-grid compact">
              {selectedRows.map((row) => <Metric key={row.driver_id} label={`P${row.rank} ${row.name}`} value={`${row.team || "Unknown"} · ${pctValue(row.confidence)} confidence`} />)}
            </div>
          </SectionCard>

          {!drivers.length && <EmptyState title={watchlistOnly ? "No pinned drivers yet" : "No driver matches"} body={watchlistOnly ? "Pin drivers from this grid or the prediction cards to build a watchlist." : "Clear the search or try a different driver/team."} />}
          <DriverExplainabilityDrawer driver={selected} onClose={() => setSelected(null)} />
        </>
      )}
    </AppShell>
  );
}
