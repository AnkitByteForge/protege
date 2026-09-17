import { cn } from "@/lib/cn";

export type WorldTone = "child" | "parent" | "tutor";

const skyGradient: Record<WorldTone, string> = {
  child: "from-sky-200 via-sand-200 to-paper",
  parent: "from-sky-200/70 via-paper to-paper",
  tutor: "from-sand-200 via-paper to-paper",
};

/**
 * The persistent, layered environment behind every scene. It never
 * unmounts as scenes change (see `SceneFrame`) — that persistence is what
 * reads as "a world" rather than "a page with a background image." Three
 * tones share one construction (gradient sky + soft hills + a few
 * restrained ambient shapes) so the three route groups feel like the same
 * place seen in different light, not three different products.
 */
export function SceneBackground({ tone = "child" }: { tone?: WorldTone }) {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className={cn("absolute inset-0 bg-gradient-to-b", skyGradient[tone])} />

      {/* sun / glow */}
      <div
        className={cn(
          "absolute -top-24 right-[8%] h-64 w-64 rounded-full blur-3xl",
          tone === "child" && "bg-apricot-200/70",
          tone === "parent" && "bg-sky-200/60",
          tone === "tutor" && "bg-sand-300/50",
        )}
      />

      {/* far hill */}
      <svg
        className="absolute bottom-0 left-0 w-full text-moss-200/80"
        style={{ height: "38%" }}
        viewBox="0 0 400 120"
        preserveAspectRatio="none"
      >
        <path d="M0 80 Q 60 30 130 55 T 260 45 T 400 60 V120 H0 Z" fill="currentColor" />
      </svg>

      {/* near hill */}
      {tone !== "tutor" && (
        <svg
          className="absolute bottom-0 left-0 w-full text-moss-500/40 animate-ambient-float motion-reduce:animate-none"
          style={{ height: "26%" }}
          viewBox="0 0 400 100"
          preserveAspectRatio="none"
        >
          <path d="M0 60 Q 90 20 200 50 T 400 40 V100 H0 Z" fill="currentColor" />
        </svg>
      )}

      {/* drifting clouds — restrained, two only, gone entirely for the calmer tutor tone */}
      {tone === "child" && (
        <>
          <div
            data-testid="ambient-motion"
            className="animate-ambient-drift motion-reduce:animate-none absolute top-10 left-[12%] h-10 w-24 rounded-full bg-white/70 blur-md"
          />
          <div
            className="animate-ambient-drift motion-reduce:animate-none absolute top-24 right-[18%] h-8 w-20 rounded-full bg-white/60 blur-md"
            style={{ animationDelay: "3s" }}
          />
        </>
      )}

      {/* a few soft ambient specks — restrained particle use, not a shower */}
      {tone === "child" &&
        [18, 46, 72].map((left, i) => (
          <span
            key={left}
            className="animate-ambient-float motion-reduce:animate-none absolute h-2 w-2 rounded-full bg-apricot-500/40"
            style={{ left: `${left}%`, top: `${30 + i * 12}%`, animationDelay: `${i * 1.4}s` }}
          />
        ))}
    </div>
  );
}
