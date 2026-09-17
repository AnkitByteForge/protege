"""Golden-set harness tests (roadmap P6; docs/DECISIONS.md D3, D9).

**None of the numbers asserted here are the roadmap's formal ship-gate
result.** The checked-in golden set is development/provisional, not
independently hand-labelled (``packages/roles/golden_set/PROVENANCE.md``),
and every ``EvalReport``/``NvidiaEvalReport`` carries
``dataset_status="development_not_ratified"`` for exactly that reason --
these tests assert that label is actually present, not just documented.

The rule-based-fallback ablation is measured twice, deliberately:

- on the 64 ``distractor_template`` examples, where the rule-based path has
  the exact evidence type it is designed for -- **this measurement is
  circular** (see ``protege.roles.eval``'s module docstring): the ground
  truth *is* the field the fallback reads, so a perfect score proves only
  that the lookup echoes its own input.
- on the full 120-item set, where the 56 free-text-only examples correctly
  abstain -- this is the honest "what does the LLM buy you" number
  (ARCHITECTURE.md §26).

Neither of these is the roadmap's real ship-gate measurement (macro-F1 on
the golden set *with the actual NVIDIA model*, docs/DECISIONS.md D3) --
that requires a live NVIDIA credential this repository's default test run
never uses (docs/DECISIONS.md D9); see
``packages/roles/tests/test_nvidia_diagnostician_eval.py`` for that, gated
and skipped by default. ``evaluate_with_router`` is exercised here only
against ``FakeProvider``, as an explicitly-labelled plumbing check, never
asserted against a quality threshold.
"""

from __future__ import annotations

from collections.abc import Sequence

from protege.contracts import Misconception
from protege.llm import FakeProvider, ModelRouter
from protege.llm.rate_limit import TokenBucket
from protege.roles.calibration import DEFAULT_CALIBRATION
from protege.roles.eval import (
    evaluate_rule_based_only,
    evaluate_with_router,
    evaluate_with_router_calibrated_held_out,
    run_nvidia_diagnostician_evaluation,
)
from protege.roles.golden_set import DATASET_STATUS, load_golden_set, split_golden_set


def _fake_router(provider: FakeProvider | None = None) -> ModelRouter:
    """A ``FakeProvider``-backed router with the real 35 RPM limiter
    replaced by an effectively unlimited one (matching
    ``packages/llm/tests/test_router.py``'s own convention). The golden set
    is 120 items; the real 35 RPM default would make a single test wait
    several real minutes for no reason -- rate limiting is P4's concern and
    is already covered by ``packages/llm``'s own tests, not this package's.
    """
    return ModelRouter(
        {"nvidia": provider if provider is not None else FakeProvider()},
        rate_limiter=TokenBucket(rate_per_minute=6000.0),
    )


def test_every_report_is_labelled_with_the_dataset_status(
    misconception_set: Sequence[Misconception],
) -> None:
    assert DATASET_STATUS == "development_not_ratified"
    report = evaluate_rule_based_only(load_golden_set(), misconception_set=misconception_set)
    assert report.dataset_status == DATASET_STATUS


def test_rule_based_fallback_is_tautologically_perfect_on_its_own_input(
    misconception_set: Sequence[Misconception],
) -> None:
    """Not a quality claim -- see this module's docstring. Asserting the
    exact-1.0 result here pins the tautology down as an explicit,
    documented invariant so it can never be mistaken for a real macro-F1
    (e.g. quoted as "F1=1.0" without the circularity caveat).
    """
    examples = [e for e in load_golden_set() if e.source == "distractor_template"]
    assert len(examples) == 64

    report = evaluate_rule_based_only(examples, misconception_set=misconception_set)

    assert report.abstention_rate == 0.0  # every one of these has a distractor
    assert report.macro_f1 == 1.0  # circular: ground truth IS Distractor.maps_to
    assert report.ece == 0.0
    assert report.brier == 0.0


def test_rule_based_fallback_alone_abstains_on_free_text_evidence(
    misconception_set: Sequence[Misconception],
) -> None:
    examples = [e for e in load_golden_set() if e.source != "distractor_template"]
    assert len(examples) == 56

    report = evaluate_rule_based_only(examples, misconception_set=misconception_set)

    # No distractor to map -> the rule-based path abstains on every one of
    # these, by design (it has no free-text signal at all). This is
    # exactly the "what is the LLM buying you" measurement, not a bug.
    assert report.abstention_rate == 1.0
    assert report.macro_f1 == 0.0


def test_rule_based_fallback_full_set_ablation_is_reported(
    misconception_set: Sequence[Misconception],
) -> None:
    examples = load_golden_set()
    report = evaluate_rule_based_only(examples, misconception_set=misconception_set)
    assert report.n == 120
    assert report.abstention_rate == 56 / 120
    # Well below 0.75 on the combined set -- expected: this is the
    # (circular-on-a-subset, but still real on the free-text majority)
    # ceiling of a distractor-only lookup with no free-text signal.
    assert report.macro_f1 < 0.75


