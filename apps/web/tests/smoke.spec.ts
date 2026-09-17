import { expect, test } from "@playwright/test";

test("app boots and renders the local dev index", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "PROTÉGÉ" })).toBeVisible();
  await expect(page.getByRole("link", { name: /design system gallery/i })).toBeVisible();
});

test("(child) world preview renders the SceneFrame shell", async ({ page }) => {
  await page.goto("/world");
  await expect(page.getByRole("heading", { name: "The garden" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Next scene" })).toBeVisible();
});

test("(parent) home preview renders its shell", async ({ page }) => {
  await page.goto("/home");
  await expect(page.getByRole("heading", { name: "Welcome" })).toBeVisible();
});

test("(tutor) briefing preview renders its shell", async ({ page }) => {
  await page.goto("/briefing");
  await expect(page.getByRole("heading", { name: "Briefing" })).toBeVisible();
});

test("gallery route renders every documented section", async ({ page }) => {
  await page.goto("/gallery");
  await expect(page.getByRole("heading", { name: "The PROTÉGÉ visual language" })).toBeVisible();
  for (const heading of [
    "Typography",
    "Color",
    "Buttons",
    "Choice controls",
    "Panels",
    "Speech bubble",
    "Leaf progress",
    "SceneFrame",
    "Loading & recovery",
    "Motion",
  ]) {
    await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
  }
});
