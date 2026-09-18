"""The 14-dim policy context vector (``PROTEGE_ARCHITECTURE.md`` §11.2,
§11.3; ``packages/contracts/src/protege/contracts/session.py``'s
``PolicyDecisionState``; ``services/session/.../db/models/policy.py``'s
``POLICY_STATE_VECTOR_DIM = 14``).

:class:`PolicyContext` is this package's own pure input record -- the raw,
already-computed signals a caller (the future P10 orchestrator; a test)
supplies for one decision. It deliberately does **not** import P7's
``SessionContext``: P7's dataclass is scoped to exactly what the FSM's own
guards read (roadmap P7: "not the full P2 mastery state ... that state is
P2/content-owned"), and is missing most of what the 14-dim vector needs
(``hint_rate``, ``session_minutes``, ``confidence_mean``,
``calibration_error``, ``prior_teachback_success``,
``time_since_last_review_days``, ``grade_band``) -- none of which P7 tracks
today. Building a second, wider context record here -- rather than bolting
those fields onto P7's ``SessionContext`` -- keeps this package's stated
scope boundary (roadmap P11 §15: no P7 changes) intact; a real orchestrator
wiring reads the overlapping fields (``p_known``, ``streak_incorrect``,
``session_minutes``) off both records identically, and supplies the rest
from wherever P9/P10 track them.

This module does not invent any new *mastery* math -- every probability
field here is a value P2 (or a P2-derived signal like hint rate) already
produces; this module only assembles the fixed-order vector and validates
its domain, exactly as ``threshold_service.py`` does for the mastery
threshold decision.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Final

from protege.contracts import ConfidenceLabel, PolicyDecisionState
from protege.learning_engine.probability import validate_probability

__all__ = [
    "STATE_VECTOR_DIMENSION_NAMES",
    "PolicyContext",
    "build_state_vector",
    "encode_grade_band",
    "mean_confidence",
]

STATE_VECTOR_DIMENSION_NAMES: Final[tuple[str, ...]] = (
    "p_known",
    "max_misconception_belief",
    "n_active_misconceptions",
    "hint_rate",
    "mean_latency_z",
    "streak_correct",
    "streak_incorrect",
    "session_minutes",
    "items_this_skill",
    "confidence_mean",
    "calibration_error",
    "prior_teachback_success",
    "time_since_last_review_days",
    "grade_band",
)
"""Exact order of ``PROTEGE_ARCHITECTURE.md`` §11.2's context vector list,
verified against ``packages/contracts/tests/builders.py``'s
``build_policy_decision_state`` fixture
(``[0.62, 0.71, 1, 0.25, -0.4, 2, 0, 8.2, 6, 0.7, 0.18, 1, 3, 3]``), which
this module's own tests replay index-for-index."""

_GRADE_BAND_PATTERN: Final[re.Pattern[str]] = re.compile(r"^([K0-9]+)-([K0-9]+)$")

_CONFIDENCE_LABEL_VALUE: Final[dict[ConfidenceLabel, float]] = {
    ConfidenceLabel.SURE: 1.0,
    ConfidenceLabel.THINK_SO: 0.5,
    ConfidenceLabel.GUESSING: 0.0,
}
"""**Informational** (docs/DECISIONS.md D11 sense): no PROTÉGÉ document
gives a numeric value for the three child-reported confidence labels
(``PROTEGE_ARCHITECTURE.md`` §10.1), but the §11.2 context vector's
``confidence_mean`` dimension needs one to average over. An evenly spaced
``1.0 / 0.5 / 0.0`` mapping is the least-arbitrary reading of an ordinal
3-point scale; whoever next revisits this dimension should confirm or
replace it before it drives a real decision."""


def _grade_band_bounds(grade_band: str) -> tuple[str, str]:
    match = _GRADE_BAND_PATTERN.fullmatch(grade_band)
    if match is None:
        raise ValueError(
            f"grade_band must match 'LOW-HIGH' (e.g. '3-4', 'K-2'), got {grade_band!r}"
        )
    return match.group(1), match.group(2)


