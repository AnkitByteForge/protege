"""Content aggregate: ``skills``, ``misconceptions``, ``learning_items``.

Schema only, per roadmap P9 scope -- content *authoring* stays P3/
``tools/authoring`` and file-based. This repository exists so a real
learner's ``mastery_estimates``/``misconceptions`` rows have somewhere to
point: ``get_or_create_skill``/``get_or_create_misconception`` mirror a
``protege.contracts.Skill``/``Misconception`` into the database by its
natural key (``code``), idempotently, with no authoring logic of its own.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from protege.contracts import Misconception as MisconceptionContract
from protege.contracts import Skill as SkillContract

from ..db.models import LearningItem, Misconception, Skill


class ContentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_skill_by_code(self, code: str) -> Skill | None:
        result = await self._session.execute(select(Skill).where(Skill.code == code))
        return result.scalar_one_or_none()

    async def get_or_create_skill(self, skill: SkillContract) -> Skill:
        existing = await self.get_skill_by_code(skill.code)
        if existing is not None:
            return existing
        row = Skill(
            code=skill.code, title=skill.title, grade_band=skill.grade_band, standard=skill.standard
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_misconception_by_code(self, code: str) -> Misconception | None:
        result = await self._session.execute(
            select(Misconception).where(Misconception.code == code)
        )
        return result.scalar_one_or_none()

    async def get_or_create_misconception(
        self, misconception: MisconceptionContract, *, skill_id: uuid.UUID | None = None
    ) -> Misconception:
        existing = await self.get_misconception_by_code(misconception.code)
        if existing is not None:
            return existing
        row = Misconception(
            code=misconception.code,
            skill_id=skill_id,
            title=misconception.title,
            description=misconception.description,
            cognitive_origin=misconception.cognitive_origin,
            distractor_likelihood=dict(misconception.distractor_likelihood),
            distractor_likelihood_if_not_misconception=(
                dict(misconception.distractor_likelihood_if_not_misconception)
                if misconception.distractor_likelihood_if_not_misconception is not None
                else None
            ),
            prevalence_prior=misconception.prevalence_prior,
            citation=misconception.citation,
            content_version=misconception.content_version,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_learning_item_by_code(self, item_code: str) -> LearningItem | None:
        result = await self._session.execute(
            select(LearningItem).where(LearningItem.item_code == item_code)
        )
        return result.scalar_one_or_none()
