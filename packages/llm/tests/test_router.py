"""Tests for `ModelRouter` — role resolution, ordered fallback chains,
circuit breaking, caching, structured-output tiering, and telemetry.

Every test uses `FakeProvider`; none makes a real network call.
"""

from __future__ import annotations

import pytest

from protege.contracts import CoachHint, PedagogicalRole, SproutTurn
from protege.llm.base import Message
from protege.llm.cache import PromptCache
from protege.llm.circuit_breaker import CircuitBreaker
from protege.llm.errors import AllProvidersExhausted, FallbackReason
from protege.llm.providers.fake import FakeOutcome, FakeProvider
from protege.llm.rate_limit import TokenBucket
from protege.llm.router import ROLE_POLICY, ModelRouter, RolePolicyError
from protege.llm.structured import StructuredMode


def _router(provider: FakeProvider, **kwargs: object) -> ModelRouter:
    kwargs.setdefault("rate_limiter", TokenBucket(rate_per_minute=6000.0))
    return ModelRouter({"nvidia": provider}, **kwargs)  # type: ignore[arg-type]


# --- Happy path --------------------------------------------------------------


def test_call_structured_returns_a_parsed_value_on_first_try() -> None:
    provider = FakeProvider()
    router = _router(provider)
    outcome = router.call_structured(PedagogicalRole.SPROUT, [Message("user", "hi")])
    assert isinstance(outcome.value, SproutTurn)
    assert outcome.structured_mode == StructuredMode.NATIVE
    assert outcome.provider == "nvidia"
    assert not outcome.used_deterministic_fallback
    assert outcome.attempts == 1


def test_explicit_model_cls_overrides_role_default() -> None:
    provider = FakeProvider()
    router = _router(provider)
    outcome = router.call_structured(
        PedagogicalRole.COACH, [Message("user", "hi")], model_cls=CoachHint
    )
    assert isinstance(outcome.value, CoachHint)


# --- Moderation: never touches the network ----------------------------------


def test_moderation_resolves_to_deterministic_fallback_without_a_network_call() -> None:
    provider = FakeProvider()
    router = _router(provider)
    outcome = router.call_structured(PedagogicalRole.MODERATION, [Message("user", "hi")])
    assert outcome.used_deterministic_fallback
    assert outcome.fallback_sentinel == "local:blocklist+classifier"
    assert provider.calls == []
    assert router.fallback_rate == 1.0


# --- Role policy errors -------------------------------------------------------


def test_unknown_role_raises_role_policy_error() -> None:
    provider = FakeProvider()
    router = ModelRouter({"nvidia": provider}, role_policy={})
    with pytest.raises(RolePolicyError):
        router.call_structured(PedagogicalRole.SPROUT, [Message("user", "hi")])


def test_missing_response_model_without_explicit_model_cls_raises() -> None:
    provider = FakeProvider()
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.MODERATION: ("nvidia:some-model",)},
    )
    with pytest.raises(RolePolicyError):
        router.call_structured(PedagogicalRole.MODERATION, [Message("user", "hi")])


def test_chain_with_no_deterministic_fallback_raises_all_providers_exhausted() -> None:
    provider = FakeProvider(script=[FakeOutcome.schema_invalid(), FakeOutcome.schema_invalid()])
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.SPROUT: ("nvidia:only-model",)},
        rate_limiter=TokenBucket(rate_per_minute=6000.0),
    )
    with pytest.raises(AllProvidersExhausted):
        router.call_structured(PedagogicalRole.SPROUT, [Message("user", "hi")])


# --- Rate limiting / 429 ------------------------------------------------------


def test_single_429_is_retried_once_against_the_same_entry_then_succeeds() -> None:
    provider = FakeProvider(
        script=[
            FakeOutcome.rate_limited(),
            FakeOutcome.ok('{"intervention_id": "X", "text": "hi"}'),
        ]
    )
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.SPROUT: ("nvidia:model-a", "authored_fallback")},
        rate_limiter=TokenBucket(rate_per_minute=6000.0),
    )
    outcome = router.call_structured(
        PedagogicalRole.SPROUT, [Message("user", "hi")], model_cls=CoachHint
    )
    assert outcome.model_id == "model-a"  # stayed on the same entry
    assert len(provider.calls) == 2

    # P1-3 regression: both real network calls (the failed 429 AND the
    # successful retry) must each produce their own ModelRunRecord, with
    # a monotonically increasing attempt_index — telemetry must never
    # undercount actual NVIDIA traffic just because a retry succeeded.
    runs = router.telemetry.runs  # type: ignore[attr-defined]
    assert len(runs) == 2
    assert runs[0].fallback_reason == FallbackReason.RATE_LIMIT
    assert runs[0].attempt_index == 0
    assert runs[1].fallback_reason is None
    assert runs[1].attempt_index == 1


