import { HEAD_PIVOT, VIEW_BOX, type HeadTransform } from "@/components/sprout/geometry";

export interface Point {
  x: number;
  y: number;
}

/**
 * Extracts every coordinate a shape element's geometry is defined by. For
 * `<path>` this parses absolute M/L/Q/C commands (the only commands any
 * rig part uses) into their control/end points; because a cubic/quadratic
 * Bezier curve never leaves the convex hull of its control points, these
 * extracted points are a valid (slightly conservative) bounding set for
 * the rendered shape — sufficient to prove containment.
 */
export function pointsFromElement(el: Element): Point[] {
  const tag = el.tagName.toLowerCase();
  switch (tag) {
    case "circle":
      return ellipsePoints(num(el, "cx"), num(el, "cy"), num(el, "r"), num(el, "r"));
    case "ellipse":
      return ellipsePoints(num(el, "cx"), num(el, "cy"), num(el, "rx"), num(el, "ry"));
    case "line": {
      return [
        { x: num(el, "x1"), y: num(el, "y1") },
        { x: num(el, "x2"), y: num(el, "y2") },
      ];
    }
    case "path": {
      return parsePathPoints(el.getAttribute("d") ?? "");
    }
    default:
      return [];
  }
}

function num(el: Element, attr: string): number {
  return Number(el.getAttribute(attr) ?? "0");
}

/**
 * Samples 16 points around a circle/ellipse's perimeter (plus its center).
 * A bounding box built from just two opposite corners is only valid for an
 * *unrotated* shape; sampling the perimeter and transforming every sample
 * stays correct once a rotation is applied, at the (generous, for our
 * modest pose rotations) cost of a slight under-approximation between
 * samples.
 */
function ellipsePoints(cx: number, cy: number, rx: number, ry: number): Point[] {
  const points: Point[] = [{ x: cx, y: cy }];
  const samples = 16;
  for (let i = 0; i < samples; i += 1) {
    const angle = (i / samples) * 2 * Math.PI;
    points.push({ x: cx + rx * Math.cos(angle), y: cy + ry * Math.sin(angle) });
  }
  return points;
}

/** Parses absolute M/L/Q/C/Z path data (the only commands the rig authors) into points. */
export function parsePathPoints(d: string): Point[] {
  const tokens = d.match(/[MLQCZ]|-?\d*\.?\d+(?:e-?\d+)?/gi) ?? [];
  const points: Point[] = [];
  let i = 0;
  let command = "";
  const argCount: Record<string, number> = { M: 2, L: 2, Q: 4, C: 6, Z: 0 };

  while (i < tokens.length) {
    const token = tokens[i];
    if (/^[MLQCZ]$/i.test(token)) {
      command = token.toUpperCase();
      i += 1;
      if (command === "Z") continue;
    }
    const count = argCount[command];
    if (!count) continue;
    const args = tokens.slice(i, i + count).map(Number);
    i += count;
    for (let p = 0; p < args.length; p += 2) {
      points.push({ x: args[p], y: args[p + 1] });
    }
  }
  return points;
}

/** Applies the exact pivot-based transform `SproutFace` uses for the head/face group. */
export function applyHeadTransform(point: Point, transform: HeadTransform): Point {
  const { dx, dy, rotate, scale } = transform;
  // translate(pivot + d) rotate(rotate) scale(scale) translate(-pivot)
  const local = { x: point.x - HEAD_PIVOT.x, y: point.y - HEAD_PIVOT.y };
  const scaled = { x: local.x * scale, y: local.y * scale };
  const rad = (rotate * Math.PI) / 180;
  const rotated = {
    x: scaled.x * Math.cos(rad) - scaled.y * Math.sin(rad),
    y: scaled.x * Math.sin(rad) + scaled.y * Math.cos(rad),
  };
  return {
    x: rotated.x + HEAD_PIVOT.x + dx,
    y: rotated.y + HEAD_PIVOT.y + dy,
  };
}

export function isWithinViewBox(point: Point, margin = 0): boolean {
  return (
    point.x >= -margin &&
    point.x <= VIEW_BOX.width + margin &&
    point.y >= -margin &&
    point.y <= VIEW_BOX.height + margin
  );
}
