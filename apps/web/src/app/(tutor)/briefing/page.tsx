import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Display, Heading, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";

/**
 * Infrastructure preview only. The real tutor briefing (what not to
 * re-teach, evidence links, time-boxed grant) is roadmap P21 — this page
 * proves the tutor-register shell only.
 */
export default function TutorBriefingPage() {
  return (
    <Stack gap="lg">
      <div>
        <Display as="h1" className="text-3xl sm:text-4xl">
          Briefing
        </Display>
        <Text muted className="mt-1">
          (tutor) route group — design-system preview, no learner data yet.
        </Text>
      </div>

      <SoftPanel elevation="floating">
        <Heading as="h2" className="text-xl">
          No active grant
        </Heading>
        <Text muted className="mt-2 max-w-prose">
          A tutor briefing opens here once a time-boxed grant is issued for a learner. It will lead
          with what not to re-teach, and every claim will link to its evidence.
        </Text>
      </SoftPanel>
    </Stack>
  );
}
