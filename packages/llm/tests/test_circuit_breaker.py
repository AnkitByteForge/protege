"""Tests for the per-(provider, model_id) circuit breaker (opens after 3
consecutive failures, addendum §2.4/§2.8)."""

from protege.llm.circuit_breaker import CircuitBreaker


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, dt: float) -> None:
        self.now += dt


def test_closed_until_third_consecutive_failure() -> None:
    breaker = CircuitBreaker(failure_threshold=3, cooldown_s=10.0)
    assert not breaker.is_open("nvidia", "m1")
    breaker.record_failure("nvidia", "m1")
    assert not breaker.is_open("nvidia", "m1")
    breaker.record_failure("nvidia", "m1")
    assert not breaker.is_open("nvidia", "m1")
    breaker.record_failure("nvidia", "m1")
    assert breaker.is_open("nvidia", "m1")


def test_success_resets_the_consecutive_failure_counter() -> None:
    breaker = CircuitBreaker(failure_threshold=3, cooldown_s=10.0)
    breaker.record_failure("nvidia", "m1")
    breaker.record_failure("nvidia", "m1")
    breaker.record_success("nvidia", "m1")
    breaker.record_failure("nvidia", "m1")
    breaker.record_failure("nvidia", "m1")
    assert not breaker.is_open("nvidia", "m1")  # only 2 since the reset


def test_reopens_closes_after_cooldown_half_open_trial_succeeds() -> None:
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=3, cooldown_s=10.0, clock=clock)
    for _ in range(3):
        breaker.record_failure("nvidia", "m1")
    assert breaker.is_open("nvidia", "m1")

    clock.advance(11.0)
    assert not breaker.is_open("nvidia", "m1")  # half-open: one trial allowed

    breaker.record_success("nvidia", "m1")
    assert not breaker.is_open("nvidia", "m1")


def test_half_open_trial_failure_reopens_with_fresh_cooldown() -> None:
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=3, cooldown_s=10.0, clock=clock)
    for _ in range(3):
        breaker.record_failure("nvidia", "m1")
    clock.advance(11.0)
    assert not breaker.is_open("nvidia", "m1")

    breaker.record_failure("nvidia", "m1")  # the trial call also failed
    assert breaker.is_open("nvidia", "m1")


def test_keys_are_independent_per_provider_and_model() -> None:
    breaker = CircuitBreaker(failure_threshold=3, cooldown_s=10.0)
    for _ in range(3):
        breaker.record_failure("nvidia", "m1")
    assert breaker.is_open("nvidia", "m1")
    assert not breaker.is_open("nvidia", "m2")
    assert not breaker.is_open("other", "m1")
