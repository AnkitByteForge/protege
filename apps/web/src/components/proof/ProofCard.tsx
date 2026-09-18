import { isProofCardReady, type ProofCardResult } from "@/lib/protege-api-client";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Heading, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import { ClaimCard } from "./ClaimCard";
import { TonightAction } from "./TonightAction";

function formatHeader(generatedAt: string, durationMinutes: number | null): string {
  const date = new Date(generatedAt);
  const day = Number.isNaN(date.getTime())
    ? null
    : date.toLocaleDateString(undefined, { weekday: "long" });
  const parts = [day, durationMinutes != null ? `${durationMinutes} minutes` : null].filter(
    (part): part is string => Boolean(part),
  );
  return parts.join(" · ");
}

/**
 * The parent proof card (roadmap P20): what was assessed, what changed,
 * how it was verified, what remains unknown, and one thing to try tonight.
 * No scores, no percentages, no letter grades anywhere in this component
 * or anything it renders — every number the backend computed (`p_known`,
 * evidence weights, thresholds) stays server-side; this reads only claim
 * text, grounded sentences, and plain-language evidence descriptions.
 */
export function ProofCard({ result, className }: { result: ProofCardResult; className?: string }) {
  if (!isProofCardReady(result)) {
    return (
      <SoftPanel elevation="floating" className={className}>
        <Heading as="h2" className="text-xl">
          Nothing to show yet
        </Heading>
        <Text muted className="mt-2 max-w-prose">
          {result.message}
        </Text>
      </SoftPanel>
    );
  }

  const header = formatHeader(result.generated_at, result.duration_minutes);

  return (
    <Stack gap="lg" className={className}>
      {header && (
        <Text muted className="font-sans text-sm font-bold tracking-wide uppercase">
          {header}
        </Text>
      )}

      {result.claims.length === 0 ? (
        <SoftPanel elevation="floating">
          <Heading as="h2" className="text-xl">
            Nothing to show yet
          </Heading>
          <Text muted className="mt-2 max-w-prose">
            This session didn&apos;t produce anything we can show you yet.
          </Text>
        </SoftPanel>
      ) : (
        result.claims.map((claim) => <ClaimCard key={claim.claim_id} claim={claim} />)
      )}

      {result.tonight_action && <TonightAction action={result.tonight_action} />}
    </Stack>
  );
}
