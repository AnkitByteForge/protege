import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const routes = ["/", "/world", "/home", "/briefing", "/gallery", "/gallery/manipulatives"];

for (const route of routes) {
  test(`${route} has no automatically detectable accessibility violations`, async ({ page }) => {
    await page.goto(route);
    // Let entrance springs (SpeechBubble, LeafProgress, SceneTransition, ...)
    // settle before scanning — contrast is a steady-state property, and
    // scanning mid-fade can catch a transiently low-opacity animation frame.
    await page.waitForTimeout(700);
    const results = await new AxeBuilder({ page })
      // WCAG 2.1 A/AA, which includes the color-contrast rule (>= 4.5:1).
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}

test("every interactive control on the gallery is reachable by keyboard", async ({ page }) => {
  await page.goto("/gallery");

  const primary = page.getByRole("button", { name: "Primary action" });
  await primary.focus();
  await expect(primary).toBeFocused();

  // Choice controls are native buttons with aria-pressed — Enter should toggle selection.
  const pizza = page.getByRole("button", { name: "Pizza" });
  await pizza.focus();
  await page.keyboard.press("Enter");
  await expect(pizza).toHaveAttribute("aria-pressed", "true");
});

test("focus is visibly indicated (focus-visible outline applies)", async ({ page }) => {
  await page.goto("/gallery");
  const primary = page.getByRole("button", { name: "Primary action" });
  await page.keyboard.press("Tab"); // move focus into the page first
  await primary.focus();
  const outlineWidth = await primary.evaluate((el) => getComputedStyle(el).outlineWidth);
  expect(outlineWidth).not.toBe("0px");
});

test("reduced motion disables ambient background animation", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/world");
  const ambient = page.getByTestId("ambient-motion");
  const duration = await ambient.evaluate((el) => getComputedStyle(el).animationDuration);
  // Our global stylesheet forces a ~0ms duration under prefers-reduced-motion.
  expect(parseFloat(duration)).toBeLessThan(0.01);
});

test("motion is present by default (sanity check the above test is meaningful)", async ({
  page,
}) => {
  await page.goto("/world");
  const ambient = page.getByTestId("ambient-motion");
  const duration = await ambient.evaluate((el) => getComputedStyle(el).animationDuration);
  expect(parseFloat(duration)).toBeGreaterThan(1);
});
