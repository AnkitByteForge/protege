import { describe, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { SproutFace } from "@/components/sprout/SproutFace";
import { PoseBody, POSE_DEFINITION } from "@/components/sprout/parts/poses";
import { EyePart } from "@/components/sprout/parts/eyes";
import { MouthPart } from "@/components/sprout/parts/mouths";
import { BrowPart } from "@/components/sprout/parts/brows";
import { HEAD_TRANSFORM_BY_POSE, VIEW_BOX } from "@/components/sprout/geometry";
import {
  applyHeadTransform,
  isWithinViewBox,
  pointsFromElement,
} from "@/components/sprout/testSupport";
import {
  BROW_IDS,
  EYE_IDS,
  MOUTH_IDS,
  POSE_IDS,
  TOTAL_EXPRESSIONS,
} from "@/components/sprout/types";
import type { SproutExpression } from "@/components/sprout/types";

const LEAF_LOCAL_CORNERS = [
  { x: 4, y: 4 },
  { x: 28, y: 4 },
  { x: 4, y: 28 },
  { x: 28, y: 28 },
]; // Leaf.tsx's own path lives inside its 0-32 viewBox; a 4px margin covers its actual glyph extent.

describe("the 480-expression combinatorial rig", () => {
  it("has exactly 5 eyes x 6 mouths x 4 brows x 4 poses = 480 combinations", () => {
    expect(EYE_IDS.length).toBe(5);
    expect(MOUTH_IDS.length).toBe(6);
    expect(BROW_IDS.length).toBe(4);
    expect(POSE_IDS.length).toBe(4);
    expect(TOTAL_EXPRESSIONS).toBe(480);
  });

  it("renders every one of the 480 combinations without throwing", () => {
    let count = 0;
    for (const eye of EYE_IDS) {
      for (const mouth of MOUTH_IDS) {
        for (const brow of BROW_IDS) {
          for (const pose of POSE_IDS) {
            const expression: SproutExpression = { eye, mouth, brow, pose };
            const { container, unmount } = render(
              <SproutFace
                expression={expression}
                label={`eye ${eye} mouth ${mouth} brow ${brow} pose ${pose}`}
              />,
            );
            const svg = container.querySelector("svg");
            expect(svg).not.toBeNull();
            expect(svg?.getAttribute("role")).toBe("img");
            unmount();
            count += 1;
          }
        }
      }
    }
    cleanup();
    expect(count).toBe(480);
  });

  it("gives every expression a distinct, non-color accessible label", () => {
    const { container } = render(
      <SproutFace
        expression={{ eye: "wide", mouth: "grin", brow: "raised", pose: "delighted" }}
        label="Sprout looks delighted"
      />,
    );
    const svg = container.querySelector("svg");
    expect(svg?.getAttribute("aria-label")).toBe("Sprout looks delighted");
  });
});

/**
 * Geometric non-clipping proof.
 *
 * An expression is the union of independent, non-interacting shapes: the
 * pose's body path (untransformed), the pose's head transform applied
 * uniformly to whichever eye/brow/mouth are selected, and the pose's two
 * arm leaves + tuft leaf. Because the parts never affect each other's
 * position, proving containment for every (part, pose) pair — rather than
 * every (eye, mouth, brow, pose) quadruple — is sufficient to prove
 * containment for all 480 combinations: the union of contained sets is
 * contained. This is what the loops below actually check, exhaustively.
 */
describe("no expression clips the viewBox", () => {
  it("every eye, at every pose's head transform, stays inside the viewBox", () => {
    for (const eye of EYE_IDS) {
      const { container } = render(
        <svg>
          <EyePart id={eye} />
        </svg>,
      );
      const shapes = Array.from(container.querySelectorAll("circle, ellipse, line, path"));
      expect(shapes.length).toBeGreaterThan(0);
      for (const pose of POSE_IDS) {
        const transform = HEAD_TRANSFORM_BY_POSE[pose];
        for (const shape of shapes) {
          for (const point of pointsFromElement(shape)) {
            const transformed = applyHeadTransform(point, transform);
            expect(
              isWithinViewBox(transformed),
              `eye=${eye} pose=${pose} point=${JSON.stringify(point)}`,
            ).toBe(true);
          }
        }
      }
      cleanup();
    }
  });

  it("every brow, at every pose's head transform, stays inside the viewBox", () => {
    for (const brow of BROW_IDS) {
      const { container } = render(
        <svg>
          <BrowPart id={brow} />
        </svg>,
      );
      const shapes = Array.from(container.querySelectorAll("circle, ellipse, line, path"));
      expect(shapes.length).toBeGreaterThan(0);
      for (const pose of POSE_IDS) {
        const transform = HEAD_TRANSFORM_BY_POSE[pose];
        for (const shape of shapes) {
          for (const point of pointsFromElement(shape)) {
            const transformed = applyHeadTransform(point, transform);
            expect(isWithinViewBox(transformed), `brow=${brow} pose=${pose}`).toBe(true);
          }
        }
      }
      cleanup();
    }
  });

  it("every mouth, at every pose's head transform, stays inside the viewBox", () => {
    for (const mouth of MOUTH_IDS) {
      const { container } = render(
        <svg>
          <MouthPart id={mouth} />
        </svg>,
      );
      const shapes = Array.from(container.querySelectorAll("circle, ellipse, line, path"));
      expect(shapes.length).toBeGreaterThan(0);
      for (const pose of POSE_IDS) {
        const transform = HEAD_TRANSFORM_BY_POSE[pose];
        for (const shape of shapes) {
          for (const point of pointsFromElement(shape)) {
            const transformed = applyHeadTransform(point, transform);
            expect(isWithinViewBox(transformed), `mouth=${mouth} pose=${pose}`).toBe(true);
          }
        }
      }
      cleanup();
    }
  });

  it("every pose's body blob path stays inside the viewBox", () => {
    for (const pose of POSE_IDS) {
      const { container } = render(
        <svg>
          <PoseBody id={pose} />
        </svg>,
      );
      const blob = container.querySelector('[data-testid="sprout-body"]');
      expect(blob).not.toBeNull();
      const points = pointsFromElement(blob as Element);
      expect(points.length).toBeGreaterThan(0);
      for (const point of points) {
        expect(isWithinViewBox(point), `pose=${pose} point=${JSON.stringify(point)}`).toBe(true);
      }
      cleanup();
    }
  });

  it("every pose's arm and tuft leaf placements stay inside the viewBox", () => {
    for (const pose of POSE_IDS) {
      const def = POSE_DEFINITION[pose];
      for (const placement of [def.armLeft, def.armRight, def.tuft]) {
        const half = (34 * placement.scale) / 2; // matches PlacedLeaf's default size=34
        const localScale = (half * 2) / 32; // Leaf's own viewBox is 0 0 32 32
        const rad = (placement.rotate * Math.PI) / 180;
        for (const corner of LEAF_LOCAL_CORNERS) {
          // Leaf-local -> centered-and-scaled -> rotated -> placed.
          const centered = { x: (corner.x - 16) * localScale, y: (corner.y - 16) * localScale };
          const rotated = {
            x: centered.x * Math.cos(rad) - centered.y * Math.sin(rad),
            y: centered.x * Math.sin(rad) + centered.y * Math.cos(rad),
          };
          const placed = { x: rotated.x + placement.x, y: rotated.y + placement.y };
          expect(
            isWithinViewBox(placed),
            `pose=${pose} placement=${JSON.stringify(placement)}`,
          ).toBe(true);
        }
      }
    }
  });

  it("the viewBox itself is the 240x240 canvas every part above was checked against", () => {
    expect(VIEW_BOX).toEqual({ width: 240, height: 240 });
  });
});
