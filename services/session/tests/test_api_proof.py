"""P20 parent proof: session -> evidence -> proof claim -> parent card.

Covers the roadmap P20 testing requirements: a completed session enqueues
the async proof job; the generated card's every claim resolves to real
evidence; ``transfer_verified`` is surfaced separately from the claim;
the uncertainty block is never empty; no-evidence generation fails closed;
and a parent cannot reach another parent's learner's card.
"""

from __future__ import annotations

import uuid

from _auth_helpers import mint_token
from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables
from _p10_helpers import api_client, create_linked_learner, new_idempotency_key
from sqlalchemy import select

from protege.authoring.loader import load_content_pack
from protege.contracts import SessionState
from protege.llm.providers.fake import FakeProvider
from protege.llm.router import ModelRouter
from protege.roles.errors import NoEvidenceForProofError
from protege.session_service.db.engine import session_scope
from protege.session_service.db.models import JobRow, ProofArtifact
from protege.session_service.engine.proof import PROOF_ARTIFACT_JOB_TYPE, generate_proof_artifact
from protege.session_service.jobs.handlers import JOB_HANDLERS
from protege.session_service.jobs.worker import claim_and_run_once
from protege.session_service.repositories.jobs import JobRepository
from protege.session_service.repositories.sessions import SessionRepository
from protege.thin_thread.fake_script import build_fake_script
from protege.thin_thread.scenario import (
    RESOLVING_EXPLANATION_TEXT,
    happy_path_scenario,
    numeric_answer_text,
    resolve_items,
    resolve_misconception,
)


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


def _correct_text(item_correct_answer: str) -> str:
    return numeric_answer_text(item_correct_answer)


async def _complete_happy_path_session(
    client, headers: dict[str, str], learner_id: uuid.UUID
) -> str:
    """Drive the exact same real thin-thread happy path
    ``test_api_e2e_thin_thread.py`` does, through ``/complete``. Returns the
    session id."""
    items = resolve_items(load_content_pack())

    create_resp = await client.post(
        "/v1/sessions",
        json={"learner_id": str(learner_id)},
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
    )
    assert create_resp.status_code == 201, create_resp.text
    session_id = create_resp.json()["session_id"]

    async def submit(payload: dict[str, object]) -> dict[str, object]:
        resp = await client.post(
            f"/v1/sessions/{session_id}/events",
            json=payload,
            headers={**headers, "Idempotency-Key": new_idempotency_key()},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    await submit(
        {
            "type": "answer_submitted",
            "item_id": items.diagnostic.item_id,
            "response_text": _correct_text(items.diagnostic.correct_answer),
        }
    )
    await submit(
        {
            "type": "answer_submitted",
            "item_id": items.practice.item_id,
            "response_text": _correct_text(items.practice.correct_answer),
        }
    )
    await submit(
        {
            "type": "explanation_given",
            "explanation": {"modality": "text", "text": "the bottom number means how many pieces"},
        }
    )
    body = await submit(
        {
            "type": "explanation_given",
            "explanation": {"modality": "text", "text": RESOLVING_EXPLANATION_TEXT},
        }
    )
    assert body["misconception_resolved"] is True
    await submit(
        {
            "type": "explanation_given",
            "explanation": {
                "modality": "text",
                "text": "He thought more pieces meant a bigger fraction.",
            },
        }
    )
    for item in items.verify:
        body = await submit(
            {
                "type": "answer_submitted",
                "item_id": item.item_id,
                "response_text": _correct_text(item.correct_answer),
            }
        )
    body = await submit(
        {
            "type": "answer_submitted",
            "item_id": items.transfer.item_id,
            "response_text": _correct_text(items.transfer.correct_answer),
        }
    )
    assert body["state"] == str(SessionState.COMPLETE)
    assert body["mastery_verified"] is True

    complete_resp = await client.post(
        f"/v1/sessions/{session_id}/complete",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
    )
    assert complete_resp.status_code == 200
    return session_id


def _fake_script() -> list[object]:
    content = load_content_pack()
    misconception = resolve_misconception(content)
    return build_fake_script(
        happy_path_scenario(), misconception=misconception, sprout_scripts=content.sprout_scripts
    )


def test_completing_a_session_enqueues_a_proof_artifact_job() -> None:
    async def scenario() -> None:
        sub = "user_proof_1"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}

        async with api_client(script=_fake_script()) as (client, _router):
            session_id = await _complete_happy_path_session(client, headers, learner_id)

        async with session_scope() as session:
            result = await session.execute(
                select(JobRow).where(JobRow.job_type == PROOF_ARTIFACT_JOB_TYPE)
            )
            jobs = result.scalars().all()
            assert len(jobs) == 1
            assert jobs[0].payload.get("session_id") == session_id

    run_async(scenario())


