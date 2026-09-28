import { readFile } from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";

const ROOT =
  process.env.PITWALL_PROJECT_ROOT ||
  path.resolve(/*turbopackIgnore: true*/ process.cwd(), "..");
const BASE = "https://api.jolpi.ca/ergast/f1";
const TTL = 5 * 60_000;
const cache = new Map();

export function timestamp(value) {
  if (typeof value !== "string" || !/(Z|[+-]\d{2}:\d{2})$/.test(value))
    throw new Error("Timestamp needs a timezone");
  const time = Date.parse(value);
  if (!Number.isFinite(time)) throw new Error("Invalid timestamp");
  return time;
}

export function eventFromRace(raw) {
  const season = Number(raw.season),
    round = Number(raw.round);
  if (
    !Number.isInteger(season) ||
    season < 1950 ||
    !Number.isInteger(round) ||
    round < 1 ||
    !raw.raceName ||
    !raw.Circuit?.circuitId
  )
    throw new Error("Invalid calendar schema");
  const start = raw.time
    ? new Date(timestamp(`${raw.date}T${raw.time}`)).toISOString()
    : null;
  const sessions = Object.entries({
    FirstPractice: "Practice 1",
    SecondPractice: "Practice 2",
    ThirdPractice: "Practice 3",
    SprintQualifying: "Sprint qualifying",
    SprintShootout: "Sprint qualifying",
    Sprint: "Sprint",
    Qualifying: "Qualifying",
  })
    .filter(([key]) => raw[key])
    .map(([key, name]) => ({
      name,
      date: raw[key].date,
      start_at: raw[key].time
        ? new Date(timestamp(`${raw[key].date}T${raw[key].time}`)).toISOString()
        : null,
    }));
  return {
    id: `${season}:${round}:race`,
    season,
    round,
    name: raw.raceName,
    circuit: raw.Circuit.circuitName,
    location: raw.Circuit.Location?.locality,
    date: raw.date,
    start_at: start,
    sessions: [...sessions, { name: "Race", date: raw.date, start_at: start }],
    source_url: `${BASE}/${season}/${round}/races/`,
  };
}

export function selectEvent(events, now = Date.now(), completed = []) {
  if (
    events.some(
      (e) => !e.start_at && e.date >= new Date(now).toISOString().slice(0, 10),
    )
  )
    return {
      state: "UNAVAILABLE",
      event: null,
      reason: "A future calendar event has no confirmed start time.",
    };
  for (const event of [...events]
    .filter((e) => e.start_at)
    .sort((a, b) => timestamp(a.start_at) - timestamp(b.start_at))) {
    if (completed.includes(event.id)) continue;
    const start = timestamp(event.start_at);
    if (start > now) return { state: "UPCOMING", event, reason: null };
    if (now - start < 8 * 3600_000)
      return {
        state: "UPDATING",
        event,
        reason:
          "Scheduled start has passed. Check timing for verified session activity.",
      };
  }
  return {
    state: "UNAVAILABLE",
    event: null,
    reason: "No upcoming race with a confirmed start time is available.",
  };
}

export function raceRows(payload, season) {
  const meta = payload?.MRData,
    rows = meta?.RaceTable?.Races;
  if (
    !Array.isArray(rows) ||
    ![meta?.offset, meta?.total, meta?.limit].every((v) =>
      /^\d+$/.test(String(v)),
    ) ||
    Number(meta.limit) < 1 ||
    Number(meta.offset) !== 0 ||
    Number(meta.total) > Number(meta.limit)
  )
    throw new Error("Invalid or incomplete provider response");
  const events = rows.map(eventFromRace);
  if (
    events.some((e) => e.season !== season) ||
    new Set(events.map((e) => e.id)).size !== events.length
  )
    throw new Error("Incorrect season or duplicate race");
  return rows;
}

async function provider(endpoint) {
  const previous = cache.get(endpoint);
  if (previous && previous.expires > Date.now()) return previous.promise;
  const promise = (async () => {
    const url = `${BASE}/${endpoint}/?limit=100`;
    const response = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    if (!response.ok) throw new Error(`Provider HTTP ${response.status}`);
    const body = await response.text();
    if (body.length > 2_000_000) throw new Error("Provider response too large");
    return {
      data: JSON.parse(body),
      source: {
        url,
        retrieved_at: new Date().toISOString(),
        status: "AVAILABLE",
      },
    };
  })();
  cache.set(endpoint, { promise, expires: Date.now() + TTL });
  try {
    return await promise;
  } catch (error) {
    cache.delete(endpoint);
    throw error;
  }
}

