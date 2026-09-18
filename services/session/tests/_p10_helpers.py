"""Shared P10 API test scaffolding: a real ASGI-driven async client (real
Clerk-shaped JWT verification, networkless; a FakeProvider-backed
ModelRouter; a real Postgres-backed session), and small DB setup helpers.

Uses ``httpx.AsyncClient`` + ``ASGITransport`` -- not Starlette's
``TestClient`` -- driven through ``_db_helpers.run_async`` alongside every
other DB call a test makes, all within the *same* ``asyncio.run()`` loop.
Mixing ``TestClient`` (its own background-thread event-loop portal) with
this repo's existing ``run_async``/``asyncio.run`` DB-test convention hits a
real Windows ``ProactorEventLoop`` cross-loop asyncpg failure (a cached
engine from one loop being torn down on another); a single async client in
the same loop as every other awaited DB call sidesteps that entirely and
matches the existing test convention better besides.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from _auth_helpers import TEST_JWT_PUBLIC_KEY_PEM

from protege.llm.providers.fake import FakeOutcome, FakeProvider
from protege.llm.router import ModelRouter
from protege.session_service.app import create_app
from protege.session_service.db.engine import session_scope
from protege.session_service.deps import get_model_router
from protege.session_service.repositories.learners import LearnerRepository
from protege.session_service.settings import Settings


def build_test_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "_env_file": None,
        "log_level": "WARNING",
        "otel_console_export": False,
        "clerk_secret_key": "sk_test_dummy",
        "clerk_jwt_key": TEST_JWT_PUBLIC_KEY_PEM,
        "clerk_authorized_parties": "",
        "sse_poll_interval_s": 0.05,
        "sse_idle_timeout_s": 1.0,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


@asynccontextmanager
async def api_client(
    *, settings: Settings | None = None, script: list[FakeOutcome] | None = None
) -> AsyncIterator[tuple[httpx.AsyncClient, ModelRouter]]:
    resolved = settings or build_test_settings()
    app = create_app(resolved)
    router = ModelRouter({"nvidia": FakeProvider(script=script)})
    app.dependency_overrides[get_model_router] = lambda: router
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, router


async def create_linked_learner(*, clerk_user_id: str, email: str | None = None) -> uuid.UUID:
    """Create a parent (linked to ``clerk_user_id``) and one learner under
    it; return the learner's id."""
    async with session_scope() as session:
        repo = LearnerRepository(session)
        parent = await repo.create_parent(
            email=email or f"{clerk_user_id}@example.com", consent_version="v1"
        )
        await repo.link_clerk_user_id(parent_id=parent.id, clerk_user_id=clerk_user_id)
        learner = await repo.create_learner(
            parent_id=parent.id, display_name="Riley", grade_band="3-4"
        )
        return learner.id


def new_idempotency_key() -> str:
    return str(uuid.uuid4())
