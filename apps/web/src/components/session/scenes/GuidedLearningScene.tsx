"use client";

import { useRef, useState } from "react";
import { Sprout } from "@/components/sprout/Sprout";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Eyebrow, Heading, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import { FractionBar } from "@/components/manipulatives/FractionBar";
import type { ManipulativeMovedEvent } from "@/lib/protege-api-client";

export interface GuidedLearningSceneProps {
  onSubmit: (event: ManipulativeMovedEvent) => Promise<void>;
}

/**
 * `guided_learning`. Most of the time the server passes through this state
 * synchronously (see `session/types.ts`'s `BEAT_STATES`), so this scene is
 * only ever glimpsed for a beat.
 *
 * **Disclosed limitation** (roadmap: "Document any resulting limitation
 * precisely" -- matching the pattern `docs/P10_SESSION_API.md` already uses
 * for the SSE token-streaming gap): the *recovery* loop-back edges into
 * this state (`PRACTICE` after 3 consecutive errors; `INDEPENDENT_VERIFY`
 * after fewer than 2 of 3 correct -- `packages/session-fsm/.../machine.py`)
 * have no dispatchable client event or server-side timeout job wired in
 * the current P10 (`services/session/.../engine/runtime.py` only
 * auto-cascades `GUIDED_LEARNING` when it is entered from `DIAGNOSTIC`, and
 * no `jobs/worker.py` handler fires a state timeout for it). A child who
 * lands here via a real loop-back is genuinely stuck server-side today --
 * not a P15 bug, and not something P15 may fix (P7/P9/P10/P11 are frozen
 * this phase). This scene keeps the moment honest and productive rather
 * than broken: Sprout stays present, the fraction bar remains usable (every
 * interaction still lands as real diagnostic evidence via
 * `manipulative_moved`), and nothing implies a "next" step that cannot
 * actually happen yet.
 */
export function GuidedLearningScene({ onSubmit }: GuidedLearningSceneProps) {
  const [numerator, setNumerator] = useState(1);
  const [denominator, setDenominator] = useState(4);
  const startedAtRef = useRef(performance.now());

  return (
    <Stack align="center" gap="md" className="w-full max-w-lg">
      <Eyebrow>Let&apos;s look at this together</Eyebrow>

      <Sprout emotion="thinking" misconceptionState="unresolved" size="md" show />

      <SoftPanel elevation="floating" className="w-full text-center">
        <Heading as="h2" className="text-xl">
          Let&apos;s slow down and try it with the bar.
        </Heading>
        <Text muted className="mt-2">
          Move the pieces around -- there&apos;s no rush.
        </Text>
      </SoftPanel>

      <SoftPanel className="w-full">
        <FractionBar
          label="Let's explore together"
          numerator={numerator}
          denominator={denominator}
          onNumeratorChange={setNumerator}
          onDenominatorChange={setDenominator}
          onTrace={(event) => {
            const t = Math.round(((performance.now() - startedAtRef.current) / 1000) * 1000) / 1000;
            void onSubmit({
              type: "manipulative_moved",
              trace: [
                {
                  t,
                  action: event.action,
                  target: event.target ?? null,
                  targets: event.targets ?? null,
                },
              ],
            });
          }}
          tone="moss"
        />
      </SoftPanel>
    </Stack>
  );
}