def _grade_token_value(token: str) -> float:
    return 0.0 if token == "K" else float(int(token))


def encode_grade_band(grade_band: str) -> float:
    """Numeric encoding of a ``GradeBand`` string (``protege.contracts.ids.
    GradeBand``, pattern ``^[K0-9]+-[K0-9]+$``) for the vector's 14th
    dimension.

    **Informational**: no canonical document gives a numeric mapping for
    ``grade_band``. This uses the band's *lower* bound (``"K"`` -> 0.0,
    ``"3-4"`` -> 3.0) rather than its mean, matching the literal `3` at
    index 13 of the worked context-vector example
    (``PROTEGE_ARCHITECTURE.md`` §11.3 / ``packages/contracts/tests/
    builders.py``'s ``build_policy_decision_state``) for content whose own
    authored ``grade_band`` is ``"3-4"`` (``tools/authoring/src/protege/
    authoring/seed_fractions_v1.py``). A monotonic, single-scalar ordinal
    feature reads most naturally as "how advanced is this learner's grade
    band, at minimum" rather than a fractional midpoint.
    """
    low, _high = _grade_band_bounds(grade_band)
    return _grade_token_value(low)


def mean_confidence(labels: Sequence[ConfidenceLabel]) -> float:
    """Mean of ``_CONFIDENCE_LABEL_VALUE`` over a sequence of recent
    child-reported confidence labels (``ARCHITECTURE.md`` §10.1). Returns
    ``0.5`` (a neutral, "think so" default) for an empty sequence rather
    than raising -- a session with no confidence signal yet is not an
    error, just uninformative."""
    if not labels:
        return 0.5
    return sum(_CONFIDENCE_LABEL_VALUE[label] for label in labels) / len(labels)


