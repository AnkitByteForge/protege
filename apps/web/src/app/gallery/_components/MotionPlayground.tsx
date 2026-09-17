"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { spring, type SpringPreset } from "@/design/tokens";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { Button } from "@/components/primitives/Button";
import { Text } from "@/components/primitives/Typography";
import { cn } from "@/lib/cn";

const presets: { key: SpringPreset; note: string }[] = [
  { key: "settle", note: "Scene entrances, layout shifts — calm arrival." },
  { key: "pop", note: "Press feedback, reward beats — snappy." },
  { key: "wobble", note: "A gentle 'try again' nudge — bouncy, never paired with red." },
  { key: "drift", note: "Idle sway, ambient motion — slow and soft." },
];

export function MotionPlayground() {
  const [active, setActive] = useState<SpringPreset>("settle");
  const [bump, setBump] = useState(0);
  const reduceMotion = useReducedMotion();
  const preset = presets.find((p) => p.key === active)!;

  return (
    <div className="grid gap-6 sm:grid-cols-[1fr_auto]">
      <div>
        <div className="flex flex-wrap gap-2">
          {presets.map((p) => (
            <Button
              key={p.key}
              size="md"
              variant={active === p.key ? "primary" : "secondary"}
              tone="sky"
              onClick={() => {
                setActive(p.key);
                setBump((n) => n + 1);
              }}
            >
              {p.key}
            </Button>
          ))}
        </div>
        <Text muted className="mt-3">
          {preset.note}
        </Text>
        {reduceMotion && (
          <Text muted className="mt-1 text-sm italic">
            Your system prefers reduced motion — the shape will fade instead of spring.
          </Text>
        )}
      </div>

      <div
        className={cn(
          "flex h-32 w-32 items-center justify-center rounded-2xl border-2 border-sand-300 bg-surface",
        )}
      >
        <motion.div
          key={bump}
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.4, y: 24 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={spring[active]}
          className="h-16 w-16 rounded-full bg-sky-600"
          aria-hidden
        />
      </div>
    </div>
  );
}
