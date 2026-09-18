import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Sprout } from "@/components/sprout/Sprout";

const reducedMotionMock = vi.hoisted(() => vi.fn(() => false));
vi.mock("@/hooks/useReducedMotion", () => ({ useReducedMotion: reducedMotionMock }));

describe("Sprout — the delighted-forbidden safety rule, end to end", () => {
  it("never renders as delighted while the misconception is unresolved", () => {
    render(<Sprout emotion="delighted" misconceptionState="unresolved" />);
    expect(screen.getByRole("img", { name: "Sprout looks dawning" })).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: "Sprout looks delighted" })).not.toBeInTheDocument();
  });

  it("renders as delighted once the misconception is resolved", () => {
    render(<Sprout emotion="delighted" misconceptionState="resolved" />);
    expect(screen.getByRole("img", { name: "Sprout looks delighted" })).toBeInTheDocument();
  });

  it("passes confused/thinking/dawning through unchanged regardless of resolution state", () => {
    for (const emotion of ["confused", "thinking", "dawning"] as const) {
      const { unmount } = render(<Sprout emotion={emotion} misconceptionState="unresolved" />);
      expect(screen.getByRole("img", { name: `Sprout looks ${emotion}` })).toBeInTheDocument();
      unmount();
    }
  });
});

describe("Sprout — composition with existing P12 primitives", () => {
  it("renders progress with the existing LeafProgress primitive, not a new counter", () => {
    render(<Sprout emotion="thinking" misconceptionState="unresolved" leafCount={3} />);
    expect(
      screen.getByRole("img", { name: "Sprout's plant: 3 of 5 leaves grown" }),
    ).toBeInTheDocument();
  });

  it("omits the leaf counter entirely when no leafCount is supplied", () => {
    render(<Sprout emotion="thinking" misconceptionState="unresolved" />);
    expect(screen.queryByText(/leaves grown/)).not.toBeInTheDocument();
  });

  it("renders an utterance inside the existing SpeechBubble shell", () => {
    // SpeechBubble's own typewriter reveal is P12 behaviour, not re-tested
    // here; reduced motion makes it show the full line immediately so this
    // test can focus on "Sprout hands utterance to SpeechBubble" alone.
    reducedMotionMock.mockReturnValue(true);
    render(
      <Sprout
        emotion="confused"
        misconceptionState="unresolved"
        utterance="Is 1/8 really bigger?"
      />,
    );
    const bubble = screen.getByRole("status");
    expect(bubble).toHaveTextContent("Is 1/8 really bigger?");
    reducedMotionMock.mockReturnValue(false);
  });

  it("renders no speech bubble when there is no utterance", () => {
    render(<Sprout emotion="confused" misconceptionState="unresolved" />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});

describe("Sprout — entrance/exit choreography", () => {
  it("is present when show is true", () => {
    render(<Sprout emotion="thinking" misconceptionState="unresolved" show />);
    expect(screen.getByRole("img", { name: "Sprout looks thinking" })).toBeInTheDocument();
  });

  it("is absent when show is false", () => {
    render(<Sprout emotion="thinking" misconceptionState="unresolved" show={false} />);
    expect(screen.queryByRole("img", { name: "Sprout looks thinking" })).not.toBeInTheDocument();
  });
});

describe("Sprout — the gallery-only raw rig escape hatch", () => {
  it("expressionOverride bypasses the emotion mapping for direct rig exploration", () => {
    render(
      <Sprout
        emotion="confused"
        misconceptionState="unresolved"
        expressionOverride={{ eye: "soft", mouth: "grin", brow: "raised", pose: "delighted" }}
      />,
    );
    // The label still reports the real (safety-clamped) learning-state emotion...
    expect(screen.getByRole("img", { name: "Sprout looks confused" })).toBeInTheDocument();
  });
});

describe("Sprout — accessibility", () => {
  it("adds no interactive/focusable element of its own (nothing to trap keyboard focus)", () => {
    const { container } = render(
      <Sprout
        emotion="delighted"
        misconceptionState="resolved"
        leafCount={5}
        utterance="I understand now!"
      />,
    );
    expect(container.querySelectorAll("button, a, input, [tabindex]").length).toBe(0);
  });

  it("still renders correctly under reduced motion", () => {
    reducedMotionMock.mockReturnValue(true);
    render(
      <Sprout
        emotion="dawning"
        misconceptionState="unresolved"
        leafCount={2}
        utterance="Wait..."
      />,
    );
    expect(screen.getByRole("img", { name: "Sprout looks dawning" })).toBeInTheDocument();
    reducedMotionMock.mockReturnValue(false);
  });
});
