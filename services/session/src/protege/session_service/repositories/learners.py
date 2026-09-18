"""Learner aggregate: ``parents`` + ``learners``, plus learner deletion.

Deletion drives every ``ON DELETE CASCADE`` foreign key installed by the P9
migration (``mastery_estimates``, ``misconception_beliefs``, ``sessions`` ->
``session_states``/``turns``, ``evidence``, ``memory_items`` ->
``embedding_records``, ``responses``, ``explanations``, ``retrieval_schedule``,
``proof_artifacts``, ``tutor_briefings``) -- this repository issues one
``DELETE FROM learners WHERE id = ...`` and lets Postgres do the cascade,
rather than reimplementing per-table deletes here (a second source of truth
for what cascades, which AGENTS.md forbids).

``skills``/``misconceptions``/``learning_items`` (content, not
learner-owned) carry no learner FK at all. ``events`` and ``safety_events``
are the roadmap's retention/audit exception ("Respect any roadmap
retention/audit exceptions instead of blindly cascading every table"): both
use ``ON DELETE SET NULL`` rather than CASCADE, so the RL/audit trail and
any safety incident record outlive the deleted account, un-linked rather
than erased (see each model's own docstring). ``model_runs.session_id`` is
likewise ``SET NULL``; it carries no ``learner_id`` at all.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.append_only import ALLOW_CASCADE_WRITE_GUC
from ..db.models import Learner, Parent


class LearnerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_parent(self, *, email: str, consent_version: str) -> Parent:
        parent = Parent(email=email, consent_version=consent_version)
        self._session.add(parent)
        await self._session.flush()
        return parent

    async def get_parent_by_email(self, email: str) -> Parent | None:
        result = await self._session.execute(select(Parent).where(Parent.email == email))
        return result.scalar_one_or_none()

    async def get_parent_by_clerk_user_id(self, clerk_user_id: str) -> Parent | None:
        result = await self._session.execute(
            select(Parent).where(Parent.clerk_user_id == clerk_user_id)
        )
        return result.scalar_one_or_none()

    async def link_clerk_user_id(self, *, parent_id: uuid.UUID, clerk_user_id: str) -> Parent:
        parent = await self._session.get(Parent, parent_id)
        if parent is None:
            raise LookupError(f"no parent {parent_id}")
        parent.clerk_user_id = clerk_user_id
        await self._session.flush()
        return parent

    async def create_learner(
        self,
        *,
        parent_id: uuid.UUID,
        display_name: str,
        grade_band: str,
        dob_year: int | None = None,
    ) -> Learner:
        learner = Learner(
            parent_id=parent_id, display_name=display_name, grade_band=grade_band, dob_year=dob_year
        )
        self._session.add(learner)
        await self._session.flush()
        return learner

    async def get(self, learner_id: uuid.UUID) -> Learner | None:
        return await self._session.get(Learner, learner_id)

    async def get_or_create(
        self, *, parent_email: str, display_name: str, grade_band: str, consent_version: str = "v1"
    ) -> Learner:
        """Test/demo convenience: one learner per parent email, created on
        first use. Not a business rule -- purely idempotent fixture setup."""
        parent = await self.get_parent_by_email(parent_email)
        if parent is None:
            parent = await self.create_parent(email=parent_email, consent_version=consent_version)
        result = await self._session.execute(select(Learner).where(Learner.parent_id == parent.id))
        learner = result.scalars().first()
        if learner is not None:
            return learner
        return await self.create_learner(
            parent_id=parent.id, display_name=display_name, grade_band=grade_band
        )

    async def delete(self, learner_id: uuid.UUID) -> None:
        """Hard delete. Every table with ``learner_id ON DELETE CASCADE``
        (see ``db/models``) is removed by Postgres in the same statement's
        cascade -- see the module docstring for the retention exceptions.

        ``SET LOCAL`` scopes the append-only escape hatch to exactly this
        transaction (auto-reset at commit/rollback): Postgres implements
        both ``ON DELETE CASCADE`` (against ``evidence``) and
        ``ON DELETE SET NULL`` (against ``events``/``safety_events``) as an
        internal DELETE/UPDATE on the referencing row -- precisely what the
        append-only trigger otherwise blocks (see ``db/append_only.py``'s
        module docstring). No other write path sets this flag.
        """
        await self._session.execute(text(f"SET LOCAL {ALLOW_CASCADE_WRITE_GUC} = 'on'"))
        await self._session.execute(delete(Learner).where(Learner.id == learner_id))
