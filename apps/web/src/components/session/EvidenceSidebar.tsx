import { Eyebrow, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import type { SessionEventOut } from "@/lib/protege-api-client";

export interface EvidenceSidebarProps {
  turnHistory: SessionEventOut[];
  serverState: string | null;
}

/**
 * Developer/demo-only evidence sidebar (roadmap P15 "EVIDENCE"). Rendered
 * only behind `?demo=1` (see `(child)/session/[sessionId]/page.tsx`) --
 * never part of the normal child UI. Every field below is read straight off
 * a real `SessionEventOut` this session actually received; nothing here is
 * computed, estimated, or invented client-side.
 */
/**
 * `DiagnosisLabel.misconception_code` carries `Field(alias="misconception_id")`
 * (`packages/contracts/src/protege/contracts/session.py`) -- the OpenAPI
 * schema (and this generated TS type) documents that alias, but
 * `routes/sessions.py`'s `SessionEventOut.from_outcome(...).model_dump(mode="json")`
 * never passes `by_alias=True`, so the actual wire key is the bare field
 * name. Confirmed against a live response: `"labels":
 * [{"misconception_code": "M003", ...}]`, not `misconception_id`. A real,
 * disclosed P10 schema/runtime mismatch (see the final P15 report) -- read
 * both keys defensively here rather than trusting the (currently
 * inaccurate) generated type.
 */
function misconceptionCode(label: { misconception_id?: string }): string {
  const wire = label as { misconception_id?: string; misconception_code?: string };
  return wire.misconception_id ?? wire.misconception_code ?? "?";
}

export function EvidenceSidebar({ turnHistory, serverState }: EvidenceSidebarProps) {
  return (
    <aside className="w-full max-w-xs shrink-0 rounded-2xl border-2 border-dashed border-sky-600/40 bg-surface-raised/80 p-4 font-mono text-xs">
      <Eyebrow className="text-sky-700">Demo evidence (not shown to the child)</Eyebrow>
      <Text className="mt-1 text-xs">state: {serverState ?? "—"}</Text>
      <Stack gap="sm" className="mt-3 max-h-[32rem] overflow-y-auto">
        {turnHistory.length === 0 && (
          <Text muted className="text-xs">
            No events yet.
          </Text>
        )}
        {turnHistory.map((turn, i) => (
          <div key={i} className="rounded-lg bg-surface p-2">
            <div>
              step {i + 1} — {turn.state}
            </div>
            {turn.sprout_turn && (
              <div className="mt-1">
                sprout: &quot;{turn.sprout_turn.utterance}&quot; [{turn.sprout_turn.exhibits}/
                {turn.sprout_turn.emotion}/{turn.sprout_turn.confidence_shown}]
              </div>
            )}
            {turn.diagnosis && (
              <div className="mt-1">
                diagnosis: abstained={String(turn.diagnosis.abstained)} asr_reliable=
                {String(turn.diagnosis.asr_reliable)}
                {(turn.diagnosis.labels ?? []).map((label, j) => (
                  <div key={j} className="pl-2">
                    - {misconceptionCode(label)}: {label.state} (conf {label.confidence.toFixed(2)})
                  </div>
                ))}
              </div>
            )}
            {turn.hint_text && <div className="mt-1">hint: &quot;{turn.hint_text}&quot;</div>}
            {typeof turn.mastery_verified === "boolean" && (
              <div className="mt-1">mastery_verified: {String(turn.mastery_verified)}</div>
            )}
            <div className="mt-1">
              misconception_resolved: {String(turn.misconception_resolved)}
            </div>
          </div>
        ))}
      </Stack>
    </aside>
  );
}
