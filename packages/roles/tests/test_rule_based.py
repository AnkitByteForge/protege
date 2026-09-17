from __future__ import annotations

from collections.abc import Sequence

import pytest

from protege.contracts import Distractor, Misconception
from protege.roles.errors import DistractorNotInClosedSetError, NoClosedSetProvidedError
from protege.roles.rule_based import RULE_BASED_CONFIDENCE, rule_based_diagnosis


def test_rule_based_diagnosis_maps_distractor_to_misconception(
    misconception_set: Sequence[Misconception],
) -> None:
    # 0.82 (Distractor.likelihood) is deliberately NOT the expected
    # confidence -- see rule_based.py's module docstring for why reusing it
    # would conflate two different authored quantities.
    distractor = Distractor(value="1/8", maps_to="M003", likelihood=0.82)
    result = rule_based_diagnosis(
        misconception_set=misconception_set,
        selected_distractor=distractor,
        source_text="1/8 is bigger",
    )
    assert result.abstained is False
    assert len(result.labels) == 1
    label = result.labels[0]
    assert label.misconception_code == "M003"
    assert label.state == "unresolved"
    assert label.evidence_span == "1/8"
    assert label.confidence == RULE_BASED_CONFIDENCE


def test_rule_based_diagnosis_drops_unverifiable_evidence_span(
    misconception_set: Sequence[Misconception],
) -> None:
    distractor = Distractor(value="1/8", maps_to="M003", likelihood=0.82)
    result = rule_based_diagnosis(
        misconception_set=misconception_set,
        selected_distractor=distractor,
        source_text="totally different text",
    )
    assert result.labels[0].evidence_span is None


def test_rule_based_diagnosis_abstains_with_no_distractor(
    misconception_set: Sequence[Misconception],
) -> None:
    result = rule_based_diagnosis(misconception_set=misconception_set, selected_distractor=None)
    assert result.abstained is True
    assert result.labels == []
    assert result.asr_reliable is True


def test_rule_based_diagnosis_raises_on_empty_closed_set() -> None:
    with pytest.raises(NoClosedSetProvidedError):
        rule_based_diagnosis(misconception_set=[], selected_distractor=None)


def test_rule_based_diagnosis_raises_when_distractor_maps_outside_closed_set(
    misconception_set: Sequence[Misconception],
) -> None:
    closed_set_without_m003 = [m for m in misconception_set if m.code != "M003"]
    distractor = Distractor(value="1/8", maps_to="M003", likelihood=0.82)
    with pytest.raises(DistractorNotInClosedSetError):
        rule_based_diagnosis(
            misconception_set=closed_set_without_m003, selected_distractor=distractor
        )


def test_rule_based_diagnosis_is_deterministic(misconception_set: Sequence[Misconception]) -> None:
    distractor = Distractor(value="1/8", maps_to="M003", likelihood=0.82)
    first = rule_based_diagnosis(
        misconception_set=misconception_set,
        selected_distractor=distractor,
        source_text="1/8 is bigger",
    )
    second = rule_based_diagnosis(
        misconception_set=misconception_set,
        selected_distractor=distractor,
        source_text="1/8 is bigger",
    )
    assert first == second
