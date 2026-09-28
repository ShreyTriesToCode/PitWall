import test from "node:test";
import assert from "node:assert/strict";
import { sessionStatus } from "../../app/lib/session-status.js";
import { formatISTTime } from "../../app/lib/time.js";
const s = { name: "Race", start_at: "2030-03-10T14:00:00Z" };
const e = { id: "2030:1:race" };
const now = Date.parse("2030-03-10T14:05:00Z");
const timing = {
  ok: true,
  is_genuinely_live: true,
  source_packet_at: "2030-03-10T14:04:45Z",
  normalized: { session: { session_name: "Race", date_start: s.start_at } },
};
test("ongoing green requires matching session and recent packet", () => {
  assert.equal(sessionStatus(s, e, {}, timing, now).tone, "green");
  assert.equal(sessionStatus(s, e, {}, timing, now + 60_000).tone, "neutral");
  assert.equal(
    sessionStatus(
      s,
      e,
      {},
      { ...timing, source_packet_at: "2030-03-10T14:06:00Z" },
      now,
    ).tone,
    "neutral",
  );
  assert.equal(
    sessionStatus({ ...s, name: "Sprint" }, e, {}, timing, now).tone,
    "neutral",
  );
});
test("elapsed clock is neutral; upcoming amber; evidence of completion red", () => {
  assert.equal(sessionStatus(s, e, {}, null, now).label, "Status unconfirmed");
  assert.equal(sessionStatus(s, e, {}, null, now - 600_000).tone, "amber");
  assert.equal(
    sessionStatus(s, e, { latest_result: { event: e } }, null, now).tone,
    "red",
  );
  assert.equal(
    sessionStatus(
      s,
      e,
      { latest_result: { event: { id: "another" } } },
      null,
      now,
    ).tone,
    "neutral",
  );
  assert.equal(
    sessionStatus(
      s,
      e,
      {},
      {
        ...timing,
        is_genuinely_live: false,
        timing_mode: "archive",
        completion_verified: true,
      },
      now,
    ).tone,
    "red",
  );
  assert.equal(
    sessionStatus({ ...s, start_at: null }, e, {}, null, now).label,
    "Time unavailable",
  );
});
test("noon is PM and midnight is AM in IST", () => {
  assert.equal(formatISTTime("2030-03-10T06:30:00Z"), "12:00:00 PM IST");
  assert.equal(formatISTTime("2030-03-10T18:30:00Z"), "12:00:00 AM IST");
});

test("sparse stint and sector updates preserve indices and earlier fields", async () => {
  const { mergeTimingLine } = await import("../../app/api/_lib/timing.js");
  const before = {
    Stints: [
      { Compound: "SOFT", TotalLaps: 3 },
      { Compound: "HARD", TotalLaps: 0 },
    ],
    Sectors: [{ Value: "1", Segments: [{ Status: 1 }, { Status: 2 }] }],
  };
  const merged = mergeTimingLine(before, {
    Stints: { 1: { TotalLaps: 4 } },
    Sectors: { 0: { Segments: { 1: { Status: 3 } } } },
  });
  assert.equal(merged.Stints[1].Compound, "HARD");
  assert.equal(merged.Stints[1].TotalLaps, 4);
  assert.equal(merged.Stints[0].TotalLaps, 3);
  assert.equal(merged.Sectors[0].Segments[0].Status, 1);
  assert.equal(merged.Sectors[0].Segments[1].Status, 3);
  assert.equal(before.Stints[1].TotalLaps, 0);
});

test("segment finishes and red-flag interruptions never imply whole-session completion", async () => {
  const { applySessionStatus } = await import("../../app/api/_lib/timing.js");
  const active = { state: "active", is_live: true };
  for (const status of [null, "Finished", "Aborted", "Inactive"]) {
    assert.equal(applySessionStatus(active, status).is_live, false);
    assert.equal(applySessionStatus(active, status).completion_verified, false);
  }
  for (const status of ["Finalised", "Ends"]) {
    assert.equal(applySessionStatus(active, status).state, "archive");
    assert.equal(applySessionStatus(active, status).completion_verified, true);
  }
  assert.equal(applySessionStatus(active, "Started").state, "active");
});
