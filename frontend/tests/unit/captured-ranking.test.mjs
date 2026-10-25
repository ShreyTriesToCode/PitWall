import test from "node:test";
import assert from "node:assert/strict";
import { capturedRanking } from "../../app/lib/captured-ranking.js";

// Isolated fixture; never loaded by the production publisher.
const event = { id: "2030:1:race", start_at: "2030-03-10T14:00:00Z" };
const capture = {
  race_id: event.id,
  event,
  generated_at: "2030-03-10T12:00:00Z",
  data_cutoff: "2030-03-10T11:59:00Z",
};
const data = { current: { state: "UPDATING", event }, predictions: [capture] };
const now = Date.parse(event.start_at);

test("saved capture survives race start without becoming a current prediction", () => {
  assert.equal(capturedRanking(data, now), capture);
  assert.equal(capturedRanking(data, now - 1), null);
  assert.equal(
    capturedRanking({ ...data, current: { state: "UPCOMING", event } }, now),
    null,
  );
});
test("capture cannot belong to a different or rescheduled event", () => {
  for (const changed of [
    { ...event, id: "2030:2:race" },
    { ...event, start_at: "2030-03-10T13:00:00Z" },
    { ...event, start_at: null },
  ]) {
    assert.equal(
      capturedRanking(
        { ...data, current: { state: "UPDATING", event: changed } },
        now,
      ),
      null,
    );
  }
});
test("missing, post-start and invalid-cutoff captures stay unavailable", () => {
  for (const predictions of [
    [],
    [{ ...capture, generated_at: event.start_at }],
    [{ ...capture, data_cutoff: event.start_at }],
    [{ ...capture, generated_at: "2030-03-10T12:00:00" }],
  ]) {
    assert.equal(capturedRanking({ ...data, predictions }, now), null);
  }
});
test("latest eligible capture is selected without mutating history", () => {
  const newer = { ...capture, generated_at: "2030-03-10T13:00:00Z" };
  const predictions = [capture, newer];
  assert.equal(capturedRanking({ ...data, predictions }, now), newer);
  assert.deepEqual(predictions, [capture, newer]);
});
