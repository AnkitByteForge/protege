"""PROTÉGÉ session service — FastAPI application (roadmap P0 + P10).

P0 scope: application boot, /healthz, structured configuration, structured JSON
logging, and an OpenTelemetry tracer emitting to the console.

P10 adds: the `/v1/*` REST + SSE surface over the P7 FSM/orchestrator and P9
persistence (see `routes/`, `engine/`), RFC 9457 problem+json error handling
(`errors.py`), and a `traceparent` response header on every request so a
client-supplied or server-generated trace context threads through to the
orchestrator and persistence layers via the same OTel span.
"""

import logging
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from protege.llm.router import ModelRouter
from protege.thin_thread.router_setup import build_router

from .errors import register_exception_handlers
from .logging import configure_logging
from .routes.learners import router as learners_router
from .routes.parents import router as parents_router
from .routes.sessions import router as sessions_router
from .settings import Settings, get_settings

logger = logging.getLogger(__name__)

SERVICE_NAME = "protege-session"
VERSION = "0.1.0"

_tracing_configured = False
_trace_propagator = TraceContextTextMapPropagator()


def _build_default_router(settings: Settings) -> ModelRouter:
    """The process-wide :class:`~protege.llm.router.ModelRouter` behind
    Sprout/Diagnostician (roadmap: "the API is a transport over P7" --
    P10 wires the *existing* P4/P5/P6 stack, never a second LLM client).

    Falls back to the deterministic ``FakeProvider`` when no NVIDIA key is
    configured, so the service still boots for local development/tests
    without one -- a route that actually reaches Sprout/the Diagnostician
    then gets stable canned output rather than a startup crash. Real
    deployments must set ``NVIDIA_API_KEY``.

    ``protege.thin_thread.router_setup.build_router("nvidia")`` always
    constructs a bare ``NvidiaProvider()`` (P4/P8 code, out of P10's scope
    to change), which reads its key directly from ``os.environ`` -- never
    from this service's own ``Settings``. Every other secret in this app is
    configured via ``.env``/``Settings`` only, so a key present in
    ``settings.nvidia_api_key`` (loaded from ``.env``) but never actually
    exported to the process environment must be exported here first, or
    ``NvidiaProvider()`` silently can't see it and the app fails to boot
    the moment a real key is configured the same way every other key is.
    """
    if settings.nvidia_api_key and not os.environ.get("NVIDIA_API_KEY"):
        os.environ["NVIDIA_API_KEY"] = settings.nvidia_api_key
    if settings.nvidia_api_key or os.environ.get("NVIDIA_API_KEY"):
        return _as_model_router(build_router("nvidia"))
    logger.warning(
        "NVIDIA_API_KEY is not configured -- Sprout/Diagnostician will use the "
        "deterministic FakeProvider until it is set"
    )
    return _as_model_router(build_router("fake"))


def _as_model_router(router: object) -> ModelRouter:
    # `protege.thin_thread` has no `py.typed` marker (pyproject.toml's own
    # mypy override note: adding one belongs to that package's P8 phase,
    # not P10) -- `build_router`'s real, documented return type is always
    # `ModelRouter`, but the type checker sees `Any` across that untyped
    # boundary. This `isinstance` check makes the guarantee explicit and
    # verified rather than casting past it.
    if not isinstance(router, ModelRouter):
        raise TypeError(f"build_router() returned {type(router)!r}, expected ModelRouter")
    return router


def setup_tracing() -> None:
    """Install an OTel tracer provider that exports spans to the console.

    P0 keeps observability local (roadmap: "OTel SDK installed and emitting to
    console"). The OTLP → Langfuse export arrives in P26 behind the same
    provider interface, so call sites do not change.
    """
    provider = TracerProvider(resource=Resource.create({"service.name": SERVICE_NAME}))
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("app.startup") as span:
        span.set_attribute("service.version", VERSION)
        logger.info("session service starting", extra={"service": SERVICE_NAME, "version": VERSION})
    yield
    logger.info("session service stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    global _tracing_configured

    resolved = settings or get_settings()
    configure_logging(resolved.log_level)

    if resolved.otel_console_export and not _tracing_configured:
        setup_tracing()
        _tracing_configured = True

    app = FastAPI(title="PROTÉGÉ Session Service", version=VERSION, lifespan=_lifespan)
    app.state.settings = resolved
    # Real NVIDIA-backed Sprout/Diagnostician by default; tests override via
    # `app.dependency_overrides[deps.get_model_router]` with a
    # `ModelRouter({"nvidia": FakeProvider(...)})`, exactly as
    # `packages/thin-thread`'s own tests do (never a second LLM client).
    app.state.model_router = _build_default_router(resolved)

    register_exception_handlers(app)

    @app.middleware("http")
    async def log_requests(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        tracer = trace.get_tracer(__name__)
        start = time.perf_counter()
        with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)
            carrier: dict[str, str] = {}
            _trace_propagator.inject(carrier)
            traceparent = carrier.get("traceparent")
            if traceparent:
                response.headers["traceparent"] = traceparent
        logger.info(
            "http request",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                "trace_id": traceparent,
            },
        )
        return response

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME, "version": VERSION}

    app.include_router(sessions_router, prefix="")
    app.include_router(learners_router, prefix="")
    app.include_router(parents_router, prefix="")

    return app


app = create_app()