def test_evaluate_with_router_is_a_wiring_check_only(
    misconception_set: Sequence[Misconception],
) -> None:
    # FakeProvider returns one static canned response for every call, so
    # this is NOT a quality measurement -- it only proves the harness's
    # diagnose()-through-ModelRouter wiring runs end to end without error
    # over all 120 examples, including the abstaining voice/low-ASR paths
    # if any existed in the set (there are none here; text-only golden set).
    router = _fake_router()
    examples = load_golden_set()
    report = evaluate_with_router(examples, router, misconception_set=misconception_set)
    assert report.n == 120
    assert 0.0 <= report.macro_f1 <= 1.0
    assert 0.0 <= report.ece <= 1.0
    assert 0.0 <= report.brier <= 1.0


# --- split_golden_set / calibration protocol --------------------------------


def test_split_golden_set_is_disjoint_and_covers_everything() -> None:
    examples = load_golden_set()
    calibration, held_out = split_golden_set(examples, calibration_fraction=0.5)
    calibration_ids = {e.id for e in calibration}
    held_out_ids = {e.id for e in held_out}
    assert calibration_ids.isdisjoint(held_out_ids)
    assert calibration_ids | held_out_ids == {e.id for e in examples}
    assert len(calibration) + len(held_out) == len(examples)


def test_split_golden_set_is_stratified_per_misconception() -> None:
    examples = load_golden_set()
    calibration, held_out = split_golden_set(examples, calibration_fraction=0.5)
    for code in {e.misconception_code for e in examples}:
        cal_count = sum(1 for e in calibration if e.misconception_code == code)
        held_count = sum(1 for e in held_out if e.misconception_code == code)
        assert cal_count == 7 or cal_count == 8  # 15 examples/code, 50/50 split
        assert cal_count + held_count == 15


def test_split_golden_set_is_deterministic() -> None:
    examples = load_golden_set()
    first = split_golden_set(examples)
    second = split_golden_set(examples)
    assert first == second


def test_evaluate_with_router_calibrated_held_out_never_fits_and_scores_the_same_cases(
    misconception_set: Sequence[Misconception],
) -> None:
    router = _fake_router()
    examples = load_golden_set()
    result = evaluate_with_router_calibrated_held_out(
        examples, router, misconception_set=misconception_set
    )
    calibration_ids = {e.id for e in split_golden_set(examples)[0]}
    held_out_record_ids = {r.example_id for r in result.held_out_report.records}
    assert held_out_record_ids.isdisjoint(calibration_ids)
    assert result.calibration_split_n + result.held_out_split_n == 120
    assert result.held_out_report.n == result.held_out_split_n
    # Same held-out cases, calibrated vs raw -- only confidence may differ.
    assert result.held_out_report.macro_f1 == result.held_out_report_uncalibrated.macro_f1


def test_evaluate_with_router_calibrated_held_out_uses_identity_when_underdetermined(
    misconception_set: Sequence[Misconception],
) -> None:
    # FakeProvider's confidence is constant (0.62) for every example, so the
    # calibration-fit input is zero-variance -> fit_calibration must fall
    # back to the identity transform, never fabricate a fit.
    router = _fake_router()
    examples = load_golden_set()
    result = evaluate_with_router_calibrated_held_out(
        examples, router, misconception_set=misconception_set
    )
    assert result.fitted_calibration == DEFAULT_CALIBRATION


# --- run_nvidia_diagnostician_evaluation (plumbing only; see the gated,
# manually-invoked real-network test for the actual NVIDIA measurement) -----


def test_run_nvidia_diagnostician_evaluation_classifies_fake_provider_as_primary(
    misconception_set: Sequence[Misconception],
) -> None:
    # FakeProvider always succeeds on the FIRST chain entry it is asked for
    # (DIAGNOSTICIAN's primary model_id), so every example must resolve to
    # "primary" -- if this ever showed secondary/rule-based fallback counts
    # against FakeProvider, the telemetry-classification logic itself would
    # be broken (this is the regression the real-network test alone can't
    # catch, since a real run's fallback counts are legitimately unknown in
    # advance).
    router = _fake_router()
    examples = load_golden_set()
    report = run_nvidia_diagnostician_evaluation(
        examples, router, misconception_set=misconception_set
    )
    assert report.n == 120
    assert report.primary_success_count == 120
    assert report.secondary_fallback_count == 0
    assert report.rule_based_fallback_count == 0
    assert report.no_telemetry_count == 0
    assert report.primary_rate == 1.0
    assert report.fallback_rate == 0.0
    assert report.dataset_status == DATASET_STATUS
    assert report.primary_model_id != report.secondary_model_id


def test_run_nvidia_diagnostician_evaluation_records_deterministic_fallback(
    misconception_set: Sequence[Misconception],
) -> None:
    from protege.llm import FakeOutcome

    # Only distractor_template examples have a distractor for the
    # rule-based path to use; restrict to those so nothing abstains here.
    examples = [e for e in load_golden_set() if e.source == "distractor_template"]

    # Exhaust both real chain entries (2 attempts each) with malformed
    # output so every example falls through to the rule-based sentinel.
    provider = FakeProvider(script=[FakeOutcome.malformed() for _ in range(4 * len(examples))])
    router = _fake_router(provider)
    report = run_nvidia_diagnostician_evaluation(
        examples, router, misconception_set=misconception_set
    )
    assert report.rule_based_fallback_count == len(examples)
    assert report.primary_success_count == 0
    assert report.fallback_rate == 1.0
