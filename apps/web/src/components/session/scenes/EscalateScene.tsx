import { Sprout } from "@/components/sprout/Sprout";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Heading, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";

/**
 * `escalate_to_human` -- reached after 3 below-readiness loops (roadmap
 * P25's "warm and in-character" escalation tone; the full escalation
 * pipeline/notification system is P25, out of scope this phase).
 *
 * **Disclosed limitation**: the current P10 (`engine/runtime.py`) has no
 * client event that maps to `Event.ESCALATION_ACKNOWLEDGED`, so nothing
 * can move a session past this state yet -- a real gap in P10's event
 * coverage, not something P15 may fix (P7/P9/P10/P11 are frozen this
 * phase). This scene stays warm and honest rather than implying a "next"
 * that cannot happen: it never shows a spinner or a broken control, only
 * Sprout, present, waiting alongside the child.
 */
export function EscalateScene() {
  return (
    <Stack align="center" gap="md" className="max-w-md text-center">
      <Sprout emotion="thinking" misconceptionState="unresolved" size="lg" show />
      <SoftPanel elevation="floating" className="w-full">
        <Heading as="h2" className="text-xl">
          Let&apos;s find a grown-up together.
        </Heading>
        <Text muted className="mt-2">
          This one&apos;s tricky enough that some extra help would be great.
        </Text>
      </SoftPanel>
    </Stack>
  );
}
