"""``GET /v1/sessions/{id}/stream`` -- HTTP SSE over the same rows every
other route reads (roadmap P10 rules 9/10: "SSE streams server-authoritative
state changes/events to the browser"; "SSE must not become a second source
of truth").

No separate message bus, no in-memory pub/sub, no WebSocket: the generator
below polls ``session_states`` (the durable transition journal, unchanged
from P9) for rows newer than the client's last-seen step and yields one SSE
event per row, in step order. Ordering is exactly Postgres's own
``ORDER BY step`` -- there is nothing else that could reorder it.
Reconnect-safety comes for free from this design: an ``EventSource``'s
native reconnect sends ``Last-Event-ID`` back as the next request's starting
point, which this generator honours identically whether the reconnect hits
the same process or, after a restart, a different one, because the only
state involved lives in Postgres.

The stream closes itself (a normal 200 end, not an error) after
``sse_idle_timeout_s`` with nothing new to send, or once the session reaches
a terminal state and that transition has been emitted -- a client's
``EventSource`` reconnects automatically in the former case; the latter
needs no reconnect, since a terminal session has nothing further to stream.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import Request

from protege.contracts import SessionState as S

from .auth import Actor
from .authz import get_owned_session
from .db.engine import session_scope
from .repositories.sessions import SessionRepository
from .settings import Settings

_TERMINAL_STATES = {str(S.COMPLETE), str(S.ABANDONED)}


def _format_event(*, event_id: int, event_name: str, data: dict[str, object]) -> str:
    return f"id: {event_id}\nevent: {event_name}\ndata: {json.dumps(data)}\n\n"


async def stream_session_events(
    request: Request,
    *,
    session_id: uuid.UUID,
    actor: Actor,
    last_event_id: int,
    settings: Settings,
) -> AsyncIterator[str]:
    async with session_scope() as session:
        await get_owned_session(session, actor, session_id)

    seen_step = last_event_id
    idle_elapsed = 0.0

    while True:
        if await request.is_disconnected():
            return

        async with session_scope() as session:
            transitions = await SessionRepository(session).list_transitions(session_id)

        new_transitions = [t for t in transitions if t.step > seen_step]
        if new_transitions:
            idle_elapsed = 0.0
            for transition in new_transitions:
                seen_step = transition.step
                yield _format_event(
                    event_id=transition.step,
                    event_name="state_changed",
                    data={
                        "from_state": transition.from_state,
                        "to_state": transition.to_state,
                        "trigger": transition.trigger,
                        "at": transition.at.isoformat(),
                    },
                )
            if new_transitions[-1].to_state in _TERMINAL_STATES:
                yield _format_event(
                    event_id=seen_step,
                    event_name="session_ended",
                    data={"state": new_transitions[-1].to_state},
                )
                return
            continue

        if idle_elapsed >= settings.sse_idle_timeout_s:
            return
        await asyncio.sleep(settings.sse_poll_interval_s)
        idle_elapsed += settings.sse_poll_interval_s
