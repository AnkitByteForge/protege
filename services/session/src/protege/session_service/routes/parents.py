"""``/v1/parents/{id}/deletion-request`` (roadmap P10; architecture §23:
"GDPR/COPPA").

Records the request (an ``audit_events`` row) and returns ``202 Accepted``;
it does not execute a deletion. P9's only deletion primitive
(``LearnerRepository.delete``) is an immediate hard delete with no 30-day
grace period, and no scheduling/job infrastructure for that delay exists
anywhere in the repository yet -- building one is outside P10's declared
scope (transport over P7/P9, not a new background-job system). Executing an
irreversible cascade delete synchronously from this endpoint would also be
a materially riskier default than roadmap P10 asks for. See
``docs/P10_SESSION_API.md`` for this judgment call.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import Actor, ActorRole, get_current_actor
from ..authz import resolve_parent
from ..db.models import AuditEventRow
from ..deps import get_app_settings
from ..errors import ForbiddenError
from ..idempotency import hash_request_body, run_idempotent_request
from ..schemas import DeletionRequestOut
from ..settings import Settings

router = APIRouter(tags=["parents"])


@router.post(
    "/v1/parents/{parent_id}/deletion-request", response_model=DeletionRequestOut, status_code=202
)
async def deletion_request_route(
    parent_id: uuid.UUID,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    actor: Actor = Depends(get_current_actor),
    settings: Settings = Depends(get_app_settings),
) -> JSONResponse:
    request_hash = hash_request_body(await request.body())

    async def handler(session: AsyncSession) -> tuple[int, dict[str, Any]]:
        parent = await resolve_parent(session, actor)
        if actor.role != ActorRole.ADMIN and parent.id != parent_id:
            raise ForbiddenError("this account does not belong to the signed-in parent")
        audit_row = AuditEventRow(
            actor=actor.clerk_user_id,
            action="deletion_requested",
            resource=f"parent:{parent_id}",
            at=datetime.now(UTC),
        )
        session.add(audit_row)
        await session.flush()
        body = DeletionRequestOut(
            request_id=audit_row.id, parent_id=parent_id, status="recorded"
        ).model_dump(mode="json")
        return 202, body

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
