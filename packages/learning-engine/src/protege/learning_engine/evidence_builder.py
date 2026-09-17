"""Deterministic evidence construction (``PROTEGE_ARCHITECTURE.md`` §10.1
rules 2, 4; §22 ``evidence`` table; roadmap P2 ``evidence_builder``).

Builds a plain, P2-internal :class:`BuiltEvidence` record shaped
field-for-field to match ``protege.contracts.Evidence``
(``learning_state.py``) -- this package does not depend on
``packages/contracts`` or Pydantic (docs/DECISIONS.md D6, D8; task
instruction: "Do not couple to FastAPI/Pydantic unless a P2 requirement
explicitly needs them"), so the caller (P9) is expected to construct the
real ``Evidence`` object from this output. Field mapping:

=====================  ==============================================
``BuiltEvidence``       ``protege.contracts.Evidence``
=====================  ==============================================
``kind``                ``kind`` (an ``EvidenceKind`` value: this module
                        emits the literal strings ``"response"``,
                        ``"teaching_episode"``, ``"transfer"``, which are
                        exactly the ``EvidenceKind`` enum's wire values)
``source_event_id``    ``source_event_id``
``weight``              ``weight``
``payload``             ``payload``
=====================  ==============================================

``evidence_id`` and ``created_at`` are not produced here -- those are
assigned at persistence time (P9), not by a pure evidence-shaping
function.

:class:`ResponseObservation`, :class:`TeachingEpisodeObservation`, and
:class:`TransferObservationInput` are the internal P2 input types
recorded in docs/DECISIONS.md D8: they are **not** new
``packages/contracts`` models, and stay internal to this package until P9
defines the canonical persisted ``Response`` contract.
"""

from dataclasses import dataclass, field

from .constants import (
    DEFAULT_EVIDENCE_WEIGHT,
    HINT_DISCOUNT_THRESHOLD,
    HINT_DISCOUNT_WEIGHT,
    VERIFICATION_EVIDENCE_WEIGHT,
)


@dataclass(frozen=True)
class ResponseObservation:
    """Internal P2 input type (docs/DECISIONS.md D8): one scored
    response, as much as ``evidence_weight``/``build_response_evidence``
    need -- not a persisted or exported contract."""

    item_id: str
    source_event_id: str
    correct: bool
    unaided: bool = False
    hints_used: int = 0
    latency_s: float | None = None


@dataclass(frozen=True)
class TeachingEpisodeObservation:
    """Internal P2 input type for a teach-back evidence record."""

    episode_id: str
    source_event_id: str
    resolved: bool
    resolution_turn: int | None = None


@dataclass(frozen=True)
class TransferObservationInput:
    """Internal P2 input type for a transfer evidence record. Distinct
    from ``protege.contracts.TransferObservation`` (a P1 contract this
    package does not import, per D6/D8) but shaped the same way."""

    item_id: str
    source_event_id: str
    representation: str | None
    result: bool | None


@dataclass(frozen=True)
class BuiltEvidence:
    """Field-for-field shaped to match ``protege.contracts.Evidence``
    (see module docstring)."""

    kind: str
    source_event_id: str
    weight: float
    payload: dict[str, object] = field(default_factory=dict)


def evidence_weight(*, unaided: bool, hints_used: int) -> float:
    """§10.1 rules 2 and 4: the hint-discounted weight for a practice
    response, or the 3x verification weight for an unaided response.

    Checks ``unaided`` first: an unaided (verification) response is by
    definition hint-free in this system (``INDEPENDENT_VERIFY`` forbids
    hints, ``PROTEGE_ARCHITECTURE.md`` §9), so the two rules never
    actually compete in practice, but this ordering makes that priority
    explicit rather than relying on callers never passing hints on an
    unaided response.
    """
    if unaided:
        return VERIFICATION_EVIDENCE_WEIGHT
    if hints_used >= HINT_DISCOUNT_THRESHOLD:
        return HINT_DISCOUNT_WEIGHT
    return DEFAULT_EVIDENCE_WEIGHT


def build_response_evidence(observation: ResponseObservation) -> BuiltEvidence:
    """Build a ``"response"``-kind evidence record from one scored
    response (§22 ``evidence`` table; matches the payload shape already
    used in ``packages/contracts/tests/builders.py``'s
    ``build_evidence()``: ``item``, ``correct``, ``unaided``, and
    optionally ``latency``)."""
    weight = evidence_weight(unaided=observation.unaided, hints_used=observation.hints_used)
    payload: dict[str, object] = {
        "item": observation.item_id,
        "correct": observation.correct,
        "unaided": observation.unaided,
        "hints_used": observation.hints_used,
    }
    if observation.latency_s is not None:
        payload["latency"] = observation.latency_s
    return BuiltEvidence(
        kind="response",
        source_event_id=observation.source_event_id,
        weight=weight,
        payload=payload,
    )


def build_teaching_episode_evidence(observation: TeachingEpisodeObservation) -> BuiltEvidence:
    """Build a ``"teaching_episode"``-kind evidence record from one
    teach-back episode (§22 ``teaching_episodes``). Weighted at the
    default weight -- teach-back resolution is not itself an unaided
    verification item, so the 3x rule does not apply here."""
    payload: dict[str, object] = {
        "episode_id": observation.episode_id,
        "resolved": observation.resolved,
    }
    if observation.resolution_turn is not None:
        payload["resolution_turn"] = observation.resolution_turn
    return BuiltEvidence(
        kind="teaching_episode",
        source_event_id=observation.source_event_id,
        weight=DEFAULT_EVIDENCE_WEIGHT,
        payload=payload,
    )


def build_transfer_evidence(observation: TransferObservationInput) -> BuiltEvidence:
    """Build a ``"transfer"``-kind evidence record from one transfer
    probe (§22; §9 ``TRANSFER`` state). Weighted at the same 3x
    verification weight as an unaided response: transfer items are, per
    the ``TRANSFER`` session state, unaided and unseen (novel
    representation, no hints) -- the same justification §10.1 rule 4
    gives for verification items."""
    payload: dict[str, object] = {"item": observation.item_id, "result": observation.result}
    if observation.representation is not None:
        payload["representation"] = observation.representation
    return BuiltEvidence(
        kind="transfer",
        source_event_id=observation.source_event_id,
        weight=VERIFICATION_EVIDENCE_WEIGHT,
        payload=payload,
    )
