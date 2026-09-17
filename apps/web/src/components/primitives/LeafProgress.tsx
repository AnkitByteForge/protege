"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/cn";
import { spring } from "@/design/tokens";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { Leaf } from "@/components/illustrations/Leaf";

export interface LeafProgressProps {
  count: number;
  total?: number;
  /** Accessible label; visually hidden, since the leaves themselves are the visible signal — never a percentage. */
  label?: string;
  className?: string;
}

/**
 * The progress primitive used everywhere a percentage would otherwise go.
 * Leaves fill in one at a time with the `pop` spring; nothing is ever
 * displayed as a number to the child. The count is still exposed to
 * assistive tech via a visually-hidden label.
 */
export function LeafProgress({ count, total = 5, label, className }: LeafProgressProps) {
  const reduceMotion = useReducedMotion();
  const filled = Math.max(0, Math.min(total, count));

  return (
    <div
      className={cn("inline-flex items-center gap-1.5", className)}
      role="img"
      aria-label={label ?? `${filled} of ${total} leaves grown`}
    >
      {Array.from({ length: total }, (_, i) => {
        const isFilled = i < filled;
        return (
          <motion.span
            key={i}
            aria-hidden
            initial={reduceMotion ? undefined : { scale: 0.4, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ ...spring.pop, delay: reduceMotion ? 0 : i * 0.06 }}
            className={cn("block h-7 w-7", isFilled ? "text-moss-600" : "text-sand-300")}
          >
            <Leaf className="h-full w-full" />
          </motion.span>
        );
      })}
    </div>
  );
}
