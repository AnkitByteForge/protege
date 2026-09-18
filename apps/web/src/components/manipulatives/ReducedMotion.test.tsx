import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { FractionBar } from "@/components/manipulatives/FractionBar";
import { NumberLine } from "@/components/manipulatives/NumberLine";
import { AreaModel } from "@/components/manipulatives/AreaModel";
import { ExplanationCards } from "@/components/manipulatives/ExplanationCards";

vi.mock("@/hooks/useReducedMotion", () => ({
  useReducedMotion: () => true,
}));

/**
 * Every manipulative must stay fully functional under
 * `prefers-reduced-motion` — springs are cosmetic, never load-bearing for
 * the interaction itself (roadmap Testing: "reduced motion" honoured).
 */
describe("manipulatives under prefers-reduced-motion", () => {
  it("FractionBar still drags/keys through to a value change", () => {
    const onNumeratorChange = vi.fn();
    render(
      <FractionBar
        label="bar"
        numerator={1}
        denominator={4}
        onNumeratorChange={onNumeratorChange}
      />,
    );
    const slider = screen.getByRole("slider", { name: /filled amount/i });
    fireEvent.keyDown(slider, { key: "ArrowRight" });
    expect(onNumeratorChange).toHaveBeenCalledWith(2);
  });

  it("NumberLine marker still responds to keyboard", () => {
    const onMarkerChange = vi.fn();
    render(
      <NumberLine
        label="line"
        markers={[{ id: "a", value: 0, label: "0" }]}
        onMarkerChange={onMarkerChange}
      />,
    );
    fireEvent.keyDown(screen.getByRole("slider", { name: "0 marker" }), { key: "ArrowRight" });
    expect(onMarkerChange).toHaveBeenCalled();
  });

  it("AreaModel still responds to keyboard", () => {
    const onNumeratorChange = vi.fn();
    render(
      <AreaModel label="pie" numerator={1} denominator={4} onNumeratorChange={onNumeratorChange} />,
    );
    fireEvent.keyDown(screen.getByRole("slider", { name: "pie" }), { key: "ArrowRight" });
    expect(onNumeratorChange).toHaveBeenCalledWith(2);
  });

  it("ExplanationCards still selects on click", () => {
    const onSelect = vi.fn();
    render(
      <ExplanationCards
        label="prompt"
        options={
          [
            { id: "a", label: "A" },
            { id: "b", label: "B" },
            { id: "c", label: "C" },
          ] as const
        }
        selectedId={null}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByRole("radio", { name: "A" }));
    expect(onSelect).toHaveBeenCalledWith("a");
  });
});
