import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { NumberLine } from "@/components/manipulatives/NumberLine";

function mockRect(el: Element, rect: Partial<DOMRect>) {
  el.getBoundingClientRect = () =>
    ({
      x: 0,
      y: 0,
      top: 0,
      left: 0,
      right: 480,
      bottom: 96,
      width: 480,
      height: 96,
      toJSON: () => "",
      ...rect,
    }) as DOMRect;
}

describe("NumberLine", () => {
  it("renders each marker as an accessible slider", () => {
    render(
      <NumberLine label="Compare fractions" markers={[{ id: "a", value: 0.25, label: "1/4" }]} />,
    );
    const marker = screen.getByRole("slider", { name: "1/4 marker" });
    expect(marker).toHaveAttribute("aria-valuetext", "1/4");
  });

  it("moves a marker with arrow keys, snapping to the tick grid", () => {
    const onMarkerChange = vi.fn();
    const onTrace = vi.fn();
    render(
      <NumberLine
        label="line"
        denominator={4}
        markers={[{ id: "a", value: 0, label: "0" }]}
        onMarkerChange={onMarkerChange}
        onTrace={onTrace}
      />,
    );
    const marker = screen.getByRole("slider", { name: "0 marker" });
    fireEvent.keyDown(marker, { key: "ArrowRight" });
    // one tick = (1-0)/4 = 0.25
    expect(onMarkerChange).toHaveBeenCalledWith("a", 0.25);
    expect(onTrace).toHaveBeenCalledWith({
      action: "keyboard_adjust",
      target: "a:0.2500",
    });
  });

  it("drags a marker along the line and reports place on release", () => {
    const onMarkerChange = vi.fn();
    const onTrace = vi.fn();
    render(
      <NumberLine
        label="line"
        denominator={4}
        markers={[{ id: "a", value: 0, label: "0" }]}
        onMarkerChange={onMarkerChange}
        onTrace={onTrace}
      />,
    );
    const group = screen.getByRole("group", { name: "line" });
    mockRect(group, { left: 0, width: 480 });
    const marker = screen.getByRole("slider", { name: "0 marker" });

    fireEvent.pointerDown(marker, { pointerId: 1, clientX: 24 });
    // innerWidth = 480 - 48 = 432; moving near the far end.
    fireEvent.pointerMove(marker, { pointerId: 1, clientX: 420 });
    fireEvent.pointerUp(marker, { pointerId: 1, clientX: 420 });

    expect(onMarkerChange).toHaveBeenCalled();
    const placeCall = onTrace.mock.calls.find(([e]) => e.action === "place");
    expect(placeCall).toBeDefined();
    expect(placeCall![0].target).toMatch(/^a:/);
  });

  it("reports a compare trace only when the watched pair's order actually changes", () => {
    const onTrace = vi.fn();
    const { rerender } = render(
      <NumberLine
        label="line"
        markers={[
          { id: "a", value: 0.25, label: "1/4" },
          { id: "b", value: 0.75, label: "3/4" },
        ]}
        compareIds={["a", "b"] as const}
        onTrace={onTrace}
      />,
    );
    // No compare event on first mount — only on an actual change.
    expect(onTrace).not.toHaveBeenCalledWith(expect.objectContaining({ action: "compare" }));

    rerender(
      <NumberLine
        label="line"
        markers={[
          { id: "a", value: 0.9, label: "1/4" },
          { id: "b", value: 0.75, label: "3/4" },
        ]}
        compareIds={["a", "b"] as const}
        onTrace={onTrace}
      />,
    );
    expect(onTrace).toHaveBeenCalledWith(
      expect.objectContaining({ action: "compare", targets: ["a", "b"] }),
    );

    onTrace.mockClear();
    // Re-rendering with the same order again must not re-fire.
    rerender(
      <NumberLine
        label="line"
        markers={[
          { id: "a", value: 0.95, label: "1/4" },
          { id: "b", value: 0.75, label: "3/4" },
        ]}
        compareIds={["a", "b"] as const}
        onTrace={onTrace}
      />,
    );
    expect(onTrace).not.toHaveBeenCalledWith(expect.objectContaining({ action: "compare" }));
  });

  it("does not respond to keyboard when disabled", () => {
    const onMarkerChange = vi.fn();
    render(
      <NumberLine
        label="line"
        markers={[{ id: "a", value: 0, label: "0" }]}
        onMarkerChange={onMarkerChange}
        disabled
      />,
    );
    const marker = screen.getByRole("slider", { name: "0 marker" });
    expect(marker).toHaveAttribute("tabindex", "-1");
    fireEvent.keyDown(marker, { key: "ArrowRight" });
    expect(onMarkerChange).not.toHaveBeenCalled();
  });
});
