import { expect, test } from "@playwright/test";

test("home dashboard loads with model/source context", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "PitWall" })).toBeVisible();
  await expect(page.getByText(/Source Health|Prediction JSON unavailable|No generated race briefing yet/)).toBeVisible();
});

test("predictions expose top 10, full grid, and driver drawer", async ({ page }) => {
  await page.goto("/predictions");
  await expect(page.getByText("Top 10 Prediction")).toBeVisible();
  await expect(page.getByText("Full Grid Prediction")).toBeVisible();
  await expect(page.getByText(/High trust|Medium trust|Low trust|Trust pending/)).toBeVisible();
  const firstOpen = page.locator(".prediction-open-hitbox").first();
  if (await firstOpen.count()) {
    await firstOpen.click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByText("Why the model ranked this driver here")).toBeVisible();
    await expect(page.getByText("Missing and available signals")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
  }
});

test("live timing labels non-live data honestly", async ({ page }) => {
  await page.goto("/live");
  await expect(page.getByRole("heading", { name: /Timing|Replay|Live/i })).toBeVisible();
  await expect(page.getByText(/Live|Delayed|Stale|Archive|Unavailable/)).toBeVisible();
});

test("model and archive pages render clear states", async ({ page }) => {
  await page.goto("/model");
  await expect(page.getByText(/Model Version|Fallback model status|Model status sync failed/)).toBeVisible();
  await page.goto("/archive");
  await expect(page.getByText(/Race Archive|No archive matches/)).toBeVisible();
});

test("sources page renders source-health state", async ({ page }) => {
  await page.goto("/sources");
  await expect(page.getByRole("heading", { name: "Data Source Health" })).toBeVisible();
  await expect(page.getByText(/Jolpica|FastF1|OpenF1|Source data unavailable|No source rows/)).toBeVisible();
});
