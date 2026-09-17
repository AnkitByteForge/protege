"""Provider-neutral error hierarchy for the ``ModelRouter`` (roadmap P4).

Every exception a provider adapter or the router raises is one of these
types, so the router's fallback and telemetry logic can classify a failure
deterministically without depending on any provider SDK's exception types.
None of these ever carries a secret (an API key or an Authorization header) —
only ``provider`` and ``model_id`` identify the failure.
"""

from __future__ import annotations

from enum import StrEnum


class FallbackReason(StrEnum):
    """Why a fallback-chain entry was abandoned.

    Addendum §2.7 documents ``model_runs.fallback_reason`` with the
    illustrative set ``rate_limit|timeout|schema|validator``; that comment is
    not exhaustive (the column is free-form ``text``), so this enum adds the
    two further deterministic reasons the router itself can produce
    (``server_error``, ``circuit_open``) plus ``config_error`` for a
    misconfigured provider. ``validator`` is reserved for P5/P6's own
    telemetry when the *educational* validator (outside P4's scope) rejects
    an otherwise schema-valid value — the router never emits it itself.
    """

    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"
    SCHEMA = "schema"
    VALIDATOR = "validator"
    CIRCUIT_OPEN = "circuit_open"
    CONFIG_ERROR = "config_error"


class ProviderError(Exception):
    """Base for every provider-adapter failure."""

    def __init__(self, provider: str, model_id: str, message: str = "") -> None:
        self.provider = provider
        self.model_id = model_id
        super().__init__(message or f"{provider}:{model_id} failed")


class ProviderRateLimited(ProviderError):
    """The provider returned 429.

    The router waits for a rate-limiter slot and retries once against the
    same chain entry before moving to the next one (addendum §2.4).
    """


class ProviderTimeout(ProviderError):
    """The provider did not respond within ``timeout_s``.

    No retry against the same entry — the router moves straight to the next
    chain entry (addendum §2.4: "timeout or 5xx -> secondary").
    """


class ProviderFailed(ProviderError):
    """The provider returned a non-2xx, non-429 status (typically 5xx)."""

    def __init__(self, provider: str, model_id: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(provider, model_id, f"{provider}:{model_id} failed (status={status_code})")


class ProviderConfigError(ProviderError):
    """The provider is misconfigured (e.g. a missing API key).

    Never carries the secret value itself — only the fact that it is absent.
    """


class CircuitBreakerOpen(ProviderError):
    """The breaker for ``(provider, model_id)`` is open.

    The router skips this chain entry without making a network call.
    """


class StructuredOutputFailed(Exception):
    """Every tier for ``role`` failed to produce a value matching its schema.

    The ``ModelRouter`` moves to the next fallback-chain entry before this
    would ever propagate out of ``call_structured`` — it exists for direct
    unit testing of the structured-output primitives and as defense in
    depth.
    """

    def __init__(self, role: str, last_error: Exception | None) -> None:
        self.role = role
        self.last_error = last_error
        super().__init__(f"structured output failed for role={role}: {last_error}")


class AllProvidersExhausted(Exception):
    """``role``'s fallback chain has no deterministic-fallback sentinel.

    ARCHITECTURE.md §21/§8.1 requires every role's chain to terminate in a
    deterministic fallback, so this is a ``ROLE_POLICY`` configuration bug,
    not a runtime condition — it should never be reachable with a correctly
    authored policy.
    """

    def __init__(self, role: str) -> None:
        self.role = role
        super().__init__(
            f"role={role} exhausted its fallback chain with no deterministic "
            "fallback entry — ROLE_POLICY is misconfigured"
        )
