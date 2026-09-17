"use client";

import { useState } from "react";
import { GallerySection } from "@/app/gallery/_components/GallerySection";
import { Display, Heading, Subheading, Text, Eyebrow } from "@/components/primitives/Typography";
import { Stack, Inline } from "@/components/primitives/Stack";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { InteractionSurface } from "@/components/primitives/InteractionSurface";
import { Button } from "@/components/primitives/Button";
import { FractionBar } from "@/components/manipulatives/FractionBar";
import { NumberLine } from "@/components/manipulatives/NumberLine";
import { AreaModel, type AreaModelShape } from "@/components/manipulatives/AreaModel";
import { ExplanationCards } from "@/components/manipulatives/ExplanationCards";
import { useManipulativeTrace } from "@/components/manipulatives/useManipulativeTrace";

const sections = [
  ["fraction-bar", "FractionBar"],
  ["number-line", "NumberLine"],
  ["area-model", "AreaModel"],
  ["explanation-cards", "ExplanationCards"],
  ["trace", "Trace log"],
] as const;

/**
 * Realistic fraction-learning scenarios for every P13 manipulative,
 * wired to one shared trace so a reviewer can watch the exact
 * `{t, action, target(s)}` record each interaction produces — the same
 * evidence the Diagnostician will eventually read. Not a product scene:
 * roadmap P15 assembles the real session screens around these primitives.
 */
