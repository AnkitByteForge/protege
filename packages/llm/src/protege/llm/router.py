"""``ModelRouter`` — role -> (provider, model) resolution, ordered fallback
chains, the 35 RPM global token bucket, per-``(provider, model)`` circuit
breaking, prompt-hash response caching, structured-output enforcement, and
per-call telemetry (roadmap P4; addendum §1.6, §2).

No component here calls the session orchestrator and no component here
decides a session transition — the router only ever answers "give me role
X's next structured value," never "what should happen next"
(ARCHITECTURE.md §39).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pydantic import BaseModel

from protege.contracts import (
    CoachHint,
    DiagnosisResult,
    PedagogicalRole,
    ReportDraft,
    SproutTurn,
)

from .base import LLMProvider, LLMResult, Message
from .cache import PromptCache, hash_prompt
from .circuit_breaker import CircuitBreaker
from .errors import (
    AllProvidersExhausted,
    ProviderConfigError,
    ProviderError,
    ProviderFailed,
    ProviderRateLimited,
    ProviderTimeout,
)
from .errors import FallbackReason as FR
from .rate_limit import RateLimitTimeout, TokenBucket
from .structured import (
    StructuredMode,
    StructuredParseError,
    build_repair_messages,
    parse_structured,
)
from .telemetry import InMemoryTelemetrySink, ModelRunRecord, TelemetrySink

# --- Role policy (addendum §1.6, §2.2) --------------------------------------
#
# Every chain entry is either "<provider_name>:<model_id>" or a deterministic
# -fallback sentinel (any entry with no registered provider prefix). Moderation
# never reaches the router's provider path at all — its "chain" is a single
# sentinel, modelling addendum §2.2/§2.3's "moderation runs locally, never via
# NVIDIA" without this package implementing the local classifier (that is
# P25's scope).
#
# Model routing refreshed 2026-09-17 after live verification against
# NVIDIA's hosted API (see test_nvidia_smoke.py). The original P4 policy
# used "meta/llama-3.3-70b-instruct" and "meta/llama-3.1-8b-instruct";
# BOTH now return HTTP 410 Gone (permanently retired by NVIDIA — confirmed
# live, not inferred from the catalog page). Every model below was
# live-tested for both a plain completion AND the full structured-output
# path (native/repair tiers, parsed and validated against a real P1
# contract model) before being used here:
#
#   nvidia/nemotron-3-super-120b-a12b   — PASS (plain + structured)
#   nvidia/nemotron-3-ultra-550b-a55b   — PASS (plain + structured)
#   nvidia/nemotron-3.5-lightning-30b-a3b        — plain OK, structured FAILED (not used)
#   nvidia/nemotron-3-nano-omni-30b-a3b-reasoning — plain OK, structured FAILED (not used)
#
# Only the two PASS models are used. Ultra (550B, the largest
# reasoning-capable model verified) is DIAGNOSTICIAN's primary per
# addendum §2.2 ("highest-stakes inference"); Super (120B) is the
# workhorse everywhere else, with Ultra held as backup.

ROLE_POLICY: dict[PedagogicalRole, tuple[str, ...]] = {
    PedagogicalRole.SPROUT: (
        "nvidia:nvidia/nemotron-3-super-120b-a12b",
        "nvidia:nvidia/nemotron-3-ultra-550b-a55b",
        "authored_fallback",
    ),
    PedagogicalRole.DIAGNOSTICIAN: (
        "nvidia:nvidia/nemotron-3-ultra-550b-a55b",
        "nvidia:nvidia/nemotron-3-super-120b-a12b",
        "rule_based_distractor_map",
    ),
    PedagogicalRole.COACH: (
        "nvidia:nvidia/nemotron-3-super-120b-a12b",
        "nvidia:nvidia/nemotron-3-ultra-550b-a55b",
        "authored_verbatim",
    ),
    PedagogicalRole.REPORTER: (
        "nvidia:nvidia/nemotron-3-super-120b-a12b",
        "nvidia:nvidia/nemotron-3-ultra-550b-a55b",
        "pure_template",
    ),
    PedagogicalRole.MODERATION: ("local:blocklist+classifier",),
}

ROLE_RESPONSE_MODEL: dict[PedagogicalRole, type[BaseModel]] = {
    PedagogicalRole.SPROUT: SproutTurn,
    PedagogicalRole.DIAGNOSTICIAN: DiagnosisResult,
    PedagogicalRole.COACH: CoachHint,
    PedagogicalRole.REPORTER: ReportDraft,
}
"""No entry for MODERATION: moderation has no P1 structured-output contract —
it is a local classifier, not an LLM role (addendum §2.2)."""

DEFAULT_MAX_TOKENS = 512
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TIMEOUT_S = 2.5
"""Addendum §2.3: hard 2.5 s timeout on Sprout turns; used as the router's
general per-call default. A caller may override per role via the
``ModelRouter`` constructor."""
DEFAULT_RPM = 35.0
"""Addendum §2.3: headroom below NVIDIA's 40 RPM cap."""


