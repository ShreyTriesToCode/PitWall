import { expect, test } from "@playwright/test";

// Synthetic UI fixtures. Production code never imports this file.
const start = "2030-03-10T14:00:00Z";
const event = {
  id: "2030:1:race",
  season: 2030,
  round: 1,
  name: "Fixture Grand Prix",
  circuit: "Fixture circuit",
  date: "2030-03-10",
  start_at: start,
  sessions: [
    { name: "Qualifying", start_at: "2030-03-09T14:00:00Z" },
    { name: "Race", start_at: start },
  ],
};
const grid = Array.from({ length: 12 }, (_, i) => ({
  driver_id: `fixture_${i + 1}`,
  name: `Fixture driver ${i + 1}`,
  team: `Fixture team ${Math.floor(i / 2) + 1}`,
  rank: i + 1,
  qualifying_position: i + 1,
}));
const prediction = {
  prediction_id: "fixture",
  race_id: event.id,
  event,
  model_version: "qualifying-order-v1",
  feature_version: "qualifying-position-v1",
  generated_at: "2030-03-10T12:00:00Z",
  data_cutoff: "2030-03-10T11:59:00Z",
  input_hash: "fixture",
  full_grid: grid,
  top10: grid.slice(0, 10),
};
const product = {
  ok: true,
  schema_version: 3,
  generated_at: "2030-03-10T12:00:00Z",
  current: { state: "UPCOMING", event },
  prediction,
  predictions: [prediction],
  evaluations: [],
  legacy_archive: [],
  calendar: [event],
  sources: [],
  warnings: [],
  latest_result: null,
  model: {
    version: "qualifying-order-v1",
    feature_version: "qualifying-position-v1",
  },
  backtest: { status: "UNAVAILABLE" },
};
async function fixture(page, data = product) {
  await page.route("**/api/predictions", (r) => r.fulfill({ json: data }));
}
async function reviewScreenshot(page, name) {
  if (process.env.PITWALL_CAPTURE_REVIEW === "1") {
    await page.screenshot({
      path: test.info().outputPath(`${name}.png`),
      fullPage: false,
    });
  }
}
test.afterEach(async ({ page }) => {
  await reviewScreenshot(page, "final-state");
});

async function noOverflow(page) {
  expect(
    await page.evaluate(
      (width) => document.documentElement.scrollWidth <= width,
      page.viewportSize().width,
    ),
  ).toBe(true);
}

test("ranking controls derive top 10 and full field and expose provenance", async ({
  page,
}) => {
  await fixture(page);
  await page.goto("/predictions");
  await expect(
    page.getByRole("heading", { name: "Fixture Grand Prix" }),
  ).toBeVisible();
  await expect(page.locator(".event-date")).toHaveText(
    "10 Mar 2030, 07:30 PM IST",
  );
  const rows = page.getByRole("table").getByRole("row");
  await expect(rows).toHaveCount(11);
  await page.getByRole("button", { name: "Show full grid" }).click();
  await expect(rows).toHaveCount(13);
  await page
    .getByLabel("Find driver", { exact: true })
    .fill("Fixture driver 12");
  await expect(rows).toHaveCount(2);
  await page.getByText("Prediction provenance", { exact: true }).click();
  await expect(page.getByText("Data cutoff", { exact: true })).toBeVisible();
  await noOverflow(page);
});

test("forecast disappears at race start without a publisher run", async ({
  page,
}) => {
  await page.clock.install({ time: new Date("2030-03-10T13:59:59Z") });
  await fixture(page);
  await page.goto("/predictions");
  await expect(
    page.getByRole("heading", { name: "Predicted classification" }),
  ).toBeVisible();
  await page.clock.fastForward(2000);
  await expect(
    page.getByRole("heading", { name: "Prediction unavailable" }),
  ).toBeVisible();
  await expect(page.getByText("UPDATING", { exact: true })).toBeVisible();
});

test("provider failure is visible and retry restores data", async ({
  page,
}) => {
  let failed = true;
  await page.route("**/api/predictions", (r) =>
    failed
      ? r.fulfill({ status: 503, json: { ok: false } })
      : r.fulfill({ json: product }),
  );
  await page.goto("/predictions");
  await expect(
    page.getByRole("alert").filter({ hasText: "Data request failed" }),
  ).toContainText("Data request failed");
  await expect(page.getByRole("table")).toHaveCount(0);
  await reviewScreenshot(page, "api-failure");
  failed = false;
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByRole("table")).toBeVisible();
});