def test_double_429_moves_to_the_next_chain_entry() -> None:
    provider = FakeProvider(script=[FakeOutcome.rate_limited(), FakeOutcome.rate_limited()])
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.SPROUT: ("nvidia:model-a", "authored_fallback")},
        rate_limiter=TokenBucket(rate_per_minute=6000.0),
    )
    outcome = router.call_structured(PedagogicalRole.SPROUT, [Message("user", "hi")])
    assert outcome.used_deterministic_fallback

    # P1-3 regression: BOTH real network calls (429, then 429 again) must
    # each produce their own ModelRunRecord — not just the first.
    runs = router.telemetry.runs  # type: ignore[attr-defined]
    rate_limit_runs = [r for r in runs if r.fallback_reason == FallbackReason.RATE_LIMIT]
    assert len(rate_limit_runs) == 2
    assert {r.attempt_index for r in rate_limit_runs} == {0, 1}
    assert len(provider.calls) == 2


def test_bucket_starvation_falls_through_to_deterministic_fallback_without_raising() -> None:
    """P0-1 regression: `TokenBucket.acquire` raising `RateLimitTimeout`
    (real, sustained rate-limiter starvation — not a provider-side 429)
    must be treated as a rate-limit failure and degrade gracefully through
    the fallback chain, exactly like the architecture's non-negotiable
    "failures degrade gracefully, never to an error" principle requires.
    Before the fix, this exception escaped `call_structured` uncaught."""
    bucket = TokenBucket(rate_per_minute=0.01, capacity=1.0)
    bucket.try_acquire()  # drain the only token so acquire() is guaranteed to starve
    provider = FakeProvider()
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.SPROUT: ("nvidia:model-a", "authored_fallback")},
        rate_limiter=bucket,
        timeout_s=0.05,
    )
    outcome = router.call_structured(
        PedagogicalRole.SPROUT, [Message("user", "hi")]
    )  # must not raise
    assert outcome.used_deterministic_fallback
    assert outcome.fallback_sentinel == "authored_fallback"
    runs = router.telemetry.runs  # type: ignore[attr-defined]
    rate_limit_runs = [r for r in runs if r.fallback_reason == FallbackReason.RATE_LIMIT]
    assert len(rate_limit_runs) >= 1
    assert provider.calls == []  # never even reached the provider — starved before that


# --- Timeout / 5xx: no retry on the same entry --------------------------------


def test_timeout_moves_straight_to_the_next_entry_without_retry() -> None:
    provider = FakeProvider(script=[FakeOutcome.timeout()])
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.SPROUT: ("nvidia:model-a", "authored_fallback")},
        rate_limiter=TokenBucket(rate_per_minute=6000.0),
    )
    outcome = router.call_structured(PedagogicalRole.SPROUT, [Message("user", "hi")])
    assert outcome.used_deterministic_fallback
    assert len(provider.calls) == 1  # no retry on timeout


def test_5xx_moves_to_the_next_entry() -> None:
    provider = FakeProvider(script=[FakeOutcome.server_error(503)])
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.SPROUT: ("nvidia:model-a", "authored_fallback")},
        rate_limiter=TokenBucket(rate_per_minute=6000.0),
    )
    outcome = router.call_structured(PedagogicalRole.SPROUT, [Message("user", "hi")])
    assert outcome.used_deterministic_fallback
    run = router.telemetry.runs[0]  # type: ignore[attr-defined]
    assert run.fallback_reason == FallbackReason.SERVER_ERROR


# --- Malformed JSON / schema mismatch: one repair, then fall through ----------


def test_malformed_json_triggers_one_repair_then_succeeds() -> None:
    provider = FakeProvider(
        script=[FakeOutcome.malformed(), FakeOutcome.ok('{"intervention_id": "X", "text": "hi"}')]
    )
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.SPROUT: ("nvidia:model-a", "authored_fallback")},
        rate_limiter=TokenBucket(rate_per_minute=6000.0),
    )
    outcome = router.call_structured(
        PedagogicalRole.SPROUT, [Message("user", "hi")], model_cls=CoachHint
    )
    assert not outcome.used_deterministic_fallback
    assert outcome.structured_mode == StructuredMode.PROMPT
    assert outcome.attempts == 2
    assert len(provider.calls) == 2


def test_repair_failure_falls_through_to_the_next_entry() -> None:
    provider = FakeProvider(
        script=[
            FakeOutcome.schema_invalid(),
            FakeOutcome.schema_invalid(),
        ]  # initial + the one repair
    )
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.SPROUT: ("nvidia:model-a", "authored_fallback")},
        rate_limiter=TokenBucket(rate_per_minute=6000.0),
    )
    outcome = router.call_structured(
        PedagogicalRole.SPROUT, [Message("user", "hi")], model_cls=CoachHint
    )
    assert outcome.used_deterministic_fallback
    schema_runs = [r for r in router.telemetry.runs if r.fallback_reason == FallbackReason.SCHEMA]  # type: ignore[attr-defined]
    assert len(schema_runs) == 2
    assert {r.attempt_index for r in schema_runs} == {0, 1}


