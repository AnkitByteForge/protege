"use client";

import { useMemo, useState } from "react";
import { Sprout } from "@/components/sprout/Sprout";
import {
  BROW_IDS,
  EYE_IDS,
  MOUTH_IDS,
  POSE_IDS,
  TOTAL_EXPRESSIONS,
  type BrowId,
  type EyeId,
  type MisconceptionState,
  type MouthId,
  type PoseId,
  type SproutEmotion,
} from "@/components/sprout";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Button } from "@/components/primitives/Button";
import { Display, Eyebrow, Heading, Text } from "@/components/primitives/Typography";
import { Inline, Stack } from "@/components/primitives/Stack";
import { GallerySection } from "@/app/gallery/_components/GallerySection";

const EMOTIONS: SproutEmotion[] = ["confused", "thinking", "dawning", "delighted"];

function randomFrom<T>(items: readonly T[]): T {
  return items[Math.floor(Math.random() * items.length)];
}

export default function SproutGalleryPage() {
  const [emotion, setEmotion] = useState<SproutEmotion>("confused");
  const [misconceptionState, setMisconceptionState] = useState<MisconceptionState>("unresolved");
  const [leafCount, setLeafCount] = useState(2);
  const [utterance, setUtterance] = useState("Wait — is 1/8 really bigger than 1/4?");
  const [show, setShow] = useState(true);

  const [eye, setEye] = useState<EyeId>("round");
  const [mouth, setMouth] = useState<MouthId>("flat");
  const [brow, setBrow] = useState<BrowId>("flat");
  const [pose, setPose] = useState<PoseId>("thinking");

  const willBeClamped = emotion === "delighted" && misconceptionState !== "resolved";

  const rigExpression = useMemo(() => ({ eye, mouth, brow, pose }), [eye, mouth, brow, pose]);

  return (
    <main id="main" className="mx-auto max-w-4xl px-4 py-10 sm:px-8">
      <Stack gap="sm" className="mb-10">
        <Eyebrow>Sprout visual system — roadmap P14</Eyebrow>
        <Display as="h1">Inspecting the rig</Display>
        <Text muted className="max-w-2xl">
          {TOTAL_EXPRESSIONS} possible expressions (5 eyes x 6 mouths x 4 brows x 4 poses),
          assembled from 19 reusable SVG parts. This page exists so the full rig can be inspected
          without any backend or session integration — no learning content ships here.
        </Text>
      </Stack>

      <Stack gap="xl">
        <GallerySection
          id="learning-state"
          title="Driven by learning state, not sentiment"
          description="Sprout's expression comes from the emotion + misconception-resolution-state props — exactly what a real session would supply (SproutTurn.emotion, MisconceptionBelief.state). There is no separate client-side mood."
        >
          <Inline gap="lg" align="start" className="flex-wrap">
            <SoftPanel elevation="floating" className="flex w-64 flex-col items-center gap-4 py-8">
              <Sprout
                emotion={emotion}
                misconceptionState={misconceptionState}
                leafCount={leafCount}
                utterance={utterance || undefined}
                show={show}
              />
            </SoftPanel>

            <Stack gap="md" className="min-w-64 flex-1">
              <div>
                <Text className="mb-2 font-bold">Emotion (from SproutTurn.emotion)</Text>
                <Inline gap="xs">
                  {EMOTIONS.map((e) => (
                    <Button
                      key={e}
                      size="md"
                      variant={emotion === e ? "primary" : "secondary"}
                      onClick={() => setEmotion(e)}
                    >
                      {e}
                    </Button>
                  ))}
                </Inline>
              </div>

              <div>
                <Text className="mb-2 font-bold">
                  Misconception state (from MisconceptionBelief.state)
                </Text>
                <Inline gap="xs">
                  <Button
                    size="md"
                    tone="clay"
                    variant={misconceptionState === "unresolved" ? "primary" : "secondary"}
                    onClick={() => setMisconceptionState("unresolved")}
                  >
                    unresolved
                  </Button>
                  <Button
                    size="md"
                    tone="moss"
                    variant={misconceptionState === "resolved" ? "primary" : "secondary"}
                    onClick={() => setMisconceptionState("resolved")}
                  >
                    resolved
                  </Button>
                </Inline>
              </div>

              {willBeClamped && (
                <SoftPanel elevation="flat" className="border-clay-600/40 bg-clay-200/40">
                  <Text className="text-sm font-semibold">
                    Safety rule engaged: &quot;delighted&quot; is requested but the misconception is
                    still unresolved, so Sprout is shown as &quot;dawning&quot; instead. Try
                    resolving it above.
                  </Text>
                </SoftPanel>
              )}

              <div>
                <Text className="mb-2 font-bold">Leaves grown</Text>
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
              </div>

              <div>
                <Text className="mb-2 font-bold">Speech bubble</Text>
                <input
                  value={utterance}
                  onChange={(e) => setUtterance(e.target.value)}
                  className="w-full rounded-xl border-2 border-sand-300 bg-surface-raised px-4 py-2 font-sans text-base text-ink"
                  placeholder="Sprout's line..."
                />
              </div>

              <Button size="md" variant="secondary" onClick={() => setShow((v) => !v)}>
                {show ? "Play exit choreography" : "Play entrance choreography"}
              </Button>
            </Stack>
          </Inline>
        </GallerySection>

        <GallerySection
          id="raw-rig"
          title="The raw 480-point rig"
          description="For engineering/QA use only: drives eye, mouth, brow and pose directly, bypassing the emotion mapping entirely (via Sprout's expressionOverride escape hatch)."
        >
          <Inline gap="lg" align="start" className="flex-wrap">
            <SoftPanel elevation="floating" className="flex w-64 flex-col items-center gap-4 py-8">
              <Sprout
                emotion="confused"
                misconceptionState="unresolved"
                expressionOverride={rigExpression}
              />
            </SoftPanel>

            <Stack gap="md" className="min-w-64 flex-1">
              <PartPicker label="Eye" ids={EYE_IDS} value={eye} onChange={setEye} />
              <PartPicker label="Mouth" ids={MOUTH_IDS} value={mouth} onChange={setMouth} />
              <PartPicker label="Brow" ids={BROW_IDS} value={brow} onChange={setBrow} />
              <PartPicker label="Pose" ids={POSE_IDS} value={pose} onChange={setPose} />

              <Button
                size="md"
                variant="secondary"
                onClick={() => {
                  setEye(randomFrom(EYE_IDS));
                  setMouth(randomFrom(MOUTH_IDS));
                  setBrow(randomFrom(BROW_IDS));
                  setPose(randomFrom(POSE_IDS));
                }}
              >
                Random expression
              </Button>
            </Stack>
          </Inline>
        </GallerySection>
      </Stack>
    </main>
  );
}

function PartPicker<T extends string>({
  label,
  ids,
  value,
  onChange,
}: {
  label: string;
  ids: readonly T[];
  value: T;
  onChange: (id: T) => void;
}) {
  return (
    <div>
      <Heading as="h3" className="mb-2 text-base">
        {label}
      </Heading>
      <Inline gap="xs">
        {ids.map((id) => (
          <Button
            key={id}
            size="md"
            variant={value === id ? "primary" : "secondary"}
            onClick={() => onChange(id)}
          >
            {id}
          </Button>
        ))}
      </Inline>
    </div>
  );
}
