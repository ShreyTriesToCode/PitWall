"use client";

import { useState } from "react";
import {
  AnimatedTicker,
  AppShell,
  FavoriteButton,
  DriverExplainabilityDrawer,
  EmptyState,
  InlineNotice,
  LoadingSkeleton,
  PageHeader,
  SearchBox,
  SectionTitle,
  usePinnedIds,
  useFilteredDrivers,
  usePitWallData,
} from "../components/PitWallComponents";

export default function DriverAnalysisPage() {
  const { loading, data, error, warning, refetch, refreshing } = usePitWallData("/api/predictions");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [watchlistOnly, setWatchlistOnly] = useState(false);
  const pins = usePinnedIds();
  const fullGrid = data?.full_grid || data?.all_predictions || data?.latest?.full_grid || data?.latest?.all_predictions || data?.top10 || [];
  const searchedDrivers = useFilteredDrivers(fullGrid, query);
  const drivers = searchedDrivers
    .filter((item) => !watchlistOnly || pins.includes(item.driver_id))
    .sort((a, b) => Number(pins.includes(b.driver_id)) - Number(pins.includes(a.driver_id)) || Number(a.rank || 999) - Number(b.rank || 999));
  return (
    <AppShell active="/drivers">
      <AnimatedTicker latest={data?.latest} />
      <PageHeader eyebrow="Driver Analysis" title="Driver Intelligence" description="Driver profiles, momentum proxies, reliability, strengths, weaknesses, teammate gaps, and 2026 Boost suitability." />
      {loading && <LoadingSkeleton />}
      {error && <InlineNotice title="Driver data sync failed" body={error} tone="error" action={<button className="control-btn" onClick={refetch}>Retry</button>} />}
      {warning && <InlineNotice title="Fallback driver data" body={warning} tone="warning" />}
      {data?.latest && (
        <>
          <section className="toolbar panel reveal">
            <SearchBox value={query} onChange={setQuery} placeholder="Search driver watchlist" />
            <button className={watchlistOnly ? "control-btn active" : "control-btn"} onClick={() => setWatchlistOnly((value) => !value)}>
              {watchlistOnly ? "Showing watchlist" : `Watchlist (${pins.length})`}
            </button>
            <button className="control-btn" onClick={refetch} disabled={refreshing}>{refreshing ? "Refreshing" : "Refresh data"}</button>
          </section>
          <section className="panel reveal">
            <SectionTitle title="Driver Grid" action={<span className="muted-action">Click a driver to open analysis</span>} />
            <div className="driver-grid">
              {drivers.map((item) => (
                <article className="driver-grid-card" key={item.driver_id}>
                  <FavoriteButton id={item.driver_id} />
                  <button className="driver-grid-open" type="button" onClick={() => setSelected(item)}>
                    <span>P{item.rank}</span>
                    <strong>{item.name}</strong>
                    <small>{item.team}</small>
                    <i>{item.confidence}% confidence</i>
                  </button>
                </article>
              ))}
            </div>
            {!drivers.length && <EmptyState title={watchlistOnly ? "No pinned drivers yet" : "No driver matches"} body={watchlistOnly ? "Pin drivers from this grid or the prediction cards to build a watchlist." : "Clear the search or try a different driver/team."} />}
          </section>
          <DriverExplainabilityDrawer driver={selected} onClose={() => setSelected(null)} />
        </>
      )}
    </AppShell>
  );
}
