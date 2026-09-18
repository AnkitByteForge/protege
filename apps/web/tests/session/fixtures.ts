import { expect, type Page } from "@playwright/test";

/**
 * Step helpers for the P15 session E2E suite. Every answer/text value here
 * is a REAL correct answer from the actual thin-thread content pack
 * (`content/math/fractions/v1/items/*.json`, item ids confirmed live
 * against `services/session/scripts/e2e_server.py`'s FakeProvider-backed
 * server) -- never a guess. Because that server has no `NVIDIA_API_KEY`,
 * every Sprout/Diagnostician call is served by `FakeProvider`'s
 * `DEFAULT_CANNED_RESPONSES` (`packages/llm/src/protege/llm/providers/fake.py`):
 * the same `SproutTurn` (exhibits M003, emotion "confused") and the same
 * `DiagnosisResult` (M003 unresolved, confidence 0.62, no understanding
 * signals) every single turn. That determinism is exactly what makes the
 * exact turn-by-turn `teach_back`/`coach_assist` sequence below reliable:
 * `stuck_turns` increments every turn (nothing the fake diagnosis ever
 * returns counts as progress), reaching `COACH_ASSIST` on turn 2 and again
 * on turn 4, then `REFLECTION` on turn 6 (`TEACH_BACK_MAX_TURNS`).
 */

export async function startSession(page: Page, learnerId: string): Promise<string> {
  await page.goto(`/garden?learnerId=${learnerId}`);
  await page.getByRole("button", { name: "Start" }).click();
  await page.waitForURL(/\/session\/[0-9a-f-]+/, { timeout: 20_000 });
  const match = page.url().match(/\/session\/([0-9a-f-]+)/);
  if (!match) throw new Error(`unexpected session URL: ${page.url()}`);
  return match[1];
}

export async function submitAnswer(page: Page, answer: string): Promise<void> {
  const input = page.locator("#answer-response");
  await expect(input).toBeEnabled({ timeout: 20_000 });
  await input.fill(answer);
  await page.getByRole("button", { name: "Submit" }).click();
}

/**
 * `#explanation-text` (`explanation`/`reflection`) and `#teach-back-text`
 * (`teach_back`) are two *different* elements with two different submit
 * buttons ("Share it" / "Teach Sprout") -- deliberately not one shared
 * compound locator. Right after submitting `explanation`, the client's
 * `sceneState` briefly still reads `EXPLANATION` (payload/scene consistency
 * -- see `SessionSceneRouter`'s `payloadMatchesScene` gate) until the SSE
 * transition to `TEACH_BACK` actually lands; a compound `"#explanation-text,
 * #teach-back-text"` locator's `.first()` would then race and resubmit
 * through the stale, already-reset `#explanation-text`/"Share it" instead
 * of waiting for the real `#teach-back-text` to appear. Each call here
 * names its own element explicitly so Playwright's auto-waiting blocks on
 * the *correct* one until the scene has genuinely arrived.
 */
async function submitTextarea(
  page: Page,
  selector: string,
  buttonName: string,
  text: string,
): Promise<void> {
  const textarea = page.locator(selector);
  await expect(textarea).toBeEnabled({ timeout: 20_000 });
  await textarea.fill(text);
  await page.getByRole("button", { name: buttonName, exact: true }).click();
}

export async function submitExplanationText(page: Page, text: string): Promise<void> {
  await submitTextarea(page, "#explanation-text", "Share it", text);
}

export async function submitTeachBackText(page: Page, text: string): Promise<void> {
  await submitTextarea(page, "#teach-back-text", "Teach Sprout", text);
}

export async function requestHint(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Get a hint" }).click();
}

export async function skipReflection(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Skip" }).click();
}

/** DIAGNOSTIC (i_0132, correct "1/4") -> server cascades to PRACTICE. */
export async function driveDiagnosticToPractice(page: Page): Promise<void> {
  await submitAnswer(page, "1/4");
}

/**
 * PRACTICE (i_2011, correct "1/2") -> EXPLANATION. Confirmed live against
 * the running server (not just read off `PRACTICE_MIN_ITEMS_ATTEMPTED`,
 * which is 4 in general): `engine/runtime.py`'s PRACTICE branch has a
 * documented content-pack-specific shortcut -- since the thin-thread pack
 * authors only one PRACTICE item, `score_practice_item` returning "still
 * dwelling" (items_attempted < 4) is treated as an immediate `TIMEOUT`
 * instead, which exits PRACTICE after exactly one submission. A "4
 * attempts" assumption here would have been wrong.
 */
export async function drivePracticeToExplanation(page: Page): Promise<void> {
  await submitAnswer(page, "1/2");
}

/** EXPLANATION capture -> server cascades through SPROUT_SETUP(_HARD) to TEACH_BACK. */
export async function driveExplanationToTeachBack(page: Page): Promise<void> {
  await submitExplanationText(page, "the pieces are the same size, just cut differently");
}

/** One TEACH_BACK turn (see module docstring for why this text never resolves the misconception). */
export async function driveOneTeachBackTurn(page: Page): Promise<void> {
  await submitTeachBackText(page, "I think the pieces might be different sizes");
}

/** Deterministically reaches REFLECTION: 6 teach-back turns, 2 hint requests, per the docstring above. */
export async function driveTeachBackToReflection(page: Page): Promise<void> {
  await driveOneTeachBackTurn(page); // turn 1
  await driveOneTeachBackTurn(page); // turn 2 -> COACH_ASSIST
  await requestHint(page); // -> TEACH_BACK
  await driveOneTeachBackTurn(page); // turn 3
  await driveOneTeachBackTurn(page); // turn 4 -> COACH_ASSIST
  await requestHint(page); // -> TEACH_BACK
  await driveOneTeachBackTurn(page); // turn 5
  await driveOneTeachBackTurn(page); // turn 6 -> REFLECTION
}

/** VERIFY_ITEM_IDS in order (i_0148, i_0155, i_0161), all correct -> TRANSFER. */
export async function driveIndependentVerify(page: Page): Promise<void> {
  await submitAnswer(page, "1/3");
  await submitAnswer(page, "1/4 piece");
  await submitAnswer(page, "1/12");
}

/** TRANSFER (i_0201, correct "1/4") -> server cascades all the way to COMPLETE. */
export async function driveTransferToComplete(page: Page): Promise<void> {
  await submitAnswer(page, "1/4");
}

/** The full deterministic happy path, ARRIVAL through COMPLETE. */
export async function driveFullSession(page: Page, learnerId: string): Promise<string> {
  const sessionId = await startSession(page, learnerId);
  await driveDiagnosticToPractice(page);
  await drivePracticeToExplanation(page);
  await driveExplanationToTeachBack(page);
  await driveTeachBackToReflection(page);
  await skipReflection(page);
  await driveIndependentVerify(page);
  await driveTransferToComplete(page);
  return sessionId;
}
