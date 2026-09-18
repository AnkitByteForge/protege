"""Named constants for the P11 policy engine, shield, and reward.

Same convention as ``packages/learning-engine/src/protege/learning_engine/
constants.py`` and ``docs/DECISIONS.md`` D11: a value copied verbatim from a
canonical document says so; a value this package had to choose because no
canonical document gives one is marked **informational**, with the
reasoning spelled out so a future reviewer can accept or revise it without
archaeology. Nothing here is duplicated as a magic number elsewhere in this
package.

Two constants are *not* redefined here even though the shield rules that
use them come from this same roadmap paragraph: the TEACH_BACK readiness
floor (0.35) and the session hard cap (25 minutes) are already locked,
named constants in ``protege.session.constants`` (P7) --
``READINESS_LOW_THRESHOLD`` and ``SESSION_HARD_CAP_SECONDS``. Re-declaring
them here with the same numeric value would be exactly the "second source
of truth for state already represented elsewhere" AGENTS.md forbids, so
:mod:`.shield` imports them directly. Every other shield/rule constant
below (the "2 consecutive errors" / "90s struggle" / "3 loops" boundaries)
is a P11-only number with no P7 counterpart -- ``PRACTICE_MAX_CONSECUTIVE_
ERRORS`` (3) and ``MAX_READINESS_LOOPS`` (2) in P7 answer a *different*
question (when does the FSM loop the session back to GUIDED_LEARNING) than
the shield's own literal boundaries quoted in roadmap P11 ("no
DIFFICULTY_UP after 2 consecutive errors", "HUMAN_TUTOR after 3 loops"), so
conflating the two would silently change either P7's or P11's already-
locked numbers.
"""

from typing import Final

# =============================================================================
# Safety shield (ARCHITECTURE.md §11.2; roadmap P11 -- verbatim boundaries)
# =============================================================================

SHIELD_MAX_CONSECUTIVE_ERRORS_FOR_DIFFICULTY_UP: Final[int] = 2
""""Never DIFFICULTY_UP after 2 consecutive errors." Forbidden once
``streak_incorrect >= 2`` -- i.e. *at* the 2nd consecutive error, not only
after a 3rd (roadmap boundary test: "exactly 2 consecutive errors")."""

SHIELD_HINT_STRUGGLE_SECONDS: Final[float] = 90.0
""""Never withhold HINT past 90s of struggle." Forced once
``struggle_seconds >= 90.0`` (roadmap boundary test: "exactly 90 seconds of
struggle")."""

SHIELD_MAX_LOOPS: Final[int] = 3
""""Force HUMAN_TUTOR after 3 loops." Forced once ``loop_count >= 3``
(roadmap boundary test: "exactly 3 loops"). This is the policy's own raw
loop counter (:attr:`~protege.policy.context.PolicyContext.loop_count`),
distinct from P7's ``SessionContext.loops``/``MAX_READINESS_LOOPS`` --
see the module docstring."""

# =============================================================================
# Rule policy (informational -- deterministic pacing; no canonical document
# gives these exact numbers, only the *signals* to pace on, roadmap P11 §5)
# =============================================================================

RULES_ANALOGY_STRUGGLE_SECONDS: Final[float] = 45.0
"""Below the shield's hard 90s HINT floor, offer an ANALOGY once visible
struggle has run half that budget -- a softer, earlier intervention than a
HINT, only when a misconception is already implicated (see
``rules.propose_action``)."""

RULES_TEACH_BACK_MIN_STREAK_CORRECT: Final[int] = 1
"""Inside the [0.35, 0.80] readiness band (P7's own window), require at
least one recent correct response before proposing TEACH_BACK -- otherwise
PRACTICE first."""

RULES_VISUALIZATION_STREAK_CORRECT: Final[int] = 3
"""In-band but with no tracked misconception and a solid streak: propose
VISUALIZATION (reinforce/vary the representation) rather than defaulting
straight to PRACTICE."""

RULES_DIFFICULTY_UP_STREAK_CORRECT: Final[int] = 3
"""Above the 0.80 readiness ceiling, require a 3-correct streak before
proposing DIFFICULTY_UP -- mirrors ``RULES_VISUALIZATION_STREAK_CORRECT``'s
threshold for the same reason (a short streak is not yet evidence of a
stable skill)."""

RULES_TRANSFER_MIN_STREAK_CORRECT: Final[int] = 1
"""Above 0.80 with no active misconception, propose TRANSFER once at least
one recent response was correct."""

RULES_RETRIEVAL_REVIEW_DAYS: Final[float] = 3.0
"""``time_since_last_review_days`` at or above this proposes RETRIEVAL
ahead of the ordinary mastery-band branches, for an already-adequate
learner (``p_known >= RULES_RETRIEVAL_MIN_P_KNOWN``) who has drifted from
recent review."""

RULES_RETRIEVAL_MIN_P_KNOWN: Final[float] = 0.5
"""Retrieval practice is only proposed for a learner already past the
readiness floor -- a struggling learner below this needs new instruction,
not spaced review."""

# =============================================================================
# Elo item selection (ARCHITECTURE.md §11.2: "item selection by Elo match
# targeting ~0.75 success", roadmap P11 §7)
# =============================================================================

ELO_TARGET_SUCCESS_PROBABILITY: Final[float] = 0.75

# =============================================================================
# Reward (ARCHITECTURE.md §11.2 -- coefficients copied verbatim)
# =============================================================================

MASTERY_DELTA_COEFFICIENT: Final[float] = 1.0
"""``+1.0 * delta mastery_verified`` (unaided, unseen items only)."""

TRANSFER_SUCCESS_COEFFICIENT: Final[float] = 0.5
"""``+0.5 * transfer_success``."""

RETENTION_COEFFICIENT: Final[float] = 0.3
"""``+0.3 * next_session_retention`` (assigned retroactively -- deferred
until known, see ``reward.compute_reward``)."""

HINT_DEPENDENCY_COEFFICIENT: Final[float] = 0.2
"""``-0.2 * hint_dependency_increase``."""

SESSION_OVERAGE_COEFFICIENT: Final[float] = 0.1
"""``-0.1 * (session_minutes > SESSION_OVERAGE_MINUTES)`` -- the explicit
anti-engagement penalty."""

SESSION_OVERAGE_MINUTES: Final[float] = 20.0

TIME_ON_TASK_COEFFICIENT: Final[float] = 0.0
"""``+0 * time_on_task`` -- **deliberately explicit and zero** (roadmap
P11: "This is intentional and must remain explicit."; ARCHITECTURE.md
§11.2: "Read that last line to the judges."). Never remove this constant
or the term that multiplies it in ``reward.compute_reward`` -- the zero
coefficient is the architectural claim, not dead code."""
