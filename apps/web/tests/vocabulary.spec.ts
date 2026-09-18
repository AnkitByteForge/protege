import { expect, test } from "@playwright/test";
import { forbidden } from "./forbidden-vocabulary";

/**
 * The child-facing world never surfaces internal/technical language. This
 * mirrors the forbidden-vocabulary check the roadmap specifies in full for
 * P15 (see `session/happy-path.spec.ts` for the live-session version); here
 * it just guards the one child route P12 ships so the rule is respected
 * from the start, not bolted on later.
 */
test("the (child) world preview never shows internal/technical language", async ({ page }) => {
  await page.goto("/world");
  const text = await page.locator("body").innerText();
  for (const pattern of forbidden) {
    expect(text, `matched forbidden pattern ${pattern}`).not.toMatch(pattern);
  }
});
