"""FSM thresholds and per-state timing (roadmap P7).

Citations use the same convention as ``docs/DECISIONS.md`` D11: a value
copied verbatim from a canonical document says so; a value this package had
to choose because no canonical document gives one is marked
**informational** and explains the reasoning, so a future reviewer (the
same audience D11 names: whoever next touches P7, P9, or P11) can accept or
revise it without archaeology.

None of these values may be duplicated as magic numbers elsewhere in this
package -- every guard and every timeout lookup in :mod:`.machine` and
:mod:`.orchestrator` reads from here.
"""

from __future__ import annotations

from protege.contracts import SessionState as S

# --- READINESS thresholds ---------------------------------------------------
# Roadmap P7 (exact spec) + ARCHITECTURE.md §1 ("P(knows) < 0.35 -> NOT
# ready... 0.35 <= P <= 0.80 -> TEACH_BACK") + addendum §3.9's own
# TRANSITIONS example (`s.p_known < 0.35`, `s.p_known <= 0.80`).

READINESS_LOW_THRESHOLD = 0.35
"""Below this: not ready -- route to the guided/recovery path."""

READINESS_HIGH_THRESHOLD = 0.80
"""Above this: route to the harder ("subtle misconception") variant."""

MAX_READINESS_LOOPS = 2
"""Escalates to a human once ``loops >= 2`` -- i.e. as soon as a *third*
below-threshold encounter happens (ARCHITECTURE.md §1: "P(knows) < 0.35 ->
back to GUIDED_LEARNING (max 2 loops); 3rd failure -> ESCALATE_TO_HUMAN").

Reconciles two phrasings of the same rule: ARCHITECTURE.md counts
*tolerated loop-backs* ("max 2 loops... 3rd failure escalates" -- the 3rd
low-``p_known`` encounter is not a 3rd loop-back, it escalates instead),
while roadmap P7 counts *encounters* ("escalation at 3 loops" -- the 3rd
time around). Both describe the identical sequence of session states; this
constant implements ARCHITECTURE.md's own counter convention (``loops`` =
completed loop-backs so far, checked *before* this encounter's own
increment) because that is the one addendum §3.9's illustrative
``TRANSITIONS`` snippet's guard shape (``s.loops >= N``, evaluated on
entry, before any increment for *this* encounter) is written against:
first encounter loops=0 -> loop back (loops->1); second encounter loops=1
-> loop back (loops->2); third encounter loops=2,
``2 >= MAX_READINESS_LOOPS`` -> escalate. See ``test_readiness.py``'s
third-encounter escalation test."""

DIAGNOSTIC_HIGH_PRIOR_THRESHOLD = 0.80
"""**Informational**, not canonical: ARCHITECTURE.md §9's mermaid diagram
draws ``DIAGNOSTIC --> PRACTICE: prior mastery high`` but no document gives
a number for "high." Reuses :data:`READINESS_HIGH_THRESHOLD` since both
edges represent the same underlying judgment ("this learner already knows
this well enough to skip ahead")."""

# --- Dwell-exit thresholds ---------------------------------------------------
# ARCHITECTURE.md §9 mermaid diagram, edge labels, verbatim.

PRACTICE_MAX_CONSECUTIVE_ERRORS = 3
PRACTICE_MIN_ITEMS_ATTEMPTED = 4
TEACH_BACK_MAX_TURNS = 6
TEACH_BACK_STUCK_TURNS = 2
INDEPENDENT_VERIFY_ITEMS = 3
INDEPENDENT_VERIFY_MIN_CORRECT = 2

# --- Timing ------------------------------------------------------------------

IDLE_TIMEOUT_SECONDS = 600.0
"""10 minutes (ARCHITECTURE.md §9 mermaid: "idle 10m"; §28.1 termination
table: "Abandon | 10 min idle | abandoned")."""

