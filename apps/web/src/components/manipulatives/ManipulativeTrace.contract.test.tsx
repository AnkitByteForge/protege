import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import {
  useManipulativeTrace,
  type ManipulativeAction,
} from "@/components/manipulatives/useManipulativeTrace";
import { FractionBar } from "@/components/manipulatives/FractionBar";
import { NumberLine } from "@/components/manipulatives/NumberLine";
import { AreaModel } from "@/components/manipulatives/AreaModel";
import { ExplanationCards } from "@/components/manipulatives/ExplanationCards";

/**
 * Roadmap P13: every manipulative emits a structured interaction trace
 * `{t, action, target(s)}`, identical to the generated `ManipulativeAction`
 * contract that flows into the Diagnostician. These tests wire each real
 * component to the real trace hook (no mocking) and check the resulting
 * trace is well-formed — this is the "trace-shape contract test" the
 * roadmap's Testing section calls for.
 */
function assertValidTrace(trace: ManipulativeAction[]) {
  expect(trace.length).toBeGreaterThan(0);
  for (const entry of trace) {
    expect(typeof entry.t).toBe("number");
    expect(Number.isFinite(entry.t)).toBe(true);
    expect(entry.t).toBeGreaterThanOrEqual(0);
    expect(typeof entry.action).toBe("string");
    expect(entry.action.length).toBeGreaterThan(0);
    expect(entry.target === null || typeof entry.target === "string").toBe(true);
    expect(entry.targets === null || Array.isArray(entry.targets)).toBe(true);
  }
}

function FractionBarHarness() {
  const { trace, record } = useManipulativeTrace();
  const [numerator, setNumerator] = useState(1);
  return (
    <>
      <FractionBar
        label="bar"
        numerator={numerator}
        denominator={4}
        onNumeratorChange={setNumerator}
        onTrace={record}
      />
      <output data-testid="trace">{JSON.stringify(trace)}</output>
    </>
  );
}

function NumberLineHarness() {
  const { trace, record } = useManipulativeTrace();
  const [value, setValue] = useState(0);
  return (
    <>
      <NumberLine
        label="line"
        markers={[{ id: "a", value, label: "a" }]}
        onMarkerChange={(_, v) => setValue(v)}
        onTrace={record}
      />
      <output data-testid="trace">{JSON.stringify(trace)}</output>
    </>
  );
}

function AreaModelHarness() {
  const { trace, record } = useManipulativeTrace();
  const [numerator, setNumerator] = useState(1);
  return (
    <>
      <AreaModel
        label="pie"
        numerator={numerator}
        denominator={4}
        onNumeratorChange={setNumerator}
        onTrace={record}
      />
      <output data-testid="trace">{JSON.stringify(trace)}</output>
    </>
  );
}

function ExplanationCardsHarness() {
  const { trace, record } = useManipulativeTrace();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const options = [
    { id: "a", label: "A" },
    { id: "b", label: "B" },
    { id: "c", label: "C" },
  ] as const;
  return (
    <>
      <ExplanationCards
        label="prompt"
        options={options}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onTrace={record}
      />
      <output data-testid="trace">{JSON.stringify(trace)}</output>
    </>
  );
}

describe("ManipulativeTrace contract", () => {
  it("FractionBar keyboard interaction produces a valid trace", () => {
    render(<FractionBarHarness />);
    const slider = screen.getByRole("slider", { name: /filled amount/i });
    fireEvent.keyDown(slider, { key: "ArrowRight" });
    const trace = JSON.parse(screen.getByTestId("trace").textContent ?? "[]");
    assertValidTrace(trace);
  });

  it("NumberLine keyboard interaction produces a valid trace", () => {
    render(<NumberLineHarness />);
    const marker = screen.getByRole("slider", { name: "a marker" });
    fireEvent.keyDown(marker, { key: "ArrowRight" });
    const trace = JSON.parse(screen.getByTestId("trace").textContent ?? "[]");
    assertValidTrace(trace);
  });

  it("AreaModel keyboard interaction produces a valid trace", () => {
    render(<AreaModelHarness />);
    const slider = screen.getByRole("slider", { name: "pie" });
    fireEvent.keyDown(slider, { key: "ArrowRight" });
    const trace = JSON.parse(screen.getByTestId("trace").textContent ?? "[]");
    assertValidTrace(trace);
  });

  it("ExplanationCards selection produces a valid trace", () => {
    render(<ExplanationCardsHarness />);
    fireEvent.click(screen.getByRole("radio", { name: "A" }));
    const trace = JSON.parse(screen.getByTestId("trace").textContent ?? "[]");
    assertValidTrace(trace);
  });

  it("t is monotonically non-decreasing across multiple events from the same component", () => {
    render(<FractionBarHarness />);
    const slider = screen.getByRole("slider", { name: /filled amount/i });
    fireEvent.keyDown(slider, { key: "ArrowRight" });
    fireEvent.keyDown(slider, { key: "ArrowRight" });
    const trace: ManipulativeAction[] = JSON.parse(screen.getByTestId("trace").textContent ?? "[]");
    assertValidTrace(trace);
    for (let i = 1; i < trace.length; i++) {
      expect(trace[i].t).toBeGreaterThanOrEqual(trace[i - 1].t);
    }
  });
});
