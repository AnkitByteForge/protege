"use client";

import type { ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { spring } from "@/design/tokens";
import { useReducedMotion } from "@/hooks/useReducedMotion";

/**
 * The one place a "scene swap" is implemented. Content cross-fades and
 * rises into place with `settle` rather than unmounting/remounting a page —
 * this is what makes the child world feel continuous instead of like
 * eighteen separate screens (roadmap P15's whole premise, laid down here
 * so nothing downstream has to re-invent it).
 */
export function SceneTransition({ sceneKey, children }: { sceneKey: string; children: ReactNode }) {
  const reduceMotion = useReducedMotion();

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={sceneKey}
        initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 18, scale: 0.985 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -12, scale: 0.99 }}
        transition={spring.settle}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
