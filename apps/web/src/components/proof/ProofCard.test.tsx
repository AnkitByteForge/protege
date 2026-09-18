import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ProofCard } from "./ProofCard";
import type { ProofCardResult } from "@/lib/protege-api-client";

const readyResult: ProofCardResult = {
  status: "ready",
  learner_id: "learner-1",
  session_id: "session-1",
  generated_at: "2026-09-15T18:04:00Z",
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
      ],
      evidence: [
        {
          evidence_id: "e_901",
          kind: "response",
          weight: 3,
          payload: { item: "i_0148", correct: true, unaided: true },
          occurred_at: "2026-09-15T18:00:00Z",
          event_type: "ANSWER_SUBMITTED",
          session_id: "session-1",
          turn_id: null,
        },
        {
          evidence_id: "e_902",
          kind: "response",
          weight: 3,
          payload: { item: "i_0155", correct: true, unaided: true },
          occurred_at: "2026-09-15T18:01:00Z",
          event_type: "ANSWER_SUBMITTED",
          session_id: "session-1",
          turn_id: null,
        },
        {
          evidence_id: "e_903",
          kind: "response",
          weight: 3,
          payload: { item: "i_0161", correct: true, unaided: true },
          occurred_at: "2026-09-15T18:02:00Z",
          event_type: "ANSWER_SUBMITTED",
          session_id: "session-1",
          turn_id: null,
        },
        {
          evidence_id: "e_904",
          kind: "teaching_episode",
          weight: 1,
          payload: { episode_id: "te_77", resolved: true, resolution_turn: 4 },
          occurred_at: "2026-09-15T18:03:00Z",
          event_type: "TEACH_BACK_COMPLETED",
          session_id: "session-1",
          turn_id: null,
        },
      ],
    },
  ],
};

const notYetAvailableResult: ProofCardResult = {
  status: "not_yet_available",
  learner_id: "learner-1",
  message: "Nothing to show yet -- this appears after a completed session.",
};

const FORBIDDEN = [
  /%/,
  /\bpercent(age)?\b/i,
  /\bscore\b/i,
  /\bmastery\b/i,
  /\bmastered\b/i,
  /\bAI\b/,
  /\balgorithm\b/i,
];

function assertNoForbiddenVocabulary(container: HTMLElement) {
  const text = container.textContent ?? "";
  for (const pattern of FORBIDDEN) {
    expect(text, `matched forbidden pattern ${pattern}`).not.toMatch(pattern);
  }
}

describe("ProofCard", () => {
  it("renders the claim, transfer-verified chip, and tonight's action", () => {
    render(<ProofCard result={readyResult} />);
    expect(screen.getByText("Ava can compare unit fractions.")).toBeInTheDocument();
    expect(screen.getByText(/checked a new way today/i)).toBeInTheDocument();
    expect(screen.getByText(/imagine the same pizza/i)).toBeInTheDocument();
  });

  it("always renders a non-empty uncertainty block for a ready card", () => {
    render(<ProofCard result={readyResult} />);
    expect(screen.getByText(/not yet confirmed/i)).toBeInTheDocument();
    expect(
      screen.getByText("Not yet checked: comparing fractions with different numerators."),
    ).toBeInTheDocument();
  });

  it("never renders scores, percentages, letter grades, or technical vocabulary", () => {
    const { container } = render(<ProofCard result={readyResult} />);
    assertNoForbiddenVocabulary(container);
  });

  it("expanding a sentence's evidence tree reveals only that sentence's own evidence", () => {
    render(<ProofCard result={readyResult} />);

    const toggles = screen.getAllByRole("button", { name: /see evidence/i });
    // First sentence cites only e_904 (the teaching episode) -> one moment.
    expect(toggles[0]).toHaveTextContent("(1 moment)");
    // Second sentence cites e_901/e_902/e_903 -> three moments.
    expect(toggles[1]).toHaveTextContent("(3 moments)");

    fireEvent.click(toggles[0]);
    expect(screen.getByText(/explained the idea back clearly/i)).toBeInTheDocument();
    // The other sentence's evidence is not shown until its own toggle opens.
    expect(screen.queryByText(/solved it alone, without any hints/i)).not.toBeInTheDocument();
  });

  it("renders the canonical not-yet-available shape without fabricating a card", () => {
    render(<ProofCard result={notYetAvailableResult} />);
    expect(screen.getByRole("heading", { name: /nothing to show yet/i })).toBeInTheDocument();
    expect(
      screen.getByText("Nothing to show yet -- this appears after a completed session."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/compare unit fractions/i)).not.toBeInTheDocument();
  });
});
