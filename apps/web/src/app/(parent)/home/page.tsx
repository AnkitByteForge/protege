import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Display, Heading, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";

/**
 * Infrastructure preview only. The real parent proof experience (evidence
 * tree, uncertainty block, tonight's action) is roadmap P20 — this page
 * only proves the parent-register shell and shows an honest empty state
 * before any session data exists.
 */
export default function ParentHomePage() {
  return (
    <Stack gap="lg">
      <div>
        <Display as="h1" className="text-3xl sm:text-4xl">
          Welcome
        </Display>
        <Text muted className="mt-1">
          (parent) route group — design-system preview, no session data yet.
        </Text>
      </div>

      <SoftPanel elevation="floating">
        <Heading as="h2" className="text-xl">
          Nothing to show yet
        </Heading>
        <Text muted className="mt-2 max-w-prose">
          Once a session finishes, this is where you&apos;ll see what was learned, how it was
          verified, what&apos;s still unconfirmed, and one small thing to try tonight. No scores, no
          percentages — just what actually happened.
        </Text>
      </SoftPanel>
    </Stack>
  );
}
