"""Golden-set acceptance tests (roadmap P6 exit criteria; docs/DECISIONS.md
D3, D9).

The rule-based-fallback ablation is measured twice, deliberately:

- on the 64 ``distractor_template`` examples, where the rule-based path has
  the exact evidence type it is designed for -- this is where the roadmap's
  macro-F1 >= 0.75 / ECE <= 0.10 / Brier <= 0.18 gates are actually met, by
  a real, deterministic, network-free measurement.
- on the full 120-item set, where the 56 free-text-only examples correctly
  abstain -- this is the honest "what does the LLM buy you" number
  (ARCHITECTURE.md §26), and it is expected, by design, to miss the gates.

Neither of these is the roadmap's real ship-gate measurement (macro-F1 on
the golden set *with the actual NVIDIA model*, docs/DECISIONS.md D3) --
that requires a live NVIDIA credential this repository's default test run
never uses (docs/DECISIONS.md D9). ``evaluate_with_router`` is exercised
here only against ``FakeProvider``, as an explicitly-labelled plumbing
check, never asserted against a quality gate.
"""

from __future__ import annotations

from collections.abc import Sequence

from protege.contracts import Misconception
from protege.llm.providers.fake import FakeProvider
from protege.llm.router import ModelRouter
from protege.roles.eval import evaluate_rule_based_only, evaluate_with_router
from protege.roles.golden_set import load_golden_set


def test_rule_based_fallback_meets_the_p6_gates_on_the_evidence_it_is_designed_for(
    misconception_set: Sequence[Misconception],
) -> None:
    examples = [e for e in load_golden_set() if e.source == "distractor_template"]
    assert len(examples) == 64

    report = evaluate_rule_based_only(examples, misconception_set=misconception_set)

    assert report.abstention_rate == 0.0  # every one of these has a distractor
    assert report.macro_f1 >= 0.75
    assert report.ece <= 0.10
    assert report.brier <= 0.18


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
    # 56/120 abstain -> well below the P6 gate on the combined set; this is
    # the documented, expected gap the LLM path exists to close.
    assert report.abstention_rate == 56 / 120
    assert report.macro_f1 < 0.75


def test_evaluate_with_router_is_a_wiring_check_only(
    misconception_set: Sequence[Misconception],
) -> None:
    # FakeProvider returns one static canned response for every call, so
    # this is NOT a quality measurement -- it only proves the harness's
    # diagnose()-through-ModelRouter wiring runs end to end without error
    # over all 120 examples, including the abstaining voice/low-ASR paths
    # if any existed in the set (there are none here; text-only golden set).
    router = ModelRouter({"nvidia": FakeProvider()})
    examples = load_golden_set()
    report = evaluate_with_router(examples, router, misconception_set=misconception_set)
    assert report.n == 120
    assert 0.0 <= report.macro_f1 <= 1.0
    assert 0.0 <= report.ece <= 1.0
    assert 0.0 <= report.brier <= 1.0
