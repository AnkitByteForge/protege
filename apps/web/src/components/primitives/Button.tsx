"use client";

import { forwardRef } from "react";
import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/cn";
import { spring } from "@/design/tokens";
import { useReducedMotion } from "@/hooks/useReducedMotion";

type Variant = "primary" | "secondary" | "ghost";
type Tone = "moss" | "sky" | "apricot" | "clay";

const toneClass: Record<Tone, { primary: string; secondary: string; ghost: string }> = {
  moss: {
    primary: "bg-moss-600 text-white hover:bg-moss-700",
    secondary: "border-moss-600 text-moss-700 hover:bg-moss-200/60",
    ghost: "text-moss-700 hover:bg-moss-200/50",
  },
  sky: {
    primary: "bg-sky-700 text-white hover:bg-sky-700/90",
    secondary: "border-sky-700 text-sky-700 hover:bg-sky-200/60",
    ghost: "text-sky-700 hover:bg-sky-200/50",
  },
  apricot: {
    primary: "bg-apricot-700 text-white hover:bg-apricot-700/90",
    secondary: "border-apricot-700 text-apricot-700 hover:bg-apricot-200/60",
    ghost: "text-apricot-700 hover:bg-apricot-200/50",
  },
  clay: {
    primary: "bg-clay-700 text-white hover:bg-clay-700/90",
    secondary: "border-clay-700 text-clay-700 hover:bg-clay-200/60",
    ghost: "text-clay-700 hover:bg-clay-200/50",
  },
};

type NativeButtonProps = Omit<
  ComponentPropsWithoutRef<"button">,
  "children" | "onDrag" | "onDragStart" | "onDragEnd" | "onAnimationStart"
>;

export interface ButtonProps extends NativeButtonProps {
  variant?: Variant;
  tone?: Tone;
  size?: "md" | "lg";
  children: ReactNode;
  icon?: ReactNode;
}

/**
 * The one interactive-button primitive. `variant="primary"` is a filled,
 * tactile call to action; `secondary` is outlined; `ghost` is text-only for
 * low-emphasis chrome. Press/hover feedback uses the `pop`/`settle` spring
 * presets and collapses to a plain opacity change under reduced motion.
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "primary",
    tone = "moss",
    size = "lg",
    className,
    children,
    icon,
    disabled,
    ...props
  },
  ref,
) {
  const reduceMotion = useReducedMotion();
  const tones = toneClass[tone];

  const base = cn(
    "inline-flex items-center justify-center gap-2 rounded-2xl font-sans font-bold",
    "transition-colors focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50",
    size === "lg" ? "h-touch-lg min-w-touch-lg px-7 text-lg" : "h-touch min-w-touch px-5 text-base",
  );

  const variantClass =
    variant === "primary"
      ? cn(tones.primary, "shadow-soft")
      : variant === "secondary"
        ? cn("border-2 bg-surface-raised", tones.secondary)
        : cn("bg-transparent", tones.ghost);

  return (
    <motion.button
      ref={ref}
      className={cn(base, variantClass, className)}
      disabled={disabled}
      whileHover={disabled || reduceMotion ? undefined : { y: -2, transition: spring.settle }}
      whileTap={
        disabled || reduceMotion ? { opacity: 0.85 } : { scale: 0.96, transition: spring.pop }
      }
      {...props}
    >
      {icon}
      {children}
    </motion.button>
  );
});

/** Preconfigured large, filled, moss-toned call to action — the child's "go" button. */
export const PrimaryAction = forwardRef<HTMLButtonElement, Omit<ButtonProps, "variant">>(
  function PrimaryAction(props, ref) {
    return <Button ref={ref} variant="primary" size="lg" {...props} />;
  },
);

/** Outlined, lower-emphasis counterpart to `PrimaryAction`. */
export const SecondaryAction = forwardRef<HTMLButtonElement, Omit<ButtonProps, "variant">>(
  function SecondaryAction(props, ref) {
    return <Button ref={ref} variant="secondary" size="lg" {...props} />;
  },
);
