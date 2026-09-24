"""Clerk-verified actor extraction (roadmap P10).

The frontend (Next.js + Clerk) sends a Clerk session JWT as
``Authorization: Bearer <token>``; this module verifies it server-side using
Clerk's own official Python backend SDK (``clerk-backend-api`` --
``clerk_backend_api.Clerk.authenticate_request``), never a hand-rolled JWT
implementation. Verification is networkless whenever ``Settings.clerk_jwt_key``
(the PEM public key from the Clerk dashboard) is configured -- a pure,
in-process signature check, cached by construction rather than by a TTL
cache this module would need to manage. Without it, the SDK falls back to
fetching + internally caching the JWKS from Clerk's Backend API using
``Settings.clerk_secret_key``.

See ``docs/P10_SESSION_API.md`` for the exact Clerk dashboard configuration,
which environment variables are secret vs. public, and how ownership maps a
verified Clerk user id to a PROTÉGÉ ``parents`` row.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from typing import Any

import httpx
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from fastapi import Depends, Request
from starlette.concurrency import run_in_threadpool

from .deps import get_app_settings
from .errors import UnauthorizedError
from .settings import Settings

logger = logging.getLogger(__name__)


class ActorRole(StrEnum):
    """PROTÉGÉ-side role, read from a custom Clerk session-token claim
    (``role``, configured in the Clerk dashboard's session token
    customization -- see the deployment doc). Defaults to ``PARENT``: a
    signed-in caller with no explicit role claim is the common case (a
    parent account; the child plays under the parent's authenticated
    session on a shared device, per this product's COPPA-driven design --
    there is no independent child identity)."""

    PARENT = "parent"
    TUTOR = "tutor"
    ADMIN = "admin"


@dataclass(frozen=True)
class Actor:
    """A verified caller. Never constructed from anything the client
    supplied unverified -- only from a Clerk-signature-checked JWT payload."""

    clerk_user_id: str
    role: ActorRole
    claimed_learner_id: str | None
    email: str | None
    """The ``email`` custom session-token claim (Clerk dashboard -> Sessions
    -> Customize session token -- see ``docs/P10_SESSION_API.md``), read the
    same way as ``role``/``learner_id`` below: verified only in the sense
    that it rode inside the signature-checked JWT, exactly like every other
    claim here. Never an ownership/authorization key -- ``authz.py`` resolves
    every ownership check off ``clerk_user_id`` alone. Its only consumer is
    ``routes/learners.py``'s ``/v1/learners/ensure``, which needs a real
    email solely to satisfy ``parents.email``'s NOT NULL/UNIQUE schema
    constraint the first time a parent row is created for this identity."""


@lru_cache(maxsize=8)
def _clerk_client(secret_key: str) -> Clerk:
    """One SDK client per secret key (effectively a singleton), so the SDK's
    own JWKS caching (when ``jwt_key`` is not configured) persists across
    requests instead of being rebuilt each time."""
    return Clerk(bearer_auth=secret_key)


def _authorized_parties(settings: Settings) -> list[str]:
    parties = settings.clerk_authorized_parties.split(",")
    return [party.strip() for party in parties if party.strip()]


def _to_httpx_request(request: Request) -> httpx.Request:
    """The Clerk SDK verifies an ``httpx.Request`` -- it only ever reads the
    method, URL, and headers (the bearer token and, for a cookie-based
    fallback, cookies), so no body copy is needed."""
    return httpx.Request(
        method=request.method,
        url=str(request.url),
        headers=list(request.headers.items()),
    )


def _role_from_claims(claims: dict[str, Any]) -> ActorRole:
    raw = claims.get("role")
    if not isinstance(raw, str):
        metadata = claims.get("public_metadata")
        raw = metadata.get("role") if isinstance(metadata, dict) else None
    if raw in (ActorRole.TUTOR.value, ActorRole.ADMIN.value):
        return ActorRole(raw)
    return ActorRole.PARENT


async def get_current_actor(
    request: Request, settings: Settings = Depends(get_app_settings)
) -> Actor:
    """FastAPI dependency: verify the request's Clerk session JWT and
    return the resulting :class:`Actor`. Raises :class:`UnauthorizedError`
    (RFC 9457, ``child_safe_message`` set) on any failure -- an invalid
    signature, an expired/not-yet-valid token, an unrecognised authorized
    party, or a missing ``Authorization`` header. Never logs the token
    itself or any raw claim payload."""
    if not settings.clerk_secret_key:
        raise UnauthorizedError("authentication is not configured")

    client = _clerk_client(settings.clerk_secret_key)
    httpx_request = _to_httpx_request(request)
    parties = _authorized_parties(settings)
    options = AuthenticateRequestOptions(
        authorized_parties=parties or None,
        jwt_key=settings.clerk_jwt_key or None,
    )

    try:
        # Networkless when `jwt_key` is set (pure signature check); still
        # run off the event loop defensively for the JWKS-fetch fallback
        # path, which does make an HTTP call.
        request_state = await run_in_threadpool(client.authenticate_request, httpx_request, options)
    except Exception:  # Clerk SDK error -- never leak provider internals
        logger.warning("clerk token verification raised", exc_info=True)
        raise UnauthorizedError("could not verify credentials") from None

    if not request_state.is_signed_in:
        logger.info("clerk token rejected", extra={"reason": str(request_state.reason)})
        raise UnauthorizedError("not signed in")

    claims: dict[str, Any] = dict(request_state.payload or {})
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise UnauthorizedError("token missing subject claim")

    claimed_learner_id = claims.get("learner_id")
    email = claims.get("email")
    return Actor(
        clerk_user_id=subject,
        role=_role_from_claims(claims),
        claimed_learner_id=claimed_learner_id if isinstance(claimed_learner_id, str) else None,
        email=email if isinstance(email, str) else None,
    )
