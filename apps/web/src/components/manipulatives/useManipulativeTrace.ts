"use client";

import { useCallback, useRef, useState } from "react";
import type { ManipulativeAction } from "@/generated/contracts/ManipulativeExplanation";

export type { ManipulativeAction };

/**
 * What a manipulative component reports when something happens to it. This
 * is deliberately smaller than `ManipulativeAction` — components never
 * stamp their own `t`, so the trace stays faithful to a single shared
 * clock (see `useManipulativeTrace`) rather than each component's own
 * mount time.
 */
export interface TraceEvent {
  action: string;
  target?: string | null;
  targets?: string[] | null;
}

export interface ManipulativeTraceApi {
  /** Every event recorded so far, in order, `{t, action, target(s)}`. */
  trace: ManipulativeAction[];
  /** Passed to a manipulative's `onTrace` prop. */
  record: (event: TraceEvent) => void;
  /** Clears the trace and restarts the clock — call when a new item is presented. */
  reset: () => void;
}

function now(): number {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

/**
 * The shared trace emitter every manipulative funnels its interactions
 * through (roadmap P13). A manipulative component never decides whether
 * what the child did was "correct" — it only ever reports what happened.
 * This hook's only job is to stamp that report with `t` (seconds since the
 * item was presented, i.e. since this hook mounted) and accumulate it into
 * the `{t, action, target(s)}[]` shape the Diagnostician consumes,
 * identical to the generated `ManipulativeAction` contract.
 */
export function useManipulativeTrace(): ManipulativeTraceApi {
  const startRef = useRef(now());
  const [trace, setTrace] = useState<ManipulativeAction[]>([]);

  const record = useCallback((event: TraceEvent) => {
    const t = Math.round(((now() - startRef.current) / 1000) * 1000) / 1000;
    const entry: ManipulativeAction = {
      t,
      action: event.action,
      target: event.target ?? null,
      targets: event.targets ?? null,
    };
    setTrace((prev) => [...prev, entry]);
  }, []);

  const reset = useCallback(() => {
    startRef.current = now();
    setTrace([]);
  }, []);

  return { trace, record, reset };
}
