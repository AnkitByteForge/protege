"use client";

import { useRouter } from "next/navigation";
import { Sprout } from "@/components/sprout/Sprout";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Heading, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import { PrimaryAction } from "@/components/primitives/Button";

export function CompleteScene({
  abandoned = false,
  learnerId,
}: {
  abandoned?: boolean;
  /** The server session payload's `learner_id`; never derived client-side. */
  learnerId: string | null;
}) {
  const router = useRouter();
  // Without a server-supplied id, `/start` re-resolves the learner server
  // side rather than landing on `/garden`'s missing-learner guard.
  const gardenHref = learnerId ? `/garden?learnerId=${encodeURIComponent(learnerId)}` : "/start";
  return (
    <Stack align="center" gap="md" className="max-w-md text-center">
      <Sprout
        emotion={abandoned ? "thinking" : "delighted"}
        misconceptionState="resolved"
        size="lg"
        show
      />
      <SoftPanel elevation="floating" className="w-full">
        <Heading as="h2" className="text-xl">
          {abandoned ? "See you again soon!" : "That's it for today!"}
        </Heading>
        <Text muted className="mt-2">
          {abandoned
            ? "We'll pick right back up next time."
            : "Great work today -- Sprout will remember what you taught him."}
        </Text>
      </SoftPanel>
      <PrimaryAction onClick={() => router.push(gardenHref)}>Back to the garden</PrimaryAction>
    </Stack>
  );
}
