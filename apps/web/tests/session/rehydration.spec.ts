import { expect, test } from "@playwright/test";
import { readE2EAuth } from "./global-setup";
import {
  driveDiagnosticToPractice,
  driveExplanationToTeachBack,
  driveIndependentVerify,
  drivePracticeToExplanation,
  driveTeachBackToReflection,
  driveTransferToComplete,
  skipReflection,
  startSession,
} from "./fixtures";

test.describe("P15 rehydration", () => {
  test("a refresh mid-session reconstructs the exact server state, not whatever the client last held", async ({
    page,
  }) => {
    const { learnerId } = readE2EAuth();
    await startSession(page, learnerId);
    await driveDiagnosticToPractice(page);
    await drivePracticeToExplanation(page);
    await driveExplanationToTeachBack(page);

    await expect(page.locator("#teach-back-text")).toBeVisible({ timeout: 15_000 });

    // A hard reload discards every bit of in-memory client state
    // (sessionMachine context, XState actor, everything). GET
    // /v1/sessions/{id} is the only thing that can put the right scene
    // back on screen (roadmap P15 "REHYDRATION").
    await page.reload();

    await expect(page.locator("#teach-back-text")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("img", { name: "Sprout looks confused" })).toBeVisible({
      timeout: 15_000,
    });
  });

  test("a session completes correctly after the browser itself is recreated mid-session", async ({
    browser,
  }) => {
    const { learnerId } = readE2EAuth();
    const firstContext = await browser.newContext({
      storageState: "./.e2e/storage-state.json",
    });
    const firstPage = await firstContext.newPage();

    await startSession(firstPage, learnerId);
    const sessionUrl = firstPage.url();
    await driveDiagnosticToPractice(firstPage);
    await drivePracticeToExplanation(firstPage);
    await driveExplanationToTeachBack(firstPage);
    await expect(firstPage.locator("#teach-back-text")).toBeVisible({ timeout: 15_000 });
    await firstContext.close();

    // A brand new browser context (roadmap P15 test #9: "process restart
    // through the existing P10 backend" -- no in-memory client state
    // survives this, only what Postgres actually persisted does).
    const secondContext = await browser.newContext({
      storageState: "./.e2e/storage-state.json",
    });
    const secondPage = await secondContext.newPage();
    await secondPage.goto(sessionUrl);

    await expect(secondPage.locator("#teach-back-text")).toBeVisible({ timeout: 20_000 });

    await driveTeachBackToReflection(secondPage);
    await skipReflection(secondPage);
    await driveIndependentVerify(secondPage);
    await driveTransferToComplete(secondPage);

    await expect(secondPage.getByRole("heading", { name: "That's it for today!" })).toBeVisible({
      timeout: 20_000,
    });

    await secondContext.close();
  });
});
