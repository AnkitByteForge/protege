import type { SproutTurnSchema, MisconceptionBeliefSchema } from "@/generated/contracts";

/**
 * Presentation emotion, driven by the Diagnostician's resolution belief
 * (roadmap P14 / architecture §8.3) — never by sentiment analysis. Re-typed
 * from the generated contract rather than re-declared, so the rig can never
 * drift from `SproutTurn.emotion`'s closed set.
 */
export type SproutEmotion = SproutTurnSchema.SproutPresentationEmotion;

/** Per-learner misconception resolution state (`MisconceptionBelief.state`). */
export type MisconceptionState = MisconceptionBeliefSchema.MisconceptionState;

/** The five reusable eye paths. */
export const EYE_IDS = ["round", "wide", "soft", "half", "squint"] as const;
export type EyeId = (typeof EYE_IDS)[number];

/** The six reusable mouth paths. */
export const MOUTH_IDS = ["worried", "flat", "frown", "smile", "open", "grin"] as const;
export type MouthId = (typeof MOUTH_IDS)[number];

/** The four reusable brow paths. */
export const BROW_IDS = ["furrowed", "flat", "quizzical", "raised"] as const;
export type BrowId = (typeof BROW_IDS)[number];

/** The four reusable body/pose paths (also carries the head's lean transform). */
export const POSE_IDS = ["confused", "thinking", "dawning", "delighted"] as const;
export type PoseId = (typeof POSE_IDS)[number];

/**
 * One point in the combinatorial rig: 5 eyes x 6 mouths x 4 brows x 4 poses
 * = 480 possible expressions from these 19 reusable parts.
 */
export interface SproutExpression {
  eye: EyeId;
  mouth: MouthId;
  brow: BrowId;
  pose: PoseId;
}

export const TOTAL_EXPRESSIONS =
  EYE_IDS.length * MOUTH_IDS.length * BROW_IDS.length * POSE_IDS.length;
