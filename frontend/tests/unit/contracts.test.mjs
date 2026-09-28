import test from "node:test";
import assert from "node:assert/strict";
import {
  eventFromRace,
  raceRows,
  selectEvent,
  currentPrediction,
  timestamp,
  validateProduct,
  inputDigest,
} from "../../app/api/_lib/contracts.js";
import {
  sessionDate,
  messageTimestamp,
  trackStateLabel,
  parseTimingJson,
  expireLivePayload,
  packetTimestamp,
  freshness,
} from "../../app/api/_lib/timing.js";

// These invented events are isolated fixtures, never read by production.
const raw = {
  season: "2030",
  round: "1",
  raceName: "Fixture GP",
  Circuit: { circuitId: "fixture", circuitName: "Fixture circuit" },
  date: "2030-03-10",
  time: "14:00:00Z",
};
const event = eventFromRace(raw);
const now = timestamp("2030-03-10T12:00:00Z");
const grid = Array.from({ length: 12 }, (_, i) => ({
  driver_id: `fixture-${i}`,
  rank: i + 1,
  name: `Fixture driver ${i}`,
  team: "Fixture constructor",
  qualifying_position: i + 1,
  ranking_score: i + 1,
}));
const forecast = {
  prediction_id: "fixture-id",
  race_id: event.id,
  event,
  model_version: "qualifying-order-v1",
  feature_version: "qualifying-position-v1",
  input_hash: "filled below",
  inputs: {
    qualifying: grid.map((r) => ({
      driver_id: r.driver_id,
      name: r.name,
      team: r.team,
      position: r.rank,
    })),
  },
  sources: [{ url: "fixture", retrieved_at: "2030-03-10T11:00:00Z" }],
  generated_at: "2030-03-10T12:00:00Z",
  data_cutoff: "2030-03-10T11:00:00Z",
  full_grid: grid,
  top10: grid.slice(0, 10),
};

forecast.input_hash = inputDigest({
  event,
  qualifying: forecast.inputs.qualifying,
});
forecast.prediction_id = inputDigest([
  event.id,
  forecast.model_version,
  forecast.input_hash,
]);

test("past Italian-like event cannot be served as current", () => {
  const past = eventFromRace({ ...raw, round: "2", date: "2030-03-01" });
  assert.equal(selectEvent([past, event], now).event.id, event.id);
  assert.equal(
    currentPrediction(
      [{ ...forecast, event: past, race_id: past.id }],
      selectEvent([past, event], now),
      now,
    ),
    null,
  );
});
test("at start a forecast expires, even without another scheduled run", () => {
  const current = { state: "UPCOMING", event };
  assert.equal(currentPrediction([forecast], current, now), forecast);
  assert.equal(
    currentPrediction([forecast], current, timestamp(event.start_at)),
    null,
  );
  assert.equal(
    selectEvent([event], timestamp(event.start_at)).state,
    "UPDATING",
  );
});
test("postponed schedule invalidates previous captured target time", () => {
  assert.equal(
    currentPrediction(
      [forecast],
      {
        state: "UPCOMING",
        event: { ...event, start_at: "2030-03-11T14:00:00Z" },
      },
      now,
    ),
    null,
  );
});
test("unknown and timezone-naive timestamps are rejected", () => {
  assert.throws(() => timestamp("2030-03-10T14:00:00"));
  const unknown = eventFromRace({ ...raw, time: null });
  assert.equal(unknown.start_at, null);
  assert.equal(selectEvent([unknown], now).state, "UNAVAILABLE");
});
test("date offset changes do not change the selection boundary", () => {
  assert.equal(
    timestamp("2030-03-10T19:30:00+05:30"),
    timestamp(event.start_at),
  );
});
test("completed events and winter calendar transitions", () => {
  const next = eventFromRace({ ...raw, season: "2031", date: "2031-03-02" });
  assert.equal(selectEvent([event, next], now, [event.id]).event.id, next.id);
  assert.equal(selectEvent([], now).state, "UNAVAILABLE");
});
test("sprint sessions come from provider fields, never fabricated practice", () => {
  const sprint = eventFromRace({
    ...raw,
    Sprint: { date: "2030-03-09", time: "12:00:00Z" },
  });
  assert.deepEqual(
    sprint.sessions.map((s) => s.name),
    ["Sprint", "Race"],
  );
});
test("strict contract rejects old schemas, duplicates, top10 drift and leaked capture", () => {
  const product = {
    schema_version: 3,
    generated_at: "2030-03-10T12:00:00Z",
    predictions: [forecast],
    calendar: [event],
    evaluations: [],
  };
  assert.equal(validateProduct(product), product);
  assert.throws(() => validateProduct({ ...product, schema_version: 2 }));
  for (const changed of [
    { ...forecast, top10: [] },
    { ...forecast, generated_at: event.start_at },
    { ...forecast, full_grid: [grid[0], grid[0]] },
    { ...forecast, model_version: "legacy" },
  ])
    assert.throws(() =>
      validateProduct({ ...product, predictions: [changed] }),
    );
});
test("timing start applies the explicit local GMT offset", () => {
  assert.equal(
    sessionDate("2030-03-10T16:00:00", "02:00:00").toISOString(),
    "2030-03-10T14:00:00.000Z",
  );
  assert.equal(sessionDate("2030-03-10T16:00:00"), null);
});
test("retrieval time is never manufactured as packet freshness", () => {
  const result = freshness({ state: "active" }, true, "F1", null, now);
  assert.equal(result.is_genuinely_live, false);
  assert.equal(result.timing_last_updated_at, null);
  assert.equal(result.timing_freshness_seconds, null);
  assert.equal(
    packetTimestamp({
      feed: { entries: [{ time: "01:03:02.000", data: { Position: 1 } }] },
    }),
    null,
  );
});
test("live requires a recent, non-future source packet and active session", () => {
  const stamp = new Date(now - 2000).toISOString();
  assert.equal(
    freshness({ state: "active" }, true, "F1", stamp, now).is_genuinely_live,
    true,
  );
  assert.equal(
    freshness({ state: "archive" }, true, "F1", stamp, now).timing_mode,
    "archive",
  );
  assert.equal(
    freshness(
      { state: "active" },
      true,
      "F1",
      new Date(now - 61000).toISOString(),
      now,
    ).timing_mode,
    "stale",
  );
  assert.equal(
    freshness(
      { state: "active" },
      true,
      "F1",
      new Date(now + 1000).toISOString(),
      now,
    ).is_genuinely_live,
    false,
  );
  assert.equal(
    freshness({ state: "active" }, true, "F1", stamp, now, false)
      .is_genuinely_live,
    false,
  );
});
test("packet timestamp preserves actual UTC evidence from feed", () => {
  assert.equal(
    packetTimestamp({
      car: {
        entries: [{ data: { Entries: [{ Utc: "2030-03-10T11:59:58Z" }] } }],
      },
    }),
    "2030-03-10T11:59:58.000Z",
  );
});

