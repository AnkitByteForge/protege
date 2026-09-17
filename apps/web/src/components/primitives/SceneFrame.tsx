import type { ReactNode } from "react";
import { SceneBackground, type WorldTone } from "@/components/illustrations/SceneBackground";
import { SceneTransition } from "@/components/motion/SceneTransition";
import { cn } from "@/lib/cn";

export interface SceneFrameProps {
  /** Identifies the current scene; changing it triggers the cross-fade in `SceneTransition`. */
  sceneKey: string;
  tone?: WorldTone;
  /** Persistent chrome that never re-mounts on scene change — e.g. leaf progress, a pause control. */
  header?: ReactNode;
  children: ReactNode;
  className?: string;
}

/**
 * The single shared frame every child scene (Sprout, Diagnostic, Discovery,
 * Guided Learning, Practice, Teach-back, Verification, Transfer, Reward,
 * Summary — roadmap P15+) will render inside. It owns:
 *   - the persistent world backdrop (never unmounts between scenes)
 *   - persistent chrome (progress, controls)
 *   - the one scene-to-scene transition (via `SceneTransition`)
 *
 * P12 ships this shell only — no product scene renders inside it yet.
 */
export function SceneFrame({
  sceneKey,
  tone = "child",
  header,
  children,
  className,
}: SceneFrameProps) {
  return (
    <div
      className={cn("relative isolate min-h-[36rem] w-full overflow-hidden rounded-2xl", className)}
    >
      <SceneBackground tone={tone} />

      <div className="relative flex min-h-[36rem] flex-col">
        {header && <div className="flex items-center justify-between px-6 pt-6">{header}</div>}

        <div className="flex flex-1 items-center justify-center px-6 py-8">
          <SceneTransition sceneKey={sceneKey}>{children}</SceneTransition>
        </div>
      </div>
    </div>
  );
}
