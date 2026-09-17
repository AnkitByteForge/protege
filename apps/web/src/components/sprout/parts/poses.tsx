import { Leaf } from "@/components/illustrations/Leaf";
import type { PoseId } from "@/components/sprout/types";

interface LeafPlacement {
  x: number;
  y: number;
  rotate: number;
  scale: number;
}

interface PoseDefinition {
  /** The body silhouette — one path per pose, all four sharing the same viewBox. */
  bodyPath: string;
  armLeft: LeafPlacement;
  armRight: LeafPlacement;
  tuft: LeafPlacement;
}

/**
 * One of the rig's 4 reusable body/pose paths. Arms and the top "sprout"
 * tuft reuse the existing P12 `Leaf` glyph (illustrations/Leaf.tsx) rather
 * than authoring new paths — Sprout is, quite literally, made of leaves.
 */
export const POSE_DEFINITION: Record<PoseId, PoseDefinition> = {
  confused: {
    bodyPath:
      "M 118 110 C 152 108 178 135 180 165 C 182 196 158 218 120 218 C 84 218 58 198 58 166 C 58 136 84 110 118 110 Z",
    armLeft: { x: 58, y: 168, rotate: -100, scale: 0.85 },
    armRight: { x: 182, y: 168, rotate: 100, scale: 0.85 },
    tuft: { x: 112, y: 104, rotate: -18, scale: 0.7 },
  },
  thinking: {
    bodyPath:
      "M 120 95 C 158 95 185 125 185 160 C 185 195 158 215 120 215 C 82 215 55 195 55 160 C 55 125 82 95 120 95 Z",
    armLeft: { x: 55, y: 150, rotate: -60, scale: 0.9 },
    armRight: { x: 150, y: 118, rotate: 55, scale: 0.9 },
    tuft: { x: 120, y: 88, rotate: 0, scale: 0.85 },
  },
  dawning: {
    bodyPath:
      "M 124 92 C 160 94 186 122 184 158 C 182 193 156 214 120 214 C 84 214 56 192 56 158 C 56 124 84 96 124 92 Z",
    armLeft: { x: 52, y: 145, rotate: -40, scale: 0.95 },
    armRight: { x: 188, y: 145, rotate: 40, scale: 0.95 },
    tuft: { x: 122, y: 80, rotate: 8, scale: 0.95 },
  },
  delighted: {
    bodyPath:
      "M 120 80 C 160 82 188 112 186 150 C 184 190 158 216 120 216 C 82 216 54 190 54 150 C 54 112 82 82 120 80 Z",
    armLeft: { x: 46, y: 110, rotate: -20, scale: 1.05 },
    armRight: { x: 194, y: 110, rotate: 20, scale: 1.05 },
    tuft: { x: 120, y: 62, rotate: 0, scale: 1.2 },
  },
};

function PlacedLeaf({ placement, size = 34 }: { placement: LeafPlacement; size?: number }) {
  const half = (size * placement.scale) / 2;
  return (
    <g transform={`translate(${placement.x} ${placement.y}) rotate(${placement.rotate})`}>
      <Leaf x={-half} y={-half} width={half * 2} height={half * 2} className="text-moss-500" />
    </g>
  );
}

export function PoseBody({ id }: { id: PoseId }) {
  const def = POSE_DEFINITION[id];
  return (
    <g>
      <PlacedLeaf placement={def.armLeft} />
      <PlacedLeaf placement={def.armRight} />
      <path
        data-testid="sprout-body"
        d={def.bodyPath}
        className="text-moss-500"
        fill="currentColor"
      />
      <path d={def.bodyPath} fill="none" stroke="#2F6B45" strokeOpacity={0.35} strokeWidth={2} />
      <PlacedLeaf placement={def.tuft} size={28} />
    </g>
  );
}
