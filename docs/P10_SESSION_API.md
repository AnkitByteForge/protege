# P10 — Session Service API

Transport layer over the existing P7 FSM/orchestrator and P9 persistence.
The server-side Python FSM (`packages/session-fsm`) remains the sole
transition authority; this document covers only what P10 itself added.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/sessions` | Start a session for a learner |
| GET | `/v1/sessions/{id}` | Rehydrate the canonical session state |
| POST | `/v1/sessions/{id}/events` | Submit one event; the server validates, advances the FSM, persists |
| GET | `/v1/sessions/{id}/stream` | SSE: authoritative state changes, in order |
| POST | `/v1/sessions/{id}/complete` | Finalize a session already in `COMPLETE` |
| GET | `/v1/learners/{id}/state` | Authoritative mastery/misconception view |
| GET | `/v1/learners/{id}/proof` | Canonical "not yet available" (P20 not shipped) |
| GET | `/v1/learners/{id}/tutor-brief` | Canonical "not yet available" (P21 not shipped); tutor/admin only |
| POST | `/v1/parents/{id}/deletion-request` | Records the request; does not execute a deletion |

No WebSocket endpoint. OpenAPI is served at `/openapi.json`; `make api-types`
exports it to `services/session/openapi.json` and regenerates
`apps/web/src/generated/api/schema.ts` via `openapi-typescript`.

## Auth: Clerk-verified session JWTs

The frontend (Next.js + Clerk) attaches `Authorization: Bearer <session JWT>`.
The backend verifies it server-side with Clerk's own Python SDK
(`clerk-backend-api`, `Clerk.authenticate_request`) — never a hand-rolled JWT
implementation (`auth.py`).

### Clerk dashboard configuration

1. **API Keys** page: copy the **Secret key** (`CLERK_SECRET_KEY`) and
   **Publishable key** (`CLERK_PUBLISHABLE_KEY`).
2. Same page, **"Show JWT public key"**: copy the PEM block into
   `CLERK_JWT_KEY`. Setting this makes verification **networkless** — a pure
   in-process signature check, no per-request (or startup) call to Clerk.
   Leaving it blank falls back to the SDK fetching + internally caching the
   JWKS from Clerk's Backend API using `CLERK_SECRET_KEY`.
3. **Sessions -> Customize session token**: add two custom claims so the
   backend can read them without a database round trip per request:
   - `role`: `"parent"` (default if omitted) | `"tutor"` | `"admin"`.
   - `learner_id` (optional, informational only — see "Ownership" below).
4. **Authorized parties**: set `CLERK_AUTHORIZED_PARTIES` to your frontend's
   origin(s) (comma-separated) once you have real ones; this guards the
   subdomain-cookie-leaking attack the Clerk docs describe. Empty disables
   the check (signature/expiry are still verified) — fine for local dev,
   not for production.

### Environment variables

| Variable | Secret? | Purpose |
|---|---|---|
| `CLERK_SECRET_KEY` | **yes** | Authenticates this backend to Clerk's own API; also the fallback JWKS-fetch credential |
| `CLERK_PUBLISHABLE_KEY` | no | Not used server-side for verification; kept for parity with the frontend's own key and future SDK calls |
| `CLERK_JWT_KEY` | treat as sensitive | The PEM public key verification is checked against; not itself a bearer credential |
| `CLERK_AUTHORIZED_PARTIES` | no | Comma-separated allowed origins |

None of these are hardcoded anywhere; all are `Settings` fields
(`settings.py`), sourced from the environment / `.env` (see `.env.example`),
never committed.

### Local development

1. Create (or reuse) a Clerk **development** instance.
2. Fill `CLERK_SECRET_KEY`, `CLERK_PUBLISHABLE_KEY`, `CLERK_JWT_KEY` in `.env`.
3. Leave `CLERK_AUTHORIZED_PARTIES` blank, or set it to
   `http://localhost:3000`.
4. `make api` boots the FastAPI service; the frontend's Clerk `<ClerkProvider>`
   mints session JWTs the browser attaches to every `/v1/*` request.

### Production

- Runs the same code path — there is no separate production-only branch.
  Set the same four variables from your **production** Clerk instance's
  values, and set real `CLERK_AUTHORIZED_PARTIES`.
- The backend is deployed independently from the frontend (no shared
  process/filesystem is required or assumed): it only ever needs the four
  environment variables above, reachable outbound to Clerk's API only when
  `CLERK_JWT_KEY` is unset (the JWKS-fetch fallback).
- Behind a reverse proxy/container: no special configuration — the service
  reads `Authorization` from the incoming request as normal; ensure the
  proxy forwards that header unmodified.

### How ownership works

A verified JWT proves *who* signed in (`sub`, the Clerk user id) — never,
by itself, permission to touch any specific learner/session. Ownership is
re-derived from Postgres on every request (`authz.py`):

- `parents.clerk_user_id` (added by migration `0003_p10_session_api`) maps a
  verified Clerk identity to its PROTÉGÉ account. This is the **only**
  schema addition P10 needed for identity — deliberately minimal.
- A `parent` role actor may only act on learners under their own linked
  `parents` row; `admin` bypasses the ownership check; `tutor` is read-scoped
  to `/v1/learners/{id}/state` and `/tutor-brief` only (no session
  read/write access — see `authz.require_tutor_or_admin`).
- There is no independent child identity in this product (COPPA-driven
  design): the child plays under the parent's authenticated session on a
  shared device. The `learner_id` session-token claim, if present, is
  informational only — actual authorization always goes through the DB
  ownership check above, never trusts a client- or claim-supplied id alone.

## Idempotency

