import { Sprout } from "@/components/sprout/Sprout";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Heading, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import type { SessionEventOut } from "@/lib/protege-api-client";

export interface SummarySceneProps {
  payload: SessionEventOut | null;
}

/**
 * `summary`. Every line here comes straight off the session's own real
 * response fields -- `misconception_resolved`, `mastery_verified` -- never
 * fabricated or inferred (roadmap P15 "EVIDENCE": "must never be
 * fabricated client-side"). No scores, percentages, or grades (roadmap's
 * eight-word vocabulary rule); a full evidence-tree proof card is P20,
 * out of scope here.
 */
export function SummaryScene({ payload }: SummarySceneProps) {
  const resolved = payload?.misconception_resolved ?? false;
  const verified = payload?.mastery_verified ?? null;

  return (
    <Stack align="center" gap="md" className="max-w-md text-center">
      <Sprout
        emotion={resolved ? "delighted" : "dawning"}
        misconceptionState={resolved ? "resolved" : "unresolved"}
        size="lg"
        show
      />
      <SoftPanel elevation="floating" className="w-full">
        <Heading as="h2" className="text-xl">
          Here&apos;s what happened today
        </Heading>
        <Stack gap="sm" className="mt-3 text-left">
          <Text>
            {resolved
              ? "You helped Sprout see it differently."
              : "You and Sprout kept working on it together."}
          </Text>
          {verified === true && <Text>You showed you could do it on your own.</Text>}
          {verified === false && (
            <Text muted>This one&apos;s still coming together -- that&apos;s okay.</Text>
          )}
        </Stack>
      </SoftPanel>
    </Stack>
  );
}
