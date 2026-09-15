/**
 * Typed API client stub (roadmap P1: "Generated TS types consumed by a
 * typed API client stub. No UI.").
 *
 * The session-service HTTP API itself is not built until P10 (`GET
 * /v1/learners/{id}/state` is the endpoint named there). This stub exists
 * only to prove, end to end, that the frontend can consume the generated
 * contract types (`src/generated/contracts`, itself generated from the
 * Pydantic models in `packages/contracts`) — P10 replaces the single method
 * below with the full endpoint surface; it does not hand-maintain a second
 * copy of the contract shapes.
 */

import type { MasteryEstimateSchema } from "@/generated/contracts";

export interface ProtegeApiClientOptions {
  /** Session-service base URL, e.g. `http://localhost:8300`. */
  baseUrl: string;
  /** Override for testing; defaults to the global `fetch`. */
  fetchImpl?: typeof fetch;
}

export interface ProtegeApiClient {
  /** `GET /v1/learners/{id}/state` (roadmap P10). */
  getLearnerMasteryEstimates(learnerId: string): Promise<MasteryEstimateSchema.MasteryEstimate[]>;
}

export function createProtegeApiClient({
  baseUrl,
  fetchImpl = fetch,
}: ProtegeApiClientOptions): ProtegeApiClient {
  return {
    async getLearnerMasteryEstimates(learnerId) {
      const path = `/v1/learners/${encodeURIComponent(learnerId)}/state`;
      const response = await fetchImpl(`${baseUrl}${path}`);
      if (!response.ok) {
        throw new Error(`GET ${path} failed: ${response.status} ${response.statusText}`);
      }
      return (await response.json()) as MasteryEstimateSchema.MasteryEstimate[];
    },
  };
}
