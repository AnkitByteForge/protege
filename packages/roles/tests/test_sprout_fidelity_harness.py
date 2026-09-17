"""Fast, free (FakeProvider) tests proving the P5 evaluation-harness logic
in ``_eval_harness.py`` is correct -- run by default, unlike
``test_sprout_fidelity_nvidia.py`` (gated, real network).

Covers the five things the harness redesign was specifically required to
prove (see the conversation/instruction that produced this file):

1. Fidelity includes validator-REJECTED real model generations, not just
   accepted ones (the original selection-bias defect).
2. A circuit-breaker simulation proving the evaluator WAITS instead of
   burning evaluation samples while every real chain entry is open.
3. Resume/checkpoint behavior: a completed misconception is never re-run.
4. Fallback outputs never contribute to model-fidelity scoring.
5. Answer leakage remains zero-tolerance on every FINAL emitted turn, even
   while individual rejected attempts are still scored for fidelity.
"""

from __future__ import annotations

from _eval_harness import (
    AttemptOutcomeKind,
    evaluate_misconception,
    load_checkpoint,
    real_chain_pairs,
    wait_for_breaker_clear,
)
from conftest import make_router, sprout_turn_json

from protege.authoring.loader import ContentPack
from protege.llm.circuit_breaker import CircuitBreaker
from protege.llm.providers.fake import FakeOutcome, FakeProvider
from protege.llm.telemetry import InMemoryTelemetrySink
from protege.roles.sprout import SproutGenerator

_CODE = "M003"


def _evaluator(
    provider: FakeProvider, content_pack: ContentPack, *, breaker: CircuitBreaker | None = None
) -> tuple[SproutGenerator, CircuitBreaker, InMemoryTelemetrySink]:
    breaker = breaker if breaker is not None else CircuitBreaker()
    telemetry = InMemoryTelemetrySink()
    router = make_router(provider, circuit_breaker=breaker, telemetry=telemetry)
    return SproutGenerator(router, content=content_pack), breaker, telemetry


# --- 1. Fidelity includes validator-rejected generations --------------------


def test_fidelity_includes_validator_rejected_real_generations(content_pack: ContentPack) -> None:
    # Both attempts name the WRONG misconception -- a real, parseable,
    # schema-valid output that the validator correctly rejects.
    wrong_misconception = sprout_turn_json(
        utterance="Three and four, two separate numbers, easy!", exhibits="M001"
    )
    provider = FakeProvider(
        script=[FakeOutcome.ok(wrong_misconception), FakeOutcome.ok(wrong_misconception)]
    )
    generator, breaker, telemetry = _evaluator(provider, content_pack)

    report = evaluate_misconception(
        generator, content_pack, _CODE, n_generations=1, breaker=breaker, telemetry=telemetry
    )

    assert report.fallback_count == 1  # both attempts rejected -> fell back
    assert report.real_model_attempts == 2
    # Both real, parseable, rejected attempts still contribute a score.
    assert report.real_model_outputs_scored == 2
    assert report.validator_rejections == 2
    assert report.reason_counts.get(AttemptOutcomeKind.MISCONCEPTION_CONSISTENCY_FAILURE) == 2
    assert len(report.fidelities) == 2
    # A misconception-mismatch drops the 0.4-weighted "exhibits_target"
    # component to 0 -- the score must reflect that, not silently vanish
    # nor equal the authored fallback's own (guaranteed ~1.0) score.
    assert report.mean_fidelity is not None
    assert report.mean_fidelity < 0.90
    assert all(f < 1.0 for f in report.fidelities)


def test_schema_failure_scores_zero_and_is_not_excluded(content_pack: ContentPack) -> None:
    """Explicit lowest-score treatment for genuinely invalid structured
    output (task instruction A) -- it must appear IN the denominator at
    0.0, never silently disappear from it."""
    provider = FakeProvider(
        script=[
            FakeOutcome.malformed(),
            FakeOutcome.malformed(),
            FakeOutcome.malformed(),
            FakeOutcome.malformed(),
        ]
    )
    generator, breaker, telemetry = _evaluator(provider, content_pack)

    report = evaluate_misconception(
        generator, content_pack, _CODE, n_generations=1, breaker=breaker, telemetry=telemetry
    )

    assert report.fallback_count == 1
    assert report.reason_counts.get(AttemptOutcomeKind.SCHEMA_FAILURE) == 1
    assert report.real_model_outputs_scored == 1
    assert report.fidelities == [0.0]


