"""Rate limits (roadmap P10, verbatim numbers: "60 events/min/learner, 10
sessions/day").

"Use the current architecture's simplest correct implementation; do not
introduce Redis prematurely" -- counts are derived directly from rows P9
already persists (``events``, ``sessions``), not from a second counter
store. This is correct without any new infrastructure: it survives process
restarts for free (the count lives in Postgres already) and needs no
cleanup job (the window is simply "rows newer than now - N").

"10 sessions/day" is interpreted as a rolling 24 h window (``started_at >=
now - 24h``), not a calendar-day boundary -- avoids a timezone-dependent
"day" definition the roadmap does not specify; called out in
``docs/P10_SESSION_API.md``'s judgment-call list.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .db.models import EventRow, SessionRow
from .errors import RateLimitExceededError
from .settings import Settings


async def check_event_rate_limit(
    session: AsyncSession, *, learner_id: uuid.UUID, settings: Settings
) -> None:
    window_start = datetime.now(UTC) - timedelta(minutes=1)
    count = (
        await session.execute(
            select(func.count())
            .select_from(EventRow)
            .where(EventRow.learner_id == learner_id, EventRow.occurred_at >= window_start)
        )
    ).scalar_one()
    if count >= settings.rate_limit_events_per_minute:
        raise RateLimitExceededError(
            f"more than {settings.rate_limit_events_per_minute} events/minute for this learner"
        )


async def check_session_rate_limit(
    session: AsyncSession, *, learner_id: uuid.UUID, settings: Settings
) -> None:
    window_start = datetime.now(UTC) - timedelta(hours=24)
    count = (
        await session.execute(
            select(func.count())
            .select_from(SessionRow)
            .where(SessionRow.learner_id == learner_id, SessionRow.started_at >= window_start)
        )
    ).scalar_one()
    if count >= settings.rate_limit_sessions_per_day:
        raise RateLimitExceededError(
            f"more than {settings.rate_limit_sessions_per_day} sessions/day for this learner"
        )
