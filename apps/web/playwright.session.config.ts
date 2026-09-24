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
      // Real env vars override the repo-root `.env`, so a developer's real
      // NVIDIA key can't replace the deterministic FakeProvider these
      // tests' exact-text assertions depend on.
      env: {
        NVIDIA_API_KEY: "",
      },
    },
    {
      command: "npm run build && npm run start -- --port 3112",
      url: "http://127.0.0.1:3112",
      reuseExistingServer: false,
      timeout: 300_000,
      // Blanked so real Clerk keys in a local `.env.local` can't get baked
      // into this build; otherwise middleware demands a real Clerk sign-in
      // the `protege_e2e_token` test identity can't satisfy.
      env: {
        PROTEGE_API_BASE_URL: "http://127.0.0.1:8301",
        NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: "",
        CLERK_SECRET_KEY: "",
      },
    },
  ],
});
