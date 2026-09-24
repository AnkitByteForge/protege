import { BeatScene } from "@/components/session/scenes/BeatScene";
import { AnswerScene } from "@/components/session/scenes/AnswerScene";
import { ExplanationScene } from "@/components/session/scenes/ExplanationScene";
import { TeachBackScene } from "@/components/session/scenes/TeachBackScene";
import { CoachAssistScene } from "@/components/session/scenes/CoachAssistScene";
import { GuidedLearningScene } from "@/components/session/scenes/GuidedLearningScene";
import { RewardScene } from "@/components/session/scenes/RewardScene";
import { SummaryScene } from "@/components/session/scenes/SummaryScene";
import { EscalateScene } from "@/components/session/scenes/EscalateScene";
import { CompleteScene } from "@/components/session/scenes/CompleteScene";
import { LoadingState } from "@/components/primitives/LoadingState";
import type { SessionStateName } from "@/session/types";
import type { SessionEventOut, SessionEventRequest, SessionOut } from "@/lib/protege-api-client";

export interface SessionSceneRouterProps {
  sceneState: SessionStateName | null;
  payload: SessionOut | SessionEventOut | null;
  onSubmit: (event: SessionEventRequest) => Promise<void>;
  submitting: boolean;
}

const RICH_STATES = new Set<SessionStateName>([
  "DIAGNOSTIC",
  "PRACTICE",
  "INDEPENDENT_VERIFY",
  "TRANSFER",
  "EXPLANATION",
  "REFLECTION",
  "TEACH_BACK",
  "COACH_ASSIST",
]);

/**
 * The one place a `SessionStateName` is mapped to a scene component
 * (roadmap P15 state->scene mapping). Nothing here decides which state
 * comes next -- `sceneState` is handed down already-authoritative from
 * `useSessionController`/`sessionMachine`; this component only ever picks
 * how to *render* it.
 */
export function SessionSceneRouter({
  sceneState,
  payload,
  onSubmit,
  submitting,
}: SessionSceneRouterProps) {
  if (sceneState === null) {
    return <LoadingState label="Walking into the garden…" />;
  }

  // A REST response's `next_item` reflects the state the server has
  // *already, fully* reached (`engine/runtime.py` resolves every
  // synchronous cascade before responding) -- which can be ahead of
  // `sceneState`, still paced by the slower SSE stream (roadmap P15's own
  // deliberate-beat design; see `session/sessionMachine.ts`). Showing that
  // item under the *old* scene would let a child start answering an item
  // that belongs to a screen they haven't actually arrived at yet, and the
  // eventual scene-key change (once `sceneState` catches up) would remount
  // the input out from under them, discarding anything already typed.
  // Gating on `payload.state === sceneState` keeps the item and the scene
  // identity always in lockstep; the brief gap in between reads as
  // "Getting your next question ready…" rather than a flash of the wrong
  // item.
  const currentItem = payload !== null && payload.state === sceneState ? payload.next_item : null;
  // `sprout_turn`/`diagnosis`/`hint_text`, by contrast, are read-only
  // display content, never an input a child is actively filling in -- nothing
  // is lost by showing the latest one even a beat before `sceneState`
  // catches up. Applying the same strict gate here actively hides real
  // content: `hint_requested`'s own response already carries `state:
  // "TEACH_BACK"` (the server auto-advances `COACH_ASSIST` -> `TEACH_BACK`
  // in the same request once a hint is delivered), so while `sceneState`
  // is still `COACH_ASSIST` a strict match would hide the hint text
  // entirely instead of showing it right where the child asked for it.
  const richPayload =
    RICH_STATES.has(sceneState) && payload && "sprout_turn" in payload ? payload : null;

  switch (sceneState) {
    case "DIAGNOSTIC":
    case "PRACTICE":
    case "INDEPENDENT_VERIFY":
    case "TRANSFER":
      return (
        <AnswerScene
          state={sceneState}
          item={currentItem}
          onSubmit={onSubmit}
          submitting={submitting}
        />
      );
    case "EXPLANATION":
    case "REFLECTION":
      return <ExplanationScene state={sceneState} onSubmit={onSubmit} submitting={submitting} />;
    case "TEACH_BACK":
      return <TeachBackScene payload={richPayload} onSubmit={onSubmit} submitting={submitting} />;
    case "COACH_ASSIST":
      return <CoachAssistScene payload={richPayload} onSubmit={onSubmit} submitting={submitting} />;
    case "GUIDED_LEARNING":
      return <GuidedLearningScene onSubmit={onSubmit} />;
    case "REWARD":
      return <RewardScene />;
    case "SUMMARY":
      return <SummaryScene payload={richPayload} />;
    case "ESCALATE_TO_HUMAN":
      return <EscalateScene />;
    case "COMPLETE":
      return <CompleteScene learnerId={payload?.learner_id ?? null} />;
    case "ABANDONED":
      return <CompleteScene abandoned learnerId={payload?.learner_id ?? null} />;
    default:
      // ARRIVAL, SPROUT_TEASE, DISCOVERY, SPROUT_SETUP(_HARD),
      // MASTERY_DECISION, RETRIEVAL_SCHEDULE -- every BEAT_STATES member.
      return <BeatScene state={sceneState} />;
  }
}
