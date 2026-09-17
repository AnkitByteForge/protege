import type { ReactNode } from "react";
import { SceneBackground } from "@/components/illustrations/SceneBackground";

/**
 * The parent register: calmer light, no ambient clouds/particles, a small
 * amount of real wayfinding chrome (parents are adults navigating a real
 * interface — unlike the child world, a header here is appropriate).
 */
export default function ParentLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen">
      <SceneBackground tone="parent" />
      <div className="relative mx-auto flex min-h-screen max-w-3xl flex-col px-4 sm:px-8">
        <header className="flex items-center gap-2 py-6">
          <span className="font-display text-xl font-extrabold text-ink">PROTÉGÉ</span>
          <span className="font-sans text-sm text-ink-soft">for families</span>
        </header>
        <main id="main" className="flex-1 pb-16">
          {children}
        </main>
      </div>
    </div>
  );
}
