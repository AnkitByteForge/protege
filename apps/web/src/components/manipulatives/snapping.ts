/**
 * Pure, framework-free math shared by every draggable manipulative
 * (FractionBar, NumberLine, AreaModel). Kept dependency-free so it can be
 * unit-tested directly, without mounting a component or simulating pointer
 * geometry.
 */

export interface HysteresisSnapOptions {
  min: number;
  max: number;
  /**
   * How far (in snap-unit distance, e.g. "parts of a whole") the pointer
   * must travel past the currently-snapped mark before the next mark takes
   * over. Kept above 0.5 so a dead zone straddles the naive midpoint
   * between two marks — this is what stops a marker jittering back and
   * forth when a pointer hovers exactly on a segment boundary.
   */
  releaseThreshold?: number;
}

const DEFAULT_RELEASE_THRESHOLD = 0.62;

/**
 * Snaps `raw` to the nearest integer mark within `[min, max]`, but — once a
 * value has been snapped once — refuses to move to a neighbouring mark
 * until `raw` has travelled at least `releaseThreshold` away from the
 * previous mark. This is the "magnetic and forgiving" feel the roadmap
 * asks for: a small tremor near a mark does nothing; a deliberate drag past
 * it releases cleanly.
 */
export function snapWithHysteresis(
  raw: number,
  previous: number | null,
  { min, max, releaseThreshold = DEFAULT_RELEASE_THRESHOLD }: HysteresisSnapOptions,
): number {
  const clamped = Math.min(max, Math.max(min, raw));
  const nearest = Math.round(clamped);
  if (previous === null) return nearest;
  const distanceFromPrevious = Math.abs(clamped - previous);
  return distanceFromPrevious < releaseThreshold ? previous : nearest;
}

/**
 * Maps a discrete-control keypress (the standard ARIA slider key set) to a
 * next value, or `null` if the key isn't one this control responds to.
 * Shared by every keyboard-drivable manipulative so arrow/Home/End/PageUp
 * behave identically everywhere in the product.
 */
export function stepFromKey(
  key: string,
  value: number,
  min: number,
  max: number,
  step = 1,
): number | null {
  switch (key) {
    case "ArrowRight":
    case "ArrowUp":
      return Math.min(max, value + step);
    case "ArrowLeft":
    case "ArrowDown":
      return Math.max(min, value - step);
    case "PageUp":
      return Math.min(max, value + step * 2);
    case "PageDown":
      return Math.max(min, value - step * 2);
    case "Home":
      return min;
    case "End":
      return max;
    default:
      return null;
  }
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
