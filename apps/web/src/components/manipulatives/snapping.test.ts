import { describe, expect, it } from "vitest";
import { clamp, snapWithHysteresis, stepFromKey } from "@/components/manipulatives/snapping";

describe("snapWithHysteresis", () => {
  it("snaps to the nearest mark when there is no previous value", () => {
    expect(snapWithHysteresis(2.4, null, { min: 0, max: 4 })).toBe(2);
    expect(snapWithHysteresis(2.6, null, { min: 0, max: 4 })).toBe(3);
  });

  it("clamps raw input to [min, max] before snapping", () => {
    expect(snapWithHysteresis(-5, null, { min: 0, max: 4 })).toBe(0);
    expect(snapWithHysteresis(99, null, { min: 0, max: 4 })).toBe(4);
  });

  it("stays on the previous mark inside the hysteresis dead zone (no jitter)", () => {
    // previous = 1; naive rounding would flip at 0.5, but the dead zone
    // extends the release threshold (0.62) past that midpoint in both directions.
    expect(snapWithHysteresis(0.5, 1, { min: 0, max: 4 })).toBe(1);
    expect(snapWithHysteresis(0.45, 1, { min: 0, max: 4 })).toBe(1);
    expect(snapWithHysteresis(1.5, 1, { min: 0, max: 4 })).toBe(1);
  });

  it("releases to the next mark once past the release threshold", () => {
    expect(snapWithHysteresis(0.37, 1, { min: 0, max: 4 })).toBe(0);
    expect(snapWithHysteresis(1.63, 1, { min: 0, max: 4 })).toBe(2);
  });

  it("honours a custom release threshold", () => {
    expect(snapWithHysteresis(1.2, 1, { min: 0, max: 4, releaseThreshold: 0.1 })).toBe(1);
    expect(snapWithHysteresis(1.3, 1, { min: 0, max: 4, releaseThreshold: 0.1 })).toBe(1);
    expect(snapWithHysteresis(1.15, 1, { min: 0, max: 4, releaseThreshold: 0.1 })).toBe(1);
  });
});

describe("stepFromKey", () => {
  it("moves by step on arrow keys", () => {
    expect(stepFromKey("ArrowRight", 2, 0, 5)).toBe(3);
    expect(stepFromKey("ArrowUp", 2, 0, 5)).toBe(3);
    expect(stepFromKey("ArrowLeft", 2, 0, 5)).toBe(1);
    expect(stepFromKey("ArrowDown", 2, 0, 5)).toBe(1);
  });

  it("clamps at bounds", () => {
    expect(stepFromKey("ArrowRight", 5, 0, 5)).toBe(5);
    expect(stepFromKey("ArrowLeft", 0, 0, 5)).toBe(0);
  });

  it("jumps to bounds on Home/End", () => {
    expect(stepFromKey("Home", 3, 0, 5)).toBe(0);
    expect(stepFromKey("End", 3, 0, 5)).toBe(5);
  });

  it("moves by double step on PageUp/PageDown", () => {
    expect(stepFromKey("PageUp", 2, 0, 10)).toBe(4);
    expect(stepFromKey("PageDown", 2, 0, 10)).toBe(0);
  });

  it("returns null for keys it doesn't handle", () => {
    expect(stepFromKey("Tab", 2, 0, 5)).toBeNull();
    expect(stepFromKey("a", 2, 0, 5)).toBeNull();
  });
});

describe("clamp", () => {
  it("clamps within range", () => {
    expect(clamp(-1, 0, 5)).toBe(0);
    expect(clamp(10, 0, 5)).toBe(5);
    expect(clamp(3, 0, 5)).toBe(3);
  });
});
