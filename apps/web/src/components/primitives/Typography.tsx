import type { ElementType, ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Typography primitives. `Display`/`Heading` use the rounded display face
 * (`--font-display`, Baloo 2); `Text`/`Eyebrow` use the rounded body face
 * (`--font-sans`, Nunito). Both were chosen for high x-height and soft
 * terminals — friendly without tipping into clip-art.
 */

interface TypographyProps {
  as?: ElementType;
  id?: string;
  children: ReactNode;
  className?: string;
}

export function Display({ as: Tag = "h1", id, children, className }: TypographyProps) {
  return (
    <Tag
      id={id}
      className={cn(
        "font-display text-4xl leading-[1.1] font-extrabold tracking-tight text-ink sm:text-5xl",
        className,
      )}
    >
      {children}
    </Tag>
  );
}

export function Heading({ as: Tag = "h2", id, children, className }: TypographyProps) {
  return (
    <Tag
      id={id}
      className={cn(
        "font-display text-2xl leading-tight font-bold text-ink sm:text-3xl",
        className,
      )}
    >
      {children}
    </Tag>
  );
}

export function Subheading({ as: Tag = "h3", id, children, className }: TypographyProps) {
  return (
    <Tag
      id={id}
      className={cn("font-display text-lg leading-snug font-bold text-ink sm:text-xl", className)}
    >
      {children}
    </Tag>
  );
}

export function Text({
  as: Tag = "p",
  id,
  muted = false,
  children,
  className,
}: TypographyProps & { muted?: boolean }) {
  return (
    <Tag
      id={id}
      className={cn(
        "font-sans text-base leading-relaxed",
        muted ? "text-ink-soft" : "text-ink",
        className,
      )}
    >
      {children}
    </Tag>
  );
}

export function Eyebrow({ id, children, className }: Omit<TypographyProps, "as">) {
  return (
    <p
      id={id}
      className={cn(
        "font-sans text-xs font-bold tracking-[0.14em] text-ink-soft uppercase",
        className,
      )}
    >
      {children}
    </p>
  );
}
