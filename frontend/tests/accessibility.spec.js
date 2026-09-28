import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFile } from "node:fs/promises";

// Real published snapshot for reproducible UI checks; synthetic timing stays in this test.
const product = JSON.parse(
  await readFile(
    new URL("../../data_cache/product.json", import.meta.url),
    "utf8",
  ),
);
async function productRoutes(page) {
  await page.route("**/api/predictions", (r) =>
    r.fulfill({ json: { ...product, ok: true } }),
  );
}
async function accessible(page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(
    results.violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
}
async function overflow(page) {
  expect(
    await page.evaluate(
      (width) => document.documentElement.scrollWidth <= width,
      page.viewportSize().width,
    ),
  ).toBe(true);
}

for (const path of [
  "/",
  "/predictions",
  "/drivers",
  "/teams",
  "/model",
  "/sources",
  "/archive",
  "/strategy",
]) {
  test(`accessible rendered product ${path}`, async ({ page }) => {
    await productRoutes(page);
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByText("Loading race data…")).toHaveCount(0);
    await accessible(page);
    await overflow(page);
  });
}

test("driver no-match state and mobile keyboard menu", async ({ page }) => {
  await productRoutes(page);
  await page.goto("/drivers");
  await page.getByLabel("Find driver or team").fill("no-driver-matches-this");
  await expect(
    page.getByRole("heading", { name: "No matching drivers" }),
  ).toBeVisible();
  await expect(page.getByRole("table")).toHaveCount(0);
  const menu = page.getByRole("button", { name: "Menu", exact: true });
  if (await menu.isVisible()) {
    await menu.click();
    await expect(page.getByRole("navigation")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(menu).toBeFocused();
    await expect(page.getByRole("navigation")).toBeHidden();
  }
  await accessible(page);
});

const timing = {
  ok: true,
  source: "Formula1LiveTiming",
  timing_mode: "archive",
  session_state: "archive",
  is_genuinely_live: false,
  meeting_options: [],
  session_options: [],
  normalized: {
    session: {
      meeting_name: "Isolated test session",
      session_name: "Race",
      date_start: "2030-03-10T14:00:00Z",
    },
    drivers: [],
    raceControl: [
      {
        date: "2030-03-10T14:05:00Z",
        category: "Flag",
        message: "Isolated test message",
      },
    ],
    radio: [],
    weather: {
      wind_speed: 3,
      air_temperature: 20,
      track_temperature: 24,
      humidity: 40,
      rainfall: 0,
      wind_direction: 180,
    },
    leaderboard: Array.from({ length: 22 }, (_, i) => ({
      driver_number: i + 1,
      position: i === 0 ? null : i + 1,
      driver: {
        full_name: `Test driver ${i + 1}`,
        team_name: "Test constructor",
      },
      tyre_age: i === 0 ? null : i === 1 ? 0 : 3,
      compound: "HARD",
      speed: 0,
      n_gear: 0,
      brake: 0,
      rpm: i === 0 ? 9000 : null,
      mini_sectors: [{ sector: 1, segment: 1, status: "2048", tone: "green" }],
    })),
  },
};
test("timing preserves missing values, complete field and accessible settings", async ({
  page,
}) => {
  await page.route("**/api/f1timing/stream?**", (r) => r.abort());
  await page.route("**/api/f1timing?**", (r) => r.fulfill({ json: timing }));
  await page.goto("/live");
  await expect(
    page.getByRole("heading", { name: "Isolated test session" }),
  ).toBeVisible();
  const expand = page.getByRole("button", {
    name: "All timing details",
    exact: true,
  });
  if (await expand.isVisible()) await expand.click();
  const board = page.getByRole("table", { name: "Session leaderboard" });
  await expect(board.getByRole("row")).toHaveCount(23);
  await expect(
    board.getByRole("row").nth(1).getByRole("cell").first(),
  ).toHaveText("-");
  await expect(board.getByText("Age unavailable")).toHaveCount(1);
  await expect(board.getByText("0 laps", { exact: true })).toHaveCount(1);
  await expect(page.locator("#tyres .compact-stack > div")).toHaveCount(22);
  await expect(page.locator("#sectors .sector-list > div")).toHaveCount(22);
  await expect(page.getByText("3 m/s", { exact: true })).toBeVisible();
  await expect(page.locator("#race-control time")).toHaveText(
    "07:35:00 PM IST",
  );
  await expect(page.getByText("Aero / Boost")).toHaveCount(0);
  await expect(
    page.getByRole("table", { name: "Available car metrics" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByLabel("Speed", { exact: true }).selectOption("mph");
  await expect(board.getByRole("row").nth(1)).toContainText("0 mph");
  await accessible(page);
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Settings", exact: true }),
  ).toBeFocused();
  await expect(page.getByLabel("Speed", { exact: true })).toHaveCount(0);
  await page.getByText("Choose a session", { exact: false }).click();
  await accessible(page);
  await overflow(page);
});

test("reduced motion and 320px layout stay usable", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 320, height: 700 });
  await productRoutes(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText("Loading race data…")).toHaveCount(0);
  expect(
    await page
      .locator(".product-header")
      .evaluate((el) => getComputedStyle(el).animationName),
  ).toBe("none");
  await overflow(page);
  await accessible(page);
});

