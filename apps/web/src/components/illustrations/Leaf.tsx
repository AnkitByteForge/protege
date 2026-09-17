import type { SVGProps } from "react";

/** A single rounded leaf glyph — hand-drawn shape, not a stock icon-font glyph. */
export function Leaf(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden {...props}>
      <path
        d="M16 4C9 6 5 12 5 19c0 4.5 3.4 8 8 8h1c7 0 13-6 13-14 0-3-1-6-2-8-3 1-7 1-9-1Z"
        fill="currentColor"
      />
      <path
        d="M11 27c2-6 5-11 10-15"
        stroke="rgba(59,47,36,0.25)"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}
