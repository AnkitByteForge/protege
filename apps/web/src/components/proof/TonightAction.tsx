import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Subheading, Text } from "@/components/primitives/Typography";

/**
 * "TONIGHT, 2 MINUTES" (roadmap P20: one concrete ~2-minute action, never
 * a homework list). `action` is authored content the backend selected
 * (P17-style: rewritten from an authored intervention, never invented by
 * this component or an LLM) — this component only presents it.
 */
export function TonightAction({ action, className }: { action: string; className?: string }) {
  return (
    <SoftPanel elevation="floating" className={className}>
      <Subheading as="h3" className="flex items-center gap-2 text-base text-moss-700">
        <span aria-hidden>🌱</span> Tonight, 2 minutes
      </Subheading>
      <Text className="mt-1.5">{action}</Text>
    </SoftPanel>
  );
}
