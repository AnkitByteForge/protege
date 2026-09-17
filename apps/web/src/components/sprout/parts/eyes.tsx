import type { EyeId } from "@/components/sprout/types";

export interface EyePartProps {
  id: EyeId;
  /** Small pointer-follow offset in local units, clamped by the caller. Only applies to eyes with a visible pupil. */
  lookOffset?: { x: number; y: number };
  /** Transient blink override — renders a shared closed-eye line regardless of `id`, so blinking works uniformly across all 5 variants. */
  blink?: boolean;
}

const LEFT_X = 92;
const RIGHT_X = 148;
const CY = 96;

/**
 * One of the rig's 5 reusable eye paths — rendered twice (mirrored) per
 * expression. Each variant carries a distinct silhouette (not just a color
 * change), so expression state never depends on color alone.
 */
export function EyePart({ id, lookOffset = { x: 0, y: 0 }, blink = false }: EyePartProps) {
  if (blink) {
    return (
      <g stroke="currentColor" strokeWidth={3} strokeLinecap="round">
        <line x1={LEFT_X - 8} y1={CY} x2={LEFT_X + 8} y2={CY} />
        <line x1={RIGHT_X - 8} y1={CY} x2={RIGHT_X + 8} y2={CY} />
      </g>
    );
  }

  switch (id) {
    case "round":
      return <RoundPair lookOffset={lookOffset} r={9} pupilR={3.5} />;
    case "wide":
      return <RoundPair lookOffset={lookOffset} r={12} pupilR={4.5} />;
    case "half":
      return <HalfLidPair lookOffset={lookOffset} />;
    case "soft":
      return <SoftArcPair />;
    case "squint":
      return <SquintPair />;
  }
}

function Pupil({
  cx,
  cy,
  r,
  offset,
}: {
  cx: number;
  cy: number;
  r: number;
  offset: { x: number; y: number };
}) {
  const clampedX = Math.max(-3, Math.min(3, offset.x));
  const clampedY = Math.max(-2, Math.min(2, offset.y));
  return <circle cx={cx + clampedX} cy={cy + clampedY} r={r} fill="#3B2F24" />;
}

function RoundPair({
  lookOffset,
  r,
  pupilR,
}: {
  lookOffset: { x: number; y: number };
  r: number;
  pupilR: number;
}) {
  return (
    <g>
      <circle cx={LEFT_X} cy={CY} r={r} fill="#FFFDF8" stroke="currentColor" strokeWidth={2} />
      <circle cx={RIGHT_X} cy={CY} r={r} fill="#FFFDF8" stroke="currentColor" strokeWidth={2} />
      <Pupil cx={LEFT_X} cy={CY} r={pupilR} offset={lookOffset} />
      <Pupil cx={RIGHT_X} cy={CY} r={pupilR} offset={lookOffset} />
    </g>
  );
}

function HalfLidPair({ lookOffset }: { lookOffset: { x: number; y: number } }) {
  return (
    <g>
      <ellipse
        cx={LEFT_X}
        cy={CY + 2}
        rx={10}
        ry={4.5}
        fill="#FFFDF8"
        stroke="currentColor"
        strokeWidth={2}
      />
      <ellipse
        cx={RIGHT_X}
        cy={CY + 2}
        rx={10}
        ry={4.5}
        fill="#FFFDF8"
        stroke="currentColor"
        strokeWidth={2}
      />
      <Pupil cx={LEFT_X} cy={CY + 2} r={3} offset={lookOffset} />
      <Pupil cx={RIGHT_X} cy={CY + 2} r={3} offset={lookOffset} />
      <path
        d={`M ${LEFT_X - 10} ${CY - 3} Q ${LEFT_X} ${CY - 9} ${LEFT_X + 10} ${CY - 3}`}
        stroke="currentColor"
        strokeWidth={2}
        fill="none"
        strokeLinecap="round"
      />
      <path
        d={`M ${RIGHT_X - 10} ${CY - 3} Q ${RIGHT_X} ${CY - 9} ${RIGHT_X + 10} ${CY - 3}`}
        stroke="currentColor"
        strokeWidth={2}
        fill="none"
        strokeLinecap="round"
      />
    </g>
  );
}

function SoftArcPair() {
  return (
    <g stroke="currentColor" strokeWidth={3} strokeLinecap="round" fill="none">
      <path d={`M ${LEFT_X - 9} ${CY + 2} Q ${LEFT_X} ${CY - 8} ${LEFT_X + 9} ${CY + 2}`} />
      <path d={`M ${RIGHT_X - 9} ${CY + 2} Q ${RIGHT_X} ${CY - 8} ${RIGHT_X + 9} ${CY + 2}`} />
    </g>
  );
}

function SquintPair() {
  return (
    <g stroke="currentColor" strokeWidth={3.5} strokeLinecap="round">
      <line x1={LEFT_X - 8} y1={CY} x2={LEFT_X + 8} y2={CY} />
      <line x1={RIGHT_X - 8} y1={CY} x2={RIGHT_X + 8} y2={CY} />
    </g>
  );
}