def test_network_timeout_is_excluded_from_the_fidelity_denominator(
    content_pack: ContentPack,
) -> None:
    """A pure transport failure produced no output at all -- scoring it
    would fabricate a fidelity judgement about content that never
    existed. It must still count as a real attempt, just not a scored
    one."""
    provider = FakeProvider(
        script=[
            FakeOutcome.timeout(),
            FakeOutcome.timeout(),
            FakeOutcome.timeout(),
            FakeOutcome.timeout(),
        ]
    )
    generator, breaker, telemetry = _evaluator(provider, content_pack)

    report = evaluate_misconception(
        generator, content_pack, _CODE, n_generations=1, breaker=breaker, telemetry=telemetry
    )

    assert report.real_model_attempts == 1
    assert report.reason_counts.get(AttemptOutcomeKind.NETWORK_TIMEOUT) == 1
    assert report.real_model_outputs_scored == 0
    assert report.fidelities == []
    assert report.mean_fidelity is None


# --- 2. Circuit-breaker: wait, never burn samples ---------------------------


def test_wait_for_breaker_clear_blocks_until_a_real_entry_closes() -> None:
    # The SAME fake clock drives both the breaker's own cooldown timing and
    # the wait loop's pacing, so the test is fully deterministic: no real
    # sleeping, and the breaker's is_open() transition is genuinely
    # exercised (not merely assumed) once enough fake time has "passed".
    fake_now = [0.0]
    slept: list[float] = []

    def clock() -> float:
        return fake_now[0]

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        fake_now[0] += seconds

    breaker = CircuitBreaker(failure_threshold=1, cooldown_s=5.0, clock=clock)
    breaker.record_failure("nvidia", "model-a")
    breaker.record_failure("nvidia", "model-b")
    assert breaker.is_open("nvidia", "model-a")
    assert breaker.is_open("nvidia", "model-b")

    waited = wait_for_breaker_clear(
        breaker,
        [("nvidia", "model-a"), ("nvidia", "model-b")],
        max_wait_s=10.0,
        poll_interval_s=1.0,
        sleep=sleep,
        clock=clock,
    )

    assert waited is True
    assert slept  # it actually paused rather than returning instantly
    # The shared fake clock has now advanced past the 5s cooldown, so the
    # breaker's own is_open() logic has genuinely transitioned to closed.
    assert not breaker.is_open("nvidia", "model-a")
    assert not breaker.is_open("nvidia", "model-b")


def test_evaluator_waits_instead_of_burning_samples_when_breaker_opens(
    content_pack: ContentPack,
) -> None:
    """Integration-level reproduction of the exact bug the real run hit:
    once every real chain entry is breaker-open, the evaluator must NOT
    silently consume the remaining generation budget via instant,
    network-free fallbacks -- it must detect the condition and wait."""
    breaker = CircuitBreaker(failure_threshold=3, cooldown_s=0.2)
    good = sprout_turn_json(
        utterance="I think 1/8 is bigger! Eight is way more than four.", exhibits="M003"
    )
    # 3 rounds of "both configured models time out" (6 real attempts) opens
    # both breakers; the 4th generation's attempt succeeds once the
    # evaluator has waited past the (short, test-only) 0.2s cooldown.
    script = [FakeOutcome.timeout() for _ in range(6)] + [FakeOutcome.ok(good)]
    provider = FakeProvider(script=script)
    generator, breaker, telemetry = _evaluator(provider, content_pack, breaker=breaker)

    report = evaluate_misconception(
        generator,
        content_pack,
        _CODE,
        n_generations=4,
        breaker=breaker,
        telemetry=telemetry,
        breaker_max_wait_s=2.0,
        breaker_poll_interval_s=0.02,
    )

    assert report.circuit_open_wait_events >= 1
    # The 4th generation reached a real, successful attempt after waiting
    # -- proving the run did not just instantly exhaust the sample budget.
    assert report.reason_counts.get(AttemptOutcomeKind.ACCEPTED) == 1
    assert report.fallback_count == 3  # generations 1-3 (before the wait) fell back
    assert provider.calls  # real network calls were actually made, not skipped throughout


def test_real_chain_pairs_matches_role_policy_sprout_entries() -> None:
    pairs = real_chain_pairs()
    assert pairs  # at least one real provider-qualified entry
    assert all(provider == "nvidia" for provider, _ in pairs)


# --- 3. Resume / checkpoint behavior -----------------------------------------


