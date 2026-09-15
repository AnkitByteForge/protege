"""Canonical enumerations for PROTÉGÉ.

Every closed vocabulary in the system lives here exactly once so that the
Python service, the generated TypeScript types, and the content packages
cannot drift. Values are the wire values (lower snake case), matching the
source documents.

Citations (docs/):
- SessionState: DECISIONS.md D1 (canonical 21-state set).
- EventType: ARCHITECTURE.md §24 event catalogue (26 types, additive-only).
- PolicyAction: ARCHITECTURE.md §11.2 action set (13 actions).
- SproutPresentationEmotion: ARCHITECTURE.md §8.3 (belief-driven, never
  sentiment-driven). SproutScriptEmotion: §38 authored scripts. The two are
  deliberately distinct enums — authored script tone is not the rig's
  presentation state, which is driven by the Diagnostician's resolution
  belief.
"""

from enum import StrEnum

# --- Session ---------------------------------------------------------------


class SessionState(StrEnum):
    """The 21 canonical session states (DECISIONS.md D1)."""

    ARRIVAL = "ARRIVAL"
    SPROUT_TEASE = "SPROUT_TEASE"
    DIAGNOSTIC = "DIAGNOSTIC"
    DISCOVERY = "DISCOVERY"
    GUIDED_LEARNING = "GUIDED_LEARNING"
    PRACTICE = "PRACTICE"
    EXPLANATION = "EXPLANATION"
    SPROUT_SETUP = "SPROUT_SETUP"
    SPROUT_SETUP_HARD = "SPROUT_SETUP_HARD"
    TEACH_BACK = "TEACH_BACK"
    COACH_ASSIST = "COACH_ASSIST"
    REFLECTION = "REFLECTION"
    INDEPENDENT_VERIFY = "INDEPENDENT_VERIFY"
    TRANSFER = "TRANSFER"
    MASTERY_DECISION = "MASTERY_DECISION"
    REWARD = "REWARD"
    SUMMARY = "SUMMARY"
    RETRIEVAL_SCHEDULE = "RETRIEVAL_SCHEDULE"
    COMPLETE = "COMPLETE"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
    ABANDONED = "ABANDONED"


# --- Events ----------------------------------------------------------------


class EventType(StrEnum):
    """Domain event catalogue (ARCHITECTURE.md §24). Additive-only per major."""

    SESSION_STARTED = "SESSION_STARTED"
    DIAGNOSTIC_COMPLETED = "DIAGNOSTIC_COMPLETED"
    LEARNING_ITEM_PRESENTED = "LEARNING_ITEM_PRESENTED"
    ANSWER_SUBMITTED = "ANSWER_SUBMITTED"
    HINT_REQUESTED = "HINT_REQUESTED"
    EXPLANATION_CREATED = "EXPLANATION_CREATED"
    MISCONCEPTION_DETECTED = "MISCONCEPTION_DETECTED"
    MISCONCEPTION_RESOLVED = "MISCONCEPTION_RESOLVED"
    INTERVENTION_SELECTED = "INTERVENTION_SELECTED"
    SPROUT_STARTED = "SPROUT_STARTED"
    SPROUT_UTTERANCE_EMITTED = "SPROUT_UTTERANCE_EMITTED"
    TEACH_BACK_COMPLETED = "TEACH_BACK_COMPLETED"
    MASTERY_UPDATED = "MASTERY_UPDATED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    TRANSFER_PASSED = "TRANSFER_PASSED"
    TRANSFER_FAILED = "TRANSFER_FAILED"
    MASTERY_VERIFIED = "MASTERY_VERIFIED"
    REWARD_GRANTED = "REWARD_GRANTED"
    SESSION_COMPLETED = "SESSION_COMPLETED"
    PROOF_CREATED = "PROOF_CREATED"
    TUTOR_BRIEF_CREATED = "TUTOR_BRIEF_CREATED"
    RETRIEVAL_SCHEDULED = "RETRIEVAL_SCHEDULED"
    SAFETY_FLAG_RAISED = "SAFETY_FLAG_RAISED"
    ESCALATED_TO_HUMAN = "ESCALATED_TO_HUMAN"
    VALIDATOR_FAILED = "VALIDATOR_FAILED"
    FALLBACK_ENGAGED = "FALLBACK_ENGAGED"


# --- Learning domain -------------------------------------------------------


class EvidenceKind(StrEnum):
    """Provenance atom kinds (ARCHITECTURE.md §22 evidence table)."""

    RESPONSE = "response"
    TEACHING_EPISODE = "teaching_episode"
    TRANSFER = "transfer"


class MisconceptionState(StrEnum):
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"


