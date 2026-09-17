"use client";

import { useReducedMotion as useFramerReducedMotion } from "framer-motion";

/**
 * Thin wrapper around Framer Motion's own `useReducedMotion` (which tracks
 * `prefers-reduced-motion` live via a media query listener). Centralised
 * here so every primitive imports from `@/hooks` rather than reaching into
 * the motion library directly, and so an app-level override could be added
 * later without touching call sites.
 */
export function useReducedMotion(): boolean {
  return useFramerReducedMotion() ?? false;
}
