import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { AreaModel } from "@/components/manipulatives/AreaModel";

describe("AreaModel", () => {
  it("exposes the shaded amount as an accessible slider", () => {
    render(<AreaModel label="One quarter pie" numerator={1} denominator={4} />);
    const slider = screen.getByRole("slider", { name: "One quarter pie" });
    expect(slider).toHaveAttribute("aria-valuenow", "1");
    expect(slider).toHaveAttribute("aria-valuetext", "1 of 4 parts shaded");
  });

  it("adjusts numerator with arrow keys", () => {
    const onNumeratorChange = vi.fn();
    const onTrace = vi.fn();
    render(
      <AreaModel
        label="pie"
        numerator={1}
        denominator={4}
        onNumeratorChange={onNumeratorChange}
        onTrace={onTrace}
      />,
    );
    const slider = screen.getByRole("slider", { name: "pie" });
    fireEvent.keyDown(slider, { key: "ArrowRight" });
    expect(onNumeratorChange).toHaveBeenCalledWith(2);
    expect(onTrace).toHaveBeenCalledWith({ action: "keyboard_adjust", target: "numerator=2" });
  });

  it("clamps numerator into range for rendering", () => {
    render(<AreaModel label="pie" numerator={-3} denominator={4} />);
    expect(screen.getByRole("slider", { name: "pie" })).toHaveAttribute("aria-valuenow", "0");
  });

  it("does not respond to keyboard when disabled", () => {
    const onNumeratorChange = vi.fn();
    render(
      <AreaModel
        label="pie"
        numerator={1}
        denominator={4}
        onNumeratorChange={onNumeratorChange}
        disabled
      />,
    );
    const slider = screen.getByRole("slider", { name: "pie" });
    expect(slider).toHaveAttribute("tabindex", "-1");
    fireEvent.keyDown(slider, { key: "ArrowRight" });
    expect(onNumeratorChange).not.toHaveBeenCalled();
  });

  it("renders a shape toggle only when onShapeChange is supplied, and reports the switch", () => {
    const onShapeChange = vi.fn();
    const onTrace = vi.fn();
    const { rerender } = render(<AreaModel label="pie" numerator={1} denominator={4} />);
    expect(screen.queryByRole("button", { name: /rectangle/i })).not.toBeInTheDocument();

    rerender(
      <AreaModel
        label="pie"
        numerator={1}
        denominator={4}
        onShapeChange={onShapeChange}
        onTrace={onTrace}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /rectangle/i }));
    expect(onShapeChange).toHaveBeenCalledWith("rect");
    expect(onTrace).toHaveBeenCalledWith({ action: "representation_changed", target: "rect" });
  });
});
