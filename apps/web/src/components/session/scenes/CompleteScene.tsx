"use client";

import { useRouter } from "next/navigation";
import { Sprout } from "@/components/sprout/Sprout";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Heading, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import { PrimaryAction } from "@/components/primitives/Button";

export function CompleteScene({ abandoned = false }: { abandoned?: boolean }) {
  const router = useRouter();
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
      <PrimaryAction onClick={() => router.push("/garden")}>Back to the garden</PrimaryAction>
    </Stack>
  );
}
