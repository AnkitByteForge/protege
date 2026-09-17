/**
 * PROTÉGÉ design tokens — the single source of truth for the visual system.
 *
 * These values are consumed two ways:
 *   1. `src/app/globals.css` mirrors the color/radius/font values into a
 *      Tailwind v4 `@theme` block (Tailwind v4 is CSS-first — it cannot read
 *      a `.ts` module directly), so keep the two in sync when a value changes.
 *   2. Runtime code (motion springs, sound tokens, anything that needs the
 *      literal value in JS rather than a class name) imports straight from
 *      here.
 *
 * Palette rule: warm, never red for a wrong answer. "Not yet" states use
 * `clay`, paired with the `wobble` spring and a shape change — never color
 * alone. Every text/background pair below was checked against WCAG AA
 * (>= 4.5:1) before being written down; see the "-700"/"-600" note per hue.
 */

export const color = {
  ink: "#3B2F24",
  inkSoft: "#6B5C4C",
  paper: "#FBF6EC",
  surface: "#F3EBDA",
  surfaceRaised: "#FFFDF8",

  moss: {
    200: "#CFE6D3",
    500: "#6FAE7E",
    600: "#3F7A4E",
    700: "#2F6B45",
  },
  sky: {
    200: "#CDE7F0",
    500: "#6FB8CF",
    600: "#3B87A8",
    700: "#2A6E8C",
  },
  apricot: {
    200: "#F6D9BD",
    500: "#E8965A",
    600: "#D97A3F",
    700: "#B85C2E",
  },
  sand: {
    200: "#F3EBDA",
    300: "#EFE0C4",
    500: "#C9AF83",
  },
  /**
   * "Not yet" / try-again feedback. Deliberately warm brown-amber, never
   * red — a wrong answer is a step in the story, not an alarm.
   */
  clay: {
    200: "#E9D3B8",
    600: "#A66B34",
    700: "#8A5A2B",
  },
} as const;

/** 600-tones are for decorative/icon use only (they clear 3:1, not 4.5:1). */
export const textSafeTone = {
  moss: color.moss[600],
  sky: color.sky[700],
  apricot: color.apricot[700],
  clay: color.clay[700],
} as const;

export const radius = {
  sm: "0.5rem",
  md: "0.75rem",
  lg: "1.25rem",
  xl: "1.75rem",
  "2xl": "2.5rem",
  full: "9999px",
} as const;

export const spacing = {
  touch: "3rem",
  touchLg: "3.75rem",
} as const;

export const fontFamily = {
  display: "var(--font-display)",
  body: "var(--font-body)",
} as const;

export const duration = {
  fast: 120,
  base: 220,
  slow: 420,
  ambient: 6000,
} as const;

/**
 * Motion spring presets — the four named in the roadmap. Everything
 * interactive in the UI should reach for one of these rather than a
 * one-off transition, so the whole world moves with one consistent
 * "hand." Framer Motion `Transition` shape.
 */
export const spring = {
  /** Calm arrival: scene/panel entrances, layout shifts, anything that should feel settled rather than snappy. */
  settle: { type: "spring", stiffness: 210, damping: 26, mass: 1 } as const,
  /** Snappy press/tap feedback, reward beats — the "tactile" feel. */
  pop: { type: "spring", stiffness: 420, damping: 18, mass: 0.7 } as const,
  /** Bouncy, oscillating — a gentle "try again" nudge. Never paired with red. */
  wobble: { type: "spring", stiffness: 300, damping: 8, mass: 1 } as const,
  /** Slow, soft, ambient — idle sway, parallax, breathing motion. */
  drift: { type: "spring", stiffness: 40, damping: 12, mass: 1.6 } as const,
} as const;

export type SpringPreset = keyof typeof spring;

/**
 * Sound tokens — named, versioned identifiers for future ambient/feedback
 * sound. Infrastructure only: no audio ships in P12, and the provider
 * defaults to `enabled: false`. See `src/hooks/useSound.ts`.
 */
export const soundToken = {
  tap: "tap",
  pop: "pop",
  settle: "settle",
  leafUnfurl: "leaf-unfurl",
  chime: "chime",
} as const;

export type SoundToken = (typeof soundToken)[keyof typeof soundToken];