class RolePolicyError(Exception):
    """``role`` has no ``ROLE_POLICY`` entry, or no response model could be
    resolved for it."""


@dataclass(frozen=True)
class StructuredCallOutcome:
    """What ``ModelRouter.call_structured`` returns.

    ``value`` is ``None`` exactly when ``used_deterministic_fallback`` is
    ``True`` — the router cannot manufacture a role's authored/rule-based
    content; the caller (P5 Sprout, P6 Diagnostician, P17 Coach, P20/P21
    Reporter) supplies it.
    """

    value: BaseModel | None
    used_deterministic_fallback: bool
    fallback_sentinel: str | None
    structured_mode: StructuredMode
    provider: str | None
    model_id: str | None
    attempts: int


@dataclass(frozen=True)
class HealthCheckResult:
    """One ``(provider, model_id)`` pair's startup health-check outcome
    (addendum §2.8: "a startup health check pings every model in
    ROLE_POLICY and refuses to boot on failure"). ``ModelRouter`` only
    reports status here — the boot decision belongs to whichever service
    embeds this router (out of P4's scope).

    ``roles`` lists every role whose chain references this exact
    ``(provider, model_id)`` pair — a pair referenced by two roles is
    still probed exactly once (docs/DECISIONS.md-style deduplication; see
    ``ModelRouter.health_check``).
    """

    roles: tuple[PedagogicalRole, ...]
    ok: bool
    provider: str
    model_id: str
    error: str | None


def _split_chain_entry(
    entry: str, registered_providers: Mapping[str, LLMProvider]
) -> tuple[str, str] | None:
    """Return ``(provider_name, model_id)`` for a provider-qualified entry,
    or ``None`` if ``entry`` is a deterministic-fallback sentinel.

    A sentinel is any entry whose ``provider_name`` prefix is not a
    *registered* provider — not merely any entry lacking a ``:``. This is
    what correctly routes ``"local:blocklist+classifier"`` (MODERATION's
    only chain entry, addendum §2.2/§2.3) to the deterministic-fallback
    path even though it contains a colon: no caller ever registers a
    provider named ``"local"``, because moderation never reaches the
    ModelRouter's network path at all.
    """
    if ":" not in entry:
        return None
    provider_name, model_id = entry.split(":", 1)
    if provider_name not in registered_providers:
        return None
    return provider_name, model_id


