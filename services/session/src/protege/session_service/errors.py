"""RFC 9457 ``problem+json`` error model (roadmap P10).

Every error this API returns is an :class:`ApiError` (or a FastAPI/Starlette
built-in the handlers below translate into one) carrying a
``child_safe_message`` the UI can render directly to a child with no further
translation -- never a stack trace, an internal exception string, SQL, a
provider secret, a model name, or an internal routing decision. Handlers are
registered once, by :func:`register_exception_handlers`, against the app
this service builds; nothing route-level ever constructs a raw
``JSONResponse`` for an error.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

PROBLEM_CONTENT_TYPE = "application/problem+json"

_GENERIC_CHILD_SAFE_MESSAGE = "Oops! Something went wrong. Let's try that again in a moment."


class ApiError(Exception):
    """Base for every P10-raised error. ``type_`` is a short, stable,
    dot-free slug (not a dereferenceable URI -- this API has no public docs
    site to host RFC 9457 ``type`` pages at, so a slug under a fixed,
    documented namespace is used instead, consistent with RFC 9457 §3.1
    permitting ``type`` to be any URI reference; readers should treat it as
    opaque)."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    type_: str = "about:blank"
    title: str = "Internal Server Error"
    child_safe_message: str = _GENERIC_CHILD_SAFE_MESSAGE

    def __init__(
        self,
        detail: str | None = None,
        *,
        child_safe_message: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail or self.title)
        self.detail = detail or self.title
        if child_safe_message is not None:
            self.child_safe_message = child_safe_message
        self.extra = extra or {}

    def to_problem(self, *, instance: str) -> dict[str, Any]:
        problem: dict[str, Any] = {
            "type": self.type_,
            "title": self.title,
            "status": self.status_code,
            "detail": self.detail,
            "instance": instance,
            "child_safe_message": self.child_safe_message,
        }
        problem.update(self.extra)
        return problem


class BadRequestError(ApiError):
    status_code = status.HTTP_400_BAD_REQUEST
    type_ = "protege:bad-request"
    title = "Bad Request"
    child_safe_message = "That didn't quite work. Let's try again."


class UnauthorizedError(ApiError):
    status_code = status.HTTP_401_UNAUTHORIZED
    type_ = "protege:unauthorized"
    title = "Unauthorized"
    child_safe_message = "You'll need a grown-up to help you sign in."


class ForbiddenError(ApiError):
    status_code = status.HTTP_403_FORBIDDEN
    type_ = "protege:forbidden"
    title = "Forbidden"
    child_safe_message = "This isn't your garden to visit."


class NotFoundError(ApiError):
    status_code = status.HTTP_404_NOT_FOUND
    type_ = "protege:not-found"
    title = "Not Found"
    child_safe_message = "We couldn't find that. Let's start fresh."


class ConflictError(ApiError):
    status_code = status.HTTP_409_CONFLICT
    type_ = "protege:conflict"
    title = "Conflict"
    child_safe_message = "Someone already did that. Let's take a look."


class IllegalSessionTransitionError(ApiError):
    status_code = status.HTTP_409_CONFLICT
    type_ = "protege:illegal-session-transition"
    title = "Illegal Session Transition"
    child_safe_message = "That step isn't ready yet. Let's go back and try."


class UnprocessableEventError(ApiError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    type_ = "protege:unprocessable-event"
    title = "Unprocessable Event"
    child_safe_message = "That didn't quite work. Let's try again."


class IdempotencyKeyRequiredError(ApiError):
    status_code = status.HTTP_400_BAD_REQUEST
    type_ = "protege:idempotency-key-required"
    title = "Idempotency-Key Required"
    child_safe_message = "That didn't quite work. Let's try again."


class IdempotencyKeyReusedError(ApiError):
    status_code = status.HTTP_409_CONFLICT
    type_ = "protege:idempotency-key-reused"
    title = "Idempotency-Key Reused With A Different Request"
    child_safe_message = "That didn't quite work. Let's try again."


class RateLimitExceededError(ApiError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    type_ = "protege:rate-limit-exceeded"
    title = "Rate Limit Exceeded"
    child_safe_message = "Let's take a little break and try again soon."


class NotYetAvailableError(ApiError):
    """The canonical "not yet available" representation for an artifact
    whose writer is a later roadmap phase (roadmap P10: "return the
    canonical not-yet-available representation instead of fabricating
    data"). Not a client error -- ``200``/``202``-shaped callers should
    prefer returning a body over raising this; this exists for routes where
    a problem response is the cleaner shape (e.g. a 404-like "no artifact
    exists for this learner yet")."""

    status_code = status.HTTP_404_NOT_FOUND
    type_ = "protege:not-yet-available"
    title = "Not Yet Available"
    child_safe_message = "This isn't ready yet -- check back soon!"


def _instance(request: Request) -> str:
    return str(request.url.path)


async def _handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    if exc.status_code >= 500:
        logger.exception("unhandled api error", exc_info=exc)
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_problem(instance=_instance(request)),
        media_type=PROBLEM_CONTENT_TYPE,
    )


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Field-level messages are safe to surface (they describe the request
    # shape, not internals), but never the raw exception repr.
    fields = [
        {"loc": [str(part) for part in error["loc"]], "msg": error["msg"]} for error in exc.errors()
    ]
    problem = {
        "type": "protege:validation-error",
        "title": "Validation Error",
        "status": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "detail": "The request did not match the expected shape.",
        "instance": _instance(request),
        "child_safe_message": _GENERIC_CHILD_SAFE_MESSAGE,
        "errors": fields,
    }
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=problem,
        media_type=PROBLEM_CONTENT_TYPE,
    )


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    problem = {
        "type": "protege:http-error",
        "title": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
        "status": exc.status_code,
        "detail": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
        "instance": _instance(request),
        "child_safe_message": _GENERIC_CHILD_SAFE_MESSAGE,
    }
    return JSONResponse(
        status_code=exc.status_code, content=problem, media_type=PROBLEM_CONTENT_TYPE
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled exception", exc_info=exc)
    problem = {
        "type": "protege:internal-error",
        "title": "Internal Server Error",
        "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "detail": "An unexpected error occurred.",
        "instance": _instance(request),
        "child_safe_message": _GENERIC_CHILD_SAFE_MESSAGE,
    }
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem,
        media_type=PROBLEM_CONTENT_TYPE,
    )


def register_exception_handlers(app: FastAPI) -> None:
    # Starlette's own `add_exception_handler` stub types a handler generically
    # over `Exception`; each handler below is intentionally narrower (it is
    # only ever dispatched for its registered exception type, by Starlette's
    # own runtime lookup) -- a standard, accepted mismatch between that
    # generic stub and a per-exception-type handler, not a real type error.
    app.add_exception_handler(ApiError, _handle_api_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unexpected_error)
