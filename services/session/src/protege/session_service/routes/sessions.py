"""``/v1/sessions/*`` (roadmap P10, the main session-service surface)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from protege.contracts import SessionEventRequest
from protege.llm.router import ModelRouter

from ..auth import Actor, get_current_actor
from ..authz import get_owned_learner, get_owned_session
from ..deps import get_app_settings, get_db, get_model_router
from ..engine.context_codec import context_from_dict
from ..engine.runtime import (
    ItemPrompt,
    apply_event,
    complete_session,
    create_session,
    get_session_view,
    next_item_prompt,
)
from ..idempotency import hash_request_body, run_idempotent_request
from ..rate_limit import check_event_rate_limit, check_session_rate_limit
from ..schemas import ItemPromptOut, SessionCreateIn, SessionEventOut, SessionOut
from ..settings import Settings
from ..sse import stream_session_events

router = APIRouter(tags=["sessions"])


def _item_out(prompt: ItemPrompt | None) -> ItemPromptOut | None:
    if prompt is None:
        return None
    return ItemPromptOut(item_id=prompt.item_id, stem=prompt.stem)


@router.post("/v1/sessions", response_model=SessionOut, status_code=201)
async def create_session_route(
    payload: SessionCreateIn,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    actor: Actor = Depends(get_current_actor),
    model_router: ModelRouter = Depends(get_model_router),
    settings: Settings = Depends(get_app_settings),
) -> JSONResponse:
    request_hash = hash_request_body(await request.body())

    async def handler(session: AsyncSession) -> tuple[int, dict[str, Any]]:
        learner = await get_owned_learner(session, actor, payload.learner_id)
        await check_session_rate_limit(session, learner_id=learner.id, settings=settings)
        outcome = await create_session(session, learner_id=learner.id, router=model_router)
        body = SessionOut.from_view(
            outcome.session, next_item=_item_out(outcome.next_item)
        ).model_dump(mode="json")
        return 201, body

    status_code, body = await run_idempotent_request(
        settings=settings,
        actor_subject=actor.clerk_user_id,
        method="POST",
        path=str(request.url.path),
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        handler=handler,
    )
    return JSONResponse(status_code=status_code, content=body)


@router.get("/v1/sessions/{session_id}", response_model=SessionOut)
async def get_session_route(
    session_id: uuid.UUID,
    actor: Actor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db),
) -> SessionOut:
    session_row = await get_owned_session(session, actor, session_id)
    view = await get_session_view(session, session_row)
    next_item = None
    if session_row.context_snapshot is not None:
        next_item = _item_out(next_item_prompt(context_from_dict(session_row.context_snapshot)))
    return SessionOut.from_view(view, next_item=next_item)


@router.post("/v1/sessions/{session_id}/events", response_model=SessionEventOut)
async def submit_event_route(
    session_id: uuid.UUID,
    payload: SessionEventRequest,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    actor: Actor = Depends(get_current_actor),
    model_router: ModelRouter = Depends(get_model_router),
    settings: Settings = Depends(get_app_settings),
) -> JSONResponse:
    request_hash = hash_request_body(await request.body())

    async def handler(session: AsyncSession) -> tuple[int, dict[str, Any]]:
        session_row = await get_owned_session(session, actor, session_id)
        await check_event_rate_limit(session, learner_id=session_row.learner_id, settings=settings)
        outcome = await apply_event(
            session, session_row=session_row, event=payload, router=model_router
        )
        body = SessionEventOut.from_outcome(outcome).model_dump(mode="json")
        return 200, body

    status_code, body = await run_idempotent_request(
        settings=settings,
        actor_subject=actor.clerk_user_id,
        method="POST",
        path=str(request.url.path),
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        handler=handler,
    )
    return JSONResponse(status_code=status_code, content=body)


@router.get("/v1/sessions/{session_id}/stream")
async def stream_session_route(
    session_id: uuid.UUID,
    request: Request,
    actor: Actor = Depends(get_current_actor),
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    header_last_id = request.headers.get("last-event-id")
    resume_from = int(header_last_id) if header_last_id else 0
    generator = stream_session_events(
        request, session_id=session_id, actor=actor, last_event_id=resume_from, settings=settings
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/v1/sessions/{session_id}/complete", response_model=SessionOut)
async def complete_session_route(
    session_id: uuid.UUID,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    actor: Actor = Depends(get_current_actor),
    settings: Settings = Depends(get_app_settings),
) -> JSONResponse:
    request_hash = hash_request_body(await request.body())

    async def handler(session: AsyncSession) -> tuple[int, dict[str, Any]]:
        session_row = await get_owned_session(session, actor, session_id)
        view = await complete_session(session, session_row=session_row)
        return 200, SessionOut.from_view(view).model_dump(mode="json")

    status_code, body = await run_idempotent_request(
        settings=settings,
        actor_subject=actor.clerk_user_id,
        method="POST",
        path=str(request.url.path),
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        handler=handler,
    )
    return JSONResponse(status_code=status_code, content=body)
