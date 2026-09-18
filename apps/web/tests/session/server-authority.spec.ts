import { expect, test } from "@playwright/test";
import { readE2EAuth } from "./global-setup";
import { driveDiagnosticToPractice, startSession } from "./fixtures";

test.describe("P15 server authority", () => {
  test("a stale client cannot force a transition the server has already moved past", async ({
    page,
  }) => {
    const { learnerId } = readE2EAuth();
    const sessionId = await startSession(page, learnerId);
    await driveDiagnosticToPractice(page);
    await expect(page.locator("#answer-response")).toBeEnabled({ timeout: 15_000 }); // now on `practice`

    // Directly replays the *original* `diagnostic` item's answer (`i_0132`)
    // through the same same-origin proxy the real UI uses -- simulating a
    // client whose own in-memory copy of "the current item" never caught
    // up (a slow tab, a race, a bug). This never goes through the UI's own
    // `useSessionController`, on purpose: it isolates whether the
    // *server* -- not this app's own optimism -- is what refuses a
    // now-illegal action.
    const result = await page.evaluate(async (id: string) => {
      const response = await fetch(`/api/protege/sessions/${id}/events`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({ type: "answer_submitted", item_id: "i_0132", response_text: "1/4" }),
      });
      return { status: response.status, body: await response.json() };
    }, sessionId);

    // The server rejects it -- the FSM has already moved past `diagnostic`,
    // and `i_0132` is no longer the item `practice` is presenting -- never
    // a silent 200 that would let a stale client fork reality.
    expect(result.status, "the server must not silently accept a stale client's action").not.toBe(
      200,
    );
    expect(result.body.child_safe_message).toBeTruthy();
  });
});
