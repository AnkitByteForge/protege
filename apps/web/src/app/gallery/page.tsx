"use client";

import { useState } from "react";
import Link from "next/link";
import { SceneFrame } from "@/components/primitives/SceneFrame";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Button, PrimaryAction, SecondaryAction } from "@/components/primitives/Button";
import { ChoiceButton } from "@/components/primitives/ChoiceButton";
import { SpeechBubble } from "@/components/primitives/SpeechBubble";
import { LeafProgress } from "@/components/primitives/LeafProgress";
import { LoadingState } from "@/components/primitives/LoadingState";
import { ErrorState } from "@/components/primitives/ErrorState";
import { InteractionSurface } from "@/components/primitives/InteractionSurface";
import { Display, Heading, Subheading, Text, Eyebrow } from "@/components/primitives/Typography";
import { Stack, Inline } from "@/components/primitives/Stack";
import { GallerySection } from "@/app/gallery/_components/GallerySection";
import { ColorSwatches } from "@/app/gallery/_components/ColorSwatches";
import { MotionPlayground } from "@/app/gallery/_components/MotionPlayground";

const sections = [
  ["typography", "Typography"],
  ["color", "Color"],
  ["buttons", "Buttons"],
  ["choices", "Choice controls"],
  ["panels", "Panels"],
  ["speech", "Speech bubble"],
  ["progress", "Leaf progress"],
  ["scene", "SceneFrame"],
  ["states", "Loading & recovery"],
  ["motion", "Motion"],
] as const;

