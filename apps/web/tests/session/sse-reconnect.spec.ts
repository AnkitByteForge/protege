import { expect, test } from "@playwright/test";
import { readE2EAuth } from "./global-setup";
import { driveDiagnosticToPractice, startSession, submitAnswer } from "./fixtures";

test.describe("P15 SSE reconnect", () => {
  test("a dropped connection reconnects and the session keeps advancing correctly", async ({
    page,
    context,
  }) => {
    const { learnerId } = readE2EAuth();
    await startSession(page, learnerId);
    await driveDiagnosticToPractice(page);
    await expect(page.locator("#answer-response")).toBeEnabled({ timeout: 15_000 }); // on `practice`

    // A genuine mid-stream network drop -- not a page reload, not a fresh
    // `EventSource`. The browser's own reconnect (roadmap P10: "the
    // browser's native EventSource reconnect sends Last-Event-ID back")
    // is what has to recover here, unaided by any app code.
    await context.setOffline(true);
    await page.waitForTimeout(2_000);
    await context.setOffline(false);

    // The stream must resume and the session must still be fully usable --
    // submitting the next real answer proves the reconnected stream (and
    // the app state built on top of it) is not stuck or duplicated. Practice
    // needs exactly one correct submission (see fixtures.ts), which moves
    // the session on to `explanation` -- asserting on `#explanation-text`
    // next, not `#answer-response` again, is itself proof the transition
    // actually happened rather than silently stalling.
    await expect(page.locator("#answer-response")).toBeEnabled({ timeout: 20_000 });
    await submitAnswer(page, "1/2");
    await expect(page.locator("#explanation-text")).toBeEnabled({ timeout: 20_000 });
  });
});
