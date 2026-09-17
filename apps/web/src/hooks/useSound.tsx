"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";
import { soundToken, type SoundToken } from "@/design/tokens";

interface SoundContextValue {
  enabled: boolean;
  play: (token: SoundToken) => void;
}

const SoundContext = createContext<SoundContextValue>({
  enabled: false,
  play: () => {},
});

/**
 * Sound is infrastructure-only at P12: tokens are named and typed, the
 * provider exists, and everything defaults to OFF. No audio asset ships
 * with this phase, so `play` is a documented no-op until a product phase
 * wires real files in and someone opts sound on.
 */
export function SoundProvider({
  enabled = false,
  children,
}: {
  enabled?: boolean;
  children: ReactNode;
}) {
  const value = useMemo<SoundContextValue>(
    () => ({
      enabled,
      play: (token: SoundToken) => {
        if (!enabled) return;
        // Intentionally inert: no audio assets ship in P12. A later phase
        // wires this to actual <audio> playback per `soundToken`.
        void token;
      },
    }),
    [enabled],
  );

  return <SoundContext.Provider value={value}>{children}</SoundContext.Provider>;
}

export function useSound() {
  return useContext(SoundContext);
}

export { soundToken };