class SessionEndReason(StrEnum):
    """Session termination reasons, in §28.1 priority order."""

    ESCALATED = "escalated"
    PRODUCTIVE_STOP = "productive_stop"
    MASTERY_VERIFIED = "mastery_verified"
    PROGRESS_MADE = "progress_made"
    TIME = "time"
    ESCALATE_TO_TUTOR = "escalate_to_tutor"
    ABANDONED = "abandoned"


class RewardKind(StrEnum):
    """Rewards, each tied to a learning event (ARCHITECTURE.md §28.2)."""

    LEAF = "leaf"
    GARDEN_AREA = "garden_area"
    NEW_WORD = "new_word"
    ACHIEVEMENT_CARD = "achievement_card"
    TIME_OF_DAY = "time_of_day"


class TurnSpeaker(StrEnum):
    """Who produced a turn (ARCHITECTURE.md §22 turns table)."""

    CHILD = "child"
    SPROUT = "sprout"
    SYSTEM = "system"


class ExplanationModality(StrEnum):
    """The four teach-back input channels (ARCHITECTURE.md §1.4)."""

    VOICE = "voice"
    TEXT = "text"
    MANIPULATIVE = "manipulative"
    EXPLANATION_CARD = "explanation_card"


class ConfidenceLabel(StrEnum):
    """Child-reported pre-answer confidence (ARCHITECTURE.md §10.1)."""

    SURE = "sure"
    THINK_SO = "think_so"
    GUESSING = "guessing"


class RepresentationType(StrEnum):
    """Item representation. Extensible; seeded from §38 + roadmap P3."""

    AREA_MODEL = "area_model"
    NUMBER_LINE = "number_line"
    SET_MODEL = "set_model"
    SYMBOLIC = "symbolic"


class ItemRole(StrEnum):
    """Where an item may be used (roadmap P3 item split)."""

    DIAGNOSTIC = "diagnostic"
    PRACTICE = "practice"
    VERIFICATION = "verification"
    TRANSFER = "transfer"


class UnderstandingSignal(StrEnum):
    """Closed-set positive signals (§38 attested; extended via P3/P6 review)."""

    INVERSE_DENOMINATOR_RELATIONSHIP = "inverse_denominator_relationship"
    PARTITIONING_LANGUAGE = "partitioning_language"


# --- Sprout ----------------------------------------------------------------


class SproutPresentationEmotion(StrEnum):
    """Rig presentation state, driven by resolution belief (§8.3).

    Sprout is never `delighted` before the misconception clears — the
    frontend maps this enum straight onto the SVG rig.
    """

    CONFUSED = "confused"
    THINKING = "thinking"
    DAWNING = "dawning"
    DELIGHTED = "delighted"


class SproutScriptEmotion(StrEnum):
    """Tone of an authored candidate utterance (§38 worked example)."""

    CONFIDENT = "confident"
    CURIOUS = "curious"
    CONFUSED = "confused"
    UNCERTAIN = "uncertain"


class SproutConfidenceShown(StrEnum):
    """Confidence Sprout displays about his (wrong) belief (addendum §7.3)."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# --- Policy ----------------------------------------------------------------


class PolicyAction(StrEnum):
    """The 13-action set (ARCHITECTURE.md §11.2)."""

    NEW_CONCEPT = "NEW_CONCEPT"
    GUIDED_EXAMPLE = "GUIDED_EXAMPLE"
    VISUALIZATION = "VISUALIZATION"
    PRACTICE = "PRACTICE"
    RETRIEVAL = "RETRIEVAL"
    TEACH_BACK = "TEACH_BACK"
    HINT = "HINT"
    ANALOGY = "ANALOGY"
    TRANSFER = "TRANSFER"
    REVIEW = "REVIEW"
    DIFFICULTY_UP = "DIFFICULTY_UP"
    DIFFICULTY_DOWN = "DIFFICULTY_DOWN"
    HUMAN_TUTOR = "HUMAN_TUTOR"


class InterventionType(StrEnum):
    """Authored intervention categories (§38; Coach never invents pedagogy)."""

    VISUALIZATION = "VISUALIZATION"
    ANALOGY = "ANALOGY"
    HINT = "HINT"
    WORKED_EXAMPLE = "WORKED_EXAMPLE"


# --- Safety ----------------------------------------------------------------


class SafetySeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# --- AI layer --------------------------------------------------------------


class PedagogicalRole(StrEnum):
    """The bounded LLM roles (§7.2). Moderation stays local (addendum §2.2)."""

    SPROUT = "SPROUT"
    DIAGNOSTICIAN = "DIAGNOSTICIAN"
    COACH = "COACH"
    REPORTER = "REPORTER"
    MODERATION = "MODERATION"
