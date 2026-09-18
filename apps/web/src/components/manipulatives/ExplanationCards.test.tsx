import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ExplanationCards } from "@/components/manipulatives/ExplanationCards";

const options = [
  { id: "more-pieces", label: "More pieces, smaller size" },
  { id: "same-size", label: "The pieces stay the same size" },
  { id: "bigger-whole", label: "The whole got bigger" },
] as const;

describe("ExplanationCards", () => {
  it("renders exactly three radio options with a group label", () => {
    render(
      <ExplanationCards
        label="Why is 1/8 smaller than 1/4?"
        options={options}
        selectedId={null}
        onSelect={() => {}}
      />,
    );
    expect(
      screen.getByRole("radiogroup", { name: "Why is 1/8 smaller than 1/4?" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("radio")).toHaveLength(3);
  });

  it("selects a card on click and reports a trace", () => {
    const onSelect = vi.fn();
    const onTrace = vi.fn();
    render(
      <ExplanationCards
        label="prompt"
        options={options}
        selectedId={null}
        onSelect={onSelect}
        onTrace={onTrace}
      />,
    );
    fireEvent.click(screen.getByRole("radio", { name: "More pieces, smaller size" }));
    expect(onSelect).toHaveBeenCalledWith("more-pieces");
    expect(onTrace).toHaveBeenCalledWith({ action: "select", target: "more-pieces" });
  });

  it("marks the selected option as checked", () => {
    render(
      <ExplanationCards
        label="prompt"
        options={options}
        selectedId="same-size"
        onSelect={() => {}}
      />,
    );
    expect(screen.getByRole("radio", { name: "The pieces stay the same size" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("radio", { name: "More pieces, smaller size" })).toHaveAttribute(
      "aria-checked",
      "false",
    );
  });

  it("navigates and selects with arrow keys (roving tabindex)", () => {
    const onSelect = vi.fn();
    render(
      <ExplanationCards
        label="prompt"
        options={options}
        selectedId="more-pieces"
        onSelect={onSelect}
      />,
    );
    const first = screen.getByRole("radio", { name: "More pieces, smaller size" });
    first.focus();
    fireEvent.keyDown(first, { key: "ArrowRight" });
    expect(onSelect).toHaveBeenCalledWith("same-size");
    expect(screen.getByRole("radio", { name: "The pieces stay the same size" })).toHaveFocus();
  });

  it("wraps from the last option back to the first", () => {
    const onSelect = vi.fn();
    render(
      <ExplanationCards
        label="prompt"
        options={options}
        selectedId="bigger-whole"
        onSelect={onSelect}
      />,
    );
    const last = screen.getByRole("radio", { name: "The whole got bigger" });
    last.focus();
    fireEvent.keyDown(last, { key: "ArrowRight" });
    expect(onSelect).toHaveBeenCalledWith("more-pieces");
  });

  it("does not select or fire traces when disabled", () => {
    const onSelect = vi.fn();
    render(
      <ExplanationCards
        label="prompt"
        options={options}
        selectedId={null}
        onSelect={onSelect}
        disabled
      />,
    );
    fireEvent.click(screen.getByRole("radio", { name: "More pieces, smaller size" }));
    expect(onSelect).not.toHaveBeenCalled();
  });
});
