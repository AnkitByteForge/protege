/**
 * The P15 client mirror (roadmap: "A `SessionMachine` client mirror (XState
 * is permitted *here* only) that reflects server state and drives scene
 * transitions -- it never decides transitions.").
 *
 * Two independent authoritative inputs feed this machine, and it is
 * important they stay separate rather than being merged into one "server
 * said so" event:
 *
 *   - `SSE_TRANSITION` -- from `GET /v1/sessions/{id}/stream`, one per row
 *     of the durable `session_states` journal (`{from_state, to_state,
 *     trigger, at}` only). This is the *pacing* authority: every state this
 *     machine ever renders came from here, in the server's own order, which
 *     is exactly what lets a handful of synchronous server-side states
 *     (`BEAT_STATES`) read as deliberate beats instead of an instant jump
 *     (roadmap P15: "deliberate beats, no instant jumps; the child always
 *     sees *why* something changed").
 *   - `PAYLOAD_RECEIVED` -- from a direct REST response (`POST /events`,
 *     `POST /sessions`, `GET /sessions/{id}`), carrying the richer fields
 *     SSE never does (`sprout_turn`, `diagnosis`, `next_item`, `hint_text`).
 *     This only ever enriches `latestPayload`/`turnHistory`; it never sets
 *     `sceneState` itself, so a scene never renders content for a state the
 *     SSE pacing stream hasn't confirmed yet.
 *
 * Nothing here computes a `SessionStateName`. `context.sceneState` is
 * always a value `context.serverState` has already, truly reached -- never
 * predicted or invented -- and neither the FSM's next state nor mastery are
 * ever decided in this file.
 */

import { assign, or, setup } from "xstate";
import { BEAT_STATES, HOLD_BEFORE_ADVANCING_STATES, type SessionStateName } from "@/session/types";
import type { ApiProblem, SessionEventOut, SessionOut } from "@/lib/protege-api-client";

export const BEAT_DWELL_MS = 2200;

export type SessionPayload = SessionOut | SessionEventOut;

export interface SessionMachineContext {
  sessionId: string | null;
  learnerId: string | null;
  serverState: SessionStateName | null;
  sceneState: SessionStateName | null;
  latestPayload: SessionPayload | null;
  /** Every `SessionEventOut` this session has produced so far -- real server responses only, never fabricated (roadmap P15 evidence sidebar / summary). */
  turnHistory: SessionEventOut[];
  error: ApiProblem | null;
}

export type SessionMachineEvent =
  | { type: "SSE_TRANSITION"; state: SessionStateName }
  | { type: "PAYLOAD_RECEIVED"; payload: SessionPayload }
  | { type: "ERROR"; error: ApiProblem }
  | { type: "RESET" };

function isBeatState(state: SessionStateName): boolean {
  return BEAT_STATES.has(state);
}

function isHoldBeforeAdvancingState(state: SessionStateName | null): boolean {
  return state !== null && HOLD_BEFORE_ADVANCING_STATES.has(state);
}

export const sessionMachine = setup({
  types: {} as {
    context: SessionMachineContext;
    events: SessionMachineEvent;
  },
  actions: {
    recordTransition: assign({
      serverState: ({ context, event }) =>
        event.type === "SSE_TRANSITION" ? event.state : context.serverState,
      error: () => null,
    }),
    recordPayload: assign(({ context, event }) => {
      if (event.type !== "PAYLOAD_RECEIVED") return {};
      const turnHistory =
        "sprout_turn" in event.payload || "diagnosis" in event.payload
          ? [...context.turnHistory, event.payload as SessionEventOut]
          : context.turnHistory;
      return {
        sessionId: event.payload.session_id,
        learnerId: event.payload.learner_id,
        latestPayload: event.payload,
        turnHistory,
      };
    }),
    syncSceneToServerState: assign(({ context }) => ({
      sceneState: context.serverState,
    })),
    recordError: assign({
      error: ({ event }) => (event.type === "ERROR" ? event.error : null),
    }),
    resetContext: assign(() => ({
      sessionId: null,
      learnerId: null,
      serverState: null,
      sceneState: null,
      latestPayload: null,
      turnHistory: [],
      error: null,
    })),
  },
  guards: {
    isEnteringBeatState: ({ event }) => event.type === "SSE_TRANSITION" && isBeatState(event.state),
    // Evaluated *before* `recordTransition`'s assign runs, so
    // `context.serverState` here is still the state this transition is
    // leaving, not the one it's entering (see `HOLD_BEFORE_ADVANCING_STATES`).
    isLeavingHoldState: ({ context }) => isHoldBeforeAdvancingState(context.serverState),
  },
  delays: {
    BEAT_DWELL_MS,
  },
}).createMachine({
  id: "session",
  context: {
    sessionId: null,
    learnerId: null,
    serverState: null,
    sceneState: null,
    latestPayload: null,
    turnHistory: [],
    error: null,
  },
  initial: "idle",
  states: {
    idle: {
      on: {
        SSE_TRANSITION: {
          target: "active.dwelling",
          actions: "recordTransition",
        },
        PAYLOAD_RECEIVED: { actions: "recordPayload" },
      },
    },
    active: {
      initial: "steady",
      states: {
        steady: {
          on: {
            SSE_TRANSITION: [
              // Either the state being entered is a pass-through beat, or
              // the state being *left* is one whose own content (e.g.
              // `COACH_ASSIST`'s hint) needs a guaranteed beat on screen
              // before the scene is allowed to move on.
              {
                guard: or(["isEnteringBeatState", "isLeavingHoldState"]),
                target: "dwelling",
                actions: "recordTransition",
              },
              { actions: ["recordTransition", "syncSceneToServerState"] },
            ],
          },
        },
        dwelling: {
          // The server frequently cascades through several states within
          // one round trip (e.g. TRANSFER -> MASTERY_DECISION -> REWARD/
          // SUMMARY -> RETRIEVAL_SCHEDULE -> COMPLETE, all in one request).
          // Another *beat* state arriving mid-dwell only updates context --
          // the reveal still waits for the timer, so a fast run of beats
          // reads as one deliberate pause rather than a flicker. But a
          // state carrying real content the child should see (anything not
          // in `BEAT_STATES` -- `REWARD`, `SUMMARY`, every interactive
          // state) cuts the dwell short and reveals immediately, so it is
          // never silently skipped just because the next beat happened to
          // arrive a moment later.
          on: {
            SSE_TRANSITION: [
              { guard: "isEnteringBeatState", actions: "recordTransition" },
              { target: "steady", actions: ["recordTransition", "syncSceneToServerState"] },
            ],
          },
          after: {
            BEAT_DWELL_MS: { target: "steady", actions: "syncSceneToServerState" },
          },
        },
      },
      on: {
        PAYLOAD_RECEIVED: { actions: "recordPayload" },
        ERROR: { target: "#session.errored", actions: "recordError" },
      },
    },
    errored: {
      on: {
        SSE_TRANSITION: { target: "active.dwelling", actions: "recordTransition" },
        PAYLOAD_RECEIVED: { actions: "recordPayload" },
      },
    },
  },
  on: {
    RESET: { target: ".idle", actions: "resetContext" },
  },
});
