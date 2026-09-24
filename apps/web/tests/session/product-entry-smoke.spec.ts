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
} from "./fixtures";

/**
 * Product-entry milestone: the one path in, and the way back --
 *
 *     / -> "Start Learning" -> /start (POST /v1/learners/ensure) ->
 *     /garden?learnerId=<real id> -> POST /v1/sessions -> /session/[sessionId]
 *     -> ... -> COMPLETE -> "Back to the garden" -> /garden?learnerId=<same id>
 *
 * against the real Next.js build, the real P10 FastAPI backend, and real
 * Postgres -- the same infrastructure `happy-path.spec.ts` and friends
 * already use (`global-setup.ts`'s `protege_e2e_token` cookie, minted by
 * `services/session/scripts/e2e_server.py` the same way the backend's own
 * pytest suite mints test JWTs; no real Clerk tenant is available in this
 * environment, and this suite does not attempt to simulate one). The session
 * itself is driven with the shared `fixtures.ts` steps; what this test owns
 * is the entry chain and that the learner identity survives completion.
 */
test.describe("Product entry", () => {
  test("/ -> Start Learning -> /start -> real ensure -> /garden -> session -> back to the same garden", async ({
    page,
  }) => {
    // A full real session (see happy-path.spec.ts's note on its own timeout).
    test.setTimeout(120_000);

    const { learnerId: seededLearnerId } = readE2EAuth();

    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "A warm little world that happens to teach fractions." }),
    ).toBeVisible();

    await page.getByRole("button", { name: "Start Learning" }).click();
    await page.waitForURL(/\/start$/, { timeout: 10_000 });

    // /start calls the real POST /v1/learners/ensure against the real
    // backend (authenticated via the same protege_e2e_token cookie
    // global-setup wires up for the rest of this suite) and redirects with
    // the real learner id it returns -- never a client-fabricated one.
    await page.waitForURL(/\/garden\?learnerId=[0-9a-f-]+/, { timeout: 10_000 });
    const learnerIdFromEnsure = new URL(page.url()).searchParams.get("learnerId");
    expect(learnerIdFromEnsure).toBe(seededLearnerId);

    await page.getByRole("button", { name: "Start" }).click();
    await page.waitForURL(/\/session\/[0-9a-f-]+/, { timeout: 20_000 });
    await expect(page.getByRole("heading", { name: /pizza|piece|which|compare/i })).toBeVisible({
      timeout: 20_000,
    });

    await driveDiagnosticToPractice(page);
    await drivePracticeToExplanation(page);
    await driveExplanationToTeachBack(page);
    await driveTeachBackToReflection(page);
    await skipReflection(page);
    await driveIndependentVerify(page);
    await driveTransferToComplete(page);

    // Completion must hand the child back to *this* learner's garden: the
    // id comes from the server's session payload, so it must equal the one
    // the session was started with -- not a bare /garden (which would hit
    // its missing-learner guard) and not a different learner.
    const backToGarden = page.getByRole("button", { name: "Back to the garden" });
    await expect(backToGarden).toBeVisible({ timeout: 30_000 });
    await backToGarden.click();

    await page.waitForURL(/\/garden\?learnerId=[0-9a-f-]+/, { timeout: 10_000 });
    expect(new URL(page.url()).searchParams.get("learnerId")).toBe(seededLearnerId);
    await expect(page.getByRole("button", { name: "Start" })).toBeVisible();
    await expect(page.getByText("No garden picked yet")).toHaveCount(0);
  });
});
