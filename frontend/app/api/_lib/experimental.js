import { createHash } from "node:crypto";

const models = {
  pre_qualifying: "pre-race-form-ridge-v1",
  post_qualifying: "prior-form-ridge-v1",
};
const mean = (values) =>
  values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;

export function validateExperimental(p, timestamp, digest) {
  const inputs = p.inputs,
    artifact = JSON.parse(inputs.model_json);
  if (
    inputs.stage !== p.stage ||
    p.entry_status !==
      (p.stage === "pre_qualifying"
        ? "PROJECTED_FROM_LAST_RESULT"
        : "QUALIFYING_FIELD")
  )
    throw new Error("Experimental stage/entry disclosure mismatch");
  const start = timestamp(p.event.start_at),
    capture = timestamp(p.generated_at);
  if (
    p.status !== "EXPERIMENTAL" ||
    p.race_id !== p.event.id ||
    models[p.stage] !== p.model_version ||
    artifact.model_version !== p.model_version ||
    p.feature_version !== artifact.feature_version ||
    p.training_data_cutoff !== artifact.training_data_cutoff ||
    !(timestamp(p.training_data_cutoff) < capture && capture < start) ||
    createHash("sha256").update(inputs.model_json).digest("hex") !==
      inputs.model_hash
  )
    throw new Error("Invalid experimental model identity or chronology");
  const history = [...inputs.history].sort(
    (a, b) => timestamp(a.event.start_at) - timestamp(b.event.start_at),
  );
  if (
    new Set(history.map((r) => r.event.id)).size !== history.length ||
    history.some(
      (r) => r.event.id === p.race_id || timestamp(r.event.start_at) >= start,
    )
  )
    throw new Error("Experimental history contains target or future data");
  const entrants = inputs.entrants;
  if (
    entrants.length < 2 ||
    new Set(entrants.map((r) => r.driver_id)).size !== entrants.length
  )
    throw new Error("Invalid experimental entrant field");
  if (p.stage === "pre_qualifying") {
    const previous = history.find(
      (r) => r.event.id === inputs.field_source.event.id,
    );
    const projected = previous?.results.map(({ driver_id, name, team }) => ({
      driver_id,
      name,
      team,
    }));
    if (
      inputs.field_source.kind !== "previous_classification" ||
      digest(projected) !== digest(entrants)
    )
      throw new Error("Projected entrant field does not match source");
  } else if (
    inputs.field_source.kind !== "qualifying" ||
    inputs.field_source.event.id !== p.race_id ||
    [...entrants]
      .map((r) => r.position)
      .sort((a, b) => a - b)
      .some((n, i) => n !== i + 1)
  ) {
    throw new Error("Invalid qualifying field");
  }
  const rows = entrants
    .map((driver) => {
      const finishes = [],
        quals = [],
        teams = [],
        failures = [];
      for (const race of history) {
        const actual = race.results || [],
          qualifying = race.qualifying || [];
        const own = actual.find((r) => r.driver_id === driver.driver_id);
        if (own && actual.length > 1) {
          finishes.push((own.position - 1) / (actual.length - 1));
          if (own.status)
            failures.push(
              Number(
                !["Finished", "Lapped"].includes(own.status) &&
                  !own.status.startsWith("+"),
              ),
            );
        }
        const q = qualifying.find((r) => r.driver_id === driver.driver_id);
        if (q && qualifying.length > 1)
          quals.push((q.position - 1) / (qualifying.length - 1));
        const members = actual
          .filter((r) => r.team === driver.team && actual.length > 1)
          .map((r) => (r.position - 1) / (actual.length - 1));
        if (members.length) teams.push(mean(members));
      }
      let x = [
        p.stage === "post_qualifying"
          ? (driver.position - 1) / (entrants.length - 1)
          : null,
        mean(finishes.slice(-5)),
        mean(quals.slice(-5)),
        mean(teams.slice(-5)),
        mean(failures.slice(-5)),
        Math.min(finishes.length, 5),
        Math.min(teams.length, 5),
      ];
      if (p.stage === "pre_qualifying") x = x.slice(1);
      const missing = x.map((v) => v === null);
      const values = x.map((v, i) =>
        missing[i] ? artifact.imputation_medians[i] : v,
      );
      values.push(
        ...artifact.missing_indicators.map((i) => Number(missing[i])),
      );
      if (values.length !== artifact.coefficients.length)
        throw new Error("Experimental feature width mismatch");
      const score = values.reduce(
        (sum, v, i) =>
          sum +
          ((v - artifact.scaler_mean[i]) / artifact.scaler_scale[i]) *
            artifact.coefficients[i],
        artifact.intercept,
      );
      if (!Number.isFinite(score))
        throw new Error("Non-finite experimental prediction");
      return {
        driver_id: driver.driver_id,
        name: driver.name,
        team: driver.team,
        qualifying_position:
          p.stage === "post_qualifying" ? driver.position : null,
        ranking_score: score,
      };
    })
    .sort(
      (a, b) =>
        a.ranking_score - b.ranking_score ||
        (a.qualifying_position || 0) - (b.qualifying_position || 0) ||
        (a.driver_id < b.driver_id ? -1 : a.driver_id > b.driver_id ? 1 : 0),
    );
  if (
    p.full_grid.length !== rows.length ||
    rows.some((r, i) => {
      const actual = p.full_grid[i];
      return (
        actual.rank !== i + 1 ||
        ["driver_id", "name", "team", "qualifying_position"].some(
          (k) => actual[k] !== r[k],
        ) ||
        Math.abs(actual.ranking_score - r.ranking_score) > 1e-12
      );
    }) ||
    JSON.stringify(p.top10) !== JSON.stringify(p.full_grid.slice(0, 10))
  )
    throw new Error("Experimental ranking differs from model inputs");
  const hash = digest({ event: p.event, inputs });
  const retrieved = p.sources.map((s) => timestamp(s.retrieved_at));
  if (
    hash !== p.input_hash ||
    digest([p.race_id, p.model_version, hash]) !== p.prediction_id ||
    !retrieved.length ||
    Math.max(...retrieved) > capture ||
    Math.max(...retrieved) !== timestamp(p.data_cutoff)
  )
    throw new Error("Experimental input hash or source cutoff mismatch");
  return p;
}

export { selectExperimental } from "../../lib/experimental-selection.js";
