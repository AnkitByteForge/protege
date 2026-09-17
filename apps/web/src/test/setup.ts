import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// RTL's automatic afterEach cleanup only registers itself when `afterEach`
// is a global; this project imports test APIs explicitly instead of using
// Vitest's `globals: true`, so cleanup is wired up by hand here.
afterEach(() => {
  cleanup();
});

// jsdom has no matchMedia implementation; framer-motion's useReducedMotion
// (and our own reduced-motion CSS) both probe it.
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}
