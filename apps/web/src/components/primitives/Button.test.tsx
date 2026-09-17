import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Button, PrimaryAction } from "@/components/primitives/Button";

describe("Button", () => {
  it("renders its label and responds to a click", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Go</Button>);

    fireEvent.click(screen.getByRole("button", { name: "Go" }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("does not fire onClick when disabled", () => {
    const onClick = vi.fn();
    render(
      <Button onClick={onClick} disabled>
        Go
      </Button>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Go" }));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("PrimaryAction renders as a native, keyboard-focusable button", () => {
    render(<PrimaryAction>Continue</PrimaryAction>);
    const button = screen.getByRole("button", { name: "Continue" });
    expect(button.tagName).toBe("BUTTON");
    button.focus();
    expect(button).toHaveFocus();
  });
});
