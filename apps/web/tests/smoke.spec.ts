import { expect, test } from "@playwright/test";

test("app boots and renders the foundation page", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "PROTÉGÉ" })).toBeVisible();
  await expect(page.getByText("Local foundation is running.")).toBeVisible();
});
