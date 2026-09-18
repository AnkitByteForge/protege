"""The P10 CRITICAL E2E EXIT GATE: the P8 thin thread, replayed entirely
over HTTP.

    client -> POST session -> POST events (x N) -> GET/consume SSE
    -> server FSM -> P9 persistence -> rehydrate -> continue -> complete

then a simulated process restart (a fresh ``session_scope()``/fresh
repository instances -- the same technique
``test_p8_persistence_exit_gate.py`` already uses, since nothing in this
service holds live orchestrator state in memory between requests) verifying:
same session, same authoritative state, same persisted evidence, no
duplicate state transition, and intact claim/evidence relationships.

Uses the exact same real content (S004/M003), the same
``happy_path_scenario()``, and the same ``FakeProvider``/``build_fake_script``
fixtures ``test_p8_persistence_exit_gate.py`` uses -- the point of this test
is that the *same* thin thread produces the *same* outcome over HTTP that it
already produces in-process.
"""

from __future__ import annotations

from _auth_helpers import mint_token
from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables
from _p10_helpers import api_client, create_linked_learner, new_idempotency_key

from protege.authoring.loader import load_content_pack
from protege.contracts import SessionState
from protege.session_service.db.engine import session_scope
from protege.session_service.repositories.evidence import EvidenceRepository
from protege.session_service.repositories.learning_state import LearningStateRepository
from protege.session_service.repositories.sessions import SessionRepository
from protege.thin_thread.fake_script import build_fake_script
from protege.thin_thread.scenario import (
    RESOLVING_EXPLANATION_TEXT,
    happy_path_scenario,
    numeric_answer_text,
    resolve_items,
    resolve_misconception,
    resolve_skill,
)


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


def _correct_text(item_correct_answer: str) -> str:
    return numeric_answer_text(item_correct_answer)


