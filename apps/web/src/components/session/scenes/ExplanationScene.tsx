"use client";

import { useState } from "react";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Eyebrow, Heading, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import { PrimaryAction, SecondaryAction } from "@/components/primitives/Button";
import { ExplanationCards } from "@/components/manipulatives/ExplanationCards";
import { useManipulativeTrace } from "@/components/manipulatives/useManipulativeTrace";
import type { ExplanationGivenEvent } from "@/lib/protege-api-client";
import type { SessionStateName } from "@/session/types";

const CARD_OPTIONS = [
  { id: "same_size_pieces", label: "The pieces are the same size" },
  { id: "more_pieces_smaller", label: "More pieces means smaller pieces" },
  { id: "not_sure", label: "I'm not sure yet" },
] as const;

export interface ExplanationSceneProps {
  state: SessionStateName;
  onSubmit: (event: ExplanationGivenEvent) => Promise<void>;
  submitting: boolean;
}

/**
 * `explanation` (READINESS's own capture step) and `reflection` (roadmap
 * §37: "Skippable") share this scene -- both just capture one
 * `Explanation` and submit `explanation_given`. Three real channels, never
 * voice (P18 is out of scope): typed text, or the non-verbal 3-card pick
 * (roadmap P13 `ExplanationCards`) for a child who'd rather show than tell.
 * "Skip" on `reflection` submits an empty `TextExplanation` -- the FSM has
 * no separate skip event, so an empty explanation *is* the honest shape of
 * "skipped" the server already understands (`schemas.py`'s `text: str`
 * field carries no minimum length).
 */
export function ExplanationScene({ state, onSubmit, submitting }: ExplanationSceneProps) {
  const [mode, setMode] = useState<"text" | "cards">("text");
  const [text, setText] = useState("");
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null);
  const trace = useManipulativeTrace();
  const isReflection = state === "REFLECTION";

  const submitText = async (value: string) => {
    await onSubmit({ type: "explanation_given", explanation: { modality: "text", text: value } });
    setText("");
  };

  const submitCard = async (cardId: string) => {
    await onSubmit({
      type: "explanation_given",
      explanation: { modality: "explanation_card", card_ids: [cardId] },
    });
    setSelectedCardId(null);
  };

  return (
    <Stack align="center" gap="md" className="w-full max-w-lg">
      <Eyebrow>{isReflection ? "Thinking back" : "Tell me why"}</Eyebrow>

      <SoftPanel elevation="floating" className="w-full text-center">
        <Heading as="h2" className="text-xl">
          {isReflection ? "What helped you figure that out?" : "Why do you think that's true?"}
        </Heading>
        {isReflection && (
          <Text muted className="mt-2 text-sm">
            You can skip this one if you&apos;d rather move on.
          </Text>
        )}
      </SoftPanel>

      <div className="flex gap-2">
        <SecondaryAction
          size="md"
          tone={mode === "text" ? "moss" : "sky"}
          onClick={() => setMode("text")}
        >
          Type it
        </SecondaryAction>
        <SecondaryAction
          size="md"
          tone={mode === "cards" ? "moss" : "sky"}
          onClick={() => setMode("cards")}
        >
          Pick a picture
        </SecondaryAction>
      </div>

      {mode === "text" ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void submitText(text.trim());
          }}
          className="flex w-full flex-col items-center gap-3"
        >
          <label htmlFor="explanation-text" className="sr-only">
            Your explanation
          </label>
          <textarea
            id="explanation-text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            disabled={submitting}
            rows={3}
            placeholder="Tell me what you're thinking…"
            className="w-full rounded-2xl border-2 border-sand-300 bg-surface-raised px-5 py-3 font-sans text-lg text-ink shadow-soft focus-visible:border-sky-600 focus-visible:outline-none"
          />
          <div className="flex gap-2">
            {isReflection && (
              <SecondaryAction
                type="button"
                disabled={submitting}
                onClick={() => void submitText("")}
              >
                Skip
              </SecondaryAction>
            )}
            <PrimaryAction type="submit" disabled={submitting || (!isReflection && !text.trim())}>
              {submitting ? "Sending…" : "Share it"}
            </PrimaryAction>
          </div>
        </form>
      ) : (
        <ExplanationCards
          label="Why do you think that's true?"
          options={CARD_OPTIONS}
          selectedId={selectedCardId}
          onSelect={(id) => {
            setSelectedCardId(id);
            trace.record({ action: "select", target: id });
          }}
          disabled={submitting}
        />
      )}

      {mode === "cards" && selectedCardId && (
        <PrimaryAction disabled={submitting} onClick={() => void submitCard(selectedCardId)}>
          {submitting ? "Sending…" : "That's my answer"}
        </PrimaryAction>
      )}
    </Stack>
  );
}
