"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { SceneFrame } from "@/components/primitives/SceneFrame";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { ErrorState } from "@/components/primitives/ErrorState";
import { Display, Heading, Text, Eyebrow } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";
import { Sprout } from "@/components/sprout/Sprout";
import { ApiProblemError, protegeApi } from "@/lib/protege-api-client";

/**
 * The authenticated product-entry bootstrap step (roadmap product-entry
 * milestone). Reached only once `middleware.ts` has already required a
 * signed-in parent (same gate as `/garden`/`/session`). Its entire job is
 * `POST /v1/learners/ensure` -> a real, owned `learner_id` -> handing off
 * to the existing, unmodified `/garden?learnerId=...` -> createSession ->
 * `/session/[sessionId]` chain. It never creates a session itself and
 * never holds any learning state -- nothing here is persisted client-side.
 */
function StartContent() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const inFlightRef = useRef(false);

  // `bootstrap` must fire exactly once automatically (on mount) and
  // otherwise only in direct response to the retry click below -- never as
  // a side effect of a re-render. Both callback and effect deliberately
  // hold empty dependency arrays rather than depending on `router`: Next's
  // real `useRouter()` is stable, but relying on that stability to gate
  // re-firing would make an automatic network call each time it wasn't,
  // which is worse than reading `router` from a closure once.
  const bootstrap = useCallback(async () => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    setError(null);
    try {
      const learner = await protegeApi.ensureLearner();
      router.replace(`/garden?learnerId=${encodeURIComponent(learner.learner_id)}`);
    } catch (err) {
      inFlightRef.current = false;
      setError(err instanceof ApiProblemError ? err.childSafeMessage : "Let's try that again.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <SceneFrame sceneKey="start" tone="child">
      <Stack align="center" gap="md" className="max-w-md text-center">
        {error ? (
          <ErrorState
            title="One moment — I got a little muddled."
            message={error}
            onRetry={() => void bootstrap()}
          />
        ) : (
          <>
            <Sprout emotion="thinking" misconceptionState="unresolved" size="lg" show />
            <SoftPanel elevation="floating" className="w-full">
              <Eyebrow>Getting ready</Eyebrow>
              <Heading as="h1" className="mt-1 text-2xl">
                Finding your garden…
              </Heading>
              <Text muted className="mt-2">
                Just a moment while Sprout gets things ready.
              </Text>
            </SoftPanel>
          </>
        )}
      </Stack>
    </SceneFrame>
  );
}

export default function StartPage() {
  return (
    <Stack gap="lg">
      <Display as="h1" className="sr-only">
        Getting started
      </Display>
      <StartContent />
    </Stack>
  );
}
