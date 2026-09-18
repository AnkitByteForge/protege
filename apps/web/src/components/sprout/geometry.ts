import type { PoseId } from "@/components/sprout/types";

/**
 * The shared coordinate system every part is authored against. All 19
 * parts (5 eyes + 6 mouths + 4 brows + 4 poses) live in this single
 * `viewBox`; a pose only ever applies a *uniform* transform to the whole
 * head+face group (never to individual parts independently), which is what
 * lets any of the 5x6x4x4 = 480 combinations compose without clipping —
 * see `SproutFace.test.tsx` for the geometric proof.
 */
export const VIEW_BOX = { width: 240, height: 240 } as const;

/** Head/face group pivot — eyes, brows and mouth are all authored around this point. */
export const HEAD_PIVOT = { x: 120, y: 100 } as const;

export interface HeadTransform {
  dx: number;
  dy: number;
  rotate: number;
  scale: number;
}

/**
 * One lean/tilt per pose, applied to the head+face group as a single
 * `transform` — never per-part — so eyes/brows/mouth always move together
 * and stay centered on the body silhouette below.
 */
export const HEAD_TRANSFORM_BY_POSE: Record<PoseId, HeadTransform> = {
  confused: { dx: 0, dy: 8, rotate: -3, scale: 0.98 },
  thinking: { dx: 2, dy: 0, rotate: 2, scale: 1.0 },
  dawning: { dx: 0, dy: -4, rotate: 0, scale: 1.02 },
  delighted: { dx: 0, dy: -10, rotate: 0, scale: 1.06 },
};

export function headTransformString({ dx, dy, rotate, scale }: HeadTransform): string {
  return `translate(${HEAD_PIVOT.x + dx} ${HEAD_PIVOT.y + dy}) rotate(${rotate}) scale(${scale}) translate(${-HEAD_PIVOT.x} ${-HEAD_PIVOT.y})`;
}