def test_max_repairs_zero_disables_the_repair_attempt() -> None:
    provider = FakeProvider(script=[FakeOutcome.malformed()])
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.SPROUT: ("nvidia:model-a", "authored_fallback")},
        rate_limiter=TokenBucket(rate_per_minute=6000.0),
    )
    outcome = router.call_structured(
        PedagogicalRole.SPROUT, [Message("user", "hi")], model_cls=CoachHint, max_repairs=0
    )
    assert outcome.used_deterministic_fallback
    assert len(provider.calls) == 1


# --- Circuit breaker integration ----------------------------------------------


def test_circuit_breaker_opens_after_three_consecutive_failures_and_skips_the_network() -> None:
    provider = FakeProvider(
        script=[FakeOutcome.server_error(), FakeOutcome.server_error(), FakeOutcome.server_error()]
    )
    breaker = CircuitBreaker(failure_threshold=3, cooldown_s=999.0)
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.SPROUT: ("nvidia:model-a", "authored_fallback")},
        rate_limiter=TokenBucket(rate_per_minute=6000.0),
        circuit_breaker=breaker,
    )
    for _ in range(3):
        outcome = router.call_structured(PedagogicalRole.SPROUT, [Message("user", "hi")])
        assert outcome.used_deterministic_fallback
    assert len(provider.calls) == 3
    assert breaker.is_open("nvidia", "model-a")

    # A fourth call must not touch the network at all — the breaker is open.
    outcome = router.call_structured(PedagogicalRole.SPROUT, [Message("user", "hi")])
    assert outcome.used_deterministic_fallback
    assert len(provider.calls) == 3  # unchanged
    circuit_open_runs = [
        r
        for r in router.telemetry.runs
        if r.fallback_reason == FallbackReason.CIRCUIT_OPEN  # type: ignore[attr-defined]
    ]
    assert len(circuit_open_runs) == 1


def test_schema_mismatch_does_not_open_the_circuit_breaker() -> None:
    """A structurally-wrong-but-transport-successful response is not a
    provider failure — repeated schema mismatches must never trip the
    breaker meant for network/5xx/timeout failures."""
    provider = FakeProvider(
        script=[
            FakeOutcome.schema_invalid(),
            FakeOutcome.schema_invalid(),
            FakeOutcome.schema_invalid(),
            FakeOutcome.schema_invalid(),
        ]
    )
    breaker = CircuitBreaker(failure_threshold=3, cooldown_s=999.0)
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.SPROUT: ("nvidia:model-a", "authored_fallback")},
        rate_limiter=TokenBucket(rate_per_minute=6000.0),
        circuit_breaker=breaker,
        max_tokens=1,
    )
    router.call_structured(PedagogicalRole.SPROUT, [Message("user", "hi")], model_cls=CoachHint)
    router.call_structured(PedagogicalRole.SPROUT, [Message("user", "hi")], model_cls=CoachHint)
    assert not breaker.is_open("nvidia", "model-a")


# --- Cache hit/miss ------------------------------------------------------------


def test_second_identical_call_is_served_from_cache() -> None:
    provider = FakeProvider()
    cache = PromptCache()
    router = _router(provider, cache=cache)
    messages = [Message("user", "hi")]
    first = router.call_structured(PedagogicalRole.SPROUT, messages)
    second = router.call_structured(PedagogicalRole.SPROUT, messages)
    assert len(provider.calls) == 1  # only the first call touched the network
    assert first.value == second.value
    assert router.telemetry.runs[-1].cache_hit is True  # type: ignore[attr-defined]


def test_different_messages_are_not_cache_hits() -> None:
    provider = FakeProvider()
    router = _router(provider)
    router.call_structured(PedagogicalRole.SPROUT, [Message("user", "hi")])
    router.call_structured(PedagogicalRole.SPROUT, [Message("user", "bye")])
    assert len(provider.calls) == 2


# --- Telemetry / fallback_rate ------------------------------------------------


def test_fallback_rate_counts_only_tier_three_events() -> None:
    provider = FakeProvider()
    router = _router(provider)
    router.call_structured(PedagogicalRole.SPROUT, [Message("user", "hi")])  # succeeds via provider
    router.call_structured(PedagogicalRole.MODERATION, [Message("user", "hi")])  # deterministic
    assert router.fallback_rate == 0.5


