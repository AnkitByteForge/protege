import { expect, test } from "@playwright/test";
import { readE2EAuth } from "./global-setup";
import {
  driveDiagnosticToPractice,
  driveExplanationToTeachBack,
  driveOneTeachBackTurn,
  drivePracticeToExplanation,
  requestHint,
  startSession,
} from "./fixtures";

test.describe("P15 misconception recovery path", () => {
  test("a child stuck on teach-back reaches recovery (coach_assist), gets an authored hint, and returns to teach-back", async ({
    page,
  }) => {
    const { learnerId } = readE2EAuth();
    await startSession(page, learnerId);
    await driveDiagnosticToPractice(page);
    await drivePracticeToExplanation(page);
    await driveExplanationToTeachBack(page);

    // Turn 1: no progress (see fixtures.ts docstring) -> stays in teach_back.
    await driveOneTeachBackTurn(page);
    await expect(page.locator("#teach-back-text")).toBeVisible({ timeout: 15_000 });

    // Turn 2: stuck_turns reaches TEACH_BACK_STUCK_TURNS (2) -> COACH_ASSIST.
    await driveOneTeachBackTurn(page);
    await expect(page.getByRole("heading", { name: "Would a hint help?" })).toBeVisible({
      timeout: 15_000,
    });

    // The hint is always an authored intervention, never invented (roadmap
    // P17: "Coach rewrites an authored intervention; it never invents
    // pedagogy") -- this exact string is FakeProvider's canned `CoachHint`
    // text (packages/llm/.../fake.py).
    await requestHint(page);
    await expect(
      page.getByText("Let's cut the SAME pizza two ways and lay them on top of each other."),
    ).toBeVisible({ timeout: 15_000 });

    // The shield-forced hint never counts as a "correct answer" -- the
    // child returns to teach_back to keep trying, not forward to reflection.
    await expect(page.locator("#teach-back-text")).toBeVisible({ timeout: 15_000 });
  });
});
