"use client";

import { useCallback } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/cn";
import { spring } from "@/design/tokens";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { stepFromKey, clamp } from "@/components/manipulatives/snapping";
import type { TraceEvent } from "@/components/manipulatives/useManipulativeTrace";
import type { FractionBarTone } from "@/components/manipulatives/FractionBar";
import { Inline } from "@/components/primitives/Stack";
import { Button } from "@/components/primitives/Button";

export type AreaModelShape = "circle" | "rect";

const fillClass: Record<FractionBarTone, string> = {
  moss: "fill-moss-500",
  sky: "fill-sky-500",
  apricot: "fill-apricot-500",
  clay: "fill-clay-600",
};

export interface AreaModelProps {
  label: string;
  numerator: number;
  denominator: number;
  onNumeratorChange?: (numerator: number) => void;
  shape?: AreaModelShape;
  /** Supplying this renders the circle/rectangle toggle — "compare representations." */
  onShapeChange?: (shape: AreaModelShape) => void;
  tone?: FractionBarTone;
  disabled?: boolean;
  size?: number;
  onTrace?: (event: TraceEvent) => void;
  className?: string;
}

const SEGMENT_GAP_DEG = 1.4;

/**
 * A pie or rectangle-grid area model — fraction partitioning as shaded
 * regions rather than a linear bar. Clicking (or tabbing to, then pressing
 * Enter/Space or an arrow key on) a segment sets how many are filled, in
 * the familiar "click the Nth star to fill N" pattern. Switching between
 * circle and rectangle keeps the same numerator/denominator, so a child
 * can see the same fraction two ways — roadmap P13's "compare
 * representations."
 */
export function AreaModel({
  label,
  numerator,
  denominator,
  onNumeratorChange,
  shape = "circle",
  onShapeChange,
  tone = "moss",
  disabled = false,
  size = 220,
  onTrace,
  className,
}: AreaModelProps) {
  const reduceMotion = useReducedMotion();
  const safeDenominator = Math.max(1, denominator);
  const safeNumerator = clamp(numerator, 0, safeDenominator);

  const selectUpTo = useCallback(
    (index: number) => {
      if (disabled || !onNumeratorChange) return;
      const isLastFilled = index === safeNumerator - 1;
      const next = isLastFilled ? index : index + 1;
      onNumeratorChange(next);
      onTrace?.({ action: "select", target: `segment=${index}`, targets: [`numerator=${next}`] });
    },
    [disabled, onNumeratorChange, safeNumerator, onTrace],
  );

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (disabled || !onNumeratorChange) return;
      const next = stepFromKey(e.key, safeNumerator, 0, safeDenominator);
      if (next !== null && next !== safeNumerator) {
        e.preventDefault();
        onNumeratorChange(next);
        onTrace?.({ action: "keyboard_adjust", target: `numerator=${next}` });
      }
    },
    [disabled, onNumeratorChange, safeNumerator, safeDenominator, onTrace],
  );

  const handleShapeChange = (next: AreaModelShape) => {
    if (next === shape) return;
    onShapeChange?.(next);
    onTrace?.({ action: "representation_changed", target: next });
  };

  return (
    <div className={cn("inline-flex flex-col items-center gap-3", className)}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        role="slider"
        aria-label={label}
        aria-orientation="horizontal"
        aria-valuemin={0}
        aria-valuemax={safeDenominator}
        aria-valuenow={safeNumerator}
        aria-valuetext={`${safeNumerator} of ${safeDenominator} parts shaded`}
        aria-disabled={disabled || undefined}
        tabIndex={disabled ? -1 : 0}
        className="focus:outline-none"
        onKeyDown={onKeyDown}
      >
        {shape === "circle" ? (
          <CircleSegments
            size={size}
            denominator={safeDenominator}
            numerator={safeNumerator}
            tone={tone}
            disabled={disabled}
            reduceMotion={reduceMotion}
            onSelect={selectUpTo}
          />
        ) : (
          <RectSegments
            size={size}
            denominator={safeDenominator}
            numerator={safeNumerator}
            tone={tone}
            disabled={disabled}
            reduceMotion={reduceMotion}
            onSelect={selectUpTo}
          />
        )}
      </svg>

      {onShapeChange && (
        <Inline gap="xs">
          <Button
            size="md"
            variant={shape === "circle" ? "primary" : "secondary"}
            onClick={() => handleShapeChange("circle")}
            disabled={disabled}
          >
            ○ Circle
          </Button>
          <Button
            size="md"
            variant={shape === "rect" ? "primary" : "secondary"}
            onClick={() => handleShapeChange("rect")}
            disabled={disabled}
          >
            ▭ Rectangle
          </Button>
        </Inline>
      )}
    </div>
  );
}

interface SegmentsProps {
  size: number;
  denominator: number;
  numerator: number;
  tone: FractionBarTone;
  disabled?: boolean;
  reduceMotion: boolean;
  onSelect: (index: number) => void;
}

function CircleSegments({
  size,
  denominator,
  numerator,
  tone,
  disabled,
  reduceMotion,
  onSelect,
}: SegmentsProps) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 8;
  const anglePer = 360 / denominator;

  return (
    <g>
      <circle cx={cx} cy={cy} r={r} className="fill-surface stroke-sand-500/60" strokeWidth={2} />
      {Array.from({ length: denominator }, (_, i) => {
        const startAngle = i * anglePer + SEGMENT_GAP_DEG / 2 - 90;
        const endAngle = (i + 1) * anglePer - SEGMENT_GAP_DEG / 2 - 90;
        const start = polarPoint(cx, cy, r, startAngle);
        const end = polarPoint(cx, cy, r, endAngle);
        const largeArc = endAngle - startAngle > 180 ? 1 : 0;
        const path = `M ${cx} ${cy} L ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y} Z`;
        const filled = i < numerator;
        return (
          <motion.path
            key={i}
            d={path}
            className={cn(filled ? fillClass[tone] : "fill-surface", "stroke-sand-500/40")}
            strokeWidth={1}
            aria-hidden
            style={{ cursor: disabled ? "default" : "pointer" }}
            onClick={() => onSelect(i)}
            animate={reduceMotion ? undefined : { scale: filled ? 1 : 0.98 }}
            transition={spring.settle}
          />
        );
      })}
    </g>
  );
}

function RectSegments({
  size,
  denominator,
  numerator,
  tone,
  disabled,
  reduceMotion,
  onSelect,
}: SegmentsProps) {
  const padding = 8;
  const inner = size - padding * 2;
  const cellWidth = inner / denominator;

  return (
    <g>
      <rect
        x={padding}
        y={padding}
        width={inner}
        height={inner}
        rx={8}
        className="fill-surface stroke-sand-500/60"
        strokeWidth={2}
      />
      {Array.from({ length: denominator }, (_, i) => {
        const filled = i < numerator;
        const x = padding + i * cellWidth;
        return (
          <motion.rect
            key={i}
            x={x + (i === 0 ? 0 : 1)}
            y={padding}
            width={Math.max(0, cellWidth - (i === 0 ? 0 : 1))}
            height={inner}
            className={cn(filled ? fillClass[tone] : "fill-transparent", "stroke-sand-500/40")}
            strokeWidth={1}
            aria-hidden
            style={{ cursor: disabled ? "default" : "pointer" }}
            onClick={() => onSelect(i)}
            animate={reduceMotion ? undefined : { opacity: filled ? 1 : 0.9 }}
            transition={spring.settle}
          />
        );
      })}
    </g>
  );
}

function polarPoint(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}
