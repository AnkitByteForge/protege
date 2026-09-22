import type { ProofCardOut } from "@/lib/protege-api-client";

export type EvidenceNode = ProofCardOut["claims"][number]["evidence"][number];

const KIND_LABEL: Record<string, string> = {
  response: "Answered a question",
  teaching_episode: "Taught Sprout",
  transfer: "Tried something new",
};

const REPRESENTATION_LABEL: Record<string, string> = {
  area_model: "a shape",
  number_line: "a number line",
  set_model: "a group of objects",
  symbolic: "numbers",
};

function friendlyRepresentation(value: unknown): string {
  if (typeof value !== "string") return "a new way";
  return REPRESENTATION_LABEL[value] ?? value.replace(/_/g, " ");
}

/**
 * Turn one evidence row's raw `payload` (P9's own recorded facts — never
 * re-derived or guessed here) into a single warm, parent-readable sentence.
 * Deliberately never renders a raw number, a `weight`, or an internal
 * `event_type` string — the "no scores, no percentages" rule extended to
 * the evidence tree's own detail view, not just the claim headline.
 */
export function describeEvidenceNode(node: EvidenceNode): string {
  const payload = node.payload;
  switch (node.kind) {
    case "response": {
      const correct = payload.correct === true;
      const unaided = payload.unaided === true;
      return correct
        ? unaided
          ? "Solved it alone, without any hints"
          : "Solved it correctly"
        : "Gave it a try";
    }
    case "teaching_episode": {
      return payload.resolved === true
        ? "Explained the idea back clearly, in their own words"
        : "Was still working out how to explain it";
    }
    case "transfer": {
      const solved = payload.result === true;
      const where = friendlyRepresentation(payload.representation);
      return solved
        ? `Solved a new kind of problem, using ${where} they hadn't seen before`
        : `Tried a new kind of problem, using ${where} they hadn't seen before`;
    }
    default:
      return "Something Sprout noticed";
  }
}

export function kindLabel(kind: string): string {
  return KIND_LABEL[kind] ?? kind;
}

export function formatEvidenceTime(occurredAt: string | null): string | null {
  if (!occurredAt) return null;
  const date = new Date(occurredAt);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

/** Subset of `nodes` whose `evidence_id` appears in `ids` — used to resolve
 * one sentence's own citations against its claim's full evidence tree
 * without a second fetch (roadmap: no duplicate evidence storage/lookup).
 * Kept in this plain (non-"use client") module, not `EvidenceTree.tsx`, so
 * a Server Component (`ClaimCard.tsx`) can call it directly at render time —
 * a "use client" module's exports are all client references and cannot be
 * invoked from server-rendered code. */
export function evidenceForIds(nodes: EvidenceNode[], ids: string[]): EvidenceNode[] {
  const wanted = new Set(ids);
  return nodes.filter((node) => wanted.has(node.evidence_id));
}
