import { defineConfig, devices } from "@playwright/test";

/**
 * The P15 session E2E suite: real browser, real Next.js build, real P10
 * FastAPI backend, real Postgres -- the only thing not real is Clerk itself
 * (no tenant available in this environment; see
 * `services/session/scripts/e2e_server.py` and `tests/session/global-setup.ts`
 * for the same test-JWT approach the backend's own pytest suite already
 * uses). Separate from `playwright.config.ts` (P12's static-page smoke
 * test) because this suite needs a live backend + seeded identity that
 * suite has no reason to pay for.
 */
export default defineConfig({
  testDir: "./tests/session",
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  globalSetup: "./tests/session/global-setup.ts",
  use: {
    baseURL: "http://127.0.0.1:3112",
    trace: "on-first-retry",
    storageState: "./.e2e/storage-state.json",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "uv run python services/session/scripts/e2e_server.py",
      cwd: "../../",
      url: "http://127.0.0.1:8301/healthz",
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: "npm run build && npm run start -- --port 3112",
      url: "http://127.0.0.1:3112",
      reuseExistingServer: false,
      timeout: 300_000,
      env: {
        PROTEGE_API_BASE_URL: "http://127.0.0.1:8301",
      },
    },
  ],
});
