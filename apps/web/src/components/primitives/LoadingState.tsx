"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/cn";
import { spring } from "@/design/tokens";
import { useReducedMotion } from "@/hooks/useReducedMotion";

/**
 * The "thinking" state — never a spinner, never technical language. Three
 * soft dots breathe in sequence; under reduced motion they simply sit
 * still and the label carries the meaning. Always announced politely to
 * assistive tech so a wait never reads as "nothing is happening."
 */
export function LoadingState({
  label = "Just a moment…",
  className,
}: {
  label?: string;
  className?: string;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn("flex flex-col items-center gap-3 py-8", className)}
    >
      <div className="flex items-center gap-2">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            aria-hidden
            className="h-3.5 w-3.5 rounded-full bg-sky-500"
            animate={reduceMotion ? undefined : { y: [0, -8] }}
            transition={
              reduceMotion
                ? undefined
                : { ...spring.drift, repeat: Infinity, repeatType: "mirror", delay: i * 0.15 }
            }
          />
        ))}
      </div>
      <p className="font-sans text-sm font-semibold text-ink-soft">{label}</p>
    </div>
  );
}
