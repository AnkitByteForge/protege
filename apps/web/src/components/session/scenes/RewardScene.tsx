import { Sprout } from "@/components/sprout/Sprout";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Heading, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import { LeafProgress } from "@/components/primitives/LeafProgress";

/**
 * `reward`. Only ever reached when the server itself computed
 * `mastery_delta > 0` (`packages/session-fsm/.../machine.py`'s
 * `MASTERY_DECISION` guard) -- this scene has no conditional logic of its
 * own to gate on, because the FSM already decided the child earned it
 * before this scene could ever render (roadmap P16's own rule,
 * `reward_eligible = mastery_delta > 0 AND unaided_verification_passed`,
 * lives entirely server-side; this scene only ever presents a reward the
 * server already granted). No particle system or running garden leaf-count
 * ships here -- that ledger is P16's, out of scope for this phase; the pop
 * below is P12's existing `LeafProgress` primitive, unmodified.
 */
export function RewardScene() {
  return (
    <Stack align="center" gap="md" className="max-w-md text-center">
      <Sprout emotion="delighted" misconceptionState="resolved" size="lg" show />
      <LeafProgress count={1} total={1} label="A new leaf grew" />
      <SoftPanel elevation="floating" className="w-full">
        <Heading as="h2" className="text-xl">
          You taught Sprout something real!
        </Heading>
        <Text muted className="mt-2">
          A new leaf grew because you helped Sprout understand.
        </Text>
      </SoftPanel>
    </Stack>
  );
}
