"""Tests for protege.learning_engine.evidence_builder.

Covers the evidence weighting rules (default / hint-discount / 3x
verification), the response/teaching-episode/transfer evidence shapers,
and the field mapping to protege.contracts.Evidence documented in the
module.
"""

from protege.learning_engine.constants import (
    DEFAULT_EVIDENCE_WEIGHT,
    HINT_DISCOUNT_WEIGHT,
    VERIFICATION_EVIDENCE_WEIGHT,
)
from protege.learning_engine.evidence_builder import (
    ResponseObservation,
    TeachingEpisodeObservation,
    TransferObservationInput,
    build_response_evidence,
    build_teaching_episode_evidence,
    build_transfer_evidence,
    evidence_weight,
)

# --- evidence_weight ---------------------------------------------------


def test_evidence_weight_default_for_unaided_practice_no_hints() -> None:
    assert evidence_weight(unaided=False, hints_used=0) == DEFAULT_EVIDENCE_WEIGHT


def test_evidence_weight_default_below_hint_threshold() -> None:
    assert evidence_weight(unaided=False, hints_used=1) == DEFAULT_EVIDENCE_WEIGHT


def test_evidence_weight_discounted_at_hint_threshold() -> None:
    assert evidence_weight(unaided=False, hints_used=2) == HINT_DISCOUNT_WEIGHT


def test_evidence_weight_discounted_above_hint_threshold() -> None:
    assert evidence_weight(unaided=False, hints_used=5) == HINT_DISCOUNT_WEIGHT


def test_evidence_weight_unaided_always_wins_verification_weight() -> None:
    assert evidence_weight(unaided=True, hints_used=0) == VERIFICATION_EVIDENCE_WEIGHT
    # Even if hints_used were (incorrectly) nonzero on an unaided
    # response, unaided still takes priority -- see evidence_weight's
    # docstring on why this ordering is explicit.
    assert evidence_weight(unaided=True, hints_used=3) == VERIFICATION_EVIDENCE_WEIGHT


# --- build_response_evidence --------------------------------------------


def test_build_response_evidence_maps_fields_to_evidence_shape() -> None:
    observation = ResponseObservation(
        item_id="i_0148",
        source_event_id="evt_1",
        correct=True,
        unaided=True,
        hints_used=0,
        latency_s=6.9,
    )
    built = build_response_evidence(observation)
    assert built.kind == "response"
    assert built.source_event_id == "evt_1"
    assert built.weight == VERIFICATION_EVIDENCE_WEIGHT
    assert built.payload == {
        "item": "i_0148",
        "correct": True,
        "unaided": True,
        "hints_used": 0,
        "latency": 6.9,
    }


def test_build_response_evidence_omits_latency_when_absent() -> None:
    observation = ResponseObservation(
        item_id="i_1", source_event_id="evt_2", correct=False, unaided=False, hints_used=0
    )
    built = build_response_evidence(observation)
    assert "latency" not in built.payload


def test_build_response_evidence_hint_discounted_practice_item() -> None:
    observation = ResponseObservation(
        item_id="i_2", source_event_id="evt_3", correct=True, unaided=False, hints_used=2
    )
    built = build_response_evidence(observation)
    assert built.weight == HINT_DISCOUNT_WEIGHT


def test_build_response_evidence_default_weight_practice_item() -> None:
    observation = ResponseObservation(
        item_id="i_3", source_event_id="evt_4", correct=True, unaided=False, hints_used=0
    )
    built = build_response_evidence(observation)
    assert built.weight == DEFAULT_EVIDENCE_WEIGHT


# --- build_teaching_episode_evidence -------------------------------------


def test_build_teaching_episode_evidence_resolved() -> None:
    observation = TeachingEpisodeObservation(
        episode_id="te_77", source_event_id="evt_5", resolved=True, resolution_turn=4
    )
    built = build_teaching_episode_evidence(observation)
    assert built.kind == "teaching_episode"
    assert built.weight == DEFAULT_EVIDENCE_WEIGHT
    assert built.payload == {"episode_id": "te_77", "resolved": True, "resolution_turn": 4}


def test_build_teaching_episode_evidence_unresolved_omits_resolution_turn() -> None:
    observation = TeachingEpisodeObservation(
        episode_id="te_78", source_event_id="evt_6", resolved=False
    )
    built = build_teaching_episode_evidence(observation)
    assert "resolution_turn" not in built.payload
    assert built.payload["resolved"] is False


# --- build_transfer_evidence ----------------------------------------------


def test_build_transfer_evidence_weighted_at_verification_weight() -> None:
    observation = TransferObservationInput(
        item_id="i_0201", source_event_id="evt_7", representation="number_line", result=True
    )
    built = build_transfer_evidence(observation)
    assert built.kind == "transfer"
    assert built.weight == VERIFICATION_EVIDENCE_WEIGHT
    assert built.payload == {"item": "i_0201", "result": True, "representation": "number_line"}


def test_build_transfer_evidence_no_representation() -> None:
    observation = TransferObservationInput(
        item_id="i_0202", source_event_id="evt_8", representation=None, result=False
    )
    built = build_transfer_evidence(observation)
    assert "representation" not in built.payload
    assert built.payload["result"] is False


def test_build_transfer_evidence_unattempted_result_none() -> None:
    # An attempted-but-not-yet-scored transfer probe: result is None.
    observation = TransferObservationInput(
        item_id="i_0203", source_event_id="evt_9", representation=None, result=None
    )
    built = build_transfer_evidence(observation)
    assert built.payload["result"] is None


# --- determinism -----------------------------------------------------------


def test_build_response_evidence_deterministic_replay() -> None:
    observation = ResponseObservation(
        item_id="i_9", source_event_id="evt_x", correct=True, unaided=True
    )
    assert build_response_evidence(observation) == build_response_evidence(observation)
