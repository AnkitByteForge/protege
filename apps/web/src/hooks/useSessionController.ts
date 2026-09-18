"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useMachine } from "@xstate/react";
import { sessionMachine } from "@/session/sessionMachine";
import type { SessionStateName } from "@/session/types";
import { TERMINAL_STATES } from "@/session/types";
import { useSessionStream } from "@/hooks/useSessionStream";
import { ApiProblemError, protegeApi, type SessionEventRequest } from "@/lib/protege-api-client";

/**
 * Wires the P10 REST client, the SSE pacing stream, and the client-mirror
 * `sessionMachine` together for one session id (roadmap P15 "SCENE
 * CONTINUITY" + "REHYDRATION"). A component only ever needs this hook plus
 * `<SceneFrame>` -- it never talks to `protegeApi`/`EventSource` directly.
 */
export function useSessionController(sessionId: string) {
  const [state, send] = useMachine(sessionMachine);
  // Real reactive state, not a ref: the "submitting" flag must actually
  // re-render (disabling the form, flipping the button's "Checking…"
  // label) while a request is in flight, not just gate re-entrancy
  // internally -- a ref alone never notifies React that anything changed.
  const [submitting, setSubmitting] = useState(false);
  const submittingRef = useRef(false);

  useSessionStream(sessionId, {
    onStateChanged: (payload) => {
      send({ type: "SSE_TRANSITION", state: payload.to_state as SessionStateName });
    },
    onSessionEnded: (payload) => {
      send({ type: "SSE_TRANSITION", state: payload.state as SessionStateName });
    },
  });

  // Rehydration (roadmap P15: "A refresh at any point in the session must
  // reconstruct the exact current server state"). `GET /sessions/{id}` is
  // the authoritative source; the SSE stream (opened by `useSessionStream`
  // above, from `Last-Event-ID` 0) independently replays the same journal
  // to drive `sceneState`'s own beat pacing -- this call only ever seeds
  // `latestPayload` (next_item etc.) faster than waiting on SSE alone.
  useEffect(() => {
    let cancelled = false;
    protegeApi
      .getSession(sessionId)
      .then((session) => {
        if (!cancelled) send({ type: "PAYLOAD_RECEIVED", payload: session });
      })
      .catch((error: unknown) => {
        if (!cancelled && error instanceof ApiProblemError) {
          send({ type: "ERROR", error: error.problem });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, send]);

  // Once the FSM has genuinely reached COMPLETE, finalize it (roadmap P10:
  // "`/complete` semantics ... only legal once the FSM has already reached
  // COMPLETE via events"). Idempotent on the server, so firing this once
  // per completion is safe even across a reconnect.
  const completedRef = useRef(false);
  useEffect(() => {
    if (state.context.serverState !== "COMPLETE" || completedRef.current) return;
    completedRef.current = true;
    void protegeApi.completeSession(sessionId).catch(() => {
      completedRef.current = false; // allow a retry on the next render if this failed
    });
  }, [sessionId, state.context.serverState]);

  const submitEvent = useCallback(
    async (event: SessionEventRequest) => {
      if (submittingRef.current) return;
      submittingRef.current = true;
      setSubmitting(true);
      try {
        const outcome = await protegeApi.submitEvent(sessionId, event);
        send({ type: "PAYLOAD_RECEIVED", payload: outcome });
      } catch (error) {
        if (error instanceof ApiProblemError) {
          send({ type: "ERROR", error: error.problem });
        } else {
          throw error;
        }
      } finally {
        submittingRef.current = false;
        setSubmitting(false);
      }
    },
    [sessionId, send],
  );

  const sceneState = state.context.sceneState;
  const isTerminal = sceneState !== null && TERMINAL_STATES.has(sceneState);

  return {
    sceneState,
    serverState: state.context.serverState,
    payload: state.context.latestPayload,
    turnHistory: state.context.turnHistory,
    error: state.context.error,
    isTerminal,
    submitEvent,
    submitting,
  };
}