export default function GalleryPage() {
  const [leafCount, setLeafCount] = useState(2);
  const [choice, setChoice] = useState<string | null>("Pizza");
  const [sceneKey, setSceneKey] = useState("a");
  const [loading, setLoading] = useState(false);
  const [recovering, setRecovering] = useState(false);

  return (
    <main id="main" className="mx-auto max-w-4xl px-4 py-10 sm:px-8">
      <Stack gap="sm" className="mb-10">
        <Eyebrow>Design system gallery — roadmap P12</Eyebrow>
        <Display as="h1">The PROTÉGÉ visual language</Display>
        <Text muted className="max-w-2xl">
          Every reusable primitive the child, parent, and tutor experiences are built from. This
          page is infrastructure, not product — it exists so the visual system can be judged as a
          whole before any scene is built on top of it.
        </Text>
        <Link
          href="/gallery/manipulatives"
          className="inline-block w-fit rounded-full border border-sand-300 bg-surface-raised px-4 py-2 font-sans text-sm font-bold text-sky-700 transition-colors hover:border-sky-700"
        >
          → Manipulatives gallery (roadmap P13): FractionBar, NumberLine, AreaModel,
          ExplanationCards
        </Link>
      </Stack>

      <nav aria-label="Gallery sections" className="mb-10">
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
          id="typography"
          title="Typography"
          description="Baloo 2 for display/headings (rounded, high x-height), Nunito for body and UI text. No condensed or narrow faces anywhere."
        >
          <Stack gap="sm">
            <Display as="div">Display — The garden grows</Display>
            <Heading as="div">Heading — Sprout has a question</Heading>
            <Subheading as="div">Subheading — Three of five leaves</Subheading>
            <Text>Body text — used for everything a child or parent reads at length.</Text>
            <Text muted>Muted body text — secondary detail, still comfortably readable.</Text>
            <Eyebrow>Eyebrow label</Eyebrow>
          </Stack>
        </GallerySection>

        <GallerySection
          id="color"
          title="Color"
          description="Warm moss / sand / sky / apricot, plus clay for gentle 'not yet' feedback. Red never appears anywhere in this palette. Every text pairing shown clears WCAG AA (4.5:1)."
        >
          <ColorSwatches />
        </GallerySection>

        <GallerySection
          id="buttons"
          title="Buttons"
          description="One Button primitive; PrimaryAction and SecondaryAction are preconfigured shortcuts. Large (60px) touch targets by default."
        >
          <Stack gap="md">
            <Inline gap="sm">
              <PrimaryAction>Primary action</PrimaryAction>
              <SecondaryAction>Secondary action</SecondaryAction>
              <Button variant="ghost">Ghost</Button>
              <Button disabled>Disabled</Button>
            </Inline>
            <Inline gap="sm">
              <Button tone="sky">Sky</Button>
              <Button tone="apricot">Apricot</Button>
              <Button tone="clay">Clay</Button>
              <Button size="md">Medium size</Button>
            </Inline>
          </Stack>
        </GallerySection>

        <GallerySection
          id="choices"
          title="Choice controls"
          description="The non-verbal explanation / multiple-choice primitive. Selected state is moss, never red for the alternative — a choice is just picked or not."
        >
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {["Pizza", "Pie", "Chocolate bar", "Ribbon"].map((label) => (
              <ChoiceButton
                key={label}
                selected={choice === label}
                onSelect={() => setChoice(label)}
                icon={
                  label === "Pizza"
                    ? "🍕"
                    : label === "Pie"
                      ? "🥧"
                      : label === "Chocolate bar"
                        ? "🍫"
                        : "🎀"
                }
              >
                {label}
              </ChoiceButton>
            ))}
          </div>
        </GallerySection>

        <GallerySection
          id="panels"
          title="Panels"
          description="SoftPanel — the opaque, warm-tinted surface. Three elevations, no glassmorphism."
        >
          <Inline gap="md" align="stretch">
            <SoftPanel elevation="flat" className="w-48">
              <Text className="font-bold">flat</Text>
              <Text muted className="text-sm">
                No shadow — sits flush with the page.
              </Text>
            </SoftPanel>
            <SoftPanel elevation="raised" className="w-48">
              <Text className="font-bold">raised</Text>
              <Text muted className="text-sm">
                Default card elevation.
              </Text>
            </SoftPanel>
            <SoftPanel elevation="floating" className="w-48">
              <Text className="font-bold">floating</Text>
              <Text muted className="text-sm">
                Modals, callouts, error states.
              </Text>
            </SoftPanel>
          </Inline>
        </GallerySection>

        <GallerySection
          id="speech"
          title="Speech bubble"
          description="A shell only — no character is implied. Typewriter reveal is timed for future TTS and skips straight to full text under reduced motion."
        >
          <Inline gap="lg" align="start">
            <SpeechBubble tailFrom="left" text="Wait — is 1/8 really bigger than 1/4?" />
            <SpeechBubble tailFrom="right" text="More pieces means smaller pieces!" />
          </Inline>
        </GallerySection>

        <GallerySection
          id="progress"
          title="Leaf progress"
          description="Replaces every percentage in the product. Leaves fill with the pop spring, never a number on screen."
        >
          <Stack gap="sm" align="start">
            <LeafProgress count={leafCount} />
            <Inline gap="xs">
              <Button
                size="md"
                variant="secondary"
                onClick={() => setLeafCount((n) => Math.max(0, n - 1))}
              >
                − leaf
              </Button>
              <Button
                size="md"
                variant="secondary"
                onClick={() => setLeafCount((n) => Math.min(5, n + 1))}
              >
                + leaf
              </Button>
            </Inline>
          </Stack>
        </GallerySection>

        <GallerySection
          id="scene"
          title="SceneFrame"
          description="The shared frame every future child scene renders inside. The background and header persist; only the inner content cross-fades — a continuous world, not page swaps."
        >
          <SceneFrame
            sceneKey={sceneKey}
            tone="child"
            header={<LeafProgress count={sceneKey === "a" ? 1 : sceneKey === "b" ? 3 : 5} />}
          >
            <Stack align="center" gap="md" className="text-center">
              <SoftPanel elevation="floating" className="max-w-sm">
                <Subheading>Sample content {sceneKey.toUpperCase()}</Subheading>
                <Text muted className="mt-1">
                  Click below to swap scenes and watch the frame stay put.
                </Text>
              </SoftPanel>
              <Inline gap="xs">
                {(["a", "b", "c"] as const).map((k) => (
                  <Button
                    key={k}
                    size="md"
                    variant={sceneKey === k ? "primary" : "secondary"}
                    onClick={() => setSceneKey(k)}
                  >
                    Scene {k.toUpperCase()}
                  </Button>
                ))}
              </Inline>
            </Stack>
          </SceneFrame>

          <div className="mt-6">
            <Subheading className="mb-2 text-base">InteractionSurface</Subheading>
            <InteractionSurface label="Sample manipulative area">
              <Text muted>Future manipulatives (fraction bars, number lines) render here.</Text>
            </InteractionSurface>
          </div>
        </GallerySection>

        <GallerySection
          id="states"
          title="Loading & recovery"
          description="'Thinking' replaces every spinner; failures are always in-character, never a stack trace or a red banner."
        >
          <Inline gap="lg" align="start">
            <SoftPanel className="w-72">
              <Button size="md" variant="secondary" onClick={() => setLoading((v) => !v)}>
                {loading ? "Hide" : "Show"} thinking state
              </Button>
              {loading && <LoadingState />}
            </SoftPanel>
            <div className="w-72">
              <Button
                size="md"
                variant="secondary"
                onClick={() => setRecovering((v) => !v)}
                className="mb-3"
              >
                {recovering ? "Hide" : "Show"} recovery state
              </Button>
              {recovering && (
                <ErrorState
                  message="I need a snack — let's do a puzzle while I get my thoughts back."
                  onRetry={() => setRecovering(false)}
                />
              )}
            </div>
          </Inline>
        </GallerySection>

        <GallerySection
          id="motion"
          title="Motion"
          description="Four named spring presets — settle, pop, wobble, drift. Everything interactive reaches for one of these rather than a one-off transition."
        >
          <MotionPlayground />
        </GallerySection>
      </Stack>
    </main>
  );
}
