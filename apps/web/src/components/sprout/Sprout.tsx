"use client";

import { useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "@/lib/cn";
import { spring } from "@/design/tokens";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { SpeechBubble } from "@/components/primitives/SpeechBubble";
import { LeafProgress } from "@/components/primitives/LeafProgress";
import { SproutFace } from "@/components/sprout/SproutFace";
import { useSproutIdle } from "@/components/sprout/useSproutIdle";
import { deriveDisplayEmotion, expressionForEmotion } from "@/components/sprout/emotion";
import type {
  MisconceptionState,
  SproutEmotion,
  SproutExpression,
} from "@/components/sprout/types";

export interface SproutProps {
  /**
   * `SproutTurn.emotion` — already server-derived from the Diagnostician's
   * resolution belief (architecture §8.3), never from sentiment analysis.
   */
  emotion: SproutEmotion;
  /**
   * `MisconceptionBelief.state` for the misconception this turn concerns.
   * Required alongside `emotion` (not optional) so the safety clamp below
   * always has real learning state to derive from — see `emotion.ts`.
   */
  misconceptionState: MisconceptionState;
  /** 0-5, rendered with P12's `LeafProgress` — no separate progress UI is invented here. */
  leafCount?: number;
  /** Sprout's current line, rendered in P12's `SpeechBubble` shell. */
  utterance?: string;
  /** Controls entrance/exit choreography. */
  show?: boolean;
  size?: "md" | "lg";
  className?: string;
  /**
   * Escape hatch for the gallery/demo explorer only: drives the raw
   * 480-point rig directly, bypassing the emotion -> expression mapping.
   * Never pass this from a real session — it exists so the full rig can be
   * inspected without a backend (roadmap P14 exit criterion).
   */
  expressionOverride?: SproutExpression;
}

const sizeClass = { md: "h-40 w-40", lg: "h-56 w-56" } as const;

/**
 * The Sprout character shell. Composes the presentational `SproutFace` rig
 * with P12's existing `SpeechBubble` and `LeafProgress` primitives — no
 * new progress or speech UI is invented here — plus idle life (blink,
 * breathing sway, occasional look-at-cursor) and spring-driven entrance,
 * exit, and expression transitions.
 *
 * Emotion is never tracked as separate client state: every render derives
 * `displayEmotion` fresh from the `emotion` + `misconceptionState` props
 * via `deriveDisplayEmotion`, so Sprout can never drift into "delighted"
 * ahead of the misconception actually clearing.
 */
export function Sprout({
  emotion,
  misconceptionState,
  leafCount,
  utterance,
  show = true,
  size = "lg",
  className,
  expressionOverride,
}: SproutProps) {
  const reduceMotion = useReducedMotion();
  const containerRef = useRef<HTMLDivElement>(null);
  const idle = useSproutIdle({ containerRef, enabled: show });

  const displayEmotion = deriveDisplayEmotion(emotion, misconceptionState);
  const expression = expressionOverride ?? expressionForEmotion(displayEmotion);
  const label = `Sprout looks ${displayEmotion}`;

  return (
    <div className={cn("flex flex-col items-center gap-3", className)}>
      {typeof leafCount === "number" && (
        <LeafProgress count={leafCount} label={`Sprout's plant: ${leafCount} of 5 leaves grown`} />
      )}

      <AnimatePresence>
        {show && (
          <motion.div
            ref={containerRef}
            key="sprout"
            initial={reduceMotion ? undefined : { opacity: 0, scale: 0.85, y: 18 }}
            animate={{
              opacity: 1,
              scale: 1,
              // Two keyframes only: Motion's spring can't interpolate more,
              // and the `mirror` repeat below already supplies the return leg.
              y: idle.breathe ? [0, -5] : 0,
              transition: idle.breathe
                ? {
                    ...spring.drift,
                    y: { ...spring.drift, repeat: Infinity, repeatType: "mirror" },
                  }
                : spring.settle,
            }}
            exit={
              reduceMotion
                ? undefined
                : { opacity: 0, scale: 0.85, y: 18, transition: spring.settle }
            }
            className={sizeClass[size]}
          >
            <SproutFace
              expression={expression}
              lookOffset={idle.lookOffset}
              blink={idle.blink}
              label={label}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {show && utterance && <SpeechBubble tailFrom="bottom" text={utterance} />}
    </div>
  );
}
