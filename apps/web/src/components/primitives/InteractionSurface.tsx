import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * The bounded "table" future manipulatives (FractionBar, NumberLine,
 * AreaModel — roadmap P13) will render onto. P12 ships the surface only:
 * an inset, textured stage with a stable focus/keyboard container contract.
 * `role="group"` plus a required `label` gives every future manipulative a
 * consistent accessible name without each one re-deriving it.
 */
export function InteractionSurface({
  label,
  children,
  className,
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className={cn(
        "relative min-h-48 rounded-2xl border-2 border-dashed border-sand-500/50 bg-surface/70",
        "shadow-[inset_0_2px_10px_rgba(59,47,36,0.06)]",
        "flex items-center justify-center p-6",
        className,
      )}
    >
      {children}
    </div>
  );
}
