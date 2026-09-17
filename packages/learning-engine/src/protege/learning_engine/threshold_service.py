"""Mastery threshold decision (``PROTEGE_ARCHITECTURE.md`` §17 provenance
chain ``th_02``; roadmap P2: "P(L) >= 0.85 AND >= 3 unaided correct AND
>= 1 transfer attempted").

Pure: no database, API, or filesystem access (task instruction).

``transfer_attempted_count`` is a caller-supplied count. Per the already-
recorded architectural decision (docs/DECISIONS.md D8;
``packages/contracts/src/protege/contracts/worked_example.py``
``VerificationRecord``), "transfer attempted" is derived from
``verification.transfer_item is not None`` -- this package does not
invent a redundant ``MasteryEstimate`` transfer-attempt field, and this
module does not recompute that derivation itself (it has no
``packages/contracts`` dependency to derive it from); the caller performs
that one-line derivation and passes the resulting count in.

``transfer_verified`` (whether the attempted transfer *passed*) is
deliberately absent from this module's threshold logic --
``PROTEGE_ARCHITECTURE.md`` §1.3 correction 3 keeps the transfer *claim*
separate from the mastery decision ("Transfer failure must not erase
mastery. It downgrades the CLAIM."); the roadmap P2 threshold rule only
requires a transfer to have been *attempted*, not that it passed.
"""

from dataclasses import dataclass

from .constants import (
    MASTERY_MIN_TRANSFER_ATTEMPTS,
    MASTERY_MIN_UNAIDED_CORRECT,
    MASTERY_P_KNOWN_THRESHOLD,
)
from .probability import validate_probability


@dataclass(frozen=True)
class ThresholdInputs:
    """Inputs to the mastery threshold decision."""

    p_known: float
    unaided_correct_count: int
    transfer_attempted_count: int


@dataclass(frozen=True)
class ThresholdDecision:
    """The threshold outcome, with each sub-condition broken out so a
    caller (or a test) can see exactly which condition(s) are unmet."""

    mastery_verified: bool
    p_known_met: bool
    unaided_correct_met: bool
    transfer_attempted_met: bool


def evaluate_mastery_threshold(inputs: ThresholdInputs) -> ThresholdDecision:
    """``mastery_verified`` iff all three roadmap P2 conditions hold:
    ``p_known >= 0.85 AND unaided_correct_count >= 3 AND
    transfer_attempted_count >= 1``."""
    validate_probability("p_known", inputs.p_known)
    if inputs.unaided_correct_count < 0:
        raise ValueError(
            f"unaided_correct_count must be non-negative, got {inputs.unaided_correct_count}"
        )
    if inputs.transfer_attempted_count < 0:
        raise ValueError(
            f"transfer_attempted_count must be non-negative, got {inputs.transfer_attempted_count}"
        )

    p_known_met = inputs.p_known >= MASTERY_P_KNOWN_THRESHOLD
    unaided_correct_met = inputs.unaided_correct_count >= MASTERY_MIN_UNAIDED_CORRECT
    transfer_attempted_met = inputs.transfer_attempted_count >= MASTERY_MIN_TRANSFER_ATTEMPTS

    return ThresholdDecision(
        mastery_verified=p_known_met and unaided_correct_met and transfer_attempted_met,
        p_known_met=p_known_met,
        unaided_correct_met=unaided_correct_met,
        transfer_attempted_met=transfer_attempted_met,
    )
