import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { CompleteScene } from "./CompleteScene";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
}));

describe("CompleteScene", () => {
  beforeEach(() => {
    pushMock.mockClear();
  });

  it("returns to the same learner's garden using the server-supplied learner id", () => {
    render(<CompleteScene learnerId="7f3c2a10-0000-4000-8000-000000000001" />);

    fireEvent.click(screen.getByRole("button", { name: "Back to the garden" }));

    expect(pushMock).toHaveBeenCalledWith("/garden?learnerId=7f3c2a10-0000-4000-8000-000000000001");
  });

  it("falls back to /start when the learner id is missing, never to a bare /garden", () => {
    render(<CompleteScene learnerId={null} />);

    fireEvent.click(screen.getByRole("button", { name: "Back to the garden" }));

    expect(pushMock).toHaveBeenCalledWith("/start");
  });

  it("keeps the learner id for an abandoned session too", () => {
    render(<CompleteScene abandoned learnerId="learner-abc" />);

    fireEvent.click(screen.getByRole("button", { name: "Back to the garden" }));

    expect(pushMock).toHaveBeenCalledWith("/garden?learnerId=learner-abc");
  });
});
