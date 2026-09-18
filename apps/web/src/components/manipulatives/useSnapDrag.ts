"use client";

import { useCallback, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent, KeyboardEvent as ReactKeyboardEvent } from "react";
import { snapWithHysteresis, stepFromKey } from "@/components/manipulatives/snapping";

export interface UseSnapDragOptions {
  min: number;
  max: number;
  value: number;
  disabled?: boolean;
  /** Keyboard step size (arrow keys); PageUp/PageDown move by 2x this. */
  step?: number;
  releaseThreshold?: number;
  /** The element pointer position is measured against (the track, not the handle). */
  trackRef: React.RefObject<Element | null>;
  /** Converts a pointer position + the track's rect into a raw value in `[min, max]`. */
  toRaw: (clientX: number, clientY: number, rect: DOMRect) => number;
  onChange: (next: number) => void;
  onDragStart?: () => void;
  /** Fired each time the snapped value changes mid-drag (not on every pointer move). */
  onSnap?: (next: number) => void;
  onDragEnd?: (next: number) => void;
  onKeyboardAdjust?: (next: number) => void;
}

export interface SnapDragHandle {
  dragging: boolean;
  onPointerDown: (e: ReactPointerEvent) => void;
  onPointerMove: (e: ReactPointerEvent) => void;
  onPointerUp: (e: ReactPointerEvent) => void;
  onPointerCancel: (e: ReactPointerEvent) => void;
  onKeyDown: (e: ReactKeyboardEvent) => void;
}

/**
 * Pointer-drag-with-hysteresis-snapping plus first-class keyboard control,
 * shared by every draggable manipulative handle (FractionBar's fill and
 * partition handles, NumberLine's markers). One implementation means drag
 * feel, snapping, and keyboard behaviour are identical everywhere in the
 * product rather than subtly re-invented per component.
 *
 * An interrupted drag (`pointercancel` — e.g. a touch scroll takes over, or
 * the OS shows a context menu mid-drag) always reverts to the value the
 * drag started from: a manipulative must never strand the child in a
 * half-committed state.
 */
export function useSnapDrag({
  min,
  max,
  value,
  disabled,
  step = 1,
  releaseThreshold,
  trackRef,
  toRaw,
  onChange,
  onDragStart,
  onSnap,
  onDragEnd,
  onKeyboardAdjust,
}: UseSnapDragOptions): SnapDragHandle {
  const [dragging, setDragging] = useState(false);
  const lastSnapped = useRef(value);
  const startValueRef = useRef(value);

  const onPointerDown = useCallback(
    (e: ReactPointerEvent) => {
      if (disabled) return;
      e.currentTarget.setPointerCapture?.(e.pointerId);
      lastSnapped.current = value;
      startValueRef.current = value;
      setDragging(true);
      onDragStart?.();
    },
    [disabled, value, onDragStart],
  );

  const onPointerMove = useCallback(
    (e: ReactPointerEvent) => {
      if (!dragging || disabled || !trackRef.current) return;
      const rect = trackRef.current.getBoundingClientRect();
      const raw = toRaw(e.clientX, e.clientY, rect);
      const snapped = snapWithHysteresis(raw, lastSnapped.current, { min, max, releaseThreshold });
      if (snapped !== lastSnapped.current) {
        lastSnapped.current = snapped;
        onChange(snapped);
        onSnap?.(snapped);
      }
    },
    [dragging, disabled, trackRef, toRaw, min, max, releaseThreshold, onChange, onSnap],
  );

  const onPointerUp = useCallback(
    (e: ReactPointerEvent) => {
      if (!dragging) return;
      e.currentTarget.releasePointerCapture?.(e.pointerId);
      setDragging(false);
      onDragEnd?.(lastSnapped.current);
    },
    [dragging, onDragEnd],
  );

  const onPointerCancel = useCallback(() => {
    if (!dragging) return;
    setDragging(false);
    onChange(startValueRef.current);
    onDragEnd?.(startValueRef.current);
  }, [dragging, onChange, onDragEnd]);

  const onKeyDown = useCallback(
    (e: ReactKeyboardEvent) => {
      if (disabled) return;
      const next = stepFromKey(e.key, value, min, max, step);
      if (next !== null && next !== value) {
        e.preventDefault();
        lastSnapped.current = next;
        onChange(next);
        onKeyboardAdjust?.(next);
      }
    },
    [disabled, value, min, max, step, onChange, onKeyboardAdjust],
  );

  return { dragging, onPointerDown, onPointerMove, onPointerUp, onPointerCancel, onKeyDown };
}