SESSION_HARD_CAP_SECONDS = 1500.0
"""25 minutes (ARCHITECTURE.md non-negotiable principles: "25-minute hard
cap"; §28.1: "Hard cap 25 minutes. The system will end a session a child
wants to continue."). Enforced by the orchestrator across the whole
session, not by any single state's dwell timeout."""

STATE_TIMEOUT_SECONDS: dict[S, float] = {
    # Cited: ARCHITECTURE.md §9's abridged per-state table.
    S.SPROUT_TEASE: 10.0,
    S.DIAGNOSTIC: 180.0,
    S.PRACTICE: 300.0,
    S.EXPLANATION: 120.0,
    S.SPROUT_SETUP: 5.0,
    S.TEACH_BACK: 480.0,
    S.INDEPENDENT_VERIFY: 240.0,
    S.MASTERY_DECISION: 5.0,  # table: "never fails" -- kept short; see machine.py docstring.
    # Cited: ARCHITECTURE.md §9 mermaid diagram edge label ("90s").
    S.DISCOVERY: 90.0,
    # Informational: no canonical duration; ARRIVAL is a synchronous
    # profile load, so a short ceiling only guards against a stalled I/O
    # call, not a child thinking.
    S.ARRIVAL: 30.0,
    # Informational: mirrors SPROUT_SETUP (also policy-only, same 5s
    # budget: "configured" is the same kind of instantaneous app step).
    S.SPROUT_SETUP_HARD: 5.0,
    # Informational: no canonical duration for the worked-example dwell;
    # set well above PRACTICE's own 300s since guided learning is meant to
    # reduce cognitive load, not race a clock.
    S.GUIDED_LEARNING: 240.0,
    # Informational: short, matching SPROUT_SETUP's "5s .. failure: pick
    # highest-prior misconception" pattern -- Coach's hint rewrite is a
    # single bounded LLM call, not a child-paced dwell.
    S.COACH_ASSIST: 30.0,
    # Informational: the §37 screen table marks Reflection "Skippable" --
    # a short ceiling matches that it's optional, not a graded step.
    S.REFLECTION: 30.0,
    # Informational: no canonical duration; matches EXPLANATION's 120s
    # since both are single free-response captures.
    S.TRANSFER: 120.0,
    # Informational: instantaneous app logic (§9 table row: "Exit:
    # computed"); a short ceiling only guards a stalled call.
    S.REWARD: 5.0,
    S.RETRIEVAL_SCHEDULE: 5.0,
    # Informational: SUMMARY kicks off the (async, P20-owned) proof/brief
    # job; this ceiling bounds only the FSM's own dwell in SUMMARY, not
    # that background job.
    S.SUMMARY: 30.0,
    # Informational: §9 table gives no timeout ("—") because this state
    # waits on a human (parent/tutor), not a fixed duration; a generous
    # ceiling here is a safety net, not a realistic expectation.
    S.ESCALATE_TO_HUMAN: 300.0,
    # COMPLETE and ABANDONED are terminal ([*] in the §9 statechart) and
    # deliberately have no entry here -- there is nothing left to time out
    # on.
}

IDLE_ELIGIBLE_STATES: frozenset[S] = frozenset(
    {
        S.ARRIVAL,
        S.SPROUT_TEASE,
        S.DIAGNOSTIC,
        S.DISCOVERY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.TEACH_BACK,
        S.COACH_ASSIST,
        S.REFLECTION,
        S.INDEPENDENT_VERIFY,
        S.TRANSFER,
    }
)
"""States where the FSM is genuinely waiting on the *child* (so 10 minutes
of silence is meaningful "idle," ARCHITECTURE.md §9 mermaid /
§28.1). Deliberately excludes the synchronous app/policy-only states
(SPROUT_SETUP(_HARD), MASTERY_DECISION, REWARD, SUMMARY,
RETRIEVAL_SCHEDULE) and ESCALATE_TO_HUMAN, where no child input is being
awaited and "idle" has no meaning -- informational, see D11-style note in
:mod:`.machine`."""
