"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/cn";
import { spring } from "@/design/tokens";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { EyePart } from "@/components/sprout/parts/eyes";
import { MouthPart } from "@/components/sprout/parts/mouths";
import { BrowPart } from "@/components/sprout/parts/brows";
import { PoseBody } from "@/components/sprout/parts/poses";
import { HEAD_PIVOT, HEAD_TRANSFORM_BY_POSE, VIEW_BOX } from "@/components/sprout/geometry";
import type { SproutExpression } from "@/components/sprout/types";

export interface SproutFaceProps {
  expression: SproutExpression;
  /** Small pointer-follow offset in local units for the "look at cursor" idle behaviour. */
  lookOffset?: { x: number; y: number };
  /** Transient blink override. */
  blink?: boolean;
  /** Accessible label describing what Sprout looks like right now — never color-only. */
  label: string;
  className?: string;
}

const transformOrigin = `${HEAD_PIVOT.x}px ${HEAD_PIVOT.y}px`;

/**
 * The combinatorial SVG rig itself: 5 eyes x 6 mouths x 4 brows x 4 poses =
 * 480 possible expressions, assembled from the 19 reusable parts in
 * `./parts`. Every part lives in the same shared coordinate system
 * (`geometry.ts`); a pose changes only the body silhouette plus one
 * uniform transform on the head+face group (translate, then rotate/scale
 * pivoted on `HEAD_PIVOT`), so any combination composes without clipping
 * (proven mathematically in `SproutFace.test.tsx`).
 *
 * Purely presentational — it has no idea what emotion means. `Sprout`
 * (the character shell) is the only place emotion is resolved into an
 * expression.
 */
export function SproutFace({ expression, lookOffset, blink, label, className }: SproutFaceProps) {
  const reduceMotion = useReducedMotion();
  const headTarget = HEAD_TRANSFORM_BY_POSE[expression.pose];

  return (
    <svg
      role="img"
      aria-label={label}
      viewBox={`0 0 ${VIEW_BOX.width} ${VIEW_BOX.height}`}
      className={cn("h-full w-full overflow-visible", className)}
    >
      <motion.g
        key={`body-${expression.pose}`}
        initial={reduceMotion ? undefined : { opacity: 0.4 }}
        animate={{ opacity: 1 }}
        transition={spring.settle}
      >
        <PoseBody id={expression.pose} />
      </motion.g>

      <motion.g
        style={{ transformOrigin }}
        animate={{
          x: headTarget.dx,
          y: headTarget.dy,
          rotate: headTarget.rotate,
          scale: headTarget.scale,
        }}
        transition={reduceMotion ? { duration: 0 } : spring.settle}
      >
        <motion.g
          key={`brow-${expression.brow}`}
          initial={reduceMotion ? undefined : { opacity: 0.3 }}
          animate={{ opacity: 1 }}
          transition={spring.settle}
        >
          <BrowPart id={expression.brow} />
        </motion.g>

        <motion.g
          key={`eye-${expression.eye}`}
          initial={reduceMotion ? undefined : { opacity: 0.3 }}
          animate={{ opacity: 1 }}
          transition={spring.settle}
        >
          <EyePart id={expression.eye} lookOffset={lookOffset} blink={blink} />
        </motion.g>

        <motion.g
          key={`mouth-${expression.mouth}`}
          initial={reduceMotion ? undefined : { opacity: 0.3 }}
          animate={{ opacity: 1 }}
          transition={spring.settle}
        >
          <MouthPart id={expression.mouth} />
        </motion.g>
      </motion.g>
    </svg>
  );
}
