import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const AUTH_FILE = path.resolve(__dirname, "../../.e2e/auth.json");
const STORAGE_STATE_FILE = path.resolve(__dirname, "../../.e2e/storage-state.json");

interface E2EAuth {
  token: string;
  learnerId: string;
  apiBaseUrl: string;
}

/**
 * Bridges `services/session/scripts/e2e_server.py`'s seeded test identity
 * into the browser (roadmap P15 testing: real E2E against the real P10
 * backend, no real Clerk tenant available in this environment). That
 * script seeds a parent+learner and mints a Clerk-shaped RS256 JWT before
 * it starts listening, writing `{token, learnerId}` to `AUTH_FILE`; this
 * setup waits for that file, then turns the token into a `storageState`
 * cookie every test's browser context loads automatically -- the same
 * `protege_e2e_token` cookie `src/app/api/protege/[...path]/route.ts`
 * checks before falling back to (unconfigured, in this suite) real Clerk.
 */
export default async function globalSetup(): Promise<void> {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (existsSync(AUTH_FILE)) break;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  if (!existsSync(AUTH_FILE)) {
    throw new Error(
      `E2E auth file never appeared at ${AUTH_FILE} -- did services/session/scripts/e2e_server.py start and seed successfully?`,
    );
  }

  const auth = JSON.parse(readFileSync(AUTH_FILE, "utf-8")) as E2EAuth;

  const storageState = {
    cookies: [
      {
        name: "protege_e2e_token",
        value: auth.token,
        domain: "127.0.0.1",
        path: "/",
        httpOnly: false,
        secure: false,
        sameSite: "Lax" as const,
        expires: Math.floor(Date.now() / 1000) + 6 * 3600,
      },
    ],
    origins: [],
  };

  const dir = path.dirname(STORAGE_STATE_FILE);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  writeFileSync(STORAGE_STATE_FILE, JSON.stringify(storageState));
}

export function readE2EAuth(): E2EAuth {
  return JSON.parse(readFileSync(AUTH_FILE, "utf-8")) as E2EAuth;
}
