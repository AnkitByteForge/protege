import type { ProofCardOut } from "@/lib/protege-api-client";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Heading, Subheading, Text } from "@/components/primitives/Typography";
import { EvidenceTree } from "./EvidenceTree";
import { evidenceForIds } from "./evidenceDescription";
import { UncertaintyBlock } from "./UncertaintyBlock";

type Claim = ProofCardOut["claims"][number];

/**
 * One claim on the proof card (roadmap P20 §29 worked example): the claim
 * itself, "HOW WE KNOW" (the grounded sentences, each expandable to the
 * exact evidence rows behind it), and the mandatory uncertainty block.
 * `transfer_verified` renders as its own separate chip — never folded into
 * the claim heading (roadmap: "transfer_verified shown separately").
 */
export function ClaimCard({ claim, className }: { claim: Claim; className?: string }) {
  return (
    <SoftPanel elevation="floating" className={className}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <Heading as="h2" className="text-xl">
          {claim.text}
        </Heading>
        {claim.transfer_verified && (
          <span className="inline-flex items-center gap-1 rounded-full bg-sky-200/60 px-3 py-1 font-sans text-xs font-bold text-sky-700">
            <span aria-hidden>✓</span> Checked a new way today
          </span>
        )}
      </div>

      {claim.sentences.length > 0 && (
        <div className="mt-4">
          <Subheading as="h3" className="text-base">
            How we know
          </Subheading>
          <ul className="mt-1.5 flex flex-col gap-2">
            {claim.sentences.map((sentence, i) => (
              <li key={i}>
                <Text className="text-sm">{sentence.text}</Text>
                <EvidenceTree
                  nodes={evidenceForIds(claim.evidence, sentence.evidence_ids)}
                  triggerLabel="See evidence"
                  className="mt-1"
                />
              </li>
            ))}
          </ul>
        </div>
      )}

      <UncertaintyBlock caveats={claim.caveats} className="mt-4" />
    </SoftPanel>
  );
}
