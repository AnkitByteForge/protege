import { expect, test } from "@playwright/test";

test("app boots and renders the real product landing page", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "A warm little world that happens to teach fractions." }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Start Learning" })).toBeVisible();
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

test("manipulatives gallery route renders every documented section", async ({ page }) => {
  await page.goto("/gallery/manipulatives");
  await expect(page.getByRole("heading", { name: "Things a child can think with" })).toBeVisible();
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