def test_resumed_evaluation_makes_zero_new_calls(content_pack: ContentPack, tmp_path) -> None:  # type: ignore[no-untyped-def]
    good = sprout_turn_json(
        utterance="I think 1/8 is bigger! Eight is way more than four.", exhibits="M003"
    )
    provider = FakeProvider(script=[FakeOutcome.ok(good) for _ in range(3)])
    generator, breaker, telemetry = _evaluator(provider, content_pack)

    first = evaluate_misconception(
        generator,
        content_pack,
        _CODE,
        n_generations=3,
        breaker=breaker,
        telemetry=telemetry,
        checkpoint_dir=tmp_path,
    )
    assert load_checkpoint(tmp_path, _CODE) is not None
    assert first.generate_turn_calls == 3

    # A second provider that would fail loudly if ever called.
    class _ExplodingProvider:
        name = "nvidia"
        base_url = ""

        def complete(self, *args: object, **kwargs: object) -> object:
            raise AssertionError("resumed evaluation must not make new calls")

    exploding = _ExplodingProvider()
    router2 = make_router(exploding)  # type: ignore[arg-type]
    generator2 = SproutGenerator(router2, content=content_pack)
    breaker2 = CircuitBreaker()
    telemetry2 = InMemoryTelemetrySink()

    second = evaluate_misconception(
        generator2,
        content_pack,
        _CODE,
        n_generations=3,
        breaker=breaker2,
        telemetry=telemetry2,
        checkpoint_dir=tmp_path,
    )

    assert second.generate_turn_calls == first.generate_turn_calls
    assert second.as_dict() == first.as_dict()


def test_force_reruns_even_with_an_existing_checkpoint(content_pack: ContentPack, tmp_path) -> None:  # type: ignore[no-untyped-def]
    good = sprout_turn_json(
        utterance="I think 1/8 is bigger! Eight is way more than four.", exhibits="M003"
    )
    provider = FakeProvider(script=[FakeOutcome.ok(good)])
    generator, breaker, telemetry = _evaluator(provider, content_pack)
    evaluate_misconception(
        generator,
        content_pack,
        _CODE,
        n_generations=1,
        breaker=breaker,
        telemetry=telemetry,
        checkpoint_dir=tmp_path,
    )

    provider2 = FakeProvider(script=[FakeOutcome.ok(good)])
    generator2, breaker2, telemetry2 = _evaluator(provider2, content_pack)
    evaluate_misconception(
        generator2,
        content_pack,
        _CODE,
        n_generations=1,
        breaker=breaker2,
        telemetry=telemetry2,
        checkpoint_dir=tmp_path,
        force=True,
    )

    assert provider2.calls  # the forced re-run made real (fake) calls


# --- 4. Fallback outputs never count as model fidelity ----------------------


def test_fallback_utterance_never_substitutes_into_model_fidelity(
    content_pack: ContentPack,
) -> None:
    leaking = sprout_turn_json(utterance="I think 1/4 is bigger, it just is!", exhibits="M003")
    provider = FakeProvider(script=[FakeOutcome.ok(leaking), FakeOutcome.ok(leaking)])
    generator, breaker, telemetry = _evaluator(provider, content_pack)

    report = evaluate_misconception(
        generator, content_pack, _CODE, n_generations=1, breaker=breaker, telemetry=telemetry
    )

    assert report.fallback_count == 1
    # The authored fallback line is high-fidelity (~1.0) by construction --
    # if the harness were scoring the EMITTED turn instead of the real
    # rejected attempts, mean_fidelity would read close to 1.0. It must
    # instead reflect the leaking attempts' own (leak-penalized) score.
    assert report.mean_fidelity is not None
    assert report.mean_fidelity < 0.90
    assert AttemptOutcomeKind.ACCEPTED not in report.reason_counts


# --- 5. Answer leakage: zero-tolerance on the emitted turn -------------------


def test_answer_leakage_is_zero_tolerance_on_the_final_emitted_turn(
    content_pack: ContentPack,
) -> None:
    leaking = sprout_turn_json(utterance="1/4 wins, easy.", exhibits="M003")
    provider = FakeProvider(script=[FakeOutcome.ok(leaking), FakeOutcome.ok(leaking)])
    generator, breaker, telemetry = _evaluator(provider, content_pack)

    report = evaluate_misconception(
        generator, content_pack, _CODE, n_generations=1, breaker=breaker, telemetry=telemetry
    )

    # The leaking candidates were both rejected pre-emission -- the FINAL
    # emitted (fallback) turn never leaks.
    assert report.leak_count == 0
    assert report.answer_leak_rate == 0.0
    # But the rejection itself is faithfully recorded as a leak failure.
    assert report.reason_counts.get(AttemptOutcomeKind.ANSWER_LEAKAGE_FAILURE) == 2
