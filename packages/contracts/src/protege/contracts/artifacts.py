"""Parent- and tutor-facing artifact contracts (ARCHITECTURE.md §17, §22, §29,
§30). Every claim carries evidence; uncertainty is mandatory; the Reporter
may only cite evidence rows that exist.
"""

from datetime import datetime

from pydantic import Field

from .base import JSONValue, ProtegeBaseModel
from .ids import ClaimId, EvidenceId, LearnerId, OpaqueId


class ProofClaim(ProtegeBaseModel):
    """One claim on the parent proof card (§17 provenance chain).

    Claims are enum-selected, not free-written (§17); each resolves through
    ``mastery_estimate_id`` to its evidence tree. ``caveats`` carry the
    mandatory uncertainty (e.g. "transfer confirmed on number line only").
    """

    claim_id: ClaimId = Field(alias="id")
    text: str
    threshold_id: str | None = None
    mastery_estimate_id: OpaqueId | None = None
    evidence_ids: list[EvidenceId] = Field(min_length=1)
    caveats: list[str] = Field(default_factory=list)


class TutorBriefing(ProtegeBaseModel):
    """Tutor briefing payload (§30 format; §22 ``tutor_briefings``).

    The §30 briefing sections are the contract; loose dicts keep the payload
    additive while P21 freezes the exact shapes. The briefing opens with
    what NOT to re-teach — the most valuable 20 seconds of tutor prep.
    """

    briefing_id: OpaqueId | None = Field(default=None, alias="id")
    learner_id: LearnerId
    generated_at: datetime
    viewed_at: datetime | None = None
    goal: str | None = None
    resolved: list[dict[str, JSONValue]] = Field(default_factory=list)
    still_open: list[dict[str, JSONValue]] = Field(default_factory=list)
    what_worked: list[str] = Field(default_factory=list)
    what_we_dont_know: list[str] = Field(default_factory=list)
    effort: str | None = None
    suggested_opener: str | None = None
    payload: dict[str, JSONValue] = Field(default_factory=dict)
