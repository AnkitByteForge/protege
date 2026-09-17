"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/cn";
import { spring } from "@/design/tokens";
import { useReducedMotion } from "@/hooks/useReducedMotion";

export interface SpeechBubbleProps {
  /** Which edge the tail points from — toward whichever character is speaking. */
  tailFrom?: "left" | "right" | "bottom";
  /** Plain text to reveal with a gentle typewriter effect (timed to future TTS). */
  text?: string;
  /** Rich content — used instead of `text` when the bubble needs more than plain text. */
  children?: ReactNode;
  className?: string;
}

/**
 * A speech-bubble *shell*: no character is implied here. Sprout (or any
 * future speaker) renders inside it. The typewriter reveal is deliberately
 * gentle and skips straight to full text under reduced motion.
 */
export function SpeechBubble({ tailFrom = "left", text, children, className }: SpeechBubbleProps) {
  const reduceMotion = useReducedMotion();
  const [revealed, setRevealed] = useState(reduceMotion || !text ? (text?.length ?? 0) : 0);

  useEffect(() => {
    if (!text || reduceMotion) {
      setRevealed(text?.length ?? 0);
      return;
    }
    setRevealed(0);
    const id = setInterval(() => {
      setRevealed((n) => (n >= text.length ? n : n + 1));
    }, 22);
    return () => clearInterval(id);
  }, [text, reduceMotion]);

  return (
    <motion.div
      role="status"
      initial={reduceMotion ? undefined : { opacity: 0, scale: 0.92, y: 8 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={spring.settle}
      className={cn(
        "relative max-w-md rounded-2xl bg-surface-raised px-5 py-4 text-ink shadow-soft-lg",
        tailFrom === "left" && "ml-4",
        tailFrom === "right" && "mr-4",
        className,
      )}
    >
      {text ? (
        <p className="font-sans text-lg leading-relaxed font-semibold">
          {text.slice(0, revealed)}
          {revealed < text.length && <span className="animate-pulse text-ink-soft">▍</span>}
        </p>
      ) : (
        children
      )}

      {tailFrom !== "bottom" && (
        <span
          aria-hidden
          className={cn(
            "absolute top-6 h-4 w-4 rotate-45 bg-surface-raised",
            tailFrom === "left" && "-left-1.5",
            tailFrom === "right" && "-right-1.5",
          )}
        />
      )}
      {tailFrom === "bottom" && (
        <span
          aria-hidden
          className="absolute -bottom-1.5 left-8 h-4 w-4 rotate-45 bg-surface-raised"
        />
      )}
    </motion.div>
  );
}
