import { Sprout } from "@/components/sprout/Sprout";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Heading, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import { BEAT_COPY } from "@/components/session/sceneCopy";
import type { SessionStateName } from "@/session/types";

/**
 * The generic passive beat (roadmap P15: states the server always passes
 * through synchronously -- see `session/sessionMachine.ts`'s `BEAT_STATES`).
 * No input, no event to send; the scene simply narrates that something is
 * happening while `sessionMachine`'s dwell timer runs, then the next real
 * scene replaces it.
 */
export function BeatScene({ state }: { state: SessionStateName }) {
  const copy = BEAT_COPY[state] ?? { title: "One moment…", body: "Getting things ready." };

  return (
    <Stack align="center" gap="md" className="max-w-md text-center">
      <Sprout emotion="thinking" misconceptionState="unresolved" size="md" show />
      <SoftPanel elevation="floating" className="w-full">
        <Heading as="h2" className="text-xl">
          {copy.title}
        </Heading>
        <Text muted className="mt-2">
          {copy.body}
        </Text>
      </SoftPanel>
    </Stack>
  );
}
