import { Display, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import { ProofCard } from "@/components/proof";
import type { NotYetAvailableOut } from "@/lib/protege-api-client";

/**
 * The parent proof route integration boundary (roadmap P20). This page
 * renders the real `ProofCard` component the API's `GET
 * /v1/learners/{id}/proof` response drives (`apps/web/src/components/proof`)
 * — the same component `/gallery/proof` demos with sample data.
 *
 * What is NOT wired up yet, and belongs to a later phase, not P20: which
 * learner this parent is looking at (no learner-selection UI exists) and
 * the Clerk session token the real request needs (no Clerk provider is
 * mounted in `app/layout.tsx` yet — P10's backend auth has no frontend
 * counterpart). Until both exist, this route always renders the same
 * canonical `not_yet_available` shape the backend itself returns before
 * any session has completed, which is a true statement either way.
 */
const noLearnerYet: NotYetAvailableOut = {
  status: "not_yet_available",
  learner_id: "00000000-0000-0000-0000-000000000000",
  message:
    "Once a session finishes, this is where you'll see what was learned, how it was verified, " +
    "what's still unconfirmed, and one small thing to try tonight. No scores, no percentages " +
    "— just what actually happened.",
};

export default function ParentHomePage() {
  return (
    <Stack gap="lg">
      <div>
        <Display as="h1" className="text-3xl sm:text-4xl">
          Welcome
        </Display>
        <Text muted className="mt-1">
          (parent) route group — design-system preview, no session data yet.
        </Text>
      </div>

      <ProofCard result={noLearnerYet} />
    </Stack>
  );
}
