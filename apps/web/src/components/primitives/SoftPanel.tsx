import type { ElementType, ReactNode } from "react";
import { cn } from "@/lib/cn";

type Elevation = "flat" | "raised" | "floating";

const elevationClass: Record<Elevation, string> = {
  flat: "bg-surface shadow-none",
  raised: "bg-surface-raised shadow-soft",
  floating: "bg-surface-raised shadow-soft-lg",
};

/**
 * The base "tactile card" surface — deliberately not glassy or translucent.
 * A soft, opaque, warm-tinted panel with generous radius and a warm
 * (never harsh-black) shadow. Everything from a choice card to the gallery
 * section wrapper sits on top of this.
 */
export function SoftPanel({
  as: Tag = "div",
  elevation = "raised",
  padded = true,
  children,
  className,
}: {
  as?: ElementType;
  elevation?: Elevation;
  padded?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Tag
      className={cn(
        "rounded-2xl border border-sand-300/60",
        elevationClass[elevation],
        padded && "p-6",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
