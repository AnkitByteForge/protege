"use client";

import { useId, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { spring } from "@/design/tokens";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { Text } from "@/components/primitives/Typography";
import {
  describeEvidenceNode,
  formatEvidenceTime,
  kindLabel,
  type EvidenceNode,
} from "./evidenceDescription";

/**
 * The clickable evidence tree (roadmap P20: "clickable evidence tree ...
 * this expansion is the most persuasive five seconds in the demo"). Closed
 * by default — a parent who trusts the claim never has to look; a parent
 * who wants proof gets the real, individually-dated evidence rows behind
 * it, each one a real fact P9 recorded, not a summary invented for display.
 */
export function EvidenceTree({
  nodes,
  triggerLabel = "See evidence",
  className,
}: {
  nodes: EvidenceNode[];
  triggerLabel?: string;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const reduceMotion = useReducedMotion();
  const panelId = useId();

  if (nodes.length === 0) return null;

  return (
    <div className={className}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1 font-sans text-sm font-bold text-sky-700 hover:text-sky-700/80 focus-visible:outline-none"
      >
        <motion.span
          aria-hidden
          animate={{ rotate: open ? 90 : 0 }}
          transition={reduceMotion ? undefined : spring.pop}
          className="inline-block"
        >
          ▸
        </motion.span>
        {open ? "Hide evidence" : triggerLabel}
        <span className="text-ink-soft">
          ({nodes.length} {nodes.length === 1 ? "moment" : "moments"})
        </span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            id={panelId}
            key="panel"
            initial={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            transition={spring.settle}
            className="overflow-hidden"
          >
            <ol className="mt-2 flex flex-col gap-2 border-l-2 border-sand-300 pl-4">
              {nodes.map((node) => {
                const time = formatEvidenceTime(node.occurred_at);
                return (
                  <li key={node.evidence_id}>
                    <Text className="text-sm font-bold text-ink">{kindLabel(node.kind)}</Text>
                    <Text muted className="text-sm">
                      {describeEvidenceNode(node)}
                      {time && <span className="text-ink-soft"> · {time}</span>}
                    </Text>
                  </li>
                );
              })}
            </ol>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
