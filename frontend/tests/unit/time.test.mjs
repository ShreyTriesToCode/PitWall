import test from "node:test";
import assert from "node:assert/strict";
import { formatISTDateTime, formatISTTime } from "../../app/lib/time.js";

test("IST displays the half-hour offset for race schedules and feed messages", () => {
  assert.equal(
    formatISTDateTime("2030-03-10T14:00:00Z"),
    "10 Mar 2030, 07:30 PM IST",
  );
  assert.equal(formatISTTime("2030-03-10T14:05:00Z"), "07:35:00 PM IST");
});
test("IST date rolls into the next day and year", () => {
  assert.equal(
    formatISTDateTime("2030-12-31T18:45:00Z"),
    "01 Jan 2031, 12:15 AM IST",
  );
  assert.equal(formatISTTime("2030-12-31T18:30:00Z"), "12:00:00 AM IST");
});
test("explicit source offsets describe the same instant without double conversion", () => {
  assert.equal(
    formatISTDateTime("2030-03-10T19:30:00+05:30"),
    formatISTDateTime("2030-03-10T14:00:00Z"),
  );
  assert.equal(formatISTTime("2030-03-10T10:00:00-04:00"), "07:30:00 PM IST");
});
test("missing, invalid and timezone-naive dates remain unavailable", () => {
  for (const value of [
    null,
    undefined,
    "",
    "invalidZ",
    "2030-03-10",
    "2030-03-10T14:00:00",
    0,
  ]) {
    assert.equal(formatISTDateTime(value), "Time unavailable");
    assert.equal(formatISTTime(value), "Time unavailable");
  }
});
