import { describe, expect, it } from "vitest";
import { color } from "@/design/tokens";

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.replace("#", ""), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function srgbToLinear(c: number): number {
  const v = c / 255;
  return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
}

function relativeLuminance([r, g, b]: [number, number, number]): number {
  const [rl, gl, bl] = [r, g, b].map(srgbToLinear);
  return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl;
}

function contrastRatio(hexA: string, hexB: string): number {
  const lA = relativeLuminance(hexToRgb(hexA));
  const lB = relativeLuminance(hexToRgb(hexB));
  const [lighter, darker] = lA > lB ? [lA, lB] : [lB, lA];
  return (lighter + 0.05) / (darker + 0.05);
}

function hueDegrees(hex: string): number {
  const [r, g, b] = hexToRgb(hex).map((c) => c / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  if (max === min) return 0;
  const d = max - min;
  let h: number;
  switch (max) {
    case r:
      h = ((g - b) / d) % 6;
      break;
    case g:
      h = (b - r) / d + 2;
      break;
    default:
      h = (r - g) / d + 4;
  }
  h *= 60;
  return h < 0 ? h + 360 : h;
}

describe("design tokens — WCAG AA text contrast (>= 4.5:1)", () => {
  const pairs: [string, string, string][] = [
    ["ink on paper", color.ink, color.paper],
    ["ink-soft on paper", color.inkSoft, color.paper],
    ["ink on surface", color.ink, color.surface],
    ["white on moss-600", "#FFFFFF", color.moss[600]],
    ["white on sky-700", "#FFFFFF", color.sky[700]],
    ["white on apricot-700", "#FFFFFF", color.apricot[700]],
    ["white on clay-700", "#FFFFFF", color.clay[700]],
    ["ink on moss-200", color.ink, color.moss[200]],
    ["ink on sky-200", color.ink, color.sky[200]],
    ["ink on apricot-200", color.ink, color.apricot[200]],
    ["ink on sand-300", color.ink, color.sand[300]],
  ];

  it.each(pairs)("%s clears 4.5:1", (_label, fg, bg) => {
    expect(contrastRatio(fg, bg)).toBeGreaterThanOrEqual(4.5);
  });
});

describe("design tokens — palette rule: never red", () => {
  // A ~30deg band centered on true red (hue 0/360). Every accent and
  // "wrong answer" feedback tone in the palette must sit outside it —
  // this is a hard product rule (see PROTEGE_ARCHITECTURE.md §2 / AGENTS.md),
  // not a style preference.
  const RED_BAND_DEGREES = 15;

  const nonNeutralTokens: [string, string][] = [
    ["moss-700", color.moss[700]],
    ["moss-600", color.moss[600]],
    ["moss-500", color.moss[500]],
    ["moss-200", color.moss[200]],
    ["sky-700", color.sky[700]],
    ["sky-600", color.sky[600]],
    ["sky-500", color.sky[500]],
    ["sky-200", color.sky[200]],
    ["apricot-700", color.apricot[700]],
    ["apricot-600", color.apricot[600]],
    ["apricot-500", color.apricot[500]],
    ["apricot-200", color.apricot[200]],
    ["clay-700 (retry feedback)", color.clay[700]],
    ["clay-600 (retry feedback)", color.clay[600]],
    ["clay-200 (retry feedback)", color.clay[200]],
  ];

  it.each(nonNeutralTokens)("%s is not a red hue", (_name, hex) => {
    const hue = hueDegrees(hex);
    const distanceFromRed = Math.min(hue, 360 - hue);
    expect(distanceFromRed).toBeGreaterThan(RED_BAND_DEGREES);
  });
});
