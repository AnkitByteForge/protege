import { GallerySection } from "@/app/gallery/_components/GallerySection";
import { Display, Eyebrow, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import { ProofCard } from "@/components/proof";
import type { ProofCardResult } from "@/lib/protege-api-client";

/**
 * The §38 worked example (Ava / M003 / S004), shaped exactly as
 * `GET /v1/learners/{id}/proof` (roadmap P20) returns it — sample data for
 * this gallery page only; the real card is fetched live in `(parent)/home`.
 * Every evidence id, claim, and caveat below mirrors ARCHITECTURE.md §29/§38
 * so this page doubles as a readable spec of the shape, not just a demo.
 */
const readyExample: ProofCardResult = {
  status: "ready",
  learner_id: "3f7b7e0a-6b7b-4b8e-9b0a-000000000001",
  session_id: "3f7b7e0a-6b7b-4b8e-9b0a-000000000002",
  generated_at: new Date().toISOString(),
  duration_minutes: 14,
  tonight_action:
    "Tonight, try this for about 2 minutes: Imagine the SAME pizza shared with more friends.",
  claims: [
    {
      claim_id: "c_88",
      text: "Ava can compare unit fractions.",
      threshold_id: "th_02",
      transfer_verified: true,
      caveats: ["Not yet checked: comparing fractions with different numerators."],
      sentences: [
        {
          text: "Ava taught Sprout the correct idea about larger denominator means larger fraction.",
          evidence_ids: ["e_904"],
        },
        {
          text: "Ava got 3 of 3 new problems right without any hints.",
          evidence_ids: ["e_901", "e_902", "e_903"],
        },
        {
          text: "Ava solved a new problem on a number line they hadn't seen before.",
          evidence_ids: ["e_905"],
        },
      ],
      evidence: [
        {
          evidence_id: "e_901",
          kind: "response",
          weight: 3,
          payload: { item: "i_0148", correct: true, unaided: true },
          occurred_at: new Date().toISOString(),
          event_type: "ANSWER_SUBMITTED",
          session_id: "3f7b7e0a-6b7b-4b8e-9b0a-000000000002",
          turn_id: null,
        },
        {
          evidence_id: "e_902",
          kind: "response",
          weight: 3,
          payload: { item: "i_0155", correct: true, unaided: true },
          occurred_at: new Date().toISOString(),
          event_type: "ANSWER_SUBMITTED",
          session_id: "3f7b7e0a-6b7b-4b8e-9b0a-000000000002",
          turn_id: null,
        },
        {
          evidence_id: "e_903",
          kind: "response",
          weight: 3,
          payload: { item: "i_0161", correct: true, unaided: true },
          occurred_at: new Date().toISOString(),
          event_type: "ANSWER_SUBMITTED",
          session_id: "3f7b7e0a-6b7b-4b8e-9b0a-000000000002",
          turn_id: null,
        },
        {
          evidence_id: "e_904",
          kind: "teaching_episode",
          weight: 1,
          payload: { episode_id: "te_77", resolved: true, resolution_turn: 4 },
          occurred_at: new Date().toISOString(),
          event_type: "TEACH_BACK_COMPLETED",
          session_id: "3f7b7e0a-6b7b-4b8e-9b0a-000000000002",
          turn_id: null,
        },
        {
          evidence_id: "e_905",
          kind: "transfer",
          weight: 3,
          payload: { item: "i_0201", result: true, representation: "number_line" },
          occurred_at: new Date().toISOString(),
          event_type: "TRANSFER_PASSED",
          session_id: "3f7b7e0a-6b7b-4b8e-9b0a-000000000002",
          turn_id: null,
        },
      ],
    },
  ],
};

const notYetAvailableExample: ProofCardResult = {
  status: "not_yet_available",
  learner_id: "3f7b7e0a-6b7b-4b8e-9b0a-000000000003",
  message: "Nothing to show yet -- this appears after a completed session.",
};

export default function ProofGalleryPage() {
  return (
    <main id="main" className="mx-auto max-w-2xl px-4 py-10 sm:px-8">
      <Stack gap="sm" className="mb-10">
        <Eyebrow>Parent proof gallery — roadmap P20</Eyebrow>
        <Display as="h1">What a proof card looks like</Display>
        <Text muted className="max-w-2xl">
          Exactly what <code>GET /v1/learners/{"{id}"}/proof</code> returns, rendered. No scores, no
          percentages, no letter grades — a claim, how it was checked, what&apos;s still unknown,
          and one thing to try tonight. Click &ldquo;See evidence&rdquo; on any line.
        </Text>
      </Stack>

      <Stack gap="xl">
        <GallerySection
          id="ready"
          title="A completed session"
          description="The §38 worked example (Ava / M003), shaped exactly as the API returns it."
        >
          <ProofCard result={readyExample} />
        </GallerySection>

        <GallerySection
          id="not-yet-available"
          title="Before any session has completed"
          description="The canonical not-yet-available shape (roadmap P10) — never a fabricated empty card."
        >
          <ProofCard result={notYetAvailableExample} />
        </GallerySection>
      </Stack>
    </main>
  );
}
