"use client";

import { useEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/cn";
import { spring } from "@/design/tokens";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { useSnapDrag } from "@/components/manipulatives/useSnapDrag";
import { clamp } from "@/components/manipulatives/snapping";
import type { TraceEvent } from "@/components/manipulatives/useManipulativeTrace";
import type { FractionBarTone } from "@/components/manipulatives/FractionBar";

export interface NumberLineMarker {
  id: string;
  value: number;
  /** Accessible + visible label, e.g. "1/4". Never a raw decimal or percentage. */
  label: string;
  tone?: FractionBarTone;
}

export interface NumberLineProps {
  label: string;
  min?: number;
  max?: number;
  /** How many equal ticks span [min, max]; also the snap grid for dragging. */
  denominator?: number;
  markers: NumberLineMarker[];
  onMarkerChange?: (id: string, value: number) => void;
  disabled?: boolean;
  width?: number;
  /**
   * When two marker ids are given, the line reports (as fact, not a
   * correctness judgement) whenever their left-to-right order changes —
   * "the child placed 1/4 to the right of 1/8" is diagnostic evidence on
   * its own.
   */
  compareIds?: readonly [string, string];
  onTrace?: (event: TraceEvent) => void;
  className?: string;
}

const PADDING = 24;
const LINE_Y = 48;
const HEIGHT = 96;

function orderLabel(a: number, b: number): "before" | "after" | "equal" {
  if (a < b) return "before";
  if (a > b) return "after";
  return "equal";
}

/**
 * A shared number line with one or more draggable markers — place, snap,
 * and compare, per roadmap P13. Fully controlled: the caller owns marker
 * values, this component only ever reports interactions via `onTrace`.
 */
export function NumberLine({
  label,
  min = 0,
  max = 1,
  denominator = 4,
  markers,
  onMarkerChange,
  disabled = false,
  width = 480,
  compareIds,
  onTrace,
  className,
}: NumberLineProps) {
  const trackRef = useRef<SVGSVGElement>(null);
  const innerWidth = width - PADDING * 2;
  const safeDenominator = Math.max(1, denominator);
  const tickStep = (max - min) / safeDenominator;

  const prevOrderRef = useRef<string | null>(null);
  useEffect(() => {
    if (!compareIds) return;
    const [idA, idB] = compareIds;
    const a = markers.find((m) => m.id === idA);
    const b = markers.find((m) => m.id === idB);
    if (!a || !b) return;
    const order = orderLabel(a.value, b.value);
    const key = `${idA}:${idB}:${order}`;
    if (prevOrderRef.current !== key) {
      const isFirstRun = prevOrderRef.current === null;
      prevOrderRef.current = key;
      if (!isFirstRun) {
        onTrace?.({
          action: "compare",
          target: `${idA}(${a.label}) ${order} ${idB}(${b.label})`,
          targets: [idA, idB],
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [compareIds, markers]);

  const wholeTicks = Array.from({ length: Math.round(max - min) + 1 }, (_, i) => min + i);
  const fineTicks = Array.from({ length: safeDenominator + 1 }, (_, i) => min + i * tickStep);

  return (
    <div className={cn("inline-flex flex-col", className)} style={{ width }}>
      <svg
        ref={trackRef}
        width={width}
        height={HEIGHT}
        viewBox={`0 0 ${width} ${HEIGHT}`}
        role="group"
        aria-label={label}
        className="touch-none"
      >
        <line
          x1={PADDING}
          y1={LINE_Y}
          x2={width - PADDING}
          y2={LINE_Y}
          className="stroke-sand-500"
          strokeWidth={3}
          strokeLinecap="round"
        />

        {fineTicks.map((v, i) => {
          const x = PADDING + ((v - min) / (max - min)) * innerWidth;
          const isWhole = wholeTicks.some((w) => Math.abs(w - v) < 1e-9);
          return (
            <line
              key={i}
              x1={x}
              y1={LINE_Y - (isWhole ? 10 : 6)}
              x2={x}
              y2={LINE_Y + (isWhole ? 10 : 6)}
              className={isWhole ? "stroke-ink-soft" : "stroke-sand-500"}
              strokeWidth={isWhole ? 2 : 1.5}
            />
          );
        })}

        {wholeTicks.map((v, i) => {
          const x = PADDING + ((v - min) / (max - min)) * innerWidth;
          return (
            <text
              key={i}
              x={x}
              y={HEIGHT - 8}
              textAnchor="middle"
              className="fill-ink-soft font-sans text-xs font-bold"
            >
              {v}
            </text>
          );
        })}

        {markers.map((marker) => (
          <NumberLineMarkerHandle
            key={marker.id}
            marker={marker}
            min={min}
            max={max}
            tickStep={tickStep}
            denominator={safeDenominator}
            innerWidth={innerWidth}
            disabled={disabled}
            trackRef={trackRef}
            onChange={(next) => onMarkerChange?.(marker.id, next)}
            onTrace={onTrace}
          />
        ))}
      </svg>
    </div>
  );
}

const dotClass: Record<FractionBarTone, string> = {
  moss: "fill-moss-600 stroke-moss-700",
  sky: "fill-sky-600 stroke-sky-700",
  apricot: "fill-apricot-600 stroke-apricot-700",
  clay: "fill-clay-600 stroke-clay-700",
};

const labelClass: Record<FractionBarTone, string> = {
  moss: "fill-moss-700",
  sky: "fill-sky-700",
  apricot: "fill-apricot-700",
  clay: "fill-clay-700",
};

function NumberLineMarkerHandle({
  marker,
  min,
  max,
  tickStep,
  denominator,
  innerWidth,
  disabled,
  trackRef,
  onChange,
  onTrace,
}: {
  marker: NumberLineMarker;
  min: number;
  max: number;
  tickStep: number;
  denominator: number;
  innerWidth: number;
  disabled?: boolean;
  trackRef: RefObject<SVGSVGElement | null>;
  onChange: (value: number) => void;
  onTrace?: (event: TraceEvent) => void;
}) {
  const reduceMotion = useReducedMotion();
  const [focused, setFocused] = useState(false);
  const tone = marker.tone ?? "moss";
  const valueToTicks = (v: number) => (v - min) / tickStep;
  const ticksToValue = (t: number) => min + t * tickStep;
  const currentTicks = clamp(valueToTicks(marker.value), 0, denominator);

  const drag = useSnapDrag({
    min: 0,
    max: denominator,
    value: currentTicks,
    disabled,
    trackRef,
    toRaw: (clientX, _clientY, rect) =>
      ((clientX - rect.left - PADDING) / innerWidth) * denominator,
    onChange: (ticks) => onChange(ticksToValue(ticks)),
    onDragStart: () => onTrace?.({ action: "drag_start", target: `${marker.id}:${marker.label}` }),
    onSnap: (ticks) =>
      onTrace?.({ action: "snap", target: `${marker.id}:${ticksToValue(ticks).toFixed(4)}` }),
    onDragEnd: (ticks) =>
      onTrace?.({ action: "place", target: `${marker.id}:${ticksToValue(ticks).toFixed(4)}` }),
    onKeyboardAdjust: (ticks) =>
      onTrace?.({
        action: "keyboard_adjust",
        target: `${marker.id}:${ticksToValue(ticks).toFixed(4)}`,
      }),
  });

  const x = PADDING + (currentTicks / denominator) * innerWidth;

  return (
    <g
      role="slider"
      aria-label={`${marker.label} marker`}
      aria-orientation="horizontal"
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={marker.value}
      aria-valuetext={marker.label}
      aria-disabled={disabled || undefined}
      tabIndex={disabled ? -1 : 0}
      className="cursor-grab focus:outline-none active:cursor-grabbing"
      onPointerDown={drag.onPointerDown}
      onPointerMove={drag.onPointerMove}
      onPointerUp={drag.onPointerUp}
      onPointerCancel={drag.onPointerCancel}
      onKeyDown={drag.onKeyDown}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    >
      {focused && (
        <circle cx={x} cy={LINE_Y} r={18} fill="none" className="stroke-sky-700" strokeWidth={2} />
      )}
      <motion.g
        animate={reduceMotion ? undefined : { y: drag.dragging ? -4 : 0 }}
        transition={spring.pop}
      >
        <circle cx={x} cy={LINE_Y} r={12} className={dotClass[tone]} strokeWidth={3} />
        <text
          x={x}
          y={LINE_Y - 20}
          textAnchor="middle"
          className={cn("font-sans text-sm font-extrabold", labelClass[tone])}
        >
          {marker.label}
        </text>
      </motion.g>
    </g>
  );
}
