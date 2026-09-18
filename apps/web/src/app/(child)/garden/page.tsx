"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SceneFrame } from "@/components/primitives/SceneFrame";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { PrimaryAction } from "@/components/primitives/Button";
import { ErrorState } from "@/components/primitives/ErrorState";
import { Display, Heading, Text, Eyebrow } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import { Sprout } from "@/components/sprout/Sprout";
import { ApiProblemError, protegeApi } from "@/lib/protege-api-client";

/**
 * The pre-session lobby (roadmap P15 "garden home"). Deliberately not
 * itself an FSM state -- `POST /v1/sessions` doesn't exist to call until
 * the child presses "Start," and the server's own `ARRIVAL`/`SPROUT_TEASE`
 * preamble only begins once it does (see `engine/runtime.py`'s
 * `create_session`, which advances through both synchronously). This
 * screen is the deliberate beat *before* that call.
 *
 * `learnerId` arrives as a query param rather than a picker backed by real
 * data: P10 ships no "list my learners" or "create a learner" endpoint
 * (only `GET /v1/learners/{id}/state`/`/proof`/`/tutor-brief`, all keyed by
 * an id you must already have) -- that's parent-onboarding surface P15 has
 * no contract to build against, and inventing one here would mean either a
 * second, ad-hoc learner store or a fabricated UI backed by nothing. See
 * the final P15 report for this disclosed gap.
 */
function GardenHomeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const learnerId = searchParams.get("learnerId");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStart = async () => {
    if (!learnerId) return;
    setStarting(true);
    setError(null);
    try {
      const session = await protegeApi.createSession({ learnerId });
      router.push(`/session/${session.session_id}`);
    } catch (err) {
      setStarting(false);
      setError(err instanceof ApiProblemError ? err.childSafeMessage : "Let's try that again.");
    }
  };

  return (
    <SceneFrame sceneKey="garden-home" tone="child">
      <Stack align="center" gap="md" className="max-w-md text-center">
        {!learnerId ? (
          <ErrorState
            title="No garden picked yet"
            message="A grown-up needs to open this garden for you first."
          />
        ) : error ? (
          <ErrorState
            title="One moment — I got a little muddled."
            message={error}
            onRetry={handleStart}
          />
        ) : (
          <>
            <Sprout emotion="thinking" misconceptionState="unresolved" size="lg" show />
            <SoftPanel elevation="floating" className="w-full">
              <Eyebrow>Welcome back</Eyebrow>
              <Heading as="h1" className="mt-1 text-2xl">
                Ready to visit the garden?
              </Heading>
              <Text muted className="mt-2">
                Sprout has been waiting for you.
              </Text>
            </SoftPanel>
            <PrimaryAction size="lg" disabled={starting} onClick={() => void handleStart()}>
              {starting ? "Walking in…" : "Start"}
            </PrimaryAction>
          </>
        )}
      </Stack>
    </SceneFrame>
  );
}

export default function GardenHomePage() {
  return (
    <Stack gap="lg">
      <Display as="h1" className="sr-only">
        The garden
      </Display>
      <Suspense fallback={null}>
        <GardenHomeContent />
      </Suspense>
    </Stack>
  );
}
