"""PROTÉGÉ session service — FastAPI skeleton (roadmap P0).

P0 scope: application boot, /healthz, structured configuration, structured JSON
logging, and an OpenTelemetry tracer emitting to the console. No learning logic
exists yet by design.
"""

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from protege.session_service.logging import configure_logging
from protege.session_service.settings import Settings, get_settings

logger = logging.getLogger(__name__)

SERVICE_NAME = "protege-session"
VERSION = "0.1.0"

_tracing_configured = False


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

    @app.middleware("http")
    async def log_requests(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        logger.info(
            "http request",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            },
        )
        return response

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME, "version": VERSION}

    return app


app = create_app()
