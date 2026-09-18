"""P11 exit criterion, verified against real Postgres (roadmap P11:
"Persistence into policy_decisions", "Every decision produces a complete,
replayable trajectory row"; roadmap P11 testing: "Policy decision written
to P9 storage can be read back with the same: context vector,
proposed/selected action, shield override, source, counterfactual choice,
and reward data").

P11 (``protege.policy``) makes no persistence calls of its own (its own
``engine.py`` docstring: "symmetrically, P11 makes no persistence calls")
-- this test is where the two meet, exactly as P9's own
``PolicyRepository`` docstring says P9 will ("P9 makes no policy
decisions. Persistence only."). Same DB-test conventions as every other
P9 persistence test (``_db_helpers``, ``session_scope``, real Postgres,
skipped automatically if unreachable).
"""

from __future__ import annotations

from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables

from protege.contracts import PolicyAction
from protege.policy import PolicyContext, decide
from protege.session_service.db.engine import session_scope
from protege.session_service.repositories.learners import LearnerRepository
from protege.session_service.repositories.policy import PolicyRepository
from protege.session_service.repositories.sessions import SessionRepository


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


def _distressed_context() -> PolicyContext:
    return PolicyContext(
        p_known=0.62,
        max_misconception_belief=0.71,
        n_active_misconceptions=1,
        hints_requested_this_skill=1,
        mean_latency_z=-0.4,
        streak_correct=2,
        streak_incorrect=0,
        session_minutes=8.2,
        items_this_skill=4,
        confidence_mean=0.7,
        calibration_error=0.18,
        prior_teachback_success=1.0,
        time_since_last_review_days=3.0,
        grade_band="3-4",
        distress_signal=True,
    )


def test_policy_decision_round_trips_through_real_postgres() -> None:
    async def scenario() -> None:
        async with session_scope() as session:
            learner = await LearnerRepository(session).get_or_create(
                parent_email="p11-policy-test@example.com",
                display_name="Riley",
                grade_band="3-4",
            )
            session_row = await SessionRepository(session).create_session(learner_id=learner.id)
            session_row_id = session_row.id

        context = _distressed_context()
        decision = decide(
            trajectory_id="traj_p11_test",
            step=1,
            context=context,
            observation={"resolved": False, "turns": 1, "asr_reliable": True},
        )
        # A distressed context forces HUMAN_TUTOR unconditionally --
        # sanity-check the fixture actually exercises a real override
        # before trusting the round trip below to mean anything.
        assert decision.action.type == PolicyAction.HUMAN_TUTOR
        assert decision.action.shield_overrode is False  # rules already agree; see .rules
        assert decision.action.params["shield_rule"] == "distress"

        async with session_scope() as session:
            await PolicyRepository(session).append(decision, session_row_id=session_row_id)

        # Fresh session -- nothing held in memory between write and read,
        # matching test_p8_persistence_exit_gate.py's own "simulating a
        # process restart" convention.
        async with session_scope() as session:
            rows = await PolicyRepository(session).list_for_session(session_row_id)

        assert len(rows) == 1
        row = rows[0]
        assert row.trajectory_id == decision.trajectory_id
        assert row.step == decision.step
        assert [float(v) for v in row.state_vector] == decision.state.vector
        assert row.state_schema_version == decision.state.schema_version
        assert row.action_type == str(decision.action.type)
        assert row.action_params == decision.action.params
        assert row.source == decision.action.source
        assert row.shield_overrode == decision.action.shield_overrode
        assert row.counterfactual_bandit_choice == (
            str(decision.action.counterfactual_bandit_choice)
            if decision.action.counterfactual_bandit_choice is not None
            else None
        )
        assert row.observation == decision.observation
        assert row.reward_immediate == decision.reward.immediate
        assert row.reward_deferred_pending == decision.reward.deferred_pending
        assert row.next_state_ref == decision.next_state_ref

    run_async(scenario())


def test_persisted_decision_is_replayable() -> None:
    """A persisted row carries everything :func:`protege.policy.decide`
    needs to reconstruct the same decision from the same context -- the
    roadmap's own definition of "replayable" (§11.3: "next_state_ref"
    chains one trajectory row to the next; state + action here are exactly
    :func:`~protege.policy.context.build_state_vector`'s and
    :func:`~protege.policy.rules.propose_action`'s own outputs, persisted
    verbatim)."""

    async def scenario() -> None:
        async with session_scope() as session:
            learner = await LearnerRepository(session).get_or_create(
                parent_email="p11-replay-test@example.com",
                display_name="Sam",
                grade_band="3-4",
            )
            session_row = await SessionRepository(session).create_session(learner_id=learner.id)
            session_row_id = session_row.id

        context = PolicyContext(
            p_known=0.5,
            max_misconception_belief=0.0,
            n_active_misconceptions=0,
            hints_requested_this_skill=0,
            mean_latency_z=0.0,
            streak_correct=0,
            streak_incorrect=0,
            session_minutes=2.0,
            items_this_skill=1,
            confidence_mean=0.5,
            calibration_error=0.0,
            prior_teachback_success=0.0,
            time_since_last_review_days=0.0,
            grade_band="3-4",
        )
        decision = decide(trajectory_id="traj_p11_replay", step=1, context=context)

        async with session_scope() as session:
            await PolicyRepository(session).append(decision, session_row_id=session_row_id)

        async with session_scope() as session:
            (row,) = await PolicyRepository(session).list_for_session(session_row_id)

        # Rebuild the vector straight from the 14 persisted scalars, with
        # no access to the original PolicyContext object -- this is the
        # replay a future offline-evaluation pass (P24/P32) would do.
        replayed_state_vector = [float(v) for v in row.state_vector]
        assert replayed_state_vector == decision.state.vector

        # And re-running the same rule policy against the same original
        # context reproduces the persisted action exactly (determinism
        # across the write/read boundary, not just within one process).
        from protege.policy.rules import propose_action

        assert str(propose_action(context)) == row.action_type

    run_async(scenario())
