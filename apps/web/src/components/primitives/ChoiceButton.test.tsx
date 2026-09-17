import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ChoiceButton } from "@/components/primitives/ChoiceButton";

describe("ChoiceButton", () => {
  it("exposes selection state via aria-pressed", () => {
    render(<ChoiceButton selected>Pizza</ChoiceButton>);
    expect(screen.getByRole("button", { name: "Pizza" })).toHaveAttribute("aria-pressed", "true");
  });

  it("calls onSelect when activated", () => {
    const onSelect = vi.fn();
    render(
      <ChoiceButton selected={false} onSelect={onSelect}>
        Pie
      </ChoiceButton>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Pie" }));
    expect(onSelect).toHaveBeenCalledTimes(1);
  });
});