export default function ManipulativesGalleryPage() {
  const { trace, record, reset } = useManipulativeTrace();

  // FractionBar scenario — partition, drag, align.
  const [childNumerator, setChildNumerator] = useState(1);
  const [childDenominator, setChildDenominator] = useState(4);

  // NumberLine scenario — place, snap, compare.
  const [markers, setMarkers] = useState([
    { id: "quarter", value: 0.25, label: "1/4", tone: "sky" as const },
    { id: "eighth", value: 0.75, label: "1/8", tone: "apricot" as const },
  ]);

  // AreaModel scenario — compare representations.
  const [areaNumerator, setAreaNumerator] = useState(1);
  const [areaShape, setAreaShape] = useState<AreaModelShape>("circle");

  // ExplanationCards scenario — non-verbal teach-back.
  const [explanationId, setExplanationId] = useState<string | null>(null);

  return (
    <main id="main" className="mx-auto max-w-4xl px-4 py-10 sm:px-8">
      <Stack gap="sm" className="mb-10">
        <Eyebrow>Manipulatives gallery — roadmap P13</Eyebrow>
        <Display as="h1">Things a child can think with</Display>
        <Text muted className="max-w-2xl">
          Every interaction primitive from the roadmap, in the fraction scenarios they were built
          for. Each one reports a faithful trace — nothing here invents a &ldquo;correct&rdquo;
          outcome; the trace log at the bottom shows exactly what these components know: what
          happened, not whether it was right.
        </Text>
      </Stack>

      <nav aria-label="Manipulatives gallery sections" className="mb-10">
        <Inline gap="xs" as="ul" className="list-none p-0">
          {sections.map(([id, label]) => (
            <li key={id}>
              <a
                href={`#${id}`}
                className="rounded-full border border-sand-300 bg-surface-raised px-3 py-1.5 font-sans text-sm font-bold text-ink-soft transition-colors hover:border-sky-700 hover:text-sky-700"
              >
                {label}
              </a>
            </li>
          ))}
        </Inline>
      </nav>

      <Stack gap="xl">
        <GallerySection
          id="fraction-bar"
          title="FractionBar"
          description="Partition, drag, align, compare — with magnetic snapping and hysteresis. Drag the second bar's edge (or use arrow keys) until it lines up with the reference above; try dragging the small grip to repartition it first."
        >
          <InteractionSurface label="Fraction bar comparison">
            <Stack gap="lg" className="w-full items-center">
              <Stack gap="xs" align="center">
                <Subheading className="text-base">Reference: one quarter</Subheading>
                <FractionBar
                  label="Reference: one quarter"
                  numerator={1}
                  denominator={4}
                  tone="sky"
                />
              </Stack>

              <Stack gap="xs" align="center">
                <Subheading className="text-base">Yours — match it</Subheading>
                <FractionBar
                  label="Your fraction bar"
                  numerator={childNumerator}
                  denominator={childDenominator}
                  onNumeratorChange={(n) => {
                    setChildNumerator(n);
                  }}
                  onDenominatorChange={(d) => {
                    setChildDenominator(d);
                    setChildNumerator((n) => Math.min(n, d));
                  }}
                  alignTo={0.25}
                  tone="moss"
                  onTrace={record}
                />
                <Text muted className="text-sm">
                  {childNumerator}/{childDenominator} filled
                </Text>
              </Stack>
            </Stack>
          </InteractionSurface>
        </GallerySection>

        <GallerySection
          id="number-line"
          title="NumberLine"
          description="Place fractions on a shared line and watch their left-to-right order — a spatial fact, reported as-is, never scored. Drag a marker or focus it and use the arrow keys."
        >
          <InteractionSurface label="Number line comparison">
            <NumberLine
              label="Compare 1/4 and 1/8"
              denominator={8}
              markers={markers}
              onMarkerChange={(id, value) =>
                setMarkers((prev) => prev.map((m) => (m.id === id ? { ...m, value } : m)))
              }
              compareIds={["quarter", "eighth"] as const}
              onTrace={record}
              width={440}
            />
          </InteractionSurface>
        </GallerySection>

        <GallerySection
          id="area-model"
          title="AreaModel"
          description="Fraction partitioning as shaded regions instead of a line. Click a wedge (or a cell) to shade up to it, or use the arrow keys; switch shapes to compare representations of the same fraction."
        >
          <InteractionSurface label="Area model">
            <AreaModel
              label="Shade a fraction of the shape"
              numerator={areaNumerator}
              denominator={4}
              shape={areaShape}
              onNumeratorChange={setAreaNumerator}
              onShapeChange={setAreaShape}
              tone="apricot"
              onTrace={record}
            />
          </InteractionSurface>
        </GallerySection>

        <GallerySection
          id="explanation-cards"
          title="ExplanationCards"
          description="The non-verbal teach-back channel: a child who can't or won't say the answer aloud picks the picture that matches what they understand instead. Exactly three choices, full keyboard support (arrow keys move and select)."
        >
          <InteractionSurface label="Non-verbal explanation">
            <Stack gap="md" className="w-full items-center">
              <Text className="text-center font-bold">
                Why does 1/8 fit inside 1/4 with room to spare?
              </Text>
              <ExplanationCards
                label="Why does 1/8 fit inside 1/4 with room to spare?"
                selectedId={explanationId}
                onSelect={setExplanationId}
                onTrace={record}
                className="w-full max-w-xl"
                options={
                  [
                    { id: "smaller-slices", label: "More slices means smaller slices", icon: "🍕" },
                    { id: "same-slices", label: "The slices stay the same size", icon: "🧩" },
                    { id: "bigger-whole", label: "The whole pizza got bigger", icon: "🍰" },
                  ] as const
                }
              />
            </Stack>
          </InteractionSurface>
        </GallerySection>

        <GallerySection
          id="trace"
          title="Trace log"
          description="Every interaction above, in order, exactly as it will reach the Diagnostician: {t, action, target(s)}. This panel is a debugging view — the child never sees it."
        >
          <SoftPanel elevation="flat" className="w-full">
            <Inline gap="sm" className="mb-3 justify-between">
              <Heading as="h3" className="text-lg">
                {trace.length} event{trace.length === 1 ? "" : "s"} recorded
              </Heading>
              <Button size="md" variant="secondary" onClick={reset}>
                Clear trace
              </Button>
            </Inline>
            {trace.length === 0 ? (
              <Text muted>Interact with anything above — every action appears here.</Text>
            ) : (
              <ol className="flex max-h-72 flex-col gap-1.5 overflow-y-auto font-mono text-sm">
                {trace.map((entry, i) => (
                  <li
                    key={i}
                    className="flex items-baseline gap-3 rounded-lg bg-surface-raised px-3 py-1.5"
                  >
                    <span className="text-ink-soft">{entry.t.toFixed(3)}s</span>
                    <span className="font-bold text-ink">{entry.action}</span>
                    {entry.target && <span className="text-ink-soft">{entry.target}</span>}
                    {entry.targets && (
                      <span className="text-ink-soft">[{entry.targets.join(", ")}]</span>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </SoftPanel>
        </GallerySection>
      </Stack>
    </main>
  );
}
