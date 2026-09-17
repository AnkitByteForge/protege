import { expect, test } from "@playwright/test";

/**
 * Visual regression snapshots for the key design-system primitives.
 *
 * These are skipped by default. Playwright's `toHaveScreenshot` baselines
 * are OS/browser-specific by filename, and this repo is developed across
 * mixed local OSes while CI runs on ubuntu-latest — committing a baseline
 * generated on a developer machine would not match the CI-generated name
 * and would fail for the wrong reason (missing baseline, not a real
 * regression). Run explicitly, in the same environment that will compare
 * against it (ideally a dedicated CI job), to seed or update baselines:
 *
 *   RUN_VISUAL_SNAPSHOTS=1 npx playwright test tests/visual --update-snapshots
 *
 * and thereafter:
 *
 *   RUN_VISUAL_SNAPSHOTS=1 npx playwright test tests/visual
 */
test.skip(!process.env.RUN_VISUAL_SNAPSHOTS, "set RUN_VISUAL_SNAPSHOTS=1 to run visual snapshots");

test("gallery — full page", async ({ page }) => {
  await page.goto("/gallery");
  await expect(page).toHaveScreenshot("gallery-full.png", {
    fullPage: true,
    maxDiffPixelRatio: 0.02,
  });
});

test("SceneFrame — child world preview", async ({ page }) => {
  await page.goto("/world");
  await expect(page.locator("main")).toHaveScreenshot("world-scene-frame.png", {
    maxDiffPixelRatio: 0.02,
  });
});

test("buttons section", async ({ page }) => {
  await page.goto("/gallery");
  await expect(page.locator("#buttons")).toHaveScreenshot("gallery-buttons.png", {
    maxDiffPixelRatio: 0.02,
  });
});

test("color section", async ({ page }) => {
  await page.goto("/gallery");
  await expect(page.locator("#color")).toHaveScreenshot("gallery-color.png", {
    maxDiffPixelRatio: 0.02,
  });
});
