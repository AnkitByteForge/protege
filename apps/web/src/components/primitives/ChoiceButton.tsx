"use client";

import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/cn";
import { spring } from "@/design/tokens";
import { useReducedMotion } from "@/hooks/useReducedMotion";

export interface ChoiceButtonProps {
  selected?: boolean;
  /**
   * Deliberately not `"correct" | "incorrect"`. A choice is either picked
   * or it isn't — right/wrong framing (and any red) lives in whatever
   * pedagogical layer consumes this, never in the primitive itself.
   */
  onSelect?: () => void;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
  disabled?: boolean;
}

/**
 * A large, tactile, single-choice card — the non-verbal explanation /
 * multiple-choice primitive. Big touch target, springy press feedback,
 * and a moss (never red) selected state.
 */
export function ChoiceButton({
  selected = false,
  onSelect,
  icon,
  children,
  className,
  disabled,
}: ChoiceButtonProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.button
      type="button"
      aria-pressed={selected}
      disabled={disabled}
      onClick={onSelect}
      whileHover={disabled || reduceMotion ? undefined : { y: -3, transition: spring.settle }}
      whileTap={
        disabled || reduceMotion ? { opacity: 0.85 } : { scale: 0.97, transition: spring.pop }
      }
      className={cn(
        "flex min-h-touch-lg flex-col items-center justify-center gap-2 rounded-2xl border-2 bg-surface-raised",
        "px-6 py-5 text-center shadow-soft transition-colors focus-visible:outline-none",
        "disabled:cursor-not-allowed disabled:opacity-50",
        selected ? "border-moss-600 bg-moss-200/40" : "border-sand-300 hover:border-sand-500",
        className,
      )}
    >
      {icon && <span className="text-3xl leading-none">{icon}</span>}
      <span className="font-sans text-lg font-bold text-ink">{children}</span>
    </motion.button>
  );
}
