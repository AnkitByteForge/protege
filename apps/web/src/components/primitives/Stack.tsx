import type { ElementType, ReactNode } from "react";
import { cn } from "@/lib/cn";

type Gap = "xs" | "sm" | "md" | "lg" | "xl";

const gapClass: Record<Gap, string> = {
  xs: "gap-2",
  sm: "gap-3",
  md: "gap-5",
  lg: "gap-8",
  xl: "gap-12",
};

interface FlowProps {
  as?: ElementType;
  gap?: Gap;
  align?: "start" | "center" | "end" | "stretch";
  children: ReactNode;
  className?: string;
}

/** Vertical rhythm primitive — the spacing scale, applied consistently. */
export function Stack({
  as: Tag = "div",
  gap = "md",
  align = "stretch",
  children,
  className,
}: FlowProps) {
  return (
    <Tag
      className={cn(
        "flex flex-col",
        gapClass[gap],
        align === "start" && "items-start",
        align === "center" && "items-center",
        align === "end" && "items-end",
        align === "stretch" && "items-stretch",
        className,
      )}
    >
      {children}
    </Tag>
  );
}

/** Horizontal counterpart to `Stack`, wrapping by default. */
export function Inline({
  as: Tag = "div",
  gap = "md",
  align = "center",
  children,
  className,
}: FlowProps) {
  return (
    <Tag
      className={cn(
        "flex flex-wrap",
        gapClass[gap],
        align === "start" && "items-start",
        align === "center" && "items-center",
        align === "end" && "items-end",
        align === "stretch" && "items-stretch",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
