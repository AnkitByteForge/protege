import { describe, expect, it } from "vitest";
import {
  deriveDisplayEmotion,
  EXPRESSION_BY_EMOTION,
  expressionForEmotion,
} from "@/components/sprout/emotion";
import type { SproutEmotion } from "@/components/sprout/types";

const EMOTIONS: SproutEmotion[] = ["confused", "thinking", "dawning", "delighted"];

describe("deriveDisplayEmotion — the delighted-forbidden safety rule", () => {
  it("never displays delighted while the misconception is unresolved", () => {
    expect(deriveDisplayEmotion("delighted", "unresolved")).toBe("dawning");
  });

  it("allows delighted once the misconception is resolved", () => {
    expect(deriveDisplayEmotion("delighted", "resolved")).toBe("delighted");
  });

  it("passes every non-delighted emotion through unchanged, regardless of resolution state", () => {
    for (const emotion of EMOTIONS.filter((e) => e !== "delighted")) {
      expect(deriveDisplayEmotion(emotion, "unresolved")).toBe(emotion);
      expect(deriveDisplayEmotion(emotion, "resolved")).toBe(emotion);
    }
  });

  it("is a pure function of its two arguments — no hidden client mood state", () => {
    // Calling it repeatedly with the same learning-state props always agrees.
    const results = Array.from({ length: 5 }, () =>
      deriveDisplayEmotion("delighted", "unresolved"),
    );
    expect(new Set(results).size).toBe(1);
    expect(results[0]).toBe("dawning");
  });
});

describe("EXPRESSION_BY_EMOTION", () => {
  it("defines exactly one canonical expression per emotion in the closed set", () => {
    expect(Object.keys(EXPRESSION_BY_EMOTION).sort()).toEqual([...EMOTIONS].sort());
  });

  it("never maps any emotion's canonical expression to the delighted pose except delighted itself", () => {
    for (const emotion of EMOTIONS) {
      if (emotion === "delighted") continue;
      expect(EXPRESSION_BY_EMOTION[emotion].pose).not.toBe("delighted");
    }
  });

  it("expressionForEmotion resolves the same table", () => {
    for (const emotion of EMOTIONS) {
      expect(expressionForEmotion(emotion)).toEqual(EXPRESSION_BY_EMOTION[emotion]);
    }
  });
});

describe("the full confused -> thinking -> dawning -> delighted progression", () => {
  it("is representable end to end through the safety clamp", () => {
    // A session moving through the progression as the misconception resolves.
    expect(deriveDisplayEmotion("confused", "unresolved")).toBe("confused");
    expect(deriveDisplayEmotion("thinking", "unresolved")).toBe("thinking");
    expect(deriveDisplayEmotion("dawning", "unresolved")).toBe("dawning");
    // The server should not emit "delighted" before resolution, but even if
    // it somehow did, the client clamp still holds the line.
    expect(deriveDisplayEmotion("delighted", "unresolved")).toBe("dawning");
    expect(deriveDisplayEmotion("delighted", "resolved")).toBe("delighted");
  });
});
