import type {
  MisconceptionState,
  SproutEmotion,
  SproutExpression,
} from "@/components/sprout/types";

/**
 * The canonical expression for each point in the deterministic
 * confused -> thinking -> dawning -> delighted progression (architecture
 * §8.3). These are defaults for when the caller supplies only an emotion;
 * the full 480-point rig (`SproutFace`) can still be driven part-by-part
 * for the gallery/demo explorer.
 */
export const EXPRESSION_BY_EMOTION: Record<SproutEmotion, SproutExpression> = {
  confused: { eye: "half", brow: "furrowed", mouth: "worried", pose: "confused" },
  thinking: { eye: "squint", brow: "quizzical", mouth: "flat", pose: "thinking" },
  dawning: { eye: "wide", brow: "quizzical", mouth: "smile", pose: "dawning" },
  delighted: { eye: "soft", brow: "raised", mouth: "grin", pose: "delighted" },
};

/**
 * CRITICAL SAFETY RULE (roadmap P14 / architecture §8.3): Sprout must never
 * appear delighted before the misconception clears. This is not a separate
 * client-side "mood" that could drift from or contradict learning state —
 * it is a pure, deterministic clamp computed from the same learning-state
 * props the caller already has (`SproutTurn.emotion`, the server-computed
 * presentation emotion, and `MisconceptionBelief.state`). There is nowhere
 * in this module, or in `Sprout`, that emotion is set from sentiment,
 * timers, or any other client-only signal.
 */
export function deriveDisplayEmotion(
  emotion: SproutEmotion,
  misconceptionState: MisconceptionState,
): SproutEmotion {
  if (emotion === "delighted" && misconceptionState !== "resolved") {
    return "dawning";
  }
  return emotion;
}

/** Resolves the canonical expression for an already-safety-clamped emotion. */
export function expressionForEmotion(emotion: SproutEmotion): SproutExpression {
  return EXPRESSION_BY_EMOTION[emotion];
}
