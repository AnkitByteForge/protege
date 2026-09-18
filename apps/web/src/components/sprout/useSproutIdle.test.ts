import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSproutIdle } from "@/components/sprout/useSproutIdle";

const reducedMotionMock = vi.hoisted(() => vi.fn(() => false));

vi.mock("@/hooks/useReducedMotion", () => ({
  useReducedMotion: reducedMotionMock,
}));

function containerRef() {
  const div = document.createElement("div");
  div.getBoundingClientRect = () =>
    ({
      left: 0,
      top: 0,
      right: 100,
      bottom: 100,
      width: 100,
      height: 100,
      x: 0,
      y: 0,
      toJSON() {},
    }) as DOMRect;
  return { current: div };
}

describe("useSproutIdle", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    reducedMotionMock.mockReturnValue(false);
    // Deterministic: Math.random() = 0 collapses every randomised gap to its minimum.
    vi.spyOn(Math, "random").mockReturnValue(0);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    reducedMotionMock.mockReset();
    reducedMotionMock.mockReturnValue(false);
  });

  it("blinks briefly on a bounded timer, then reopens, when motion is allowed", () => {
    const ref = containerRef();
    const { result } = renderHook(() => useSproutIdle({ containerRef: ref }));
    expect(result.current.blink).toBe(false);
    expect(result.current.breathe).toBe(true);

    // Minimum gap (Math.random mocked to 0) is 2600ms.
    act(() => {
      vi.advanceTimersByTime(2600);
    });
    expect(result.current.blink).toBe(true);

    // Closed for 140ms, then reopens and reschedules.
    act(() => {
      vi.advanceTimersByTime(140);
    });
    expect(result.current.blink).toBe(false);
  });

  it("never blinks, never breathes, and never looks around when motion is reduced", () => {
    reducedMotionMock.mockReturnValue(true);
    const ref = containerRef();
    const { result } = renderHook(() => useSproutIdle({ containerRef: ref }));

    act(() => {
      vi.advanceTimersByTime(20000);
    });

    expect(result.current.blink).toBe(false);
    expect(result.current.breathe).toBe(false);
    expect(result.current.lookOffset).toEqual({ x: 0, y: 0 });
  });

  it("disables all idle behaviour when enabled=false (e.g. mid entrance/exit)", () => {
    const ref = containerRef();
    const { result } = renderHook(() => useSproutIdle({ containerRef: ref, enabled: false }));

    act(() => {
      vi.advanceTimersByTime(20000);
    });

    expect(result.current.blink).toBe(false);
    expect(result.current.breathe).toBe(false);
    expect(result.current.lookOffset).toEqual({ x: 0, y: 0 });
  });

  it("looks toward a nearby pointer within a small, clamped offset", () => {
    const ref = containerRef();
    const { result } = renderHook(() => useSproutIdle({ containerRef: ref }));

    act(() => {
      // Container center is (50, 50); pointer well within LOOK_MAX_DISTANCE_PX.
      window.dispatchEvent(new MouseEvent("pointermove", { clientX: 250, clientY: 50 }));
      vi.advanceTimersByTime(900);
    });

    expect(result.current.lookOffset.x).toBeGreaterThan(0);
    expect(result.current.lookOffset.x).toBeLessThanOrEqual(3);
    expect(result.current.lookOffset.y).toBe(0);
  });

  it("resets to center when the pointer is far away", () => {
    const ref = containerRef();
    const { result } = renderHook(() => useSproutIdle({ containerRef: ref }));

    act(() => {
      window.dispatchEvent(new MouseEvent("pointermove", { clientX: 5000, clientY: 5000 }));
      vi.advanceTimersByTime(900);
    });

    expect(result.current.lookOffset).toEqual({ x: 0, y: 0 });
  });
});
