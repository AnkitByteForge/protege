"""P20 orchestration: session -> evidence -> proof claim -> parent card.

State/data-flow (roadmap P20 "before coding" requirement):

    SESSION_COMPLETED (engine/runtime.py::complete_session)
      -> enqueue job(PROOF_ARTIFACT_JOB_TYPE, {session_id})   [jobs table]
      -> jobs/handlers.py claims the job, opens its own session_scope
      -> build_evidence_bundle():
           EvidenceRepository.list_for_session()  -- P9 evidence rows, unchanged
           -> protege.roles.reporter.EvidenceBundle (fails closed if empty)
      -> evaluate_mastery_threshold()              -- existing P2 threshold
      -> select_claim_template()                   -- enum, not free-written
      -> generate_report()                         -- P4 ModelRouter + REPORTER
                                                        role, grounded, falls
                                                        back to a deterministic
                                                        template
      -> build_uncertainty_caveats(), select_tonight_action()
      -> ProofRepository.create()                   -- one ProofArtifact row
      -> GET /v1/learners/{id}/proof (routes/learners.py) resolves each
         claim's evidence_ids back through EvidenceRepository.resolve_claim
         at READ time -- no evidence tree is duplicated into the artifact.

Nothing here writes ``mastery_estimates``/``misconception_beliefs`` (roadmap
P20: "do not move mastery authority into the Reporter") -- this module only
READS what P9/P10 already persisted and narrates it.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from protege.contracts import ProofClaim
from protege.learning_engine.threshold_service import ThresholdInputs, evaluate_mastery_threshold
from protege.llm.router import ModelRouter
from protege.roles.reporter import (
    EvidenceBundle,
    ResponseFact,
    TeachingEpisodeFact,
    TransferFact,
    build_claim_text,
    build_uncertainty_caveats,
    generate_report,
    select_claim_template,
    select_tonight_action,
)

from ..db.models import EvidenceRow, Learner, ProofArtifact, SessionRow
from ..repositories.content import ContentRepository
from ..repositories.evidence import EvidenceRepository
from ..repositories.learning_state import LearningStateRepository
from ..repositories.proof import ProofRepository
from .content import get_content_pack, get_misconception, get_skill
from .context_codec import context_from_dict

PROOF_ARTIFACT_JOB_TYPE = "generate_proof_artifact"
MASTERY_THRESHOLD_ID = "th_02"
"""ARCHITECTURE.md §17 provenance chain's own id for the P2 mastery
threshold rule -- carried through onto every ``ProofClaim`` unchanged, not
reinvented, so a claim's ``threshold_id`` matches the doc's worked example."""

_MAX_OPEN_MISCONCEPTION_CAVEATS = 2
"""Keeps the "not yet confirmed" block to a parent-readable length (the
§29 worked example shows exactly one) while still surfacing more than one
when the learner genuinely has more than one open belief."""


async def build_evidence_bundle(
    session: AsyncSession, *, session_row: SessionRow, learner: Learner
) -> tuple[EvidenceBundle, list[EvidenceRow]]:
    """Resolve one session's persisted evidence rows into a
    ``protege.roles.reporter.EvidenceBundle``.

    Scoped to exactly this session (roadmap P20 example: "Ava · Tuesday, 14
    minutes" is one session's proof, not a cumulative history). Raises
    :class:`~protege.roles.errors.NoEvidenceForProofError` (via
    ``EvidenceBundle.__post_init__``) if the session recorded nothing --
    the caller (``jobs/handlers.py``) treats that as "nothing to report
    yet," never as a reason to fabricate a card.

    The live session engine (``engine/runtime.py``, following
    ``engine/content.py``'s own pattern) currently drives exactly one
    authored skill/misconception per session (the thin-thread content
    pack's S004/M003) -- ``get_skill()``/``get_misconception()`` resolve
    the same singleton ``engine/runtime.py`` itself resolves for teach-back
    handling, so a teaching-episode evidence row's misconception identity
    is exact, not guessed. A future multi-skill session would need each
    evidence row to carry its own misconception reference (e.g. via
    ``EvidenceRow.misconception_belief_id``, which ``engine/runtime.py``
    does not yet populate for teaching-episode rows) -- a disclosed
    limitation, not a silent one.
    """
    rows = await EvidenceRepository(session).list_for_session(
        session_row.id, learner_row_id=learner.id
    )
    skill = get_skill()
    misconception = get_misconception()

    responses: list[ResponseFact] = []
    episodes: list[TeachingEpisodeFact] = []
    transfer: TransferFact | None = None

    for row in rows:
        if row.external_ref is None:  # pragma: no cover - every P9 write sets this
            continue
        payload = row.payload
        if row.kind == "response":
            responses.append(
                ResponseFact(
                    evidence_id=row.external_ref,
                    item_id=str(payload.get("item", "")),
                    correct=bool(payload.get("correct", False)),
                    unaided=bool(payload.get("unaided", False)),
                )
            )
        elif row.kind == "teaching_episode":
            resolution_turn = payload.get("resolution_turn")
            episodes.append(
                TeachingEpisodeFact(
                    evidence_id=row.external_ref,
                    misconception_code=str(misconception.code),
                    misconception_title=str(misconception.title),
                    resolved=bool(payload.get("resolved", False)),
                    resolution_turn=(
                        int(resolution_turn)
                        if isinstance(resolution_turn, int | float | str)
                        else None
                    ),
                )
            )
        elif row.kind == "transfer":
            representation = payload.get("representation")
            result = payload.get("result")
            transfer = TransferFact(
                evidence_id=row.external_ref,
                item_id=str(payload.get("item", "")),
                representation=str(representation) if representation is not None else None,
                result=bool(result) if result is not None else None,
            )

    bundle = EvidenceBundle(
        learner_label=learner.display_name,
        skill_title=skill.title,
        responses=tuple(responses),
        teaching_episodes=tuple(episodes),
        transfer=transfer,
    )
    return bundle, rows


def _duration_minutes(session_row: SessionRow) -> int | None:
    if session_row.ended_at is None:
        return None
    delta = session_row.ended_at - session_row.started_at
    return max(round(delta.total_seconds() / 60), 0)


def _misconception_title_for_code(code: str) -> str:
    for misconception in get_content_pack().misconceptions:
        if misconception.code == code:
            return str(misconception.title)
    return code


async def _open_misconception_titles(
    learning_state_repo: LearningStateRepository,
    *,
    learner_id: uuid.UUID,
    resolved_code: str | None,
) -> list[str]:
    """Titles of the learner's OWN unresolved misconception beliefs
    (roadmap P20: the uncertainty block must be grounded, never a
    speculative list of "everything else in the curriculum"). A
    first-touched misconception has no belief row for anything else yet,
    which is itself an honest "not yet checked" -- the caller's fallback
    caveat covers that case."""
    beliefs = await learning_state_repo.list_misconception_beliefs_for_learner(learner_id)
    titles = [
        _misconception_title_for_code(item.misconception_code)
        for item in beliefs
        if item.misconception_code != resolved_code and item.row.state != "resolved"
    ]
    return titles[:_MAX_OPEN_MISCONCEPTION_CAVEATS]


async def generate_proof_artifact(
    session: AsyncSession,
    *,
    session_row: SessionRow,
    router: ModelRouter,
    trace_id: str | None = None,
) -> ProofArtifact:
    """Build and persist one ``ProofArtifact`` for a completed session.

    Fails closed (propagates :class:`~protege.roles.errors.NoEvidenceForProofError`)
    when the session has no evidence -- the caller decides what "closed"
    means for its context (the job handler treats it as a benign no-op; a
    direct/synchronous caller should let it surface as an error).
    """
    learner = await session.get(Learner, session_row.learner_id)
    if learner is None:  # pragma: no cover - sessions.learner_id is a non-null FK
        raise LookupError(f"session {session_row.id} has no learner {session_row.learner_id}")

    bundle, rows = await build_evidence_bundle(session, session_row=session_row, learner=learner)

    context = (
        context_from_dict(session_row.context_snapshot)
        if session_row.context_snapshot is not None
        else None
    )
    p_known = context.p_known if context is not None else 0.0
    threshold_decision = evaluate_mastery_threshold(
        ThresholdInputs(
            p_known=p_known,
            unaided_correct_count=bundle.unaided_correct_count,
            transfer_attempted_count=bundle.transfer_attempted_count,
        )
    )
    claim_kind = select_claim_template(mastery_verified=threshold_decision.mastery_verified)

    content_repo = ContentRepository(session)
    learning_state_repo = LearningStateRepository(session)
    skill = get_skill()
    skill_row = await content_repo.get_or_create_skill(skill)
    mastery_row = await learning_state_repo.get_mastery(learner.id, skill_row.id)

    report = generate_report(router, bundle=bundle, claim_key=claim_kind, trace_id=trace_id)

    resolved_episode = bundle.resolved_teaching_episode
    open_titles = await _open_misconception_titles(
        learning_state_repo,
        learner_id=learner.id,
        resolved_code=resolved_episode.misconception_code if resolved_episode is not None else None,
    )
    caveats = build_uncertainty_caveats(
        open_misconception_titles=open_titles, transfer=bundle.transfer
    )

    claim = ProofClaim(
        id=f"c_{uuid.uuid4().hex}",
        text=build_claim_text(
            claim_kind, learner_label=bundle.learner_label, skill_title=bundle.skill_title
        ),
        threshold_id=MASTERY_THRESHOLD_ID,
        mastery_estimate_id=str(mastery_row.id) if mastery_row is not None else None,
        evidence_ids=list(bundle.all_evidence_ids()),
        caveats=caveats,
    )

    tonight_action: str | None = None
    target_episode = resolved_episode or (
        bundle.teaching_episodes[0] if bundle.teaching_episodes else None
    )
    if target_episode is not None:
        tonight_action = select_tonight_action(
            misconception_code=target_episode.misconception_code,
            interventions=get_content_pack().interventions,
        )

    claim_record: dict[str, Any] = {
        "claim": claim.model_dump(mode="json", by_alias=True),
        "claim_kind": claim_kind.value,
        "transfer_verified": bundle.transfer_verified,
        "sentences": [s.model_dump(mode="json") for s in report.draft.sentences],
        "used_fallback": report.used_fallback,
        "tonight_action": tonight_action,
        "skill_code": skill.code,
        "duration_minutes": _duration_minutes(session_row),
    }

    return await ProofRepository(session).create(
        learner_row_id=learner.id,
        session_row_id=session_row.id,
        claims=[claim_record],
        evidence_ids=[row.id for row in rows],
    )
