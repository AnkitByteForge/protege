"use client";

import { useEffect, useRef } from "react";
import { protegeApi } from "@/lib/protege-api-client";

export interface StateChangedPayload {
  from_state: string;
  to_state: string;
  trigger: string;
  at: string;
}

export interface SessionEndedPayload {
  state: string;
}

export interface UseSessionStreamCallbacks {
  onStateChanged: (payload: StateChangedPayload) => void;
  onSessionEnded: (payload: SessionEndedPayload) => void;
  onError?: () => void;
}

/**
 * `GET /v1/sessions/{id}/stream` over the browser's native `EventSource`
 * (roadmap P10: "No WebSocket endpoint"). Reconnect and `Last-Event-ID`
 * resumption are `EventSource`'s own built-in behaviour -- this hook adds
 * nothing on top of it beyond routing the two named event types P10 emits
 * (`state_changed`, `session_ended`) to the caller; it never buffers a
 * second copy of session state.
 */
export function useSessionStream(sessionId: string | null, callbacks: UseSessionStreamCallbacks) {
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;

  useEffect(() => {
    if (!sessionId) return;

    const source = new EventSource(protegeApi.streamUrl(sessionId));

    source.addEventListener("state_changed", (event) => {
      const data = JSON.parse((event as MessageEvent).data) as StateChangedPayload;
      callbacksRef.current.onStateChanged(data);
    });

    source.addEventListener("session_ended", (event) => {
      const data = JSON.parse((event as MessageEvent).data) as SessionEndedPayload;
      callbacksRef.current.onSessionEnded(data);
    });

    source.onerror = () => {
      // A closed idle connection is a normal part of this design (P10 SSE
      // docstring: the stream ends itself after `sse_idle_timeout_s` with
      // nothing new to send); `EventSource` reconnects automatically with
      // `Last-Event-ID` in every other case. Nothing to do here beyond
      // letting the caller show a gentle "reconnecting" state if it wants.
      callbacksRef.current.onError?.();
    };

    return () => source.close();
  }, [sessionId]);
}
