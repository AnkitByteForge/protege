import { expect, test } from "@playwright/test";
import { readE2EAuth } from "./global-setup";
import {
  driveDiagnosticToPractice,
  driveExplanationToTeachBack,
  driveIndependentVerify,
  driveOneTeachBackTurn,
  drivePracticeToExplanation,
  driveTransferToComplete,
  requestHint,
  skipReflection,
  startSession,
} from "./fixtures";
import { forbidden } from "../forbidden-vocabulary";

test.describe("P15 happy path", () => {
  test("a full session plays start to finish, with real Sprout state, real manipulative evidence, and no forbidden vocabulary", async ({
    page,
  }) => {
    const { learnerId } = readE2EAuth();

    await startSession(page, learnerId);
    await expect(page.getByRole("heading", { name: /pizza|piece|which|compare/i })).toBeVisible({
      timeout: 20_000,
    });

    // --- A manipulative interaction is real diagnostic evidence, not decoration ---
    // Moving the "thinking space" FractionBar before answering must reach the
    // server as its own `manipulative_moved` event (roadmap P13: "equal in
    // standing to speech"), not just live in local component state.
    const slider = page.locator('[role="slider"][aria-label="Thinking space — filled amount"]');
    await expect(slider).toBeVisible({ timeout: 15_000 });
    await slider.focus();
    const manipulativeRequest = page.waitForRequest(
      (request) =>
        request.url().includes("/events") &&
        request.method() === "POST" &&
        (request.postData() ?? "").includes("manipulative_moved"),
    );
    await page.keyboard.press("ArrowRight");
    await driveDiagnosticToPractice(page);
    const manipulativeReq = await manipulativeRequest;
    expect(manipulativeReq.postData()).toContain('"action":"keyboard_adjust"');

    await drivePracticeToExplanation(page);
    await driveExplanationToTeachBack(page);

    // Sprout says nothing until the child's own first teach-back attempt --
    // `SPROUT_SETUP`/`SPROUT_SETUP_HARD` only *select* a misconception,
    // they never call Sprout (`engine/runtime.py`'s teach_back branch is the
    // only place `run_teach_back_turn` -- and therefore a real
    // `SproutTurn` -- gets produced). One real turn first, then assert.
    await driveOneTeachBackTurn(page);

    // --- Sprout's visual state follows the authoritative diagnosis, never sentiment ---
    // FakeProvider's canned SproutTurn always exhibits M003 with emotion "confused"
    // (packages/llm/.../fake.py DEFAULT_CANNED_RESPONSES); the misconception is
    // unresolved (see fixtures.ts docstring), so Sprout must render as "confused",
    // never "delighted" -- exactly the P14 safety-clamp rule.
    await expect(page.getByRole("img", { name: "Sprout looks confused" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("img", { name: "Sprout looks delighted" })).toHaveCount(0);
    await expect(
      page.getByText("I think 1/8 is bigger! Eight is way more than four."),
    ).toBeVisible();

    // 5 more turns (1 already done above) + 2 hint requests -> REFLECTION.
    await driveOneTeachBackTurn(page); // turn 2 -> COACH_ASSIST
    await requestHint(page); // -> TEACH_BACK
    await driveOneTeachBackTurn(page); // turn 3
    await driveOneTeachBackTurn(page); // turn 4 -> COACH_ASSIST
    await requestHint(page); // -> TEACH_BACK
    await driveOneTeachBackTurn(page); // turn 5
    await driveOneTeachBackTurn(page); // turn 6 -> REFLECTION
    await skipReflection(page);
    await driveIndependentVerify(page);
    await driveTransferToComplete(page);

    await expect(page.getByRole("heading", { name: "That's it for today!" })).toBeVisible({
      timeout: 20_000,
    });

    // --- No forbidden child-facing vocabulary anywhere across the whole flow ---
    const text = await page.locator("body").innerText();
    for (const pattern of forbidden) {
      expect(text, `matched forbidden pattern ${pattern}`).not.toMatch(pattern);
    }
  });

  test("the demo evidence sidebar shows only real server data, never fabricated content", async ({
    page,
  }) => {
    const { learnerId } = readE2EAuth();
    const sessionId = await startSession(page, learnerId);
    await page.goto(`/session/${sessionId}?demo=1`);

    await driveDiagnosticToPractice(page);
    await drivePracticeToExplanation(page);
    await driveExplanationToTeachBack(page);
    await driveOneTeachBackTurn(page);

    // The sidebar's diagnosis block must match FakeProvider's exact canned
    // DiagnosisResult verbatim -- any other text would mean the sidebar
    // invented something the server never actually returned.
    const sidebar = page.getByText("Demo evidence (not shown to the child)").locator("..");
    await expect(sidebar.getByText(/M003: unresolved \(conf 0\.62\)/)).toBeVisible({
      timeout: 15_000,
    });
  });
});
