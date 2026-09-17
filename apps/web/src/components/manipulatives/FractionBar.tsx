"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/cn";
import { spring } from "@/design/tokens";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { useSnapDrag } from "@/components/manipulatives/useSnapDrag";
import { clamp } from "@/components/manipulatives/snapping";
import type { TraceEvent } from "@/components/manipulatives/useManipulativeTrace";

export type FractionBarTone = "moss" | "sky" | "apricot" | "clay";

const fillClass: Record<FractionBarTone, string> = {
  moss: "fill-moss-500",
  sky: "fill-sky-500",
  apricot: "fill-apricot-500",
  clay: "fill-clay-600",
};

const handleClass: Record<FractionBarTone, string> = {
  moss: "fill-moss-600 stroke-moss-700",
  sky: "fill-sky-600 stroke-sky-700",
  apricot: "fill-apricot-600 stroke-apricot-700",
  clay: "fill-clay-600 stroke-clay-700",
};

export interface FractionBarProps {
  /** Accessible name for the bar as a whole (e.g. "One quarter bar"). */
  label: string;
  numerator: number;
  denominator: number;
  onNumeratorChange?: (numerator: number) => void;
  /** Supplying this renders a second, smaller drag handle that repartitions the bar. */
  onDenominatorChange?: (denominator: number) => void;
  minDenominator?: number;
  maxDenominator?: number;
  /** Another bar's fill ratio (0..1) to visually align against — draws a guide line and pulses when matched. */
  alignTo?: number | null;
  alignTolerance?: number;
  onAlign?: () => void;
  tone?: FractionBarTone;
  disabled?: boolean;
  width?: number;
  /** Reports every interaction; feed this `useManipulativeTrace().record`. */
  onTrace?: (event: TraceEvent) => void;
  className?: string;
}

const HANDLE_RADIUS = 16;
const BAR_HEIGHT = 64;
const PADDING = HANDLE_RADIUS + 4;

/**
 * A horizontal fraction bar the child partitions, drags, and aligns —
 * roadmap P13's primary "physically think with fractions" manipulative.
 * The filled boundary is an ARIA slider (drag, touch, and arrow-key
 * control all move the same value); an optional second handle repartitions
 * the bar into a different number of equal pieces. Every interaction is
 * reported via `onTrace`, verbatim — this component never decides whether
 * the resulting fraction is "the right answer."
 */
