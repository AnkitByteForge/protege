"use client";

import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Subheading, Text } from "@/components/primitives/Typography";
import { SecondaryAction } from "@/components/primitives/Button";
import { cn } from "@/lib/cn";

/**
 * The degraded/error state every failure in the product should render as —
 * never a stack trace, never a red banner. `message` must always be
 * in-character copy (e.g. "I need a snack — let's do puzzles"), supplied
 * by whatever layer knows why things degraded; this component only knows
 * how to present it warmly.
 */
export function ErrorState({
  title = "One moment — I got a little muddled.",
  message,
  onRetry,
  retryLabel = "Try again",
  icon,
  className,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
  icon?: ReactNode;
  className?: string;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <SoftPanel elevation="floating" className={cn("mx-auto max-w-sm text-center", className)}>
      <motion.div
        aria-hidden
        className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-clay-200 text-3xl"
        animate={reduceMotion ? undefined : { rotate: [0, -6, 6, -3, 0] }}
        // A multi-keyframe wobble needs a tween: Motion's spring supports only two keyframes.
        transition={reduceMotion ? undefined : { duration: 0.6, ease: "easeInOut" }}
      >
        {icon ?? "🍂"}
      </motion.div>
      <Subheading className="mb-1">{title}</Subheading>
      <Text muted className="mb-4">
        {message}
      </Text>
      {onRetry && (
        <SecondaryAction tone="clay" size="md" onClick={onRetry}>
          {retryLabel}
        </SecondaryAction>
      )}
    </SoftPanel>
  );
}
