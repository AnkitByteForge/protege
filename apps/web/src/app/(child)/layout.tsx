import type { ReactNode } from "react";

/**
 * The child route group's shell. Deliberately bare: no nav bar, no chrome
 * a child would read as "software." The world itself (background, scene
 * continuity, persistent progress) lives inside `SceneFrame`, which every
 * page in this group renders — this layout only provides the page-level
 * frame and the skip-link landing target.
 */
export default function ChildLayout({ children }: { children: ReactNode }) {
  return (
    <main id="main" className="mx-auto min-h-screen max-w-5xl px-4 py-6 sm:px-8 sm:py-10">
      {children}
    </main>
  );
}
