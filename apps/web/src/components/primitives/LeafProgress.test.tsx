import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LeafProgress } from "@/components/primitives/LeafProgress";

describe("LeafProgress", () => {
  it("exposes progress as an accessible label, never a visible percentage", () => {
    render(<LeafProgress count={3} total={5} />);
    const progress = screen.getByRole("img", { name: "3 of 5 leaves grown" });
    expect(progress).toBeInTheDocument();
    expect(progress.textContent).not.toMatch(/%|percent/i);
  });

  it("clamps count within [0, total]", () => {
    render(<LeafProgress count={99} total={5} />);
    expect(screen.getByRole("img", { name: "5 of 5 leaves grown" })).toBeInTheDocument();
  });

  it("accepts a custom accessible label", () => {
    render(<LeafProgress count={2} total={5} label="Custom progress label" />);
    expect(screen.getByRole("img", { name: "Custom progress label" })).toBeInTheDocument();
  });
});
