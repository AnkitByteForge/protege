"use client";

import { useRef } from "react";
import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/cn";
import { spring } from "@/design/tokens";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import type { TraceEvent } from "@/components/manipulatives/useManipulativeTrace";

export interface ExplanationCardOption {
  id: string;
  label: string;
  icon?: ReactNode;
  /** Rich visual content — e.g. a small FractionBar/AreaModel preview — shown above the label. */
  render?: ReactNode;
}

export interface ExplanationCardsProps {
  /** Accessible name for the group, e.g. "Which picture shows why 1/4 is bigger than 1/8?" */
  label: string;
  /** Exactly three choices — the non-verbal, 3-choice teach-back interaction (roadmap P13). */
  options: readonly [ExplanationCardOption, ExplanationCardOption, ExplanationCardOption];
  selectedId: string | null;
  onSelect: (id: string) => void;
  disabled?: boolean;
  onTrace?: (event: TraceEvent) => void;
  className?: string;
}

/**
 * A three-choice, radio-group explanation picker — the channel a child who
 * can't or won't say the answer aloud uses to demonstrate understanding
 * instead. Selecting a card is itself the "explanation"; this component
 * reports the pick via `onTrace` and never grades it — whatever consumes
 * the trace decides what a given pick means pedagogically.
 */
export function ExplanationCards({
  label,
  options,
  selectedId,
  onSelect,
  disabled = false,
  onTrace,
  className,
}: ExplanationCardsProps) {
  const reduceMotion = useReducedMotion();
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  const select = (id: string) => {
    if (disabled) return;
    onSelect(id);
    onTrace?.({ action: "select", target: id });
  };

  const onKeyDown = (e: React.KeyboardEvent, index: number) => {
    if (disabled) return;
    let nextIndex: number | null = null;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") nextIndex = (index + 1) % options.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp")
      nextIndex = (index - 1 + options.length) % options.length;
    else if (e.key === "Home") nextIndex = 0;
    else if (e.key === "End") nextIndex = options.length - 1;

    if (nextIndex !== null) {
      e.preventDefault();
      const next = options[nextIndex];
      refs.current[nextIndex]?.focus();
      select(next.id);
    }
  };

  const activeIndex = Math.max(
    0,
    options.findIndex((o) => o.id === selectedId),
  );

  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={cn("grid grid-cols-1 gap-3 sm:grid-cols-3", className)}
    >
      {options.map((option, index) => {
        const selected = option.id === selectedId;
        return (
          <motion.button
            key={option.id}
            ref={(el) => {
              refs.current[index] = el;
            }}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={disabled ? -1 : index === activeIndex ? 0 : -1}
            disabled={disabled}
            onClick={() => select(option.id)}
            onKeyDown={(e) => onKeyDown(e, index)}
            whileHover={disabled || reduceMotion ? undefined : { y: -3, transition: spring.settle }}
            whileTap={
              disabled || reduceMotion ? { opacity: 0.85 } : { scale: 0.97, transition: spring.pop }
            }
            className={cn(
              "flex min-h-touch-lg flex-col items-center justify-center gap-2 rounded-2xl border-2 bg-surface-raised",
              "px-5 py-6 text-center shadow-soft transition-colors focus-visible:outline-none",
              "disabled:cursor-not-allowed disabled:opacity-50",
              selected ? "border-moss-600 bg-moss-200/40" : "border-sand-300 hover:border-sand-500",
            )}
          >
            {option.render}
            {option.icon && <span className="text-4xl leading-none">{option.icon}</span>}
            <span className="font-sans text-base font-bold text-ink">{option.label}</span>
          </motion.button>
        );
      })}
    </div>
  );
}
