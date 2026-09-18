"use client";

import { Sprout } from "@/components/sprout/Sprout";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Eyebrow, Heading, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import { PrimaryAction } from "@/components/primitives/Button";
import type { HintRequestedEvent, SessionEventOut } from "@/lib/protege-api-client";

export interface CoachAssistSceneProps {
  payload: SessionEventOut | null;
  onSubmit: (event: HintRequestedEvent) => Promise<void>;
  submitting: boolean;
}

/**
 * `coach_assist` -- roadmap's "recovery" screen. Reached only when the
 * child has stayed stuck in `teach_back` past
 * `TEACH_BACK_STUCK_TURNS` (roadmap P17's shield-forced-hint path); the
 * hint itself always comes from `hint_text` on the server response
 * (`engine/runtime.py`: an authored `Intervention.script`, never invented
 * client-side -- roadmap P17: "Coach rewrites an authored intervention; it
 * never invents pedagogy").
 */
export function CoachAssistScene({ payload, onSubmit, submitting }: CoachAssistSceneProps) {
  const hintText = payload?.hint_text ?? null;

  return (
    <Stack align="center" gap="md" className="w-full max-w-lg">
      <Eyebrow>A little help</Eyebrow>

      <Sprout
        emotion="thinking"
        misconceptionState="unresolved"
        size="md"
        show
        utterance={hintText ?? undefined}
      />

      <SoftPanel elevation="floating" className="w-full text-center">
        <Heading as="h2" className="text-xl">
          {hintText ? "Here's a little nudge." : "Would a hint help?"}
        </Heading>
        {!hintText && (
          <Text muted className="mt-2">
            This one&apos;s just for you and Sprout -- it won&apos;t count against anything.
          </Text>
        )}
      </SoftPanel>

      {!hintText && (
        <PrimaryAction
          disabled={submitting}
          onClick={() => void onSubmit({ type: "hint_requested" })}
        >
          {submitting ? "Asking Sprout…" : "Get a hint"}
        </PrimaryAction>
      )}
    </Stack>
  );
}