def test_thin_thread_replays_over_http_with_identical_outcomes_and_survives_a_restart() -> None:
    async def scenario() -> None:
        content = load_content_pack()
        items = resolve_items(content)
        misconception = resolve_misconception(content)
        skill = resolve_skill(content)
        scenario_script = happy_path_scenario()
        fake_outcomes = build_fake_script(
            scenario_script, misconception=misconception, sprout_scripts=content.sprout_scripts
        )

        sub = "user_e2e_parent"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}

        async with api_client(script=fake_outcomes) as (client, _router):
            # --- POST /v1/sessions --------------------------------------
            create_resp = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            assert create_resp.status_code == 201, create_resp.text
            session_body = create_resp.json()
            session_id = session_body["session_id"]
            assert session_body["state"] == str(SessionState.DIAGNOSTIC)
            assert session_body["next_item"]["item_id"] == items.diagnostic.item_id

            async def submit(payload: dict[str, object]) -> dict[str, object]:
                resp = await client.post(
                    f"/v1/sessions/{session_id}/events",
                    json=payload,
                    headers={**headers, "Idempotency-Key": new_idempotency_key()},
                )
                assert resp.status_code == 200, resp.text
                return resp.json()

            # --- DIAGNOSTIC ----------------------------------------------
            body = await submit(
                {
                    "type": "answer_submitted",
                    "item_id": items.diagnostic.item_id,
                    "response_text": _correct_text(items.diagnostic.correct_answer),
                }
            )
            assert body["state"] == str(SessionState.PRACTICE)
            assert body["next_item"]["item_id"] == items.practice.item_id

            # --- PRACTICE (only 1 authored item -> auto-advances) --------
            body = await submit(
                {
                    "type": "answer_submitted",
                    "item_id": items.practice.item_id,
                    "response_text": _correct_text(items.practice.correct_answer),
                }
            )
            assert body["state"] == str(SessionState.EXPLANATION)

            # --- EXPLANATION (readiness capture) --------------------------
            body = await submit(
                {
                    "type": "explanation_given",
                    "explanation": {
                        "modality": "text",
                        "text": "the bottom number means how many pieces",
                    },
                }
            )
            assert body["state"] == str(SessionState.TEACH_BACK)

            # --- TEACH_BACK (real Sprout+Diagnostician via FakeProvider) --
            body = await submit(
                {
                    "type": "explanation_given",
                    "explanation": {"modality": "text", "text": RESOLVING_EXPLANATION_TEXT},
                }
            )
            assert body["misconception_resolved"] is True
            assert body["sprout_turn"] is not None
            assert body["diagnosis"] is not None
            assert body["state"] == str(SessionState.REFLECTION)

            # --- REFLECTION ------------------------------------------------
            body = await submit(
                {
                    "type": "explanation_given",
                    "explanation": {
                        "modality": "text",
                        "text": "He thought more pieces meant a bigger fraction.",
                    },
                }
            )
            assert body["state"] == str(SessionState.INDEPENDENT_VERIFY)

            # --- INDEPENDENT_VERIFY (3 items, unaided) ---------------------
            for item in items.verify:
                body = await submit(
                    {
                        "type": "answer_submitted",
                        "item_id": item.item_id,
                        "response_text": _correct_text(item.correct_answer),
                    }
                )
            assert body["state"] == str(SessionState.TRANSFER)

            # --- TRANSFER (cascades MASTERY_DECISION/REWARD/SUMMARY/... ) --
            body = await submit(
                {
                    "type": "answer_submitted",
                    "item_id": items.transfer.item_id,
                    "response_text": _correct_text(items.transfer.correct_answer),
                }
            )
            assert body["state"] == str(SessionState.COMPLETE)
            assert body["mastery_verified"] is True

            # --- SSE: authoritative events, in stable order ---------------
            seen_steps: list[int] = []
            async with client.stream(
                "GET", f"/v1/sessions/{session_id}/stream", headers=headers
            ) as stream:
                assert stream.status_code == 200
                current_id: int | None = None
                async for line in stream.aiter_lines():
                    if line.startswith("id: "):
                        current_id = int(line.removeprefix("id: "))
                    elif line.startswith("event: session_ended"):
                        break
                    elif line == "" and current_id is not None:
                        seen_steps.append(current_id)
            assert seen_steps == sorted(seen_steps)
            assert len(seen_steps) >= 1
            assert seen_steps == list(range(1, len(seen_steps) + 1))

            # --- POST /complete (idempotent finalize) ----------------------
            complete_key = new_idempotency_key()
            complete_resp_1 = await client.post(
                f"/v1/sessions/{session_id}/complete",
                headers={**headers, "Idempotency-Key": complete_key},
            )
            assert complete_resp_1.status_code == 200
            assert complete_resp_1.json()["end_reason"] == "mastery_verified"

            complete_resp_2 = await client.post(
                f"/v1/sessions/{session_id}/complete",
                headers={**headers, "Idempotency-Key": complete_key},
            )
            assert complete_resp_2.status_code == 200
            assert complete_resp_2.json() == complete_resp_1.json()

            # --- GET rehydration -------------------------------------------
            get_resp = await client.get(f"/v1/sessions/{session_id}", headers=headers)
            assert get_resp.status_code == 200
            assert get_resp.json()["state"] == str(SessionState.COMPLETE)
            assert get_resp.json()["ended_at"] is not None

        # --- simulate a process restart: fresh session_scope, fresh repos --
        import uuid as uuid_mod

        session_uuid = uuid_mod.UUID(session_id)
        learner_uuid = uuid_mod.UUID(str(learner_id))
        async with session_scope() as session:
            rehydrated = await SessionRepository(session).rehydrate(session_uuid)
            assert rehydrated.current_state == SessionState.COMPLETE
            assert rehydrated.learner_id == learner_uuid
            assert rehydrated.ended_at is not None

            mastery_rows = await LearningStateRepository(session).list_mastery_for_learner(
                learner_uuid
            )
            assert len(mastery_rows) == 1
            assert mastery_rows[0].skill_code == skill.code
            assert mastery_rows[0].row.transfer_verified is True

            beliefs = await LearningStateRepository(session).list_misconception_beliefs_for_learner(
                learner_uuid
            )
            assert len(beliefs) == 1
            assert beliefs[0].misconception_code == misconception.code
            assert beliefs[0].row.state == "resolved"

            # No duplicate SESSION_COMPLETED despite the duplicate /complete call.
            from sqlalchemy import func, select

            from protege.session_service.db.models import EventRow

            completed_count = (
                await session.execute(
                    select(func.count())
                    .select_from(EventRow)
                    .where(
                        EventRow.session_id == session_uuid,
                        EventRow.event_type == "SESSION_COMPLETED",
                    )
                )
            ).scalar_one()
            assert completed_count == 1

            transitions = await SessionRepository(session).list_transitions(session_uuid)
            steps = [t.step for t in transitions]
            assert steps == list(range(1, len(steps) + 1)), "no duplicate/out-of-order transitions"

            from sqlalchemy import select as _select

            from protege.session_service.db.models import EvidenceRow

            evidence_query = _select(EvidenceRow).where(EvidenceRow.session_id == session_uuid)
            all_evidence = (await session.execute(evidence_query)).scalars().all()
            # diagnostic + practice + 3 verify + transfer + teaching-episode
            assert len(all_evidence) >= 6
            transfer_evidence = [row for row in all_evidence if row.kind == "transfer"]
            assert len(transfer_evidence) == 1
            assert transfer_evidence[0].mastery_estimate_id == mastery_rows[0].row.id
            for evidence_row in all_evidence:
                resolved = await EvidenceRepository(session).resolve_claim(
                    [evidence_row.external_ref], learner_row_id=learner_uuid
                )
                assert len(resolved) == 1
                assert resolved[0].source_event is not None
                assert resolved[0].session is not None
                assert resolved[0].session.id == session_uuid

    run_async(scenario())
