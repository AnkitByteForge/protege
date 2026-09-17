"use client";

import { useEffect, useRef, useState, type RefObject } from "react";
import { useReducedMotion } from "@/hooks/useReducedMotion";

export interface SproutIdleOptions {
  containerRef: RefObject<HTMLElement | null>;
  /** Disable all idle behaviour — e.g. while Sprout is mid entrance/exit. */
  enabled?: boolean;
}

export interface SproutIdleState {
  /** Transient eyes-closed state, on a natural (randomised) Poisson-ish timer. */
  blink: boolean;
  /** Small, clamped pupil offset toward the pointer — sampled occasionally, not tracked continuously. */
  lookOffset: { x: number; y: number };
  /** Whether the calm breathing sway should run. */
  breathe: boolean;
}

const BLINK_MIN_GAP_MS = 2600;
const BLINK_MAX_GAP_MS = 6000;
const BLINK_CLOSED_MS = 140;
const LOOK_SAMPLE_MIN_MS = 900;
const LOOK_SAMPLE_JITTER_MS = 500;
const LOOK_MAX_DISTANCE_PX = 600;

/**
 * "Idle life" (roadmap P14): a natural blink, a gentle breathing sway, and
 * an occasional glance toward the pointer — never a constant, attention-
 * grabbing tic. Everything here is disabled under reduced motion, and
 * fully disabled when `enabled` is false (e.g. mid entrance/exit).
 */
export function useSproutIdle({
  containerRef,
  enabled = true,
}: SproutIdleOptions): SproutIdleState {
  const reduceMotion = useReducedMotion();
  const active = enabled && !reduceMotion;
  const [blink, setBlink] = useState(false);
  const [lookOffset, setLookOffset] = useState({ x: 0, y: 0 });
  const pointerRef = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (!active) {
      setBlink(false);
      return;
    }
    let closeTimeout: ReturnType<typeof setTimeout>;
    let openTimeout: ReturnType<typeof setTimeout>;
    let cancelled = false;

    function scheduleBlink() {
      const gap = BLINK_MIN_GAP_MS + Math.random() * (BLINK_MAX_GAP_MS - BLINK_MIN_GAP_MS);
      closeTimeout = setTimeout(() => {
        if (cancelled) return;
        setBlink(true);
        openTimeout = setTimeout(() => {
          if (cancelled) return;
          setBlink(false);
          scheduleBlink();
        }, BLINK_CLOSED_MS);
      }, gap);
    }

    scheduleBlink();
    return () => {
      cancelled = true;
      clearTimeout(closeTimeout);
      clearTimeout(openTimeout);
    };
  }, [active]);

  useEffect(() => {
    if (!active) {
      setLookOffset({ x: 0, y: 0 });
      return;
    }

    function onPointerMove(event: PointerEvent) {
      pointerRef.current = { x: event.clientX, y: event.clientY };
    }
    window.addEventListener("pointermove", onPointerMove);

    let cancelled = false;
    let sampleTimeout: ReturnType<typeof setTimeout>;

    function sample() {
      const el = containerRef.current;
      const pointer = pointerRef.current;
      if (!el || !pointer) {
        setLookOffset({ x: 0, y: 0 });
      } else {
        const rect = el.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const dx = pointer.x - cx;
        const dy = pointer.y - cy;
        if (Math.hypot(dx, dy) > LOOK_MAX_DISTANCE_PX) {
          setLookOffset({ x: 0, y: 0 });
        } else {
          setLookOffset({
            x: Math.max(-3, Math.min(3, dx / 80)),
            y: Math.max(-2, Math.min(2, dy / 100)),
          });
        }
      }
      if (!cancelled) {
        sampleTimeout = setTimeout(
          sample,
          LOOK_SAMPLE_MIN_MS + Math.random() * LOOK_SAMPLE_JITTER_MS,
        );
      }
    }

    sampleTimeout = setTimeout(sample, LOOK_SAMPLE_MIN_MS);
    return () => {
      cancelled = true;
      clearTimeout(sampleTimeout);
      window.removeEventListener("pointermove", onPointerMove);
    };
  }, [active, containerRef]);

  return { blink, lookOffset, breathe: active };
}