def test_every_provider_call_produces_a_telemetry_record_with_documented_fields() -> None:
    provider = FakeProvider()
    router = _router(provider)
    router.call_structured(PedagogicalRole.SPROUT, [Message("user", "hi")])
    run = router.telemetry.runs[-1]  # type: ignore[attr-defined]
    assert run.provider == "nvidia"
    assert run.role == str(PedagogicalRole.SPROUT)
    assert run.structured_mode == StructuredMode.NATIVE
    assert run.trace_id is not None
    assert run.credits_estimated == 1.0


# --- health_check --------------------------------------------------------------


def test_health_check_reports_ok_for_every_reachable_model() -> None:
    provider = FakeProvider()
    router = _router(provider)
    results = router.health_check()
    # MODERATION's only chain entry is a sentinel: skipped, never reported.
    assert all(PedagogicalRole.MODERATION not in r.roles for r in results.values())
    for result in results.values():
        assert result.ok, f"{result.model_id} expected healthy"


def test_health_check_probes_every_unique_provider_qualified_model_in_role_policy() -> None:
    """P1-1 regression: addendum §2.8 requires pinging *every* model in
    ROLE_POLICY, not just each role's primary. This must cover every
    provider-qualified entry across every role, deduplicated, and skip
    sentinels entirely."""
    provider = FakeProvider()
    router = _router(provider)
    results = router.health_check()

    expected_pairs: set[tuple[str, str]] = set()
    for chain in ROLE_POLICY.values():
        for entry in chain:
            if ":" not in entry:
                continue
            provider_name, model_id = entry.split(":", 1)
            if provider_name != "nvidia":
                continue  # e.g. MODERATION's "local:..." sentinel
            expected_pairs.add((provider_name, model_id))

    assert set(results) == expected_pairs
    # SPROUT's secondary model must actually have been pinged, not just its primary.
    assert ("nvidia", "nvidia/nemotron-3-super-120b-a12b") in results
    assert PedagogicalRole.SPROUT in results[("nvidia", "nvidia/nemotron-3-super-120b-a12b")].roles
    assert (
        PedagogicalRole.DIAGNOSTICIAN
        in results[("nvidia", "nvidia/nemotron-3-super-120b-a12b")].roles
    )


def test_health_check_skips_deterministic_fallback_sentinels() -> None:
    provider = FakeProvider()
    router = _router(provider)
    results = router.health_check(roles=[PedagogicalRole.MODERATION])
    assert results == {}
    assert provider.calls == []  # never touched the network for a sentinel-only role


def test_health_check_deduplicates_a_model_referenced_by_two_roles() -> None:
    provider = FakeProvider()
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={
            PedagogicalRole.SPROUT: ("nvidia:shared-model", "authored_fallback"),
            PedagogicalRole.COACH: ("nvidia:shared-model", "authored_verbatim"),
        },
        rate_limiter=TokenBucket(rate_per_minute=6000.0),
    )
    results = router.health_check()
    assert len(results) == 1
    result = results[("nvidia", "shared-model")]
    assert set(result.roles) == {PedagogicalRole.SPROUT, PedagogicalRole.COACH}
    assert len(provider.calls) == 1  # probed exactly once despite two roles referencing it


def test_health_check_reports_failure_without_raising() -> None:
    provider = FakeProvider(script=[FakeOutcome.server_error()])
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.SPROUT: ("nvidia:model-a", "authored_fallback")},
        rate_limiter=TokenBucket(rate_per_minute=6000.0),
    )
    results = router.health_check(roles=[PedagogicalRole.SPROUT])
    result = results[("nvidia", "model-a")]
    assert not result.ok
    assert result.error is not None


def test_health_check_never_falls_through_the_chain() -> None:
    """A health check probes each configured model on its own merits — it
    must not silently retry a role's secondary model when the primary
    fails; that would hide exactly the primary failure it exists to catch."""
    provider = FakeProvider(script=[FakeOutcome.timeout()])
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.SPROUT: ("nvidia:model-a", "authored_fallback")},
        rate_limiter=TokenBucket(rate_per_minute=6000.0),
    )
    results = router.health_check(roles=[PedagogicalRole.SPROUT])
    assert not results[("nvidia", "model-a")].ok
    assert len(provider.calls) == 1  # never tried a secondary model for this entry


def test_health_check_handles_rate_limiter_starvation_without_raising() -> None:
    """P0-1 regression: bucket starvation must be reported as a failed
    health check, never escape as an uncaught RateLimitTimeout."""
    bucket = TokenBucket(rate_per_minute=0.01, capacity=1.0)
    bucket.try_acquire()  # drain the only token
    provider = FakeProvider()
    router = ModelRouter(
        {"nvidia": provider},
        role_policy={PedagogicalRole.SPROUT: ("nvidia:model-a", "authored_fallback")},
        rate_limiter=bucket,
        timeout_s=0.05,
    )
    results = router.health_check(roles=[PedagogicalRole.SPROUT])  # must not raise
    result = results[("nvidia", "model-a")]
    assert not result.ok
    assert result.error is not None