// Matches Python's sorted, ASCII JSON encoding for the contract's integer/string inputs.
export function inputDigest(value) {
  function canonical(item) {
    if (item === null || typeof item !== "object") return item;
    if (Array.isArray(item)) return item.map(canonical);
    return Object.fromEntries(
      Object.keys(item)
        .sort()
        .map((key) => [key, canonical(item[key])]),
    );
  }
  const text = JSON.stringify(canonical(value)).replace(
    /[\u0080-\uffff]/g,
    (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, "0")}`,
  );
  return createHash("sha256").update(text).digest("hex");
}

export function validateProduct(data) {
  if (
    data?.schema_version !== 3 ||
    !Array.isArray(data.predictions) ||
    !Array.isArray(data.calendar) ||
    !Array.isArray(data.evaluations)
  )
    throw new Error("Unsupported product contract");
  timestamp(data.generated_at);
  if (
    new Set(data.predictions.map((p) => p.prediction_id)).size !==
    data.predictions.length
  )
    throw new Error("Duplicate prediction IDs");
  for (const prediction of data.predictions) {
    if (
      !prediction.prediction_id ||
      !prediction.model_version ||
      !prediction.feature_version ||
      !prediction.input_hash ||
      !prediction.sources?.length
    )
      throw new Error("Prediction provenance missing");
    if (
      !(
        timestamp(prediction.data_cutoff) <=
          timestamp(prediction.generated_at) &&
        timestamp(prediction.generated_at) <
          timestamp(prediction.event.start_at)
      )
    )
      throw new Error("Invalid forecast chronology");
    const grid = prediction.full_grid;
    if (
      !Array.isArray(grid) ||
      grid.length < 2 ||
      new Set(grid.map((r) => r.driver_id)).size !== grid.length ||
      grid.some((r, i) => r.rank !== i + 1)
    )
      throw new Error("Invalid prediction field");
    if (
      prediction.race_id !== prediction.event.id ||
      prediction.model_version !== "qualifying-order-v1"
    )
      throw new Error("Unsupported prediction identity/model");
    if (JSON.stringify(prediction.top10) !== JSON.stringify(grid.slice(0, 10)))
      throw new Error("Top 10 differs from full grid");
    const qualifying = prediction.inputs?.qualifying;
    if (
      !Array.isArray(qualifying) ||
      qualifying.length !== grid.length ||
      prediction.feature_version !== "qualifying-position-v1"
    )
      throw new Error("Prediction input field missing or unsupported");
    const hash = inputDigest({ event: prediction.event, qualifying });
    if (
      hash !== prediction.input_hash ||
      inputDigest([prediction.race_id, prediction.model_version, hash]) !==
        prediction.prediction_id
    )
      throw new Error("Prediction input identity mismatch");
    const ordered = [...qualifying].sort((a, b) => a.position - b.position);
    if (
      ordered.some(
        (q, i) =>
          !q.driver_id ||
          q.position !== i + 1 ||
          grid[i].driver_id !== q.driver_id ||
          grid[i].name !== q.name ||
          grid[i].team !== q.team ||
          grid[i].qualifying_position !== q.position ||
          grid[i].ranking_score !== q.position,
      )
    )
      throw new Error("Ranking differs from published model inputs");
    const capture = timestamp(prediction.generated_at);
    const retrieved = prediction.sources.map((source) =>
      timestamp(source.retrieved_at),
    );
    if (
      retrieved.some((t) => t > capture) ||
      Math.max(...retrieved) !== timestamp(prediction.data_cutoff)
    )
      throw new Error("Source cutoff differs from prediction provenance");
  }
  return data;
}

async function readProduct() {
  try {
    let body;
    try {
      body = await readFile(
        /*turbopackIgnore: true*/ path.join(ROOT, "data_cache/product.json"),
        "utf8",
      );
    } catch (error) {
      if (error.code !== "ENOENT" || !process.env.PITWALL_DATA_BASE_URL)
        throw error;
      const base = new URL(process.env.PITWALL_DATA_BASE_URL);
      if (base.protocol !== "https:")
        throw new Error("Data base must use HTTPS", { cause: error });
      const response = await fetch(
        new URL("data_cache/product.json", base.href.replace(/\/?$/, "/")),
        { cache: "no-store", signal: AbortSignal.timeout(8_000) },
      );
      if (!response.ok)
        throw new Error(`Contract HTTP ${response.status}`, { cause: error });
      body = await response.text();
    }
    if (body.length > 5_000_000)
      throw new Error("Product contract exceeds size limit");
    return validateProduct(JSON.parse(body));
  } catch (error) {
    console.error("PitWall product contract unavailable:", error.message);
    return {
      schema_version: 3,
      generated_at: null,
      calendar: [],
      predictions: [],
      evaluations: [],
      legacy_archive: [],
      sources: [],
      warnings: ["Published rankings and evaluation data are unavailable."],
    };
  }
}

export function currentPrediction(records, current, now = Date.now()) {
  if (current.state !== "UPCOMING" || !current.event) return null;
  return (
    [...records]
      .filter(
        (p) =>
          p.race_id === current.event.id &&
          timestamp(p.event.start_at) === timestamp(current.event.start_at) &&
          timestamp(p.generated_at) <= now &&
          now < timestamp(p.event.start_at),
      )
      .sort(
        (a, b) => timestamp(b.generated_at) - timestamp(a.generated_at),
      )[0] || null
  );
}

export async function loadPredictionsPayload() {
  const product = await readProduct();
  const now = Date.now(),
    season = new Date(now).getUTCFullYear();
  let calendar = [],
    current = {
      state: "UNAVAILABLE",
      event: null,
      reason: "Current calendar could not be verified.",
    };
  const warnings = [...(product.warnings || [])],
    sources = [];
  let latestResult = product.latest_result || null;
  const [calendarResponse, resultResponse] = await Promise.allSettled([
    provider(`${season}/races`),
    provider(`${season}/last/results`),
  ]);
  try {
    if (calendarResponse.status === "rejected") throw calendarResponse.reason;
    const response = calendarResponse.value;
    calendar = raceRows(response.data, season).map(eventFromRace);
    if (!calendar.length) throw new Error("Empty season calendar");
    sources.push(response.source);
    current = selectEvent(calendar, now);
    if (
      !current.event &&
      calendar.every((e) => e.start_at && timestamp(e.start_at) < now)
    ) {
      const following = await provider(`${season + 1}/races`);
      calendar.push(...raceRows(following.data, season + 1).map(eventFromRace));
      sources.push(following.source);
      current = selectEvent(calendar, now);
    }
  } catch (error) {
    console.warn("PitWall calendar unavailable:", error.message);
    warnings.push(
      "Calendar provider unavailable. Previously published events are not treated as current.",
    );
    // A stale calendar may be inspected in history but may never select a current race.
  }
  try {
    if (resultResponse.status === "rejected") throw resultResponse.reason;
    const response = resultResponse.value;
    const raw = raceRows(response.data, season)[0];
    if (raw) {
      const event = eventFromRace(raw),
        result = raw.Results;
      if (
        !Array.isArray(result) ||
        result.length < 2 ||
        new Set(result.map((r) => r.Driver?.driverId)).size !== result.length ||
        result.some(
          (r, i) =>
            Number(r.position) !== i + 1 ||
            !r.Driver?.driverId ||
            !r.Constructor?.name,
        )
      )
        throw new Error("Invalid result classification");
      if (!event.start_at || timestamp(event.start_at) >= now)
        throw new Error("Result has a future/unknown start");
      latestResult = {
        event,
        rows: result.map((r) => ({
          driver_id: r.Driver.driverId,
          name: `${r.Driver.givenName} ${r.Driver.familyName}`,
          team: r.Constructor.name,
          position: Number(r.position),
          points: r.points,
          status: r.status,
        })),
        source: response.source,
      };
      if (calendar.length) current = selectEvent(calendar, now, [event.id]);
      sources.push(response.source);
    }
  } catch (error) {
    console.warn("PitWall results unavailable:", error.message);
    warnings.push(
      "Latest results could not be refreshed; any saved result below is explicitly historical.",
    );
  }
  const prediction = currentPrediction(product.predictions, current, now);
  return {
    ...product,
    ok: true,
    served_at: new Date(now).toISOString(),
    current_data_retrieved_at:
      sources
        .map((s) => s.retrieved_at)
        .filter(Boolean)
        .sort()
        .at(-1) || null,
    current,
    calendar,
    prediction,
    latest_result: latestResult,
    sources: [...sources, ...(product.sources || [])].map((s) => ({
      ...s,
      status:
        s.retrieved_at && now - Date.parse(s.retrieved_at) > TTL
          ? "STALE"
          : s.status,
    })),
    warnings: [...new Set(warnings)],
    latest: null,
  };
}

export const loadFrontendContract = loadPredictionsPayload;
export async function loadGeneratedTargets() {
  return [];
}
export async function loadModelStatus() {
  const p = await readProduct();
  return {
    ok: !!p.model,
    model: p.model,
    backtest: p.backtest,
    evaluations: p.evaluations,
  };
}
export async function loadBacktest() {
  const p = await readProduct();
  return p.backtest || { status: "UNAVAILABLE" };
}
export async function loadArchive() {
  const p = await readProduct();
  return {
    ok: true,
    predictions: p.predictions,
    evaluations: p.evaluations,
    legacy_archive: p.legacy_archive,
  };
}
export function jsonResponse(payload) {
  return Response.json(payload, {
    headers: {
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
