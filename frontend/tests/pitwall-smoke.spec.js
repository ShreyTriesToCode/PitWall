import { expect, test } from "@playwright/test";

test("home dashboard loads with model/source context", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "PitWall" })).toBeVisible();
  await expect(page.getByText(/Race Intelligence Summary|No generated race briefing yet/)).toBeVisible();
  await expect(page.getByText(/Source Health|Prediction JSON unavailable|No generated race briefing yet/).first()).toBeVisible();
});

test("predictions expose top 10, full grid, and driver drawer", async ({ page }) => {
  await page.goto("/predictions");
  await expect(page.getByText("Top 10 Prediction")).toBeVisible();
  await expect(page.getByText("Full Grid Prediction")).toBeVisible();
  await expect(page.getByText(/AI-Style Race Summary|Deterministic race summary pending/)).toBeVisible();
  await expect(page.getByText(/High trust|Medium trust|Low trust|Trust pending/).first()).toBeVisible();
  const firstOpen = page.locator(".prediction-open-hitbox").first();
  if (await firstOpen.count()) {
    await firstOpen.click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByText("AI-style explanation")).toBeVisible();
    await expect(page.getByText("Why the model ranked this driver here")).toBeVisible();
    await expect(page.getByText("Missing and available signals")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
  }
});

test("live timing labels non-live data honestly", async ({ page }) => {
  await page.goto("/live");
  await expect(page.getByRole("heading", { name: /Timing|Replay|Live/i })).toBeVisible();
  await expect(page.getByText(/Live|Delayed|Stale|Archive|Unavailable/).first()).toBeVisible();
});

test("model and archive pages render clear states", async ({ page }) => {
  await page.goto("/model");
  await expect(page.getByText(/Model Version|Fallback model status|Model status sync failed/)).toBeVisible();
  await expect(page.getByText(/AI-Style Model Review|Deterministic model review pending/)).toBeVisible();
  await expect(page.getByText("Actual Result Comparison")).toBeVisible();
  await expect(page.getByRole("heading", { name: /Champion vs Challenger Model/ })).toBeVisible();
  await page.goto("/archive");
  await expect(page.getByText(/Race Archive|No archive matches/)).toBeVisible();
  await expect(page.getByText(/Latest actuals|Pending actual result|Top 10 Recall/).first()).toBeVisible();
});

test("predictions target links render rows or pending states", async ({ page }) => {
  await page.goto("/predictions?target=sprint");
  await expect(page.getByText(/Sprint|Race/).first()).toBeVisible();
  await expect(page.getByText(/Top 10 Prediction|Full Grid Prediction|sprint pending|prediction pending/i).first()).toBeVisible();
});

test("stale prediction target query falls back to current race", async ({ page }) => {
  await page.goto("/predictions?target=post_practice");
  await expect(page.getByText("Prediction ID").first()).toBeVisible();
  await expect(page.getByText(/barcelona-grand-prix/i).first()).toBeVisible();
  await expect(page.getByText(/canadian-grand-prix-race-post-practice/i)).toHaveCount(0);
});

test("sources page renders source-health state", async ({ page }) => {
  await page.goto("/sources");
  await expect(page.getByRole("heading", { name: "Data Source Health" })).toBeVisible();
  await expect(page.getByText(/Jolpica|FastF1|OpenF1|Source data unavailable|No source rows/).first()).toBeVisible();
});
