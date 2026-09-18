/**
 * The full P10 typed client (roadmap P15: "Use the existing P10 generated
 * typed client. Do not create ad-hoc fetch wrappers where the generated
 * client should be used.").
 *
 * `src/generated/api/schema.ts` (openapi-typescript, `make api-types`) gives
 * the wire shapes; this module is the thin, hand-written call layer every
 * generated-client stub still needs (openapi-typescript emits *types*, not a
 * client) -- it never redeclares a shape the generated schema already owns.
 *
 * Transport: every call is relative to `/api/protege` -- a same-origin
 * Next.js route handler (`src/app/api/protege/[...path]/route.ts`), never
 * the session-service's own origin directly. Two real constraints force
 * this, neither invented for P15: (1) `services/session` registers no CORS
 * middleware, so a cross-origin browser call would simply fail; (2) the
 * browser's native `EventSource` (the SSE client roadmap P10 specifies --
 * "No WebSocket endpoint") cannot attach an `Authorization` header at all,
 * so *something* server-side has to attach the Clerk bearer token on the
 * stream's behalf. The proxy route solves both the same way: it holds the
 * only copy of `PROTEGE_API_BASE_URL` and attaches `Authorization` itself
 * (via Clerk's server-side `auth()`), so this client -- and `EventSource`,
 * unmodified -- only ever need a same-origin, unauthenticated-looking URL.
 *
 * Errors: every non-2xx response is RFC 9457 `application/problem+json`
 * (roadmap P10 `errors.py`) -- surfaced here as `ApiProblemError`, carrying
 * `child_safe_message` verbatim so the UI never has to translate a raw
 * status code or exception string itself.
 */

import type { components } from "@/generated/api/schema";

export type SessionOut = components["schemas"]["SessionOut"];
export type SessionEventOut = components["schemas"]["SessionEventOut"];
export type ItemPromptOut = components["schemas"]["ItemPromptOut"];
export type LearnerStateOut = components["schemas"]["LearnerStateOut"];
export type NotYetAvailableOut = components["schemas"]["NotYetAvailableOut"];
export type AnswerSubmittedEvent = components["schemas"]["AnswerSubmittedEvent"];
export type ExplanationGivenEvent = components["schemas"]["ExplanationGivenEvent"];
export type ManipulativeMovedEvent = components["schemas"]["ManipulativeMovedEvent"];
export type HintRequestedEvent = components["schemas"]["HintRequestedEvent"];
export type SessionEventRequest =
  AnswerSubmittedEvent | ExplanationGivenEvent | ManipulativeMovedEvent | HintRequestedEvent;

/** RFC 9457 `application/problem+json` (roadmap P10 `errors.py`, verbatim shape). */
export interface ApiProblem {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  child_safe_message: string;
}

const FALLBACK_CHILD_SAFE_MESSAGE = "Oops! Something went wrong. Let's try that again in a moment.";

export class ApiProblemError extends Error {
  readonly problem: ApiProblem;

  constructor(problem: ApiProblem) {
    super(problem.detail || problem.title);
    this.name = "ApiProblemError";
    this.problem = problem;
  }

  /** The one string the child-facing UI is ever allowed to render. */
  get childSafeMessage(): string {
    return this.problem.child_safe_message || FALLBACK_CHILD_SAFE_MESSAGE;
  }
}

export interface ProtegeApiClientOptions {
  /** Same-origin proxy base path. Defaults to `/api/protege`; overridable for tests only. */
  baseUrl?: string;
  /** Override for testing; defaults to the global `fetch`. */
  fetchImpl?: typeof fetch;
}

export interface ProtegeApiClient {
  /** `POST /v1/sessions` (roadmap P10). */
  createSession(input: { learnerId: string }): Promise<SessionOut>;
  /** `GET /v1/sessions/{id}` -- the rehydration call (roadmap P15 "Rehydration"). */
  getSession(sessionId: string): Promise<SessionOut>;
  /** `POST /v1/sessions/{id}/events` -- the one verb that advances the FSM. */
  submitEvent(sessionId: string, event: SessionEventRequest): Promise<SessionEventOut>;
  /** `POST /v1/sessions/{id}/complete`. */
  completeSession(sessionId: string): Promise<SessionOut>;
  /** `GET /v1/learners/{id}/state` -- authoritative mastery/misconception view. */
  getLearnerState(learnerId: string): Promise<LearnerStateOut>;
  /**
   * The same-origin proxy's SSE URL for this session (roadmap P10/P15) --
   * `useSessionStream` passes this straight to `new EventSource(url)`, so
   * its native reconnect/`Last-Event-ID` behaviour keeps working unmodified;
   * the proxy forwards `Last-Event-ID` through to the real stream.
   */
  streamUrl(sessionId: string): string;
}

async function _parseProblem(response: Response, instance: string): Promise<ApiProblem> {
  try {
    const body = (await response.json()) as Partial<ApiProblem>;
    if (body && typeof body.child_safe_message === "string") {
      return {
        type: body.type ?? "about:blank",
        title: body.title ?? response.statusText,
        status: body.status ?? response.status,
        detail: body.detail ?? response.statusText,
        instance: body.instance ?? instance,
        child_safe_message: body.child_safe_message,
      };
    }
  } catch {
    // Falls through to the generic problem below -- never surfaces the raw
    // parse failure or response body to the child-facing UI.
  }
  return {
    type: "about:blank",
    title: response.statusText || "Error",
    status: response.status,
    detail: "The server returned an unexpected response.",
    instance,
    child_safe_message: FALLBACK_CHILD_SAFE_MESSAGE,
  };
}

export function createProtegeApiClient({
  baseUrl = "/api/protege",
  fetchImpl = fetch,
}: ProtegeApiClientOptions = {}): ProtegeApiClient {
  async function request<T>(
    path: string,
    init: RequestInit & { idempotent?: boolean } = {},
  ): Promise<T> {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...(init.idempotent ? { "Idempotency-Key": crypto.randomUUID() } : {}),
      ...init.headers,
    };
    const response = await fetchImpl(`${baseUrl}${path}`, { ...init, headers });
    if (!response.ok) {
      throw new ApiProblemError(await _parseProblem(response, path));
    }
    return (await response.json()) as T;
  }

  return {
    async createSession({ learnerId }) {
      return request<SessionOut>("/sessions", {
        method: "POST",
        idempotent: true,
        body: JSON.stringify({ learner_id: learnerId }),
      });
    },

    async getSession(sessionId) {
      return request<SessionOut>(`/sessions/${encodeURIComponent(sessionId)}`);
    },

    async submitEvent(sessionId, event) {
      return request<SessionEventOut>(`/sessions/${encodeURIComponent(sessionId)}/events`, {
        method: "POST",
        idempotent: true,
        body: JSON.stringify(event),
      });
    },

    async completeSession(sessionId) {
      return request<SessionOut>(`/sessions/${encodeURIComponent(sessionId)}/complete`, {
        method: "POST",
        idempotent: true,
      });
    },

    async getLearnerState(learnerId) {
      return request<LearnerStateOut>(`/learners/${encodeURIComponent(learnerId)}/state`);
    },

    streamUrl(sessionId) {
      return `${baseUrl}/sessions/${encodeURIComponent(sessionId)}/stream`;
    },
  };
}

/** The one instance every component should import -- see the module docstring for why `baseUrl` needs no configuration. */
export const protegeApi = createProtegeApiClient();
