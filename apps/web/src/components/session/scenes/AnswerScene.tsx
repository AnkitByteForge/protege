"use client";

import { useState } from "react";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Eyebrow, Heading, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import { PrimaryAction } from "@/components/primitives/Button";
import { FractionBar } from "@/components/manipulatives/FractionBar";
import { useManipulativeTrace } from "@/components/manipulatives/useManipulativeTrace";
import { ANSWER_SCENE_COPY } from "@/components/session/sceneCopy";
import type { SessionStateName } from "@/session/types";
import type { ItemPromptOut, SessionEventRequest } from "@/lib/protege-api-client";

export interface AnswerSceneProps {
  state: SessionStateName;
  item: ItemPromptOut | null | undefined;
  onSubmit: (event: SessionEventRequest) => Promise<void>;
  submitting: boolean;
}

/**
 * The one "answer an item" scene shared by `diagnostic`/`practice`/
 * `independent_verify`/`transfer` (roadmap P15 screens of the same names) --
 * they differ only in framing copy and in whether a `FractionBar` scratch
 * space is offered, never in the event they submit
 * (`answer_submitted`, validated server-side; this scene never grades it
 * itself). The bar is optional thinking space, not the answer channel
 * itself (roadmap P13: the manipulative is "something to think with"); its
 * own interactions are still reported as real `manipulative_moved` evidence
 * via `onTrace`/`useManipulativeTrace`, exactly as every other manipulative
 * use in this app does.
 */
export function AnswerScene({ state, item, onSubmit, submitting }: AnswerSceneProps) {
  const [responseText, setResponseText] = useState("");
  const [numerator, setNumerator] = useState(1);
  const [denominator, setDenominator] = useState(4);
  const trace = useManipulativeTrace();
  const copy = ANSWER_SCENE_COPY[state] ?? { eyebrow: "Let's try this one", hintAvailable: false };

  const flushManipulativeTrace = async () => {
    if (trace.trace.length === 0) return;
    await onSubmit({ type: "manipulative_moved", trace: trace.trace });
    trace.reset();
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!item || !responseText.trim()) return;
    await flushManipulativeTrace();
    await onSubmit({
      type: "answer_submitted",
      item_id: item.item_id,
      response_text: responseText.trim(),
    });
    setResponseText("");
  };

  return (
    <Stack align="center" gap="md" className="w-full max-w-lg">
      <Eyebrow>{copy.eyebrow}</Eyebrow>

      <SoftPanel elevation="floating" className="w-full text-center">
        <Heading as="h2" className="text-xl">
          {item?.stem ?? "Getting your next question ready…"}
        </Heading>
      </SoftPanel>

      <SoftPanel className="w-full">
        <Text muted className="mb-3 text-sm">
          Want to think it through first? Try the fraction bar.
        </Text>
        <FractionBar
          label="Thinking space"
          numerator={numerator}
          denominator={denominator}
          onNumeratorChange={setNumerator}
          onDenominatorChange={setDenominator}
          onTrace={trace.record}
          tone="sky"
        />
      </SoftPanel>

      <form onSubmit={handleSubmit} className="flex w-full flex-col items-center gap-3">
        <label htmlFor="answer-response" className="sr-only">
          Your answer
        </label>
        <input
          id="answer-response"
          type="text"
          value={responseText}
          onChange={(event) => setResponseText(event.target.value)}
          disabled={!item || submitting}
          placeholder="Type your answer"
          className="w-full max-w-xs rounded-2xl border-2 border-sand-300 bg-surface-raised px-5 py-3 text-center font-sans text-lg font-bold text-ink shadow-soft focus-visible:border-sky-600 focus-visible:outline-none"
        />
        <PrimaryAction type="submit" disabled={!item || !responseText.trim() || submitting}>
          {submitting ? "Checking…" : "Submit"}
        </PrimaryAction>
      </form>
    </Stack>
  );
}