def test_completing_a_session_twice_enqueues_exactly_one_job() -> None:
    async def scenario() -> None:
        sub = "user_proof_1b"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}

        async with api_client(script=_fake_script()) as (client, _router):
            session_id = await _complete_happy_path_session(client, headers, learner_id)
            # The same idempotent-by-construction guard as SESSION_COMPLETED:
            # a second /complete call must not enqueue a second job.
            second = await client.post(
                f"/v1/sessions/{session_id}/complete",
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            assert second.status_code == 200

        async with session_scope() as session:
            result = await session.execute(
                select(JobRow).where(JobRow.job_type == PROOF_ARTIFACT_JOB_TYPE)
            )
            assert len(result.scalars().all()) == 1

    run_async(scenario())


def test_proof_card_is_grounded_and_surfaces_transfer_separately() -> None:
    async def scenario() -> None:
        sub = "user_proof_2"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}

        async with api_client(script=_fake_script()) as (client, router):
            session_id = await _complete_happy_path_session(client, headers, learner_id)

            async with session_scope() as session:
                session_row = await SessionRepository(session).get(uuid.UUID(session_id))
                assert session_row is not None
                await generate_proof_artifact(session, session_row=session_row, router=router)

            response = await client.get(f"/v1/learners/{learner_id}/proof", headers=headers)
            assert response.status_code == 200
            body = response.json()

            assert body["status"] == "ready"
            assert body["session_id"] == session_id
            assert body["claims"], "expected at least one claim"
            assert body["tonight_action"] is not None
            assert "2 minutes" in body["tonight_action"]

            claim = body["claims"][0]
            assert claim["text"]  # a real, non-empty claim
            assert claim["threshold_id"] == "th_02"
            assert claim["transfer_verified"] is True  # shown separately from the claim text
            assert claim["caveats"], "the uncertainty block must never be empty"

            # No forbidden parent-register vocabulary anywhere in the card.
            forbidden = ("%", "percent", "score", "mastery", "mastered")
            haystack = " ".join(
                [claim["text"], *claim["caveats"], *(s["text"] for s in claim["sentences"])]
            ).lower()
            for word in forbidden:
                assert word not in haystack

            # Every claim/evidence statement is grounded: every evidence node
            # resolves to a real source event within this exact session.
            assert claim["evidence"], "expected a non-empty evidence tree"
            evidence_ids = {node["evidence_id"] for node in claim["evidence"]}
            assert evidence_ids == set(claim_evidence_ids(claim))
            for node in claim["evidence"]:
                assert node["session_id"] == session_id
                assert node["event_type"]

            # Every sentence's own evidence ids are a subset of the claim's.
            for sentence in claim["sentences"]:
                assert set(sentence["evidence_ids"]).issubset(evidence_ids)

    run_async(scenario())


def claim_evidence_ids(claim: dict[str, object]) -> list[str]:
    return [str(node["evidence_id"]) for node in claim["evidence"]]  # type: ignore[index]


def test_no_evidence_proof_generation_fails_closed() -> None:
    async def scenario() -> None:
        sub = "user_proof_3"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        router = ModelRouter({"nvidia": FakeProvider()})

        async with session_scope() as session:
            session_row = await SessionRepository(session).create_session(
                learner_id=learner_id, initial_state=SessionState.COMPLETE
            )
            try:
                await generate_proof_artifact(session, session_row=session_row, router=router)
            except NoEvidenceForProofError:
                pass
            else:
                raise AssertionError(
                    "expected NoEvidenceForProofError for a session with no evidence"
                )

        async with session_scope() as session:
            result = await session.execute(
                select(ProofArtifact).where(ProofArtifact.learner_id == learner_id)
            )
            assert result.scalars().first() is None

    run_async(scenario())


def test_job_handler_completes_without_creating_an_artifact_when_no_evidence() -> None:
    async def scenario() -> None:
        sub = "user_proof_4"
        learner_id = await create_linked_learner(clerk_user_id=sub)

        async with session_scope() as session:
            session_row = await SessionRepository(session).create_session(
                learner_id=learner_id, initial_state=SessionState.COMPLETE
            )
            job = await JobRepository(session).enqueue(
                job_type=PROOF_ARTIFACT_JOB_TYPE, payload={"session_id": str(session_row.id)}
            )
            job_id = job.id

        claimed = await claim_and_run_once(worker_id="test-worker", handlers=JOB_HANDLERS)
        assert claimed is True

        async with session_scope() as session:
            row = await JobRepository(session).get(job_id)
            assert row is not None
            assert row.status == "succeeded"  # no evidence is not a job failure

            result = await session.execute(
                select(ProofArtifact).where(ProofArtifact.learner_id == learner_id)
            )
            assert result.scalars().first() is None

    run_async(scenario())


def test_proof_route_forbidden_for_a_different_parent() -> None:
    async def scenario() -> None:
        owner_learner_id = await create_linked_learner(clerk_user_id="user_proof_5_owner")
        intruder_token = mint_token(sub="user_proof_5_intruder", role="parent")
        await create_linked_learner(clerk_user_id="user_proof_5_intruder")

        async with api_client() as (client, _router):
            response = await client.get(
                f"/v1/learners/{owner_learner_id}/proof",
                headers={"Authorization": f"Bearer {intruder_token}"},
            )
            assert response.status_code == 403

    run_async(scenario())