`Idempotency-Key` is required on every `POST`. Keyed by
`(actor_subject, http_method, request_path, idempotency_key)` in a new
`idempotency_keys` table (Postgres — no Redis). See
`repositories/idempotency.py` and `idempotency.py` for the two-phase
reserve/complete design: the ledger row and the work it guards share one
transaction, so a genuine race (two requests, identical key, arriving
concurrently) is resolved by Postgres's own unique-constraint violation
rolling back the entire loser transaction — not a best-effort check. A key
reused with a different request body returns `409` rather than serving the
wrong cached response. Rows carry a 24 h `expires_at`
(`Settings.idempotency_ttl_hours`); expired rows are simply excluded from
lookups (no cleanup job).

## SSE

`GET /v1/sessions/{id}/stream` polls the same `session_states` rows every
other route reads (no second message bus, no in-memory pub/sub, no
WebSocket). Ordering is Postgres's own `ORDER BY step`. Reconnect-safety:
the browser's native `EventSource` reconnect sends `Last-Event-ID` back,
which this endpoint honours identically whether it lands on the same
process or, after a restart, a different one — the only state involved
lives in Postgres. The stream closes itself (a normal `200` end) after
`Settings.sse_idle_timeout_s` with nothing new to send, or once a terminal
state has been emitted.

**Known limitation:** streamed Sprout *tokens* (word-by-word) are not
implemented — `packages/roles`' `SproutGenerator.generate_turn` is a single
whole-call, non-streaming API today. Faking token-level streaming over a
call that isn't actually streaming would be fabrication; instead, the SSE
stream emits the complete `SproutTurn` once generated, as part of the
`answer_submitted`/`explanation_given` HTTP response, and streams
authoritative *state-change* events continuously. True token streaming
needs a streaming-capable role API, which is out of P10's scope.

## FSM / persistence integration

- `engine/runtime.py` reconstructs a live `SessionOrchestrator` per request
  from `sessions.context_snapshot` (a JSONB checkpoint of
  `SessionContext` — see that column's docstring), drives it with the exact
  same orchestrator methods `protege.thin_thread.engine` drives in-process,
  then flushes the journal to `session_states` and re-checkpoints.
- `persistence/thin_thread_bridge.py` (P8/P9's batch-dump bridge) is
  **not** reused for live requests — its own docstring says a real P10
  service should call `SessionRepository.append_transition` directly off
  the orchestrator's journal instead, which is exactly what `runtime.py`
  does.
- Content: the live session replays the exact same authored S004/M003
  thin-thread content P8 uses (`protege.thin_thread.scenario`/
  `protege.authoring.loader`) — P10 exposes "Thin Thread over HTTP," not a
  generalized content-selection service (that is P11's future job).

## Rate limits

Derived from rows P9 already persists — no new counter store:
- 60 events/minute/learner: count of `events` rows for that learner in the
  last 60 s.
- 10 sessions/day/learner: count of `sessions` rows for that learner in the
  last rolling 24 h (not a calendar-day boundary — the roadmap does not
  specify one, and a rolling window avoids a timezone-dependent definition).

## Error model

RFC 9457 `application/problem+json` on every error
(`errors.py`): `type`, `title`, `status`, `detail`, `instance`, plus
`child_safe_message` — the field the UI renders directly to a child. Never a
stack trace, a raw exception string, SQL, a provider secret, or an internal
routing decision.

## Judgment calls and roadmap ambiguities

These are the P10-scope decisions the roadmap text did not fully specify;
recorded here rather than left implicit.

1. **Auth mechanism.** No auth abstraction existed anywhere in the repo
   before P10. Built real Clerk RS256 JWT verification via the official
   `clerk-backend-api` SDK (networkless when `CLERK_JWT_KEY` is set) per
   explicit direction, rather than a self-contained HS256 scheme.
2. **`clerk_user_id` placement.** Added to `parents`, not a new table — a
   parent is the only account holder in this product; a learner has no
   independent identity.
3. **`POST /v1/parents/{id}/deletion-request`.** Records the request
   (`audit_events` row) and returns `202`; does not execute
   `LearnerRepository.delete()`. Architecture §23 describes "30-day hard
   delete + tombstone," but no scheduling/job infrastructure for that delay
   exists anywhere in the repo, and building one is outside P10's transport
   scope. Flagged as a genuine gap for whichever phase owns the deletion
   pipeline.
4. **Tutor-brief access.** Gated on the `role` claim only
   (`authz.require_tutor_or_admin`). Architecture §23 says tutor access
   "requires a time-boxed tutor grant"; no such grant ledger exists yet
   (no earlier phase built one), so this is the minimum real check
   available today, not the full model.
5. **`/complete` semantics.** Only legal once the FSM has already reached
   `COMPLETE` via events (never a manual early-termination/abandon flow —
   that would need policy P11/P25 does not exist yet to decide). Idempotent:
   a second call returns the already-recorded result without emitting a
   second `SESSION_COMPLETED` event.
6. **`hint_requested` semantics.** The FSM's `COACH_ASSIST` state already
   exists as a real, addressable dwelling state; P10 makes hint delivery
   client-driven (the child must ask) rather than auto-firing
   `HINT_DELIVERED` the instant `COACH_ASSIST` is entered (which is what the
   in-process P8 thin-thread does, since it has no real "child" to wait on).
   Both reach the identical state sequence; P10's version is the more
   realistic interactive shape.
7. **Streamed Sprout tokens.** Not implemented — see the SSE section above.
8. **Evidence-to-mastery-estimate linkage.** Only the transfer item's
   evidence row gets `mastery_estimate_id` set at insert time (the estimate
   does not exist yet when earlier evidence in the same session is
   persisted, and evidence is append-only — no backfill). Documented in
   `engine/runtime.py`'s module docstring; claim resolution
   (`EvidenceRepository.resolve_claim`) does not depend on this link.
