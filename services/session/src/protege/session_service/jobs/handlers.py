"""Job handlers registered with the P9 worker loop (``jobs/worker.py``).

Roadmap P20: "async job on SESSION_COMPLETED." ``engine/runtime.py::complete_session``
enqueues :data:`~..engine.proof.PROOF_ARTIFACT_JOB_TYPE`; this module is what
actually claims and runs it, opening its own transaction (the worker's own
rule: "job handler runs outside any transaction the claim held").
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping

from protege.roles.errors import NoEvidenceForProofError

from ..db.engine import session_scope
from ..db.models import JobRow
from ..engine.proof import PROOF_ARTIFACT_JOB_TYPE, generate_proof_artifact
from ..repositories.sessions import SessionRepository
from ..router_factory import build_default_model_router
from ..settings import get_settings
from .worker import JobHandler

logger = logging.getLogger(__name__)


async def _handle_generate_proof_artifact(job: JobRow) -> None:
    session_id_raw = job.payload.get("session_id")
    if not isinstance(session_id_raw, str):
        raise ValueError(f"job {job.id}: payload missing a string 'session_id'")
    session_id = uuid.UUID(session_id_raw)

    settings = get_settings()
    router = build_default_model_router(settings)

    async with session_scope(settings) as session:
        session_row = await SessionRepository(session).get(session_id)
        if session_row is None:
            # The session (or the learner it cascades from) was deleted
            # between enqueue and claim -- nothing to report on, not a
            # failure to retry.
            logger.info("proof artifact job: session %s no longer exists", session_id)
            return
        try:
            await generate_proof_artifact(session, session_row=session_row, router=router)
        except NoEvidenceForProofError:
            # Roadmap P20: "no-evidence proof generation fails closed" --
            # for the automatic post-session job this is not a bug (an
            # abandoned/near-instant session may genuinely record nothing),
            # so the job still succeeds; it simply produces no artifact.
            logger.info(
                "proof artifact job: session %s has no evidence yet -- nothing to report",
                session_id,
            )
            return


JOB_HANDLERS: Mapping[str, JobHandler] = {
    PROOF_ARTIFACT_JOB_TYPE: _handle_generate_proof_artifact,
}
"""Every job type this service's worker process knows how to run, passed to
``jobs/worker.py::run_worker_loop``'s ``handlers`` argument."""
