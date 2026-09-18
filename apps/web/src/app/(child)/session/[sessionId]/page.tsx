"use client";

import { use, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { SceneFrame } from "@/components/primitives/SceneFrame";
import { LeafProgress } from "@/components/primitives/LeafProgress";
import { ErrorState } from "@/components/primitives/ErrorState";
import { SessionSceneRouter } from "@/components/session/SessionSceneRouter";
import { EvidenceSidebar } from "@/components/session/EvidenceSidebar";
import { useSessionController } from "@/hooks/useSessionController";

function SessionExperience({ sessionId }: { sessionId: string }) {
  const searchParams = useSearchParams();
  const showEvidence = searchParams.get("demo") === "1";
  const controller = useSessionController(sessionId);

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
      <div className="flex-1">
        <SceneFrame
          sceneKey={controller.sceneState ?? "loading"}
          tone="child"
          header={<LeafProgress count={0} label="Session progress" />}
        >
          {controller.error ? (
            <ErrorState message={controller.error.child_safe_message} />
          ) : (
            <SessionSceneRouter
              sceneState={controller.sceneState}
              payload={controller.payload}
              onSubmit={controller.submitEvent}
              submitting={controller.submitting}
            />
          )}
        </SceneFrame>
      </div>
      {showEvidence && (
        <EvidenceSidebar
          turnHistory={controller.turnHistory}
          serverState={controller.serverState}
        />
      )}
    </div>
  );
}

export default function SessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  return (
    <Suspense fallback={null}>
      <SessionExperience sessionId={sessionId} />
    </Suspense>
  );
}
