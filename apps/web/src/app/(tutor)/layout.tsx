import type { ReactNode } from "react";
import { SceneBackground } from "@/components/illustrations/SceneBackground";

/**
 * The tutor register: the calmest of the three — a working tool for a
 * professional who needs to scan quickly, still built from the same warm
 * palette so it reads as the same product, not a separate admin console.
 */
export default function TutorLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen">
      <SceneBackground tone="tutor" />
      <div className="relative mx-auto flex min-h-screen max-w-3xl flex-col px-4 sm:px-8">
        <header className="flex items-center gap-2 py-6">
          <span className="font-display text-xl font-extrabold text-ink">PROTÉGÉ</span>
          <span className="font-sans text-sm text-ink-soft">tutor briefing</span>
        </header>
        <main id="main" className="flex-1 pb-16">
          {children}
        </main>
      </div>
    </div>
  );
}
