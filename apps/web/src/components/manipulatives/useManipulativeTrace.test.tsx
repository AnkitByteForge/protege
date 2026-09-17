import { describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useManipulativeTrace } from "@/components/manipulatives/useManipulativeTrace";

describe("useManipulativeTrace", () => {
  it("starts empty", () => {
    const { result } = renderHook(() => useManipulativeTrace());
    expect(result.current.trace).toEqual([]);
  });

  it("records events in order, matching the {t, action, target(s)} contract shape", () => {
    const { result } = renderHook(() => useManipulativeTrace());

    act(() => {
      result.current.record({ action: "drag_start", target: "numerator=0" });
    });
    act(() => {
      result.current.record({ action: "drag_end", target: "numerator=2" });
    });

    expect(result.current.trace).toHaveLength(2);
    for (const entry of result.current.trace) {
      expect(typeof entry.t).toBe("number");
      expect(entry.t).toBeGreaterThanOrEqual(0);
      expect(typeof entry.action).toBe("string");
      expect("target" in entry).toBe(true);
      expect("targets" in entry).toBe(true);
    }
    expect(result.current.trace[0].action).toBe("drag_start");
    expect(result.current.trace[1].action).toBe("drag_end");
  });

  it("defaults target/targets to null rather than undefined", () => {
    const { result } = renderHook(() => useManipulativeTrace());
    act(() => {
      result.current.record({ action: "select" });
    });
    expect(result.current.trace[0].target).toBeNull();
    expect(result.current.trace[0].targets).toBeNull();
  });

  it("reset clears the trace and restarts the clock", () => {
    const { result } = renderHook(() => useManipulativeTrace());
    act(() => {
      result.current.record({ action: "select", target: "a" });
    });
    expect(result.current.trace).toHaveLength(1);

    act(() => {
      result.current.reset();
    });
    expect(result.current.trace).toEqual([]);
  });
});
