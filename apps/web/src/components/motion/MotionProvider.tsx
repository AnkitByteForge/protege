"use client";

import type { ReactNode } from "react";
import { MotionConfig } from "framer-motion";

/**
 * Root-level motion configuration. `reducedMotion="user"` makes Framer
 * Motion honour `prefers-reduced-motion` for every animation in the tree
 * automatically; primitives additionally check `useReducedMotion()` where
 * they need to swap an animation for a discrete state change rather than
 * just shortening it.
 */
export function MotionProvider({ children }: { children: ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
