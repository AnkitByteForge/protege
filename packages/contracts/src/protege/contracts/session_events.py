"""``POST /v1/sessions/{id}/events`` request contracts (roadmap P10;
ARCHITECTURE.md §23/§24: "One polymorphic event: ``answer_submitted``,
``explanation_given``, ``manipulative_moved``, ``hint_requested``").

Distinct from :class:`~.enums.EventType` (the persisted domain-event
catalogue): that is what the server *records happened*; this is the shape
of what the client *reports*. The server decides which (if any)
``EventType`` row(s) a given request produces -- the client never supplies
one directly, and cannot request a specific state transition (roadmap P10
rule: "the browser never decides the next learning state").
"""

from typing import Annotated, Literal

from pydantic import Field

from .base import ProtegeBaseModel
from .ids import ItemId
from .session import Explanation, ManipulativeAction


class AnswerSubmittedEvent(ProtegeBaseModel):
    """The child answered the currently-presented item. ``response_text``
    is validated server-side (``protege.learning_engine.validate_answer``)
    against that item's authored correct answer -- never trusted, and the
    correct answer itself is never present in this or any request payload."""

    type: Literal["answer_submitted"] = "answer_submitted"
    item_id: ItemId
    response_text: str = Field(min_length=1, max_length=200)


class ExplanationGivenEvent(ProtegeBaseModel):
    """A teach-back / readiness / reflection explanation, in any of the
    four authored modalities (see :data:`~.session.Explanation`)."""

    type: Literal["explanation_given"] = "explanation_given"
    explanation: Explanation


class ManipulativeMovedEvent(ProtegeBaseModel):
    """A structured manipulative interaction trace (roadmap P13: "equal in
    standing to speech" as diagnostic evidence)."""

    type: Literal["manipulative_moved"] = "manipulative_moved"
    trace: list[ManipulativeAction] = Field(min_length=1)


class HintRequestedEvent(ProtegeBaseModel):
    """The child asked for the available hint (valid only while the server
    considers one available -- i.e. session state ``COACH_ASSIST``)."""

    type: Literal["hint_requested"] = "hint_requested"


SessionEventRequest = Annotated[
    AnswerSubmittedEvent | ExplanationGivenEvent | ManipulativeMovedEvent | HintRequestedEvent,
    Field(discriminator="type"),
]