@dataclass(frozen=True)
class PolicyContext:
    """One decision's raw inputs: the 14 context-vector signals, plus the
    handful of extra raw signals the safety shield needs that are *not*
    part of the persisted vector (``struggle_seconds``, ``loop_count``,
    ``distress_signal`` -- see ``shield.py``'s module docstring for why
    those three are shield-only).

    Every field is a value some upstream system already computes (P2's
    ``mastery_effective``/misconception beliefs, P6's diagnosis confidence,
    P7's session clock, P9's persisted history) -- this package never
    derives a probability itself, only assembles and validates them
    (docstring, module level).
    """

    p_known: float
    """P2's ``mastery_effective`` for the active skill (§10.1 rule 1).
    Vector dim 0."""
    max_misconception_belief: float
    """``max_k P(M_k)`` over this skill's currently tracked misconceptions
    (0.0 if none tracked). Vector dim 1."""
    n_active_misconceptions: int
    """Count of misconceptions with ``MisconceptionState.UNRESOLVED``
    currently tracked for this skill. Vector dim 2."""
    hints_requested_this_skill: int
    """Raw ``HINT_REQUESTED`` event count for this skill this session --
    the numerator :func:`hint_rate` divides by ``items_this_skill``."""
    mean_latency_z: float
    """Z-scored mean response latency against this learner's own baseline.
    Vector dim 4. No canonical document specifies the baseline population;
    supplied pre-computed by the caller."""
    streak_correct: int
    """Consecutive correct responses, most recent first. Vector dim 5."""
    streak_incorrect: int
    """Consecutive incorrect responses. Vector dim 6. Also the shield's
    rule-2 input (``shield.py``) -- P11's own signal, not P7's
    ``consecutive_errors`` (see ``constants.py``'s module docstring)."""
    session_minutes: float
    """Elapsed session wall-clock minutes. Vector dim 7. Also the shield's
    rule-6 (hard cap) input."""
    items_this_skill: int
    """Items attempted so far for the active skill this session. Vector
    dim 8."""
    confidence_mean: float
    """Mean child-reported confidence (:func:`mean_confidence`). Vector
    dim 9."""
    calibration_error: float
    """This session's running |confidence - accuracy| gap, in [0, 1].
    Vector dim 10. No canonical per-decision definition exists; supplied
    pre-computed by the caller (e.g. from a running Brier/ECE-style
    estimate, mirroring ``protege.roles.eval.expected_calibration_error``'s
    formula, scoped to this session rather than a golden set)."""
    prior_teachback_success: float
    """Proportion of this learner's past teach-back attempts that resolved
    the targeted misconception, in [0, 1]. Vector dim 11."""
    time_since_last_review_days: float
    """Days since this skill was last reviewed (0.0 if never or if this is
    the first encounter). Vector dim 12."""
    grade_band: str
    """``GradeBand`` string (``protege.contracts.ids.GradeBand``), encoded
    via :func:`encode_grade_band` for vector dim 13."""

    struggle_seconds: float = 0.0
    """Seconds of visible struggle on the current item/turn (shield rule 3
    only -- not part of the persisted vector)."""
    loop_count: int = 0
    """This policy's own raw readiness-loop counter (shield rule 4 only --
    not part of the persisted vector; see ``constants.py``)."""
    distress_signal: bool = False
    """Upstream moderation/distress flag (P25, out of P11 scope --
    consumed here as an opaque boolean; shield rule 5 only, not part of
    the persisted vector)."""

    def __post_init__(self) -> None:
        for name, value in (
            ("p_known", self.p_known),
            ("max_misconception_belief", self.max_misconception_belief),
            ("confidence_mean", self.confidence_mean),
            ("calibration_error", self.calibration_error),
            ("prior_teachback_success", self.prior_teachback_success),
        ):
            validate_probability(name, value)
        for name, value in (
            ("n_active_misconceptions", self.n_active_misconceptions),
            ("hints_requested_this_skill", self.hints_requested_this_skill),
            ("streak_correct", self.streak_correct),
            ("streak_incorrect", self.streak_incorrect),
            ("items_this_skill", self.items_this_skill),
            ("loop_count", self.loop_count),
        ):
            if value < 0:
                raise ValueError(f"{name} must be >= 0, got {value!r}")
        for name, value in (
            ("session_minutes", self.session_minutes),
            ("time_since_last_review_days", self.time_since_last_review_days),
            ("struggle_seconds", self.struggle_seconds),
        ):
            if value < 0.0:
                raise ValueError(f"{name} must be >= 0, got {value!r}")
        if not isfinite(self.mean_latency_z):
            raise ValueError(f"mean_latency_z must be finite, got {self.mean_latency_z!r}")
        # Validates the pattern eagerly so a malformed grade_band fails at
        # context construction, not later inside build_state_vector().
        _grade_band_bounds(self.grade_band)
        if self.hints_requested_this_skill > 0 and self.items_this_skill == 0:
            raise ValueError(
                "hints_requested_this_skill > 0 requires items_this_skill > 0 "
                f"(got hints={self.hints_requested_this_skill}, items=0)"
            )

    @property
    def hint_rate(self) -> float:
        """``hints_requested_this_skill / items_this_skill``, or ``0.0``
        with no items attempted yet. Vector dim 3."""
        if self.items_this_skill == 0:
            return 0.0
        return self.hints_requested_this_skill / self.items_this_skill


def build_state_vector(context: PolicyContext) -> PolicyDecisionState:
    """Assemble the 14-dim, ordered, versioned context vector
    (``PolicyDecisionState``, contract-fixed at exactly 14 entries) from a
    :class:`PolicyContext`. Pure and deterministic: identical input always
    produces an identical vector (roadmap P11 testing: "Same context + same
    state must always produce the same rule decision")."""
    vector = [
        context.p_known,
        context.max_misconception_belief,
        float(context.n_active_misconceptions),
        context.hint_rate,
        context.mean_latency_z,
        float(context.streak_correct),
        float(context.streak_incorrect),
        context.session_minutes,
        float(context.items_this_skill),
        context.confidence_mean,
        context.calibration_error,
        context.prior_teachback_success,
        context.time_since_last_review_days,
        encode_grade_band(context.grade_band),
    ]
    assert len(vector) == len(STATE_VECTOR_DIMENSION_NAMES)
    return PolicyDecisionState(vector=vector)
