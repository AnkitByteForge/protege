"""Process-wide :class:`~protege.llm.router.ModelRouter` construction.

Shared by the FastAPI app (``app.py``, one router on ``app.state``) and the
P9 job worker (``jobs/handlers.py``'s ``generate_proof_artifact`` handler,
roadmap P20): one place decides how Sprout/Diagnostician/Coach/Reporter
reach NVIDIA (or the deterministic ``FakeProvider`` fallback when no key is
configured), never two -- a worker process needs the exact same
NVIDIA-or-fake decision the API process makes, not a second copy of it.

Extracted from ``app.py`` (P10) rather than duplicated, per AGENTS.md's
"never create a second source of truth."
"""

from __future__ import annotations

import logging
import os

from protege.llm.router import ModelRouter
from protege.thin_thread.router_setup import build_router

from .settings import Settings

logger = logging.getLogger(__name__)


def build_default_model_router(settings: Settings) -> ModelRouter:
    """Real NVIDIA-backed router when a key is configured; otherwise the
    deterministic ``FakeProvider``, so both the API and the worker still
    boot for local development/tests without one.

    ``protege.thin_thread.router_setup.build_router("nvidia")`` always
    constructs a bare ``NvidiaProvider()``, which reads its key directly
    from ``os.environ`` -- never from this service's own ``Settings``. A
    key present in ``settings.nvidia_api_key`` (loaded from ``.env``) but
    never actually exported to the process environment must be exported
    here first, or ``NvidiaProvider()`` silently can't see it.
    """
    if settings.nvidia_api_key and not os.environ.get("NVIDIA_API_KEY"):
        os.environ["NVIDIA_API_KEY"] = settings.nvidia_api_key
    if settings.nvidia_api_key or os.environ.get("NVIDIA_API_KEY"):
        return _as_model_router(build_router("nvidia"))
    logger.warning(
        "NVIDIA_API_KEY is not configured -- Sprout/Diagnostician/Coach/Reporter will use "
        "the deterministic FakeProvider until it is set"
    )
    return _as_model_router(build_router("fake"))


def _as_model_router(router: object) -> ModelRouter:
    # `protege.thin_thread` has no `py.typed` marker (see `app.py`'s
    # original note on this same check) -- `build_router`'s real,
    # documented return type is always `ModelRouter`, but the type checker
    # sees `Any` across that untyped boundary. This `isinstance` check
    # makes the guarantee explicit and verified rather than casting past it.
    if not isinstance(router, ModelRouter):
        raise TypeError(f"build_router() returned {type(router)!r}, expected ModelRouter")
    return router
