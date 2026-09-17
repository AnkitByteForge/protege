"use client";

import { useState } from "react";
import { SceneFrame } from "@/components/primitives/SceneFrame";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { LeafProgress } from "@/components/primitives/LeafProgress";
import { PrimaryAction, SecondaryAction } from "@/components/primitives/Button";
import { SpeechBubble } from "@/components/primitives/SpeechBubble";
import { Display, Text, Eyebrow } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";

/**
 * Infrastructure preview only — NOT a product scene. This page exists to
 * prove `SceneFrame` gives continuous, non-page-swap transitions (roadmap
 * P12 exit criterion: "three sample scenes cross-fade without layout
 * jump"). The actual Sprout/Diagnostic/Discovery/... scenes arrive in
 * P14–P16 and will render inside this exact frame.
 */
const sampleScenes = [
  {
    key: "arrival",
    eyebrow: "Sample scene 1 of 3",
    title: "A place, not a page",
    body: "This frame — the sky, the hills, the light — stays put while what's inside it changes. That's the whole idea.",
  },
  {
    key: "a-visitor",
    eyebrow: "Sample scene 2 of 3",
    title: "Someone to talk to",
    body: "A future scene puts a character here — this is only the shell they'll speak from.",
    speech: "Hello! I'm just a placeholder bubble for now.",
  },
  {
    key: "onward",
    eyebrow: "Sample scene 3 of 3",
    title: "Progress that shows itself",
    body: "Just leaves that grow as real understanding shows itself — nothing to count, nothing to compare.",
  },
] as const;

export default function WorldPreviewPage() {
  const [index, setIndex] = useState(0);
  const scene = sampleScenes[index];

  return (
    <Stack gap="lg">
      <div>
        <Eyebrow>(child) route group — design-system preview</Eyebrow>
        <Display as="h1">The garden</Display>
        <Text muted className="mt-1 max-w-xl">
          This page demonstrates the shared <code>SceneFrame</code>. No learning content ships here
          yet — that&apos;s later phases.
        </Text>
      </div>

      <SceneFrame
        sceneKey={scene.key}
        tone="child"
        header={
          <LeafProgress count={index + 1} total={sampleScenes.length} label="Preview progress" />
        }
      >
        <Stack align="center" gap="md" className="max-w-md text-center">
          <SoftPanel elevation="floating" className="w-full">
            <Eyebrow>{scene.eyebrow}</Eyebrow>
            <h2 className="mt-1 font-display text-2xl font-bold text-ink">{scene.title}</h2>
            <Text muted className="mt-2">
              {scene.body}
            </Text>
          </SoftPanel>

          {"speech" in scene && <SpeechBubble text={scene.speech} tailFrom="bottom" />}

          <div className="flex gap-3 pt-2">
            <SecondaryAction
              size="md"
              onClick={() => setIndex((i) => (i - 1 + sampleScenes.length) % sampleScenes.length)}
            >
              Back
            </SecondaryAction>
            <PrimaryAction size="md" onClick={() => setIndex((i) => (i + 1) % sampleScenes.length)}>
              Next scene
            </PrimaryAction>
          </div>
        </Stack>
      </SceneFrame>
    </Stack>
  );
}
