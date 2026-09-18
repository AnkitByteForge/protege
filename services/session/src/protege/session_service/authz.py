"""Server-side ownership checks (roadmap P10 rule: "no trusting learner_id
from the body alone"; "parent/child/tutor/admin resource boundaries must be
explicit where the current contracts already support them").

Every function here re-derives ownership from the database on every call --
nothing here trusts a path/body-supplied id without checking it against the
verified :class:`~.auth.Actor`. A child never holds an independent Clerk
identity in this product (COPPA-driven design, see ``auth.py``'s
``ActorRole`` docstring): a session is "owned" by the parent account, and a
learner profile belongs to that parent -- so "the child accessing their own
session" and "the parent's browser accessing that child's session" are the
same authorization check.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from .auth import Actor, ActorRole
from .db.models import Learner, Parent, SessionRow
from .errors import ForbiddenError, NotFoundError
from .repositories.learners import LearnerRepository
from .repositories.sessions import SessionRepository


async def resolve_parent(session: AsyncSession, actor: Actor) -> Parent:
    """The :class:`~.db.models.Parent` row backing this verified actor.
    Raises :class:`ForbiddenError` if no PROTÉGÉ account is linked to this
    Clerk identity yet -- being signed in to Clerk is not, by itself,
    authorization to touch any PROTÉGÉ resource."""
    parent = await LearnerRepository(session).get_parent_by_clerk_user_id(actor.clerk_user_id)
    if parent is None:
        raise ForbiddenError("no PROTÉGÉ account is linked to this sign-in yet")
    return parent


async def get_owned_learner(session: AsyncSession, actor: Actor, learner_id: uuid.UUID) -> Learner:
    """The learner, only if it exists and the actor is authorized to act on
    it: an admin may act on any learner; a tutor is out of scope for
    write/ownership actions in P10 (read-only tutor-brief access is
    checked separately by its own route, not here); otherwise the actor
    must be the linked parent of that exact learner."""
    learner = await LearnerRepository(session).get(learner_id)
    if learner is None:
        raise NotFoundError("learner not found")
    if actor.role == ActorRole.ADMIN:
        return learner
    parent = await resolve_parent(session, actor)
    if learner.parent_id != parent.id:
        raise ForbiddenError("this learner does not belong to the signed-in account")
    return learner


async def get_owned_session(
    session: AsyncSession, actor: Actor, session_id: uuid.UUID
) -> SessionRow:
    """The session row, only if it exists and its owning learner belongs to
    the actor (or the actor is an admin)."""
    session_row = await SessionRepository(session).get(session_id)
    if session_row is None:
        raise NotFoundError("session not found")
    await get_owned_learner(session, actor, session_row.learner_id)
    return session_row


def require_tutor_or_admin(actor: Actor) -> None:
    """Gate for the tutor-brief route (architecture §23: "Requires
    time-boxed tutor grant"). P10 does not implement a time-boxed grant
    ledger (no roadmap phase before P10 has written one -- see
    ``docs/P10_SESSION_API.md``'s blockers section); this checks only the
    role claim, which is the minimum real check available today."""
    if actor.role not in (ActorRole.TUTOR, ActorRole.ADMIN):
        raise ForbiddenError("tutor access is required for this resource")