class ModelRouter:
    """Resolves a pedagogical role to a structured value, or to the
    signal that the caller must use its own deterministic fallback.

    Construct with a mapping of registered provider names (the prefix used
    in ``ROLE_POLICY`` chain entries, e.g. ``"nvidia"``) to ``LLMProvider``
    instances. Tests register ``{"nvidia": FakeProvider()}``.
    """

    def __init__(
        self,
        providers: Mapping[str, LLMProvider],
        *,
        role_policy: Mapping[PedagogicalRole, Sequence[str]] = ROLE_POLICY,
        rate_limiter: TokenBucket | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        cache: PromptCache | None = None,
        telemetry: TelemetrySink | None = None,
        prompt_version: str = "v1",
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self._providers = dict(providers)
        self._role_policy: dict[PedagogicalRole, tuple[str, ...]] = {
            role: tuple(chain) for role, chain in role_policy.items()
        }
        self._bucket = rate_limiter if rate_limiter is not None else TokenBucket(DEFAULT_RPM)
        self._breaker = circuit_breaker if circuit_breaker is not None else CircuitBreaker()
        self._cache = cache if cache is not None else PromptCache()
        self._telemetry = telemetry if telemetry is not None else InMemoryTelemetrySink()
        self._prompt_version = prompt_version
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._timeout_s = timeout_s
        self._total_calls = 0
        self._fallback_calls = 0

    @property
    def telemetry(self) -> TelemetrySink:
        return self._telemetry

    @property
    def fallback_rate(self) -> float:
        """Fraction of ``call_structured`` invocations that reached tier 3
        (deterministic fallback) — addendum §2.5's ship metric: "every
        tier-3 event increments fallback_rate."""
        return self._fallback_calls / self._total_calls if self._total_calls else 0.0

    def _provider_for(self, name: str) -> LLMProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise ProviderConfigError(name, "", f"no provider registered as '{name}'") from exc

    def _base_url_for(self, provider_name: str) -> str:
        provider = self._providers.get(provider_name)
        return getattr(provider, "base_url", "") if provider is not None else ""

    def call_structured(
        self,
        role: PedagogicalRole,
        messages: Sequence[Message],
        *,
        model_cls: type[BaseModel] | None = None,
        max_repairs: int = 1,
        trace_id: str | None = None,
    ) -> StructuredCallOutcome:
        """Resolve ``role``'s fallback chain to a structured value.

        Walks ``ROLE_POLICY[role]`` in order. Each provider-qualified entry
        is attempted with the documented three-tier structured-output
        strategy (native -> one repair -> give up on this entry); the first
        deterministic-fallback sentinel encountered is returned as
        ``used_deterministic_fallback=True`` rather than attempted.
        """
        chain = self._role_policy.get(role)
        if chain is None:
            raise RolePolicyError(f"no ROLE_POLICY entry for role={role}")

        self._total_calls += 1
        run_trace_id = trace_id if trace_id is not None else str(uuid.uuid4())
        resolved_model_cls: type[BaseModel] | None = None
        schema: dict[str, object] | None = None
        schema_title = ""

        for entry in chain:
            split = _split_chain_entry(entry, self._providers)
            if split is None:
                self._fallback_calls += 1
                self._telemetry.record(
                    ModelRunRecord(
                        provider="deterministic",
                        endpoint_base_url="",
                        model_id=entry,
                        role=str(role),
                        prompt_version=self._prompt_version,
                        attempt_index=0,
                        fallback_reason=None,
                        structured_mode=StructuredMode.FAILED,
                        tokens_in=0,
                        tokens_out=0,
                        latency_ms=0,
                        trace_id=run_trace_id,
                        credits_estimated=0.0,
                    )
                )
                return StructuredCallOutcome(
                    value=None,
                    used_deterministic_fallback=True,
                    fallback_sentinel=entry,
                    structured_mode=StructuredMode.FAILED,
                    provider=None,
                    model_id=None,
                    attempts=0,
                )

            provider_name, model_id = split

            if resolved_model_cls is None:
                resolved_model_cls = (
                    model_cls if model_cls is not None else ROLE_RESPONSE_MODEL.get(role)
                )
                if resolved_model_cls is None:
                    raise RolePolicyError(
                        f"no response model for role={role}; pass model_cls explicitly"
                    )
                schema = resolved_model_cls.model_json_schema()
                schema_title = str(schema.get("title", resolved_model_cls.__name__))

            if self._breaker.is_open(provider_name, model_id):
                self._telemetry.record(
                    ModelRunRecord(
                        provider=provider_name,
                        endpoint_base_url=self._base_url_for(provider_name),
                        model_id=model_id,
                        role=str(role),
                        prompt_version=self._prompt_version,
                        attempt_index=0,
                        fallback_reason=FR.CIRCUIT_OPEN,
                        structured_mode=StructuredMode.FAILED,
                        tokens_in=0,
                        tokens_out=0,
                        latency_ms=0,
                        trace_id=run_trace_id,
                        credits_estimated=0.0,
                    )
                )
                continue

            outcome = self._attempt_chain_entry(
                provider_name=provider_name,
                model_id=model_id,
                role=role,
                messages=messages,
                model_cls=resolved_model_cls,
                schema=schema or {},
                schema_title=schema_title,
                max_repairs=max_repairs,
                trace_id=run_trace_id,
            )
            if outcome is not None:
                return outcome
            # This entry failed outright (rate-limited twice, timed out,
            # 5xx, or exhausted its repair attempts) — fall through.

        raise AllProvidersExhausted(str(role))

    def _complete_once(
        self,
        provider: LLMProvider,
        provider_name: str,
        model_id: str,
        messages: Sequence[Message],
        schema: dict[str, object],
        *,
        role: PedagogicalRole,
        base_url: str,
        trace_id: str,
        start_attempt_index: int,
    ) -> tuple[LLMResult | None, int]:
        """One logical network attempt against ``(provider_name, model_id)``,
        including the documented single 429 retry against the same model
        after waiting for a fresh bucket slot (addendum §2.4).

        Bucket starvation (``RateLimitTimeout``) is treated identically to a
        429 response from the provider itself — the deterministic fallback
        must always stay reachable even when the rate limiter, not the
        provider, is what is exhausted (addendum §2.4: "requests wait rather
        than fail"; ARCHITECTURE.md §39: "failure degrades to authored
        content, never to an error message").

        Records one ``ModelRunRecord`` for every REAL attempt made here
        (including the internal 429 retry), so telemetry never undercounts
        actual network traffic. Returns ``(result, next_attempt_index)``;
        ``result`` is ``None`` iff every attempt failed, in which case the
        caller must move to the next chain entry — a network failure is
        never "repaired" by re-prompting, unlike a schema mismatch.

        Known tradeoff (not addressed here — the global bucket is shared
        across every role/model, so starvation caused by unrelated traffic
        also counts as a failure against *this* ``(provider, model_id)``'s
        circuit breaker, even though the pair itself may be perfectly
        healthy). Correcting this would mean giving the breaker a distinct
        "starved" category separate from "provider failed," which is a
        circuit-breaker redesign question, not part of this fix.
        """
        attempt_index = start_attempt_index
        for rate_limit_attempt in range(2):  # first try + one retry on 429
            try:
                self._bucket.acquire(timeout_s=self._timeout_s * 4)
            except RateLimitTimeout:
                self._breaker.record_failure(provider_name, model_id)
                self._record_failed_attempt(
                    provider_name, base_url, model_id, role, attempt_index, FR.RATE_LIMIT, trace_id
                )
                attempt_index += 1
                if rate_limit_attempt == 0:
                    continue
                return None, attempt_index
            try:
                result = provider.complete(
                    messages,
                    model_id=model_id,
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                    timeout_s=self._timeout_s,
                    json_schema=schema,
                )
            except ProviderRateLimited:
                self._breaker.record_failure(provider_name, model_id)
                self._record_failed_attempt(
                    provider_name, base_url, model_id, role, attempt_index, FR.RATE_LIMIT, trace_id
                )
                attempt_index += 1
                if rate_limit_attempt == 0:
                    continue
                return None, attempt_index
            except ProviderTimeout:
                self._breaker.record_failure(provider_name, model_id)
                self._record_failed_attempt(
                    provider_name, base_url, model_id, role, attempt_index, FR.TIMEOUT, trace_id
                )
                return None, attempt_index + 1
            except ProviderFailed:
                self._breaker.record_failure(provider_name, model_id)
                self._record_failed_attempt(
                    provider_name,
                    base_url,
                    model_id,
                    role,
                    attempt_index,
                    FR.SERVER_ERROR,
                    trace_id,
                )
                return None, attempt_index + 1
            else:
                return result, attempt_index
        return None, attempt_index  # pragma: no cover - defensive, unreachable

    def _attempt_chain_entry(
        self,
        *,
        provider_name: str,
        model_id: str,
        role: PedagogicalRole,
        messages: Sequence[Message],
        model_cls: type[BaseModel],
        schema: dict[str, object],
        schema_title: str,
        max_repairs: int,
        trace_id: str,
    ) -> StructuredCallOutcome | None:
        provider = self._provider_for(provider_name)
        base_url = self._base_url_for(provider_name)

        cache_key = hash_prompt(provider_name, str(role), model_id, messages, schema_title)
        cached = self._cache.get(cache_key)
        if cached is not None:
            cached_text, cached_result = cached
            try:
                value = parse_structured(cached_text, model_cls)
            except StructuredParseError:
                pass  # A corrupt cache entry is treated as a miss, not trusted.
            else:
                self._telemetry.record(
                    ModelRunRecord(
                        provider=provider_name,
                        endpoint_base_url=base_url,
                        model_id=model_id,
                        role=str(role),
                        prompt_version=self._prompt_version,
                        attempt_index=0,
                        fallback_reason=None,
                        structured_mode=StructuredMode.NATIVE,
                        tokens_in=cached_result.tokens_in,
                        tokens_out=cached_result.tokens_out,
                        latency_ms=0,
                        trace_id=trace_id,
                        credits_estimated=0.0,
                        cache_hit=True,
                    )
                )
                return StructuredCallOutcome(
                    value=value,
                    used_deterministic_fallback=False,
                    fallback_sentinel=None,
                    structured_mode=StructuredMode.NATIVE,
                    provider=provider_name,
                    model_id=model_id,
                    attempts=0,
                )

        current_messages: list[Message] = list(messages)
        network_attempt_index = 0
        """Counts every REAL network call made against this chain entry, in
        order — including the internal 429 retry inside `_complete_once` —
        so `ModelRunRecord.attempt_index` never undercounts actual traffic.
        Distinct from the outer `repair_attempt` loop variable, which counts
        schema-repair tiers only (0 = native, 1 = the one repair prompt)."""

        for repair_attempt in range(max_repairs + 1):
            result, network_attempt_index = self._complete_once(
                provider,
                provider_name,
                model_id,
                current_messages,
                schema,
                role=role,
                base_url=base_url,
                trace_id=trace_id,
                start_attempt_index=network_attempt_index,
            )
            if result is None:
                # `_complete_once` already recorded a `ModelRunRecord` for
                # every failed network attempt it made — nothing further to
                # log here. A network failure is never "repaired" by
                # re-prompting, so the entry is abandoned outright.
                return None

            try:
                value = parse_structured(result.text, model_cls)
            except StructuredParseError as exc:
                # The provider itself answered fine; only the content shape
                # is wrong, so this is not a circuit-breaker failure.
                self._breaker.record_success(provider_name, model_id)
                mode = StructuredMode.NATIVE if repair_attempt == 0 else StructuredMode.PROMPT
                self._telemetry.record(
                    ModelRunRecord(
                        provider=provider_name,
                        endpoint_base_url=base_url,
                        model_id=model_id,
                        role=str(role),
                        prompt_version=self._prompt_version,
                        attempt_index=network_attempt_index,
                        fallback_reason=FR.SCHEMA,
                        structured_mode=mode,
                        tokens_in=result.tokens_in,
                        tokens_out=result.tokens_out,
                        latency_ms=result.latency_ms,
                        trace_id=trace_id,
                        credits_estimated=1.0,
                    )
                )
                network_attempt_index += 1
                if repair_attempt < max_repairs:
                    current_messages = build_repair_messages(list(messages), result.text, exc.cause)
                    continue
                return None  # repair attempt(s) exhausted -> next chain entry

            self._breaker.record_success(provider_name, model_id)
            mode = StructuredMode.NATIVE if repair_attempt == 0 else StructuredMode.PROMPT
            self._telemetry.record(
                ModelRunRecord(
                    provider=provider_name,
                    endpoint_base_url=base_url,
                    model_id=model_id,
                    role=str(role),
                    prompt_version=self._prompt_version,
                    attempt_index=network_attempt_index,
                    fallback_reason=None,
                    structured_mode=mode,
                    tokens_in=result.tokens_in,
                    tokens_out=result.tokens_out,
                    latency_ms=result.latency_ms,
                    trace_id=trace_id,
                    credits_estimated=1.0,
                )
            )
            self._cache.put(cache_key, result.text, result)
            return StructuredCallOutcome(
                value=value,
                used_deterministic_fallback=False,
                fallback_sentinel=None,
                structured_mode=mode,
                provider=provider_name,
                model_id=model_id,
                attempts=repair_attempt + 1,
            )

        return None  # pragma: no cover - defensive, loop always returns above

    def _record_failed_attempt(
        self,
        provider_name: str,
        base_url: str,
        model_id: str,
        role: PedagogicalRole,
        attempt_index: int,
        reason: FR,
        trace_id: str,
    ) -> None:
        self._telemetry.record(
            ModelRunRecord(
                provider=provider_name,
                endpoint_base_url=base_url,
                model_id=model_id,
                role=str(role),
                prompt_version=self._prompt_version,
                attempt_index=attempt_index,
                fallback_reason=reason,
                structured_mode=StructuredMode.FAILED,
                tokens_in=0,
                tokens_out=0,
                latency_ms=0,
                trace_id=trace_id,
                credits_estimated=0.0 if reason == FR.RATE_LIMIT else 1.0,
            )
        )

    def health_check(
        self, *, roles: Sequence[PedagogicalRole] | None = None
    ) -> dict[tuple[str, str], HealthCheckResult]:
        """Ping every unique real ``(provider, model_id)`` pair referenced
        by ``roles``' chains — addendum §2.8: "a startup health check pings
        **every model** in ROLE_POLICY," not just each role's primary.

        Deterministic-fallback sentinels (e.g. MODERATION's local
        classifier) are skipped entirely — they are never network-reachable
        and never spend rate-limiter budget. A ``(provider, model_id)`` pair
        referenced by more than one role's chain is probed exactly once;
        its result's ``roles`` field lists every role that references it.

        Reports status only; it never falls through a chain to a secondary
        model on failure (a health check probes each configured model on
        its own merits) and it never raises — including on rate-limiter
        starvation (``RateLimitTimeout``), which is caught here exactly as
        ``call_structured`` catches it. Callers (the service, at boot) use
        this to "refuse to boot" on failure — that decision belongs to
        whichever service embeds this router, out of P4's scope.
        """
        targets = roles if roles is not None else list(self._role_policy.keys())

        roles_by_model: dict[tuple[str, str], list[PedagogicalRole]] = {}
        for role in targets:
            for entry in self._role_policy.get(role, ()):
                split = _split_chain_entry(entry, self._providers)
                if split is None:
                    continue  # deterministic-fallback sentinel: never network-reachable
                roles_by_model.setdefault(split, []).append(role)

        results: dict[tuple[str, str], HealthCheckResult] = {}
        for (provider_name, model_id), owning_roles in roles_by_model.items():
            try:
                provider = self._provider_for(provider_name)
                self._bucket.acquire(timeout_s=self._timeout_s * 4)
                provider.complete(
                    [Message("user", "ping")],
                    model_id=model_id,
                    max_tokens=2,
                    temperature=0.0,
                    timeout_s=self._timeout_s,
                    json_schema=None,
                )
            except (ProviderError, RateLimitTimeout) as exc:
                results[provider_name, model_id] = HealthCheckResult(
                    roles=tuple(owning_roles),
                    ok=False,
                    provider=provider_name,
                    model_id=model_id,
                    error=str(exc),
                )
            else:
                results[provider_name, model_id] = HealthCheckResult(
                    roles=tuple(owning_roles),
                    ok=True,
                    provider=provider_name,
                    model_id=model_id,
                    error=None,
                )
        return results
