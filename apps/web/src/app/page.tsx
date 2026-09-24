"use client";

import { useRouter } from "next/navigation";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { PrimaryAction } from "@/components/primitives/Button";
import { Display, Eyebrow, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";

/**
 * The real product landing page (roadmap product-entry milestone; replaces
 * the former local developer index that used to live here). One job: say
 * what PROTÉGÉ is, and offer the one way in.
 *
 * "Start Learning" navigates to `/start` -- `middleware.ts` gates that
 * route on a signed-in parent, so an unauthenticated click lands on Clerk's
 * `/sign-in` first and returns to `/start` afterward. This page never calls
 * the session API and never creates a session itself; `/start` -> `/garden`
 * -> the existing `createSession` call still own that entirely.
 */
export default function Home() {
  const router = useRouter();

  return (
    <main
      id="main"
      className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center px-6 py-16 text-center"
    >
      <Stack align="center" gap="lg">
        <div>
          <Eyebrow>PROTÉGÉ</Eyebrow>
          <Display as="h1" className="mt-1">
            A warm little world that happens to teach fractions.
          </Display>
          <Text muted className="mt-3">
            Learn it, practice it, explain it, teach Sprout — then prove you really know it.
          </Text>
        </div>

        <PrimaryAction size="lg" onClick={() => router.push("/start")}>
          Start Learning
        </PrimaryAction>

        <SoftPanel elevation="raised" className="mt-4 max-w-sm">
          <Text muted className="text-sm">
            For grown-ups: you&apos;ll sign in first, then hand the device to your child.
          </Text>
        </SoftPanel>
      </Stack>
    </main>
  );
}