test("loading and unavailable states have meaningful copy", async ({
  page,
}) => {
  let release;
  const gate = new Promise((resolve) => (release = resolve));
  await page.route("**/api/predictions", async (r) => {
    await gate;
    await r.fulfill({
      json: {
        ...product,
        prediction: null,
        predictions: [],
        current: { state: "UNAVAILABLE", event: null },
        calendar: [],
      },
    });
  });
  await page.goto("/predictions");
  await expect(
    page.getByText("Loading race data…", { exact: true }),
  ).toBeVisible();
  await reviewScreenshot(page, "loading");
  release();
  await expect(
    page.getByRole("heading", { name: "Race schedule unavailable" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Prediction unavailable" }),
  ).toBeVisible();
  await noOverflow(page);
});

test("historical results remain separate from forecasts", async ({ page }) => {
  const result = {
    event: { ...event, name: "Historical fixture GP" },
    rows: grid.map((r) => ({
      ...r,
      position: r.rank,
      status: r.rank === 12 ? "Disqualified" : "Finished",
      points: "0",
    })),
    source: { retrieved_at: "2030-03-11T12:00:00Z" },
  };
  await fixture(page, { ...product, prediction: null, latest_result: result });
  await page.goto("/archive");
  await expect(page.getByText("COMPLETED", { exact: true })).toBeVisible();
  await expect(page.getByText("Disqualified", { exact: true })).toBeVisible();
  await noOverflow(page);
});

test("primary routes and navigation work without layout overflow", async ({
  page,
  isMobile,
}) => {
  await fixture(page, { ...product, prediction: null, predictions: [] });
  const failures = [];
  page.on("pageerror", (e) => failures.push(e.message));
  for (const [path, title] of [
    ["/drivers", "Drivers"],
    ["/teams", "Constructors"],
    ["/strategy", "Strategy desk"],
    ["/model", "Methodology & evaluation"],
    ["/sources", "Data sources"],
  ]) {
    await page.goto(path);
    await expect(
      page.getByRole("heading", { name: title, exact: true, level: 1 }),
    ).toBeVisible();
    await noOverflow(page);
  }
  if (isMobile) {
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    await expect(
      page.getByRole("link", { name: "Race ranking", exact: true }),
    ).toBeVisible();
  }
  expect(failures).toEqual([]);
});

test("timing distinguishes historical, live and unavailable fixtures", async ({
  page,
}) => {
  await page.route("**/api/f1timing/stream?**", (r) => r.abort());
  let state = "archive";
  const timing = () => ({
    ok: state !== "unavailable",
    source: "Fixture timing",
    timing_mode: state,
    is_genuinely_live: state === "live",
    session_state: state,
    meeting_options: [],
    session_options: [],
    normalized: {
      session: {
        meeting_name: "Timing fixture GP",
        session_name: "Race",
        date_start: start,
      },
      drivers: [],
      leaderboard: [],
      raceControl: [],
      radio: [],
    },
    warnings: [],
    server_fetched_at: "2030-03-10T14:01:00Z",
    source_packet_at: state === "live" ? new Date().toISOString() : null,
  });
  await page.route("**/api/f1timing?**", (r) => r.fulfill({ json: timing() }));
  await page.goto("/live");
  await expect(
    page.getByRole("heading", { name: "Timing fixture GP", level: 1 }),
  ).toBeVisible();
  await expect(
    page.getByText("Historical session timing", { exact: true }).first(),
  ).toBeVisible();
  await noOverflow(page);
  state = "live";
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(
    page.getByText("Live timing", { exact: true }).first(),
  ).toBeVisible();
  await reviewScreenshot(page, "live-fixture");
  state = "unavailable";
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(
    page.getByText("unavailable", { exact: true }).first(),
  ).toBeVisible();
});

test("real API excludes legacy probabilities from production", async ({
  request,
}) => {
  const response = await request.get("/api/predictions");
  expect(response.ok()).toBe(true);
  const data = await response.json();
  expect(data.schema_version).toBe(3);
  expect(data.latest).toBe(null);
  if (data.current.event)
    expect(Date.parse(data.current.event.start_at)).toBeGreaterThan(
      Date.now() - 8 * 3600_000,
    );
  expect(
    data.legacy_archive.every((p) => p.status === "UNVERIFIED_LEGACY"),
  ).toBe(true);
  expect(
    (
      await request.get(
        "/api/local-data?path=data_cache/latest-model-debug.json",
      )
    ).status(),
  ).toBe(410);
  expect(
    (await request.get("/api/audio?url=https://example.com/test.mp3")).status(),
  ).toBe(400);
  expect((await request.get("/api/f1timing?year=invalid")).status()).toBe(400);
});

test("sprint request cannot display a grand prix forecast", async ({
  page,
}) => {
  await fixture(page);
  await page.goto("/predictions?target=sprint");
  await expect(
    page.getByRole("heading", { name: "Sprint prediction unavailable" }),
  ).toBeVisible();
  await expect(page.getByRole("table")).toHaveCount(0);
});