export function FractionBar({
  label,
  numerator,
  denominator,
  onNumeratorChange,
  onDenominatorChange,
  minDenominator = 1,
  maxDenominator = 12,
  alignTo = null,
  alignTolerance = 0.02,
  onAlign,
  tone = "moss",
  disabled = false,
  width = 480,
  onTrace,
  className,
}: FractionBarProps) {
  const reduceMotion = useReducedMotion();
  const trackRef = useRef<SVGSVGElement>(null);
  const partitionTrackRef = useRef<SVGSVGElement>(null);
  const [focusedHandle, setFocusedHandle] = useState<"fill" | "partition" | null>(null);
  const wasAligned = useRef(false);

  const safeDenominator = Math.max(1, denominator);
  const safeNumerator = clamp(numerator, 0, safeDenominator);
  const innerWidth = width - PADDING * 2;
  const ratio = safeNumerator / safeDenominator;

  const isAligned = alignTo != null && Math.abs(ratio - alignTo) <= alignTolerance;

  useEffect(() => {
    if (isAligned && !wasAligned.current) {
      onAlign?.();
      onTrace?.({ action: "align", target: `${safeNumerator}/${safeDenominator}` });
    }
    wasAligned.current = isAligned;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAligned]);

  const fillDrag = useSnapDrag({
    min: 0,
    max: safeDenominator,
    value: safeNumerator,
    disabled: disabled || !onNumeratorChange,
    trackRef,
    toRaw: (clientX, _clientY, rect) =>
      ((clientX - rect.left - PADDING) / innerWidth) * safeDenominator,
    onChange: (next) => onNumeratorChange?.(next),
    onDragStart: () => onTrace?.({ action: "drag_start", target: `numerator=${safeNumerator}` }),
    onSnap: (next) => onTrace?.({ action: "snap", target: `numerator=${next}` }),
    onDragEnd: (next) => onTrace?.({ action: "drag_end", target: `numerator=${next}` }),
    onKeyboardAdjust: (next) =>
      onTrace?.({ action: "keyboard_adjust", target: `numerator=${next}` }),
  });

  const partitionDrag = useSnapDrag({
    min: minDenominator,
    max: maxDenominator,
    value: safeDenominator,
    disabled: disabled || !onDenominatorChange,
    trackRef: partitionTrackRef,
    toRaw: (clientX, _clientY, rect) =>
      ((clientX - rect.left - PADDING) / innerWidth) * (maxDenominator - minDenominator) +
      minDenominator,
    onChange: (next) => onDenominatorChange?.(next),
    onDragStart: () =>
      onTrace?.({ action: "drag_start", target: `denominator=${safeDenominator}` }),
    onSnap: (next) => onTrace?.({ action: "partition_changed", target: `denominator=${next}` }),
    onDragEnd: (next) => onTrace?.({ action: "drag_end", target: `denominator=${next}` }),
    onKeyboardAdjust: (next) =>
      onTrace?.({ action: "partition_changed", target: `denominator=${next}` }),
  });

  const fillX = PADDING + ratio * innerWidth;
  const dividers = Array.from({ length: safeDenominator - 1 }, (_, i) => {
    const x = PADDING + ((i + 1) / safeDenominator) * innerWidth;
    return x;
  });

  return (
    <div className={cn("inline-flex flex-col gap-2", className)} style={{ width }}>
      {onDenominatorChange && (
        <svg
          ref={partitionTrackRef}
          width={width}
          height={28}
          viewBox={`0 0 ${width} 28`}
          role="slider"
          aria-label={`${label} — number of equal parts`}
          aria-orientation="horizontal"
          aria-valuemin={minDenominator}
          aria-valuemax={maxDenominator}
          aria-valuenow={safeDenominator}
          aria-valuetext={`${safeDenominator} equal parts`}
          aria-disabled={disabled || undefined}
          tabIndex={disabled ? -1 : 0}
          className="touch-none focus:outline-none"
          onPointerDown={partitionDrag.onPointerDown}
          onPointerMove={partitionDrag.onPointerMove}
          onPointerUp={partitionDrag.onPointerUp}
          onPointerCancel={partitionDrag.onPointerCancel}
          onKeyDown={partitionDrag.onKeyDown}
          onFocus={() => setFocusedHandle("partition")}
          onBlur={() => setFocusedHandle(null)}
        >
          <line
            x1={PADDING}
            y1={14}
            x2={width - PADDING}
            y2={14}
            className="stroke-sand-500"
            strokeWidth={3}
            strokeLinecap="round"
          />
          <motion.circle
            cx={
              PADDING +
              ((safeDenominator - minDenominator) / (maxDenominator - minDenominator || 1)) *
                innerWidth
            }
            cy={14}
            r={9}
            className={cn(handleClass[tone], "cursor-ew-resize")}
            strokeWidth={2}
            animate={
              reduceMotion
                ? undefined
                : {
                    scale: partitionDrag.dragging ? 1.15 : 1,
                  }
            }
            transition={spring.pop}
          />
          {focusedHandle === "partition" && (
            <circle
              cx={
                PADDING +
                ((safeDenominator - minDenominator) / (maxDenominator - minDenominator || 1)) *
                  innerWidth
              }
              cy={14}
              r={13}
              fill="none"
              className="stroke-sky-700"
              strokeWidth={2}
            />
          )}
        </svg>
      )}

      <motion.svg
        ref={trackRef}
        width={width}
        height={BAR_HEIGHT}
        viewBox={`0 0 ${width} ${BAR_HEIGHT}`}
        role="group"
        aria-label={label}
        className="touch-none"
        animate={isAligned && !reduceMotion ? { scale: [1, 1.02, 1] } : { scale: 1 }}
        transition={spring.settle}
      >
        <rect
          x={PADDING}
          y={0}
          width={innerWidth}
          height={BAR_HEIGHT}
          rx={12}
          className={cn("fill-surface stroke-sand-500/60", isAligned && "stroke-moss-600")}
          strokeWidth={isAligned ? 3 : 2}
        />

        <motion.rect
          x={PADDING}
          y={0}
          height={BAR_HEIGHT}
          rx={12}
          className={fillClass[tone]}
          initial={false}
          animate={{ width: Math.max(0, ratio * innerWidth) }}
          transition={reduceMotion ? { duration: 0 } : spring.settle}
        />

        {dividers.map((x, i) => (
          <line
            key={i}
            x1={x}
            y1={4}
            x2={x}
            y2={BAR_HEIGHT - 4}
            className="stroke-sand-500/70"
            strokeWidth={2}
          />
        ))}

        {alignTo != null && (
          <line
            x1={PADDING + alignTo * innerWidth}
            y1={-6}
            x2={PADDING + alignTo * innerWidth}
            y2={BAR_HEIGHT + 6}
            className={cn("stroke-sky-700", isAligned ? "opacity-100" : "opacity-50")}
            strokeWidth={2}
            strokeDasharray="4 4"
          />
        )}

        <g
          role="slider"
          aria-label={`${label} — filled amount`}
          aria-orientation="horizontal"
          aria-valuemin={0}
          aria-valuemax={safeDenominator}
          aria-valuenow={safeNumerator}
          aria-valuetext={`${safeNumerator} of ${safeDenominator} parts filled`}
          aria-disabled={disabled || undefined}
          tabIndex={disabled ? -1 : 0}
          className="cursor-grab focus:outline-none active:cursor-grabbing"
          onPointerDown={fillDrag.onPointerDown}
          onPointerMove={fillDrag.onPointerMove}
          onPointerUp={fillDrag.onPointerUp}
          onPointerCancel={fillDrag.onPointerCancel}
          onKeyDown={fillDrag.onKeyDown}
          onFocus={() => setFocusedHandle("fill")}
          onBlur={() => setFocusedHandle(null)}
        >
          {focusedHandle === "fill" && (
            <circle
              cx={fillX}
              cy={BAR_HEIGHT / 2}
              r={HANDLE_RADIUS + 4}
              fill="none"
              className="stroke-sky-700"
              strokeWidth={2}
            />
          )}
          <motion.circle
            cx={fillX}
            cy={BAR_HEIGHT / 2}
            r={HANDLE_RADIUS}
            className={handleClass[tone]}
            strokeWidth={3}
            animate={reduceMotion ? undefined : { scale: fillDrag.dragging ? 1.12 : 1 }}
            transition={spring.pop}
          />
        </g>
      </motion.svg>
    </div>
  );
}
