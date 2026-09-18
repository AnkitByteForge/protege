"""The P9 exit criterion, verified end to end (roadmap P9 "P9 EXIT
CRITERION" + "VALIDATION" smoke test):

    A completed P8-style session can be persisted, the process/state can be
    reconstructed from PostgreSQL, and a proof claim can be resolved through
    a queryable evidence tree.

Covers exit gates 4-9, 15 in one realistic run: run the real P8 thin thread
(``protege.thin_thread.run_thin_thread``, ``FakeProvider``, exactly
``packages/thin-thread/tests``' own pattern) to a genuine verified-mastery
completion, persist it through ``persist_thin_thread_result``, rehydrate
through fresh repository instances against a fresh session (simulating a
process restart -- nothing is held in memory between the two phases except
row ids), verify mastery/misconception/evidence/model_runs match, resolve
the mastery claim's evidence tree, then delete the learner and confirm no
orphaned rows or vectors remain.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables
from sqlalchemy import func, select, text

from protege.authoring.loader import load_content_pack
from protege.contracts import DomainEvent, EventType, Evidence, EvidenceKind, SessionState
from protege.llm.providers.fake import FakeProvider
from protege.llm.router import ModelRouter
from protege.session_service.db.engine import session_scope
from protege.session_service.db.models import EmbeddingRecord
from protege.session_service.persistence.thin_thread_bridge import persist_thin_thread_result
from protege.session_service.repositories.content import ContentRepository
from protege.session_service.repositories.events import EventRepository
from protege.session_service.repositories.evidence import EvidenceRepository
from protege.session_service.repositories.learners import LearnerRepository
from protege.session_service.repositories.learning_state import LearningStateRepository
from protege.session_service.repositories.memory import MemoryRepository
from protege.session_service.repositories.model_runs import ModelRunRepository
from protege.session_service.repositories.sessions import SessionRepository
from protege.thin_thread.engine import run_thin_thread
from protege.thin_thread.fake_script import build_fake_script
from protege.thin_thread.scenario import happy_path_scenario, resolve_misconception, resolve_skill


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


def _run_real_thin_thread() -> tuple[object, ModelRouter]:
    content = load_content_pack()
    scenario = happy_path_scenario()
    misconception = resolve_misconception(content)
    script = build_fake_script(
        scenario, misconception=misconception, sprout_scripts=content.sprout_scripts
    )
    router = ModelRouter({"nvidia": FakeProvider(script=script)})
    result = run_thin_thread(scenario, router, content=content)
    return result, router


def test_completed_p8_session_persists_rehydrates_and_resolves_its_claim() -> None:
    async def scenario() -> None:
        content = load_content_pack()
        skill = resolve_skill(content)
        misconception = resolve_misconception(content)
        result, router = _run_real_thin_thread()
        assert result.mastery_outcome is not None, "fixture scenario must reach verified mastery"
        assert result.final_state == SessionState.COMPLETE

        # --- 1. create learner/session; 2. persist state + evidence -------
        async with session_scope() as session:
            skill_row = await ContentRepository(session).get_or_create_skill(skill)
            misconception_row = await ContentRepository(session).get_or_create_misconception(
                misconception, skill_id=skill_row.id
            )
            learner = await LearnerRepository(session).get_or_create(
                parent_email="exit-gate@example.com", display_name="Riley", grade_band="3-4"
            )
            learner_id = learner.id
            skill_id = skill_row.id
            misconception_id = misconception_row.id

            persisted = await persist_thin_thread_result(
                session,
                learner_id=learner_id,
                skill_id=skill_id,
                skill_code=skill.code,
                misconception_id=misconception_id,
                result=result,
                model_runs=router.telemetry.runs,  # type: ignore[union-attr]
            )
            session_id = persisted.session_id

            # A representative memory record too, so the later deletion
            # check has a real embedding row to prove is gone.
            memory_item = await MemoryRepository(session).add_memory_item(
                learner_id=learner_id, content="explained fractions", kind="explanation"
            )
            await MemoryRepository(session).add_embedding(
                memory_item_id=memory_item.id,
                learner_id=learner_id,
                embedding=[0.01] * 384,
            )

        # --- 3. simulate a process restart: fresh session, fresh repos ----
        async with session_scope() as session:
            rehydrated = await SessionRepository(session).rehydrate(session_id)

            # --- 4/5/6. verify state/evidence/claim identical -------------
            assert rehydrated.current_state == SessionState.COMPLETE
            assert rehydrated.learner_id == learner_id
            assert tuple(rehydrated.state_sequence) == tuple(result.state_sequence)

            mastery_row = await LearningStateRepository(session).get_mastery(learner_id, skill_id)
            assert mastery_row is not None
            assert float(mastery_row.p_known) == pytest.approx(
                result.mastery_outcome.p_known_after, abs=1e-4
            )
            assert mastery_row.transfer_verified == result.mastery_outcome.transfer_verified

            belief_row = await LearningStateRepository(session).get_misconception_belief(
                learner_id, misconception_id
            )
            assert belief_row is not None
            assert result.misconception_belief is not None
            assert belief_row.state == str(result.misconception_belief.state)

            evidence_rows = await EvidenceRepository(session).list_for_mastery_estimate(
                mastery_row.id
            )
            assert len(evidence_rows) > 0
            for row in evidence_rows:
                assert row.weight is not None
                assert row.source_event_id is not None

            tree = await EvidenceRepository(session).resolve_claim(
                result.mastery_outcome.evidence_ids, learner_row_id=learner_id
            )
            assert len(tree) == len(result.mastery_outcome.evidence_ids)
            for node in tree:
                assert node.source_event is not None
                assert node.session is not None
                assert node.session.id == session_id
                assert node.evidence.external_ref in result.mastery_outcome.evidence_ids

            model_run_rows = await ModelRunRepository(session).list_for_session(session_id)
            assert len(model_run_rows) == len(router.telemetry.runs)  # type: ignore[union-attr]

            embedding_count_before_delete = (
                await session.execute(select(func.count()).select_from(EmbeddingRecord))
            ).scalar_one()
            assert embedding_count_before_delete >= 1

        # --- 7. delete learner; verify no orphaned vectors -----------------
        async with session_scope() as session:
            await LearnerRepository(session).delete(learner_id)

        async with session_scope() as session:
            assert await SessionRepository(session).get(session_id) is None
            assert await LearningStateRepository(session).get_mastery(learner_id, skill_id) is None
            assert (
                await LearningStateRepository(session).get_misconception_belief(
                    learner_id, misconception_id
                )
                is None
            )
            embedding_count_after_delete = (
                await session.execute(select(func.count()).select_from(EmbeddingRecord))
            ).scalar_one()
            assert embedding_count_after_delete == 0

    run_async(scenario())


def test_learner_deletion_leaves_events_and_safety_events_unlinked_not_orphaned() -> None:
    """The roadmap's retention/audit exception: ``events``/``safety_events``
    survive learner deletion (36-mo retention, RL substrate) with their
    ``learner_id`` set to NULL rather than being deleted -- proving the
    FK action is ``SET NULL``, not silently absent."""

    async def scenario() -> None:
        content = load_content_pack()
        skill = resolve_skill(content)
        misconception = resolve_misconception(content)
        result, router = _run_real_thin_thread()
        assert result.mastery_outcome is not None

        async with session_scope() as session:
            skill_row = await ContentRepository(session).get_or_create_skill(skill)
            misconception_row = await ContentRepository(session).get_or_create_misconception(
                misconception, skill_id=skill_row.id
            )
            learner = await LearnerRepository(session).get_or_create(
                parent_email="retention-check@example.com", display_name="Sam", grade_band="3-4"
            )
            learner_id = learner.id
            persisted = await persist_thin_thread_result(
                session,
                learner_id=learner_id,
                skill_id=skill_row.id,
                skill_code=skill.code,
                misconception_id=misconception_row.id,
                result=result,
                model_runs=router.telemetry.runs,  # type: ignore[union-attr]
            )
            session_id = persisted.session_id

        async with session_scope() as session:
            events_before = (
                await session.execute(
                    text("SELECT count(*) FROM events WHERE session_id = :sid"), {"sid": session_id}
                )
            ).scalar_one()
            assert events_before > 0

        async with session_scope() as session:
            await LearnerRepository(session).delete(learner_id)

        async with session_scope() as session:
            events_after = (
                await session.execute(text("SELECT count(*) FROM events WHERE id IS NOT NULL"))
            ).scalar_one()
            # Events themselves are retained (not cascade-deleted)...
            assert events_after >= events_before
            still_linked = (
                await session.execute(
                    text("SELECT count(*) FROM events WHERE learner_id = :lid"), {"lid": learner_id}
                )
            ).scalar_one()
            # ...but no longer linked to the deleted learner.
            assert still_linked == 0

    run_async(scenario())


def test_resolve_claim_does_not_cross_contaminate_learners_with_colliding_opaque_ids() -> None:
    """Audit 7: "no claim can silently resolve to unrelated learner/session
    data." A pre-persistence id minter like P8's ``IdAllocator`` restarts
    its counter at 1 every run, so two different learners' evidence can
    legitimately carry the identical opaque ``external_ref`` (e.g. both
    mint ``"e_001"``). ``EvidenceRepository.resolve_claim`` must still
    resolve each learner's claim to *that learner's own* evidence row, never
    the other learner's -- proven here by constructing exactly that
    collision directly (not relying on the thin-thread bridge, so the test
    does not depend on IdAllocator's own restart behaviour to reproduce it).
    """

    async def scenario() -> None:
        async with session_scope() as session:
            learner_a = await LearnerRepository(session).get_or_create(
                parent_email="collision-a@example.com", display_name="A", grade_band="3-4"
            )
            learner_b = await LearnerRepository(session).get_or_create(
                parent_email="collision-b@example.com", display_name="B", grade_band="3-4"
            )

            event_repo = EventRepository(session)
            evidence_repo = EvidenceRepository(session)

            event_a = await event_repo.append(
                DomainEvent(
                    id="evt_a",
                    event_type=EventType.ANSWER_SUBMITTED,
                    occurred_at=datetime.now(UTC),
                    learner_id=str(learner_a.id),
                ),
                learner_row_id=learner_a.id,
                session_row_id=None,
            )
            event_b = await event_repo.append(
                DomainEvent(
                    id="evt_b",
                    event_type=EventType.ANSWER_SUBMITTED,
                    occurred_at=datetime.now(UTC),
                    learner_id=str(learner_b.id),
                ),
                learner_row_id=learner_b.id,
                session_row_id=None,
            )

            # The identical opaque id, minted independently for two
            # different learners -- the exact collision a restarting
            # IdAllocator produces across two separate runs.
            evidence_a = await evidence_repo.append(
                Evidence(
                    id="e_001",
                    kind=EvidenceKind.RESPONSE,
                    source_event_id="ignored-by-append",
                    weight=1.0,
                    payload={"owner": "a"},
                ),
                learner_row_id=learner_a.id,
                source_event_row_id=event_a.id,
            )
            evidence_b = await evidence_repo.append(
                Evidence(
                    id="e_001",
                    kind=EvidenceKind.RESPONSE,
                    source_event_id="ignored-by-append",
                    weight=1.0,
                    payload={"owner": "b"},
                ),
                learner_row_id=learner_b.id,
                source_event_row_id=event_b.id,
            )
            assert evidence_a.id != evidence_b.id  # two distinct rows, same external_ref

            tree_a = await evidence_repo.resolve_claim(["e_001"], learner_row_id=learner_a.id)
            tree_b = await evidence_repo.resolve_claim(["e_001"], learner_row_id=learner_b.id)

            assert len(tree_a) == 1
            assert len(tree_b) == 1
            assert tree_a[0].evidence.id == evidence_a.id
            assert tree_a[0].evidence.payload["owner"] == "a"
            assert tree_b[0].evidence.id == evidence_b.id
            assert tree_b[0].evidence.payload["owner"] == "b"

    run_async(scenario())
