"""The un-gameable reward definition (roadmap P11 §9; ARCHITECTURE.md
§11.2):

    r = 1.0 * delta mastery_verified          (unaided, unseen items only)
      + 0.5 * transfer_success
      + 0.3 * next_session_retention          (assigned retroactively)
      - 0.2 * hint_dependency_increase
      - 0.1 * (session_minutes > 20)          <- explicit anti-engagement penalty
      + 0   * (clicks, time_on_task, streaks, return_rate)

":func:`compute_reward` never optimizes for engagement, time spent,
streaks, or session length as a positive signal (roadmap P11 §9) -- every
coefficient above is copied verbatim from ``constants.py``, which cites
ARCHITECTURE.md §11.2 for each one. The zero-coefficient term
(``TIME_ON_TASK_COEFFICIENT * time_on_task_seconds``) is written out
explicitly in :func:`compute_reward` rather than omitted, exactly as the
roadmap requires ("+0*time_on_task ... This is intentional and must remain
explicit").
"""

from __future__ import annotations

from dataclasses import dataclass

from protege.contracts import PolicyDecisionReward

from .constants import (
    HINT_DEPENDENCY_COEFFICIENT,
    MASTERY_DELTA_COEFFICIENT,
    RETENTION_COEFFICIENT,
    SESSION_OVERAGE_COEFFICIENT,
    SESSION_OVERAGE_MINUTES,
    TIME_ON_TASK_COEFFICIENT,
    TRANSFER_SUCCESS_COEFFICIENT,
)

__all__ = ["RewardComponents", "compute_reward"]

RETENTION_DEFERRED_KEY = "retention_d7"
"""Matches ``PROTEGE_ARCHITECTURE.md`` §11.3's own trajectory example
(``"deferred_pending": ["retention_d7"]``) verbatim."""


@dataclass(frozen=True)
class RewardComponents:
    """One decision's reward inputs. Every field the caller already knows
    at logging time is required; the one field that is *not* known yet
    (``next_session_retention`` -- "assigned retroactively", §11.2) is
    optional and, when absent, the whole 0.3-weighted retention term is
    left out of :func:`compute_reward`'s immediate sum and
    ``retention_d7`` is recorded as deferred instead -- never assumed to
    be zero.
    """

    mastery_delta_verified: float = 0.0
    """Change in mastery from **unaided, unseen items only** (§11.2) --
    the caller is responsible for that scoping; this module does not
    re-derive it from raw responses (roadmap P11 §5: do not duplicate P2's
    mastery math)."""
    transfer_success: bool | None = None
    """``None`` if no transfer item was attempted at this decision (the
    ``+0.5`` term is then simply not added -- there is no "the transfer
    that didn't happen was a failure" reading here)."""
    hint_dependency_increase: float = 0.0
    """Non-negative increase in hint reliance this decision represents."""
    session_minutes: float = 0.0
    """Elapsed session minutes at this decision -- same clock as
    :attr:`~protege.policy.context.PolicyContext.session_minutes`."""
    next_session_retention: float | None = None
    """``None`` (the common case, at decision time) defers this component;
    a caller replaying/backfilling a trajectory once the next session has
    happened may supply the observed value."""
    time_on_task_seconds: float = 0.0
    """Carried through only to prove :data:`~.constants.
    TIME_ON_TASK_COEFFICIENT` truly has no effect on the sum -- see
    :func:`compute_reward` and ``tests/test_reward.py``'s explicit
    zero-coefficient test (roadmap P11 testing: "Explicitly test the zero
    coefficient: time_on_task coefficient == 0")."""


def compute_reward(components: RewardComponents) -> PolicyDecisionReward:
    """The §11.2 formula, computed term by term. Deterministic and pure --
    no I/O, no randomness (roadmap P11 testing: "determinism" applies here
    too)."""
    immediate = MASTERY_DELTA_COEFFICIENT * components.mastery_delta_verified

    if components.transfer_success is not None:
        immediate += TRANSFER_SUCCESS_COEFFICIENT * (1.0 if components.transfer_success else 0.0)

    deferred_pending: list[str] = []
    if components.next_session_retention is not None:
        immediate += RETENTION_COEFFICIENT * components.next_session_retention
    else:
        deferred_pending.append(RETENTION_DEFERRED_KEY)

    immediate -= HINT_DEPENDENCY_COEFFICIENT * components.hint_dependency_increase
    immediate -= SESSION_OVERAGE_COEFFICIENT * (
        1.0 if components.session_minutes > SESSION_OVERAGE_MINUTES else 0.0
    )

    # Explicit +0*time_on_task (roadmap P11: "intentional and must remain
    # explicit"). Do not delete this term or the constant it multiplies.
    immediate += TIME_ON_TASK_COEFFICIENT * components.time_on_task_seconds

    return PolicyDecisionReward(immediate=immediate, deferred_pending=deferred_pending)
