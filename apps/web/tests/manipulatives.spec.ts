import { expect, test } from "@playwright/test";

/**
 * End-to-end coverage for roadmap P13's manipulative gallery: real pointer
 * drags, real keyboard-only completion, and touch, on top of the
 * component-level Vitest suite (which covers drag/snap/align/compare/trace
 * math in isolation).
 */
test.describe("manipulatives gallery", () => {
  test("every documented section renders", async ({ page }) => {
    await page.goto("/gallery/manipulatives");
    for (const heading of [
      "FractionBar",
      "NumberLine",
      "AreaModel",
      "ExplanationCards",
      "Trace log",
    ]) {
      await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
    }
  });

  test("FractionBar is completable by keyboard alone and records a trace", async ({ page }) => {
    await page.goto("/gallery/manipulatives");
    const handle = page.getByRole("slider", { name: "Your fraction bar — filled amount" });
    await handle.focus();
    await expect(handle).toHaveAttribute("aria-valuenow", "1");

    await page.keyboard.press("ArrowRight");
    await page.keyboard.press("ArrowRight");
    await expect(handle).toHaveAttribute("aria-valuenow", "3");

    await page.keyboard.press("Home");
    await expect(handle).toHaveAttribute("aria-valuenow", "0");

    await expect(page.getByText(/events? recorded/)).toContainText(/[1-9]/);
  });

  test("dragging the FractionBar handle updates the value with a mouse", async ({ page }) => {
    await page.goto("/gallery/manipulatives");
    const handle = page.getByRole("slider", { name: "Your fraction bar — filled amount" });
    await handle.scrollIntoViewIfNeeded();
    const box = await handle.boundingBox();
    if (!box) throw new Error("handle has no bounding box");

    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + 300, box.y + box.height / 2, { steps: 10 });
    await page.mouse.up();

    const value = await handle.getAttribute("aria-valuenow");
    expect(Number(value)).toBeGreaterThan(1);
  });

  test("NumberLine markers are keyboard-operable and report a compare trace", async ({ page }) => {
    await page.goto("/gallery/manipulatives");
    const quarter = page.getByRole("slider", { name: "1/4 marker" });
    await quarter.focus();
    for (let i = 0; i < 8; i++) {
      await page.keyboard.press("ArrowRight");
    }
    await expect(page.getByText(/events? recorded/)).toContainText(/[1-9]/);
  });

  test("AreaModel segments respond to touch", async ({ browser }) => {
    const context = await browser.newContext({ hasTouch: true });
    const page = await context.newPage();
    await page.goto("/gallery/manipulatives");
    const slider = page.getByRole("slider", { name: "Shade a fraction of the shape" });
    await expect(slider).toHaveAttribute("aria-valuenow", "1");
    await slider.scrollIntoViewIfNeeded();

    const box = await slider.boundingBox();
    if (!box) throw new Error("area model has no bounding box");
    // Tap well inside the lower-right wedge — the default circle's second
    // segment, which starts unfilled (only the first quarter is filled),
    // so a correctly-handled tap must raise the shaded count.
    await page.touchscreen.tap(box.x + box.width * 0.75, box.y + box.height * 0.75);

    await expect
      .poll(async () => Number(await slider.getAttribute("aria-valuenow")))
      .toBeGreaterThan(1);

    await context.close();
  });

  test("ExplanationCards can be completed with keyboard only", async ({ page }) => {
    await page.goto("/gallery/manipulatives");
    const group = page.getByRole("radiogroup");
    const first = group.getByRole("radio").first();
    await first.focus();
    await page.keyboard.press("ArrowRight");
    const second = group.getByRole("radio").nth(1);
    await expect(second).toBeFocused();
    await expect(second).toHaveAttribute("aria-checked", "true");
  });

  test("an interrupted FractionBar drag recovers to its last committed value", async ({ page }) => {
    await page.goto("/gallery/manipulatives");
    const handle = page.getByRole("slider", { name: "Your fraction bar — filled amount" });
    await expect(handle).toHaveAttribute("aria-valuenow", "1");
    await handle.scrollIntoViewIfNeeded();

    const box = await handle.boundingBox();
    if (!box) throw new Error("handle has no bounding box");
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + 250, box.y + box.height / 2, { steps: 5 });

    // Simulate the browser cancelling the gesture mid-drag (e.g. a system
    // gesture takes over) rather than a clean pointerup.
    await handle.dispatchEvent("pointercancel", { pointerId: 1 });
    await page.mouse.up();

    await expect(handle).toHaveAttribute("aria-valuenow", "1");
  });

  test("respects prefers-reduced-motion while staying fully interactive", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/gallery/manipulatives");
    const handle = page.getByRole("slider", { name: "Your fraction bar — filled amount" });
    await handle.focus();
    await page.keyboard.press("ArrowRight");
    await expect(handle).toHaveAttribute("aria-valuenow", "2");
  });
});
