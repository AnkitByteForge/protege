import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { FractionBar } from "@/components/manipulatives/FractionBar";

function mockRect(el: Element, rect: Partial<DOMRect>) {
  el.getBoundingClientRect = () =>
    ({
      x: 0,
      y: 0,
      top: 0,
      left: 0,
      right: 480,
      bottom: 64,
      width: 480,
      height: 64,
      toJSON: () => "",
      ...rect,
    }) as DOMRect;
}

describe("FractionBar", () => {
  it("exposes the fill amount as an accessible slider", () => {
    render(<FractionBar label="One quarter" numerator={1} denominator={4} />);
    const slider = screen.getByRole("slider", { name: /filled amount/i });
    expect(slider).toHaveAttribute("aria-valuemin", "0");
    expect(slider).toHaveAttribute("aria-valuemax", "4");
    expect(slider).toHaveAttribute("aria-valuenow", "1");
    expect(slider).toHaveAttribute("aria-valuetext", "1 of 4 parts filled");
  });

  it("clamps numerator into [0, denominator] for rendering", () => {
    render(<FractionBar label="Overfull" numerator={99} denominator={4} />);
    expect(screen.getByRole("slider", { name: /filled amount/i })).toHaveAttribute(
      "aria-valuenow",
      "4",
    );
  });

  it("moves the numerator with arrow keys and reports a keyboard trace", () => {
    const onNumeratorChange = vi.fn();
    const onTrace = vi.fn();
    render(
      <FractionBar
        label="One quarter"
        numerator={1}
        denominator={4}
        onNumeratorChange={onNumeratorChange}
        onTrace={onTrace}
      />,
    );
    const slider = screen.getByRole("slider", { name: /filled amount/i });
    slider.focus();
    fireEvent.keyDown(slider, { key: "ArrowRight" });
    expect(onNumeratorChange).toHaveBeenCalledWith(2);
    expect(onTrace).toHaveBeenCalledWith({ action: "keyboard_adjust", target: "numerator=2" });
  });

  it("clamps at bounds via Home/End", () => {
    const onNumeratorChange = vi.fn();
    render(
      <FractionBar
        label="bar"
        numerator={2}
        denominator={4}
        onNumeratorChange={onNumeratorChange}
      />,
    );
    const slider = screen.getByRole("slider", { name: /filled amount/i });
    fireEvent.keyDown(slider, { key: "End" });
    expect(onNumeratorChange).toHaveBeenCalledWith(4);
    fireEvent.keyDown(slider, { key: "Home" });
    expect(onNumeratorChange).toHaveBeenCalledWith(0);
  });

  it("drags the handle and snaps with hysteresis", () => {
    const onNumeratorChange = vi.fn();
    const onTrace = vi.fn();
    render(
      <FractionBar
        label="bar"
        numerator={0}
        denominator={4}
        width={480}
        onNumeratorChange={onNumeratorChange}
        onTrace={onTrace}
      />,
    );
    const track = screen.getByRole("group", { name: "bar" });
    mockRect(track, { left: 0, width: 480 });
    const handle = screen.getByRole("slider", { name: /filled amount/i });

    fireEvent.pointerDown(handle, { pointerId: 1, clientX: 20 });
    expect(onTrace).toHaveBeenCalledWith({ action: "drag_start", target: "numerator=0" });

    // innerWidth = 480 - 2*20 = 440; each unit = 110px. Moving to x=250
    // lands at raw ~ (250-20)/440*4 = 2.09 -> snaps to 2.
    fireEvent.pointerMove(handle, { pointerId: 1, clientX: 250 });
    expect(onNumeratorChange).toHaveBeenCalledWith(2);
    expect(onTrace).toHaveBeenCalledWith({ action: "snap", target: "numerator=2" });

    fireEvent.pointerUp(handle, { pointerId: 1, clientX: 250 });
    expect(onTrace).toHaveBeenCalledWith({ action: "drag_end", target: "numerator=2" });
  });

  it("reverts to the pre-drag value on pointer cancel (invalid interaction recovery)", () => {
    const onNumeratorChange = vi.fn();
    render(
      <FractionBar
        label="bar"
        numerator={1}
        denominator={4}
        width={480}
        onNumeratorChange={onNumeratorChange}
      />,
    );
    const track = screen.getByRole("group", { name: "bar" });
    mockRect(track, { left: 0, width: 480 });
    const handle = screen.getByRole("slider", { name: /filled amount/i });

    fireEvent.pointerDown(handle, { pointerId: 1, clientX: 20 });
    fireEvent.pointerMove(handle, { pointerId: 1, clientX: 400 });
    onNumeratorChange.mockClear();
    fireEvent.pointerCancel(handle, { pointerId: 1 });
    expect(onNumeratorChange).toHaveBeenCalledWith(1);
  });

  it("does not respond to drag or keyboard when disabled", () => {
    const onNumeratorChange = vi.fn();
    render(
      <FractionBar
        label="bar"
        numerator={1}
        denominator={4}
        onNumeratorChange={onNumeratorChange}
        disabled
      />,
    );
    const slider = screen.getByRole("slider", { name: /filled amount/i });
    expect(slider).toHaveAttribute("tabindex", "-1");
    fireEvent.keyDown(slider, { key: "ArrowRight" });
    expect(onNumeratorChange).not.toHaveBeenCalled();
  });

  it("renders a partition handle only when onDenominatorChange is supplied", () => {
    const { rerender } = render(<FractionBar label="bar" numerator={1} denominator={4} />);
    expect(
      screen.queryByRole("slider", { name: /number of equal parts/i }),
    ).not.toBeInTheDocument();

    rerender(
      <FractionBar label="bar" numerator={1} denominator={4} onDenominatorChange={() => {}} />,
    );
    expect(screen.getByRole("slider", { name: /number of equal parts/i })).toBeInTheDocument();
  });

  it("adjusts denominator with arrow keys on the partition handle", () => {
    const onDenominatorChange = vi.fn();
    const onTrace = vi.fn();
    render(
      <FractionBar
        label="bar"
        numerator={1}
        denominator={4}
        onDenominatorChange={onDenominatorChange}
        onTrace={onTrace}
      />,
    );
    const partitionHandle = screen.getByRole("slider", { name: /number of equal parts/i });
    fireEvent.keyDown(partitionHandle, { key: "ArrowRight" });
    expect(onDenominatorChange).toHaveBeenCalledWith(5);
    expect(onTrace).toHaveBeenCalledWith({ action: "partition_changed", target: "denominator=5" });
  });

  it("fires onAlign and an align trace exactly once when the ratio matches alignTo", () => {
    const onAlign = vi.fn();
    const onTrace = vi.fn();
    const { rerender } = render(
      <FractionBar
        label="bar"
        numerator={1}
        denominator={4}
        alignTo={0.25}
        onAlign={onAlign}
        onTrace={onTrace}
      />,
    );
    expect(onAlign).toHaveBeenCalledTimes(1);
    expect(onTrace).toHaveBeenCalledWith({ action: "align", target: "1/4" });

    // Re-rendering while still aligned must not re-fire.
    rerender(
      <FractionBar
        label="bar"
        numerator={1}
        denominator={4}
        alignTo={0.25}
        onAlign={onAlign}
        onTrace={onTrace}
      />,
    );
    expect(onAlign).toHaveBeenCalledTimes(1);
  });

  it("does not fire onAlign when the ratio does not match alignTo", () => {
    const onAlign = vi.fn();
    render(
      <FractionBar label="bar" numerator={1} denominator={4} alignTo={0.5} onAlign={onAlign} />,
    );
    expect(onAlign).not.toHaveBeenCalled();
  });
});
