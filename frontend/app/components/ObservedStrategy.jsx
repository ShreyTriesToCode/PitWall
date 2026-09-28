"use client";

import { useState } from "react";
import { EmptyState } from "./PitWallComponents";

const label = (row) =>
  row.driver?.full_name ||
  row.driver?.name_acronym ||
  row.driver?.broadcast_name ||
  `Driver ${row.driver_number}`;
const age = (row) => {
  const raw = row.tyre_age;
  if (
    (typeof raw !== "number" && typeof raw !== "string") ||
    String(raw).trim() === ""
  )
    return null;
  const count = Number(raw);
  return Number.isInteger(count) && count >= 0 ? count : null;
};

export default function ObservedStrategy({ rows, available, loading }) {
  const [compound, setCompound] = useState("all");
  const [sort, setSort] = useState("position");
  const compounds = [
    ...new Set(rows.map((r) => r.compound).filter(Boolean)),
  ].sort();
  const selected = compounds.includes(compound) ? compound : "all";
  const visible = rows
    .filter((r) => selected === "all" || r.compound === selected)
    .toSorted((a, b) =>
      sort === "age"
        ? (age(b) ?? -1) - (age(a) ?? -1)
        : (a.position ?? Infinity) - (b.position ?? Infinity),
    );
  return (
    <section className="product-section observed-strategy">
      <div className="section-heading">
        <h2>Tyre comparison</h2>
        <span className="muted">Observed, not a pit-stop forecast</span>
      </div>
      <p className="product-note">
        Compare the latest reported compound and tyre age in this session. Lap
        times include traffic, fuel and track conditions; they do not establish
        tyre degradation or an optimal pit window.
      </p>
      {!available || !rows.length ? (
        <EmptyState
          title={
            loading
              ? "Loading tyre observations…"
              : "Tyre observations unavailable"
          }
          body={
            loading
              ? "Checking the selected session’s tyre feed."
              : "Choose another session or refresh. No tyre plan is substituted for missing data."
          }
        />
      ) : (
        <>
          <div className="strategy-controls">
            <label>
              Compound
              <select
                aria-label="Compound"
                value={selected}
                onChange={(e) => setCompound(e.target.value)}
              >
                <option value="all">All compounds</option>
                {compounds.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <label>
              Order
              <select
                aria-label="Order"
                value={sort}
                onChange={(e) => setSort(e.target.value)}
              >
                <option value="position">Timing position</option>
                <option value="age">Oldest reported tyres</option>
              </select>
            </label>
          </div>
          <p className="product-note">
            {visible.length} of {rows.length} drivers shown ·{" "}
            {rows.filter((r) => !r.compound || age(r) === null).length} with
            incomplete tyre observations
          </p>
          <div
            className="table-scroll"
            role="region"
            aria-label="Observed tyre comparison"
            tabIndex={0}
          >
            <table className="product-table strategy-table">
              <caption className="sr-only">Observed tyre comparison</caption>
              <thead>
                <tr>
                  <th scope="col">Driver</th>
                  <th scope="col">Compound</th>
                  <th scope="col">Age</th>
                  <th scope="col">Last lap</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((r) => (
                  <tr key={r.driver_number}>
                    <th scope="row">{label(r)}</th>
                    <td>
                      <span
                        className={`compound-label compound-${String(r.compound).toLowerCase()}`}
                      >
                        {r.compound || "Unavailable"}
                      </span>
                    </td>
                    <td>
                      {age(r) === null ? "Unavailable" : `${age(r)} laps`}
                    </td>
                    <td>{r.lap_duration ?? "Unavailable"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="product-note">
            Tyre age is the provider’s latest reported lap count. Stops, tyre
            reuse and missing updates can prevent a complete stint history.
            Weather and race control below belong to this selected session.
          </p>
        </>
      )}
    </section>
  );
}
