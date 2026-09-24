import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import StartPage from "./page";
import { ApiProblemError, type ApiProblem } from "@/lib/protege-api-client";

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: vi.fn() }),
}));

const ensureLearnerMock = vi.fn();

vi.mock("@/lib/protege-api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/protege-api-client")>(
    "@/lib/protege-api-client",
  );
  return {
    ...actual,
    protegeApi: { ensureLearner: () => ensureLearnerMock() },
  };
});

function problem(overrides: Partial<ApiProblem> = {}): ApiProblem {
  return {
    type: "protege:bad-request",
    title: "Bad Request",
    status: 400,
    detail: "nope",
    instance: "/v1/learners/ensure",
    child_safe_message: "A grown-up needs to finish signing in first.",
    ...overrides,
  };
}

describe("StartPage", () => {
  beforeEach(() => {
    replaceMock.mockClear();
    ensureLearnerMock.mockReset();
  });

  it("bootstraps on mount and navigates to /garden with the real learner id", async () => {
    ensureLearnerMock.mockResolvedValue({ learner_id: "learner-abc-123", display_name: "Learner" });

    render(<StartPage />);

    await waitFor(() => expect(ensureLearnerMock).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(replaceMock).toHaveBeenCalledWith("/garden?learnerId=learner-abc-123"),
    );
  });

  it("shows a child-safe error and lets the child/parent retry on failure", async () => {
    ensureLearnerMock
      .mockRejectedValueOnce(new ApiProblemError(problem()))
      .mockResolvedValueOnce({ learner_id: "learner-xyz-789", display_name: "Learner" });

    render(<StartPage />);

    await waitFor(() =>
      expect(screen.getByText("A grown-up needs to finish signing in first.")).toBeInTheDocument(),
    );
    expect(replaceMock).not.toHaveBeenCalled();

    screen.getByRole("button", { name: "Try again" }).click();

    await waitFor(() =>
      expect(replaceMock).toHaveBeenCalledWith("/garden?learnerId=learner-xyz-789"),
    );
  });
});