test("keyboard entry and bounded motion", async ({ page, browserName }) => {
  await productRoutes(page);
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/drivers");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  // Safari uses Option-Tab for links unless full keyboard navigation is enabled.
  await page.keyboard.press(browserName === "webkit" ? "Alt+Tab" : "Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("main")).toBeFocused();
  const motion = await page.locator(".product-header").evaluate(async (el) => {
    const animations = el.getAnimations();
    const durations = animations.map((a) => a.effect.getTiming().duration);
    await Promise.all(animations.map((a) => a.finished));
    return {
      durations,
      stationary: new DOMMatrixReadOnly(getComputedStyle(el).transform)
        .isIdentity,
    };
  });
  expect(motion.durations.every((ms) => ms <= 300)).toBe(true);
  expect(motion.stationary).toBe(true);
  await expect(
    page.getByRole("button", { name: "Refresh data", exact: true }),
  ).toHaveCSS("min-height", "44px");
});

test.afterEach(async ({ page }) => {
  if (process.env.PITWALL_CAPTURE_REVIEW === "1") {
    await page.screenshot({
      path: test.info().outputPath("review.png"),
      fullPage: false,
    });
  }
});

test("racing theme keeps decoration separate from data and motion finite", async ({
  page,
}) => {
  await productRoutes(page);
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: product.current.event.name,
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.locator(".round-plate")).toHaveAttribute(
    "aria-hidden",
    "true",
  );
  await expect(page.locator(".round-plate-number")).toHaveText(
    `R${String(product.current.event.round).padStart(2, "0")}`,
  );
  await expect(page.locator(".event-art")).toHaveAttribute(
    "aria-hidden",
    "true",
  );
  await expect
    .poll(() =>
      page.locator(".event-art img").evaluate((el) => el.naturalWidth),
    )
    .toBeGreaterThan(0);
  const stripe = await page.locator(".event-focus").evaluate((el) => {
    const style = getComputedStyle(el, "::before");
    return {
      duration: style.animationDuration,
      iterations: style.animationIterationCount,
    };
  });
  expect(stripe.duration).toBe("0.28s");
  expect(stripe.iterations).toBe("1");
  await page.emulateMedia({ reducedMotion: "reduce" });
  expect(
    await page
      .locator(".event-focus")
      .evaluate((el) => getComputedStyle(el, "::before").animationName),
  ).toBe("none");
  await overflow(page);
});

test("strategy compares observed tyres and preserves missing ages", async ({
  page,
}) => {
  await page.route("**/api/f1timing**", (r) => r.fulfill({ json: timing }));
  await page.goto("/strategy");
  await expect(
    page.getByRole("heading", { name: "Strategy desk", exact: true }),
  ).toBeVisible();
  const table = page.getByRole("table", { name: "Observed tyre comparison" });
  await expect(table.getByRole("row")).toHaveCount(23);
  await expect(
    table
      .getByRole("row")
      .filter({
        has: page.getByRole("rowheader", {
          name: "Test driver 1",
          exact: true,
        }),
      })
      .getByRole("cell")
      .nth(1),
  ).toHaveText("Unavailable");
  await page.getByLabel("Order", { exact: true }).selectOption("age");
  await page.getByLabel("Compound", { exact: true }).selectOption("HARD");
  await expect(table.getByRole("row")).toHaveCount(23);
  await accessible(page);
  await overflow(page);
});

test("compact phone timing exposes full detail on demand", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/f1timing**", (r) => r.fulfill({ json: timing }));
  await page.goto("/live");
  const table = page.getByRole("table", { name: "Session leaderboard" });
  await expect(table).toBeVisible();
  await expect(
    table.getByRole("columnheader", { name: "Last lap" }),
  ).toBeHidden();
  await expect(page.locator("#tyres")).toBeHidden();
  expect(
    await table.evaluate((el) => el.getBoundingClientRect().width),
  ).toBeLessThan(355);
  await page
    .getByRole("button", { name: "All timing details", exact: true })
    .click();
  await expect(
    table.getByRole("columnheader", { name: "Last lap" }),
  ).toBeVisible();
  await expect(page.locator("#tyres")).toBeVisible();
  await overflow(page);
});
