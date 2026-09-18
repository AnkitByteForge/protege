"""``evidence`` aggregate: the provenance ledger (append-only; §17).

``append`` is the only write (database-enforced append-only, like
``events`` -- see ``db/append_only.py``). ``resolve_claim`` is the roadmap's
"claim -> evidence-tree resolution by query": given the opaque evidence ids
a ``protege.contracts.MasteryOutcome``/``ProofClaim`` carries, it returns
each evidence row joined to its source event and (if the event names one)
the originating session -- the exact chain the roadmap specifies: "claim ->
evidence IDs -> evidence rows -> source event -> originating session/turn."
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from protege.contracts import Evidence as EvidenceContract

from ..db.models import EventRow, EvidenceRow, SessionRow, TurnRow


@dataclass(frozen=True)
class EvidenceTreeNode:
    """One resolved link in a claim's evidence tree."""

    evidence: EvidenceRow
    source_event: EventRow | None
    session: SessionRow | None
    turn: TurnRow | None


class EvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        evidence: EvidenceContract,
        *,
        learner_row_id: uuid.UUID,
        source_event_row_id: uuid.UUID,
        session_row_id: uuid.UUID | None = None,
        turn_row_id: uuid.UUID | None = None,
        mastery_estimate_row_id: uuid.UUID | None = None,
        misconception_belief_row_id: uuid.UUID | None = None,
    ) -> EvidenceRow:
        row = EvidenceRow(
            external_ref=evidence.evidence_id,
            learner_id=learner_row_id,
            session_id=session_row_id,
            turn_id=turn_row_id,
            mastery_estimate_id=mastery_estimate_row_id,
            misconception_belief_id=misconception_belief_row_id,
            kind=str(evidence.kind),
            source_event_id=source_event_row_id,
            weight=evidence.weight,
            payload=dict(evidence.payload),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_by_external_ref(self, external_ref: str) -> EvidenceRow | None:
        result = await self._session.execute(
            select(EvidenceRow).where(EvidenceRow.external_ref == external_ref)
        )
        return result.scalar_one_or_none()

    async def list_for_mastery_estimate(
        self, mastery_estimate_row_id: uuid.UUID
    ) -> list[EvidenceRow]:
        result = await self._session.execute(
            select(EvidenceRow).where(EvidenceRow.mastery_estimate_id == mastery_estimate_row_id)
        )
        return list(result.scalars().all())

    async def resolve_claim(self, evidence_ids: Sequence[str]) -> list[EvidenceTreeNode]:
        """Resolve a claim's opaque ``evidence_ids`` (as carried by
        ``MasteryOutcome.evidence_ids``/``ProofClaim.evidence_ids``) to the
        full tree: evidence row -> source event -> originating session/turn.

        Missing ids are silently skipped rather than raising -- a caller
        auditing a claim wants to see what actually resolves, and a claim
        referencing a since-deleted (learner-deletion-cascaded) evidence row
        is itself useful information, not an error in this query.
        """
        nodes: list[EvidenceTreeNode] = []
        for evidence_id in evidence_ids:
            evidence_row = await self.get_by_external_ref(evidence_id)
            if evidence_row is None:
                continue
            event_row = await self._session.get(EventRow, evidence_row.source_event_id)
            session_row = (
                await self._session.get(SessionRow, evidence_row.session_id)
                if evidence_row.session_id is not None
                else None
            )
            turn_row = (
                await self._session.get(TurnRow, evidence_row.turn_id)
                if evidence_row.turn_id is not None
                else None
            )
            nodes.append(
                EvidenceTreeNode(
                    evidence=evidence_row,
                    source_event=event_row,
                    session=session_row,
                    turn=turn_row,
                )
            )
        return nodes