test("incomplete provider pagination is rejected", () => {
  const meta = {
    offset: "0",
    limit: "100",
    total: "1",
    RaceTable: { Races: [raw] },
  };
  assert.equal(raceRows({ MRData: meta }, 2030).length, 1);
  for (const changed of [
    { limit: undefined },
    { total: "NaN" },
    { total: "101" },
    { offset: "1" },
  ])
    assert.throws(() => raceRows({ MRData: { ...meta, ...changed } }, 2030));
});
test("a disconnected screen expires live status from source packet time", () => {
  const payload = {
    is_genuinely_live: true,
    timing_mode: "live",
    source_packet_at: new Date(now).toISOString(),
  };
  assert.equal(expireLivePayload(payload, now + 60_000), payload);
  assert.equal(expireLivePayload(payload, now + 60_001).timing_mode, "stale");
  assert.equal(
    expireLivePayload({ ...payload, source_packet_at: null }, now)
      .is_genuinely_live,
    false,
  );
});

test("Formula 1 UTF-8 BOM JSON parses after a bounded byte read", () => {
  assert.deepEqual(parseTimingJson('\uFEFF{"Meetings":[]}'), { Meetings: [] });
  assert.equal(parseTimingJson("<html>Unavailable</html>"), null);
});

test("altered input identity, ranks and source cutoff are rejected", () => {
  const product = {
    schema_version: 3,
    generated_at: forecast.generated_at,
    predictions: [forecast],
    calendar: [event],
    evaluations: [],
  };
  for (const patch of [
    { input_hash: "tampered" },
    { prediction_id: "tampered" },
    { inputs: { qualifying: [] } },
    { data_cutoff: "2030-03-10T10:00:00Z" },
    { sources: [{ retrieved_at: "2030-03-11T12:00:00Z" }] },
  ])
    assert.throws(() =>
      validateProduct({ ...product, predictions: [{ ...forecast, ...patch }] }),
    );
  const changed = structuredClone(forecast);
  changed.full_grid[0].ranking_score = 99;
  changed.top10 = changed.full_grid.slice(0, 10);
  assert.throws(() => validateProduct({ ...product, predictions: [changed] }));
});

test("input hashing matches the Python publisher including Unicode", () => {
  assert.equal(
    inputDigest({
      event: { name: "São Paulo 🏁", round: 21 },
      qualifying: [{ position: 1, name: "Test" }],
    }),
    "7c56c5aadeb62ea971d7b1fd773d1742a7f7d48d36d90b5640706ae3da257e45",
  );
});
test("track flags preserve unknown states and distinguish VSC ending", () => {
  assert.equal(trackStateLabel("1"), "Track clear");
  assert.equal(trackStateLabel("7"), "Virtual safety car ending");
  assert.equal(trackStateLabel(""), "Status unavailable");
  assert.equal(trackStateLabel("99"), "Unknown status (99)");
});

test("race-control and radio UTC timestamps never inherit the server or browser timezone", () => {
  assert.equal(
    messageTimestamp({ Utc: "2026-09-13T14:47:48" }),
    "2026-09-13T14:47:48.000Z",
  );
  assert.equal(
    messageTimestamp({ Utc: "2026-09-13T16:47:48+02:00" }),
    "2026-09-13T14:47:48.000Z",
  );
  assert.equal(messageTimestamp({ Time: "01:47:48" }), null);
  assert.equal(messageTimestamp({ Date: "2026-09-13T14:47:48" }), null);
});
