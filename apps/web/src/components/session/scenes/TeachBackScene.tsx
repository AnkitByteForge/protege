"use client";

import { useState } from "react";
import { Sprout } from "@/components/sprout/Sprout";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Eyebrow, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import { PrimaryAction } from "@/components/primitives/Button";
import { LeafProgress } from "@/components/primitives/LeafProgress";
import type { ExplanationGivenEvent, SessionEventOut } from "@/lib/protege-api-client";

export interface TeachBackSceneProps {
  payload: SessionEventOut | null;
  onSubmit: (event: ExplanationGivenEvent) => Promise<void>;
  submitting: boolean;
}

/**
 * `teach_back` (roadmap P15/P14): Sprout states his (misconception-driven,
 * never leaked-answer) belief; the child teaches him back. `emotion` and
 * `misconceptionState` come straight from the latest `SproutTurn`/
 * `SessionEventOut.misconception_resolved` -- this scene never derives an
 * emotion itself (roadmap P14: "never from sentiment analysis").
 */
export function TeachBackScene({ payload, onSubmit, submitting }: TeachBackSceneProps) {
  const [text, setText] = useState("");
  const turn = payload?.sprout_turn ?? null;
  const misconceptionState = payload?.misconception_resolved ? "resolved" : "unresolved";

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!text.trim()) return;
    await onSubmit({
      type: "explanation_given",
      explanation: { modality: "text", text: text.trim() },
    });
    setText("");
  };

  return (
    <Stack align="center" gap="md" className="w-full max-w-lg">
      <LeafProgress count={0} label="Teaching Sprout" />
      <Eyebrow>Teach Sprout</Eyebrow>

      <Sprout
        emotion={turn?.emotion ?? "confused"}
        misconceptionState={misconceptionState}
        utterance={turn?.utterance}
        size="lg"
        show
      />

      <SoftPanel className="w-full">
        <Text muted className="text-sm">
          What would you tell Sprout to help him understand?
        </Text>
      </SoftPanel>

      <form onSubmit={handleSubmit} className="flex w-full flex-col items-center gap-3">
        <label htmlFor="teach-back-text" className="sr-only">
          What you&apos;d tell Sprout
        </label>
        <textarea
          id="teach-back-text"
          value={text}
          onChange={(event) => setText(event.target.value)}
          disabled={submitting}
          rows={3}
          placeholder="Tell Sprout what's really going on…"
          className="w-full rounded-2xl border-2 border-sand-300 bg-surface-raised px-5 py-3 font-sans text-lg text-ink shadow-soft focus-visible:border-sky-600 focus-visible:outline-none"
        />
        <PrimaryAction type="submit" disabled={submitting || !text.trim()}>
          {submitting ? "Telling Sprout…" : "Teach Sprout"}
        </PrimaryAction>
      </form>
    </Stack>
  );
}
