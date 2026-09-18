"""Shared FastAPI dependencies: a request-scoped DB session for read-only
routes, and the process-wide :class:`~protege.llm.router.ModelRouter`.

``POST`` routes do **not** use :func:`get_db` -- they need the idempotency
ledger row and the work it guards to share one transaction (see
``idempotency.py``), so they open their own ``session_scope()`` inside the
handler passed to :func:`~.idempotency.run_idempotent_request` instead.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from protege.llm.router import ModelRouter

from .db.engine import session_scope
from .settings import Settings


async def get_db() -> AsyncIterator[AsyncSession]:
    async with session_scope() as session:
        yield session


def get_model_router(request: Request) -> ModelRouter:
    router = getattr(request.app.state, "model_router", None)
    if not isinstance(router, ModelRouter):  # pragma: no cover - defensive
        raise RuntimeError("model_router was not initialised on app.state")
    return router


def get_app_settings(request: Request) -> Settings:
    """The exact :class:`~.settings.Settings` instance this app was built
    with (``app.state.settings``, set once in ``create_app``) -- not the
    process-wide ``get_settings()`` cache, which a test's own
    ``Settings(...)`` instance passed to ``create_app`` would otherwise
    silently bypass."""
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):  # pragma: no cover - defensive
        raise RuntimeError("settings was not initialised on app.state")
    return settings
