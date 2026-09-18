import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  // `tests/session/**` needs a live P10 backend + seeded identity
  // (`playwright.session.config.ts`, `make test-e2e-session`) -- excluded
  // here so this static-page suite's own `webServer` (no backend) never
  // tries to run them.
  testIgnore: "**/session/**",
  timeout: 30_000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  use: {
    // Dedicated port for the e2e server: never collides with the dev server
    // (:3000) or anything else the developer runs locally.
    baseURL: "http://127.0.0.1:3111",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run build && npm run start -- --port 3111",
    url: "http://127.0.0.1:3111",
    reuseExistingServer: false,
    timeout: 300_000,
  },
});
