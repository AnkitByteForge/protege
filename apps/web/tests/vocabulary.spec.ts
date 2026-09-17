import { expect, test } from "@playwright/test";

/**
 * The child-facing world never surfaces internal/technical language. This
 * mirrors the forbidden-vocabulary check the roadmap specifies in full for
 * P15 (once real scenes exist); here it just guards the one child route
 * P12 ships so the rule is respected from the start, not bolted on later.
 */
const forbidden = [
  /\bAI\b/i,
  /\bmodel\b/i,
  /\bmastery\b/i,
  /%/,
  /\bpercent(age)?\b/i,
  /\bscore\b/i,
];

test("the (child) world preview never shows internal/technical language", async ({ page }) => {
  await page.goto("/world");
  const text = await page.locator("body").innerText();
  for (const pattern of forbidden) {
    expect(text, `matched forbidden pattern ${pattern}`).not.toMatch(pattern);
  }
});
