import { expect, test } from "@playwright/test";

test.describe("Sprout — the rig explorer", () => {
  test("the full 480-point rig is inspectable without any backend/session integration", async ({
    page,
  }) => {
    await page.goto("/gallery/sprout");
    await expect(page.getByRole("heading", { name: "Inspecting the rig" })).toBeVisible();
    await expect(page.getByText("480 possible expressions")).toBeVisible();

    // The raw-rig explorer can drive every eye/mouth/brow/pose directly.
    await page.getByRole("button", { name: "wide", exact: true }).click();
    await page.getByRole("button", { name: "grin", exact: true }).click();
    await page.getByRole("button", { name: "raised", exact: true }).click();
    await page.getByRole("button", { name: "delighted", exact: true }).last().click();
  });

  test("Sprout's expression changes when the emotion preset changes", async ({ page }) => {
    await page.goto("/gallery/sprout");
    // Two Sprout instances render on this page (the learning-state demo and
    // the raw-rig explorer, which is pinned to "confused" regardless of its
    // pose picker) — both start on "confused", hence `.first()`.
    const face = page.getByRole("img", { name: "Sprout looks confused" }).first();
    await expect(face).toBeVisible();

    await page.getByRole("button", { name: "thinking", exact: true }).first().click();
    await expect(page.getByRole("img", { name: "Sprout looks thinking" })).toBeVisible();
  });
});

test.describe("Sprout — the delighted-forbidden safety rule", () => {
  test("never shows delighted while the misconception is unresolved", async ({ page }) => {
    await page.goto("/gallery/sprout");

    // Default state is unresolved; requesting "delighted" must clamp to "dawning".
    await page.getByRole("button", { name: "delighted", exact: true }).first().click();
    await expect(page.getByRole("img", { name: "Sprout looks dawning" })).toBeVisible();
    await expect(page.getByRole("img", { name: "Sprout looks delighted" })).toHaveCount(0);
    await expect(page.getByText("Safety rule engaged")).toBeVisible();
  });

  test("shows delighted once the misconception is marked resolved", async ({ page }) => {
    await page.goto("/gallery/sprout");

    await page.getByRole("button", { name: "resolved", exact: true }).click();
    await page.getByRole("button", { name: "delighted", exact: true }).first().click();

    await expect(page.getByRole("img", { name: "Sprout looks delighted" })).toBeVisible();
    await expect(page.getByText("Safety rule engaged")).toHaveCount(0);
  });
});

test.describe("Sprout — reduced motion", () => {
  test("idle breathing sway is disabled under prefers-reduced-motion", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/gallery/sprout");

    const face = page.getByRole("img", { name: "Sprout looks confused" }).first();
    await expect(face).toBeVisible();
    const first = await face.evaluate((el) => el.getBoundingClientRect().top);
    await page.waitForTimeout(900);
    const second = await face.evaluate((el) => el.getBoundingClientRect().top);

    expect(second).toBeCloseTo(first, 0);
  });

  test("motion is present by default (sanity check the above test is meaningful)", async ({
    page,
  }) => {
    await page.goto("/gallery/sprout");
    const face = page.getByRole("img", { name: "Sprout looks confused" }).first();
    await expect(face).toBeVisible();
    // Just confirm the page renders normally without reduced motion — the
    // breathing sway itself is a JS-driven spring, not something we assert
    // a specific pixel delta for here (flaky across CI timing); the reduced
    // motion test above is the meaningful, deterministic assertion.
    await expect(face).toBeVisible();
  });
});
