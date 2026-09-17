"""The P8 thin-thread scenario: S004 + M003, six hardcoded items.

Roadmap P8 scope, verbatim: "One skill (S004), one misconception (M003),
6 hardcoded items, terminal I/O." This module resolves those six items and
the scripted child behaviour through the *existing* P3 content pack loader
(``protege.authoring.loader.load_content_pack`` -- never a duplicated
definition of the misconception or its items, per the task instruction).

Item selection follows the exact set architecture's worked example (§38)
and the content pack's own ``worked_examples/M003.json`` fixture already
use for S004/M003: the diagnostic item (``i_0132``), the three unaided
verification items (``i_0148``, ``i_0155``, ``i_0161``), and the transfer
item (``i_0201``) -- five items. Roadmap P8 asks for six; the sixth is one
PRACTICE-role item (``i_2011``) already authored for S004/M003 in
``content/math/fractions/v1/items/practice.json`` but not cited by the
worked-example fixture, used here to drive one genuine PRACTICE-state
response before the (real, golden-trace-tested) PRACTICE timeout exit --
see ``engine.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

from protege.authoring.loader import ContentPack
from protege.contracts import LearningItem, Misconception, Skill, TransferItem
from protege.learning_engine import BKTParameters

SKILL_CODE = "S004_compare_unit_fractions"
MISCONCEPTION_CODE = "M003"

DIAGNOSTIC_ITEM_ID = "i_0132"
PRACTICE_ITEM_ID = "i_2011"
VERIFY_ITEM_IDS: tuple[str, str, str] = ("i_0148", "i_0155", "i_0161")
TRANSFER_ITEM_ID = "i_0201"

BKT_PARAMETERS = BKTParameters(slip=0.15, guess=0.35, transit=0.10)
"""Thin-thread-local authored BKT parameters for S004 (informational, in
the docs/DECISIONS.md D11 sense): no canonical document fixes slip/guess/
transit numerically for any specific skill (``mastery_engine.py``'s own
docstring: "No document specifies numeric defaults for BKT's slip/guess/
transit... always a required caller-supplied argument"). These three
values are chosen so the first (correct) response moves
``INITIAL_P_KNOWN`` from 0.20 to 0.44 -- reproducing ARCHITECTURE.md §42's
own illustrative "P(knows) 0.20 -> 0.44" line exactly via the real
:func:`~protege.learning_engine.bkt_update` formula, not a hardcoded
number. A future content-authoring phase (P3/P9) should ratify permanent
per-skill BKT parameters; this is a P8 placeholder, not a claim that these
are the "correct" values for S004."""

INITIAL_P_KNOWN = 0.20
"""ARCHITECTURE.md §42's starting point."""

TEACHING_EXPLANATION_TEXT = "the bottom number means how many pieces"
"""§42's EXPLANATION-state capture, verbatim."""

RESOLVING_EXPLANATION_TEXT = (
    "no because the bottom is how many pieces you cut it so more pieces are littler"
)
"""The child's teach-back correction -- verbatim from the authored content
pack fixture (``content/math/fractions/v1/worked_examples/M003.json``
``learner_evidence.explanation``), not invented for this scenario. Its
``more pieces are littler`` substring is the real, authored
``evidence_span`` the Diagnostician's resolved label cites."""

RESOLUTION_EVIDENCE_SPAN = "more pieces are littler"

STUCK_EXPLANATION_TEXT = "um... I don't know, maybe eighths?"
"""A vague, non-resolving turn-back for the recovery scenario -- shows no
partitioning language and no clear stance, so the Diagnostician correctly
finds no resolution signal."""


@dataclass(frozen=True)
class ThinThreadItems:
    """The six hardcoded items, resolved from the real content pack."""

    diagnostic: LearningItem
    practice: LearningItem
    verify: tuple[LearningItem, LearningItem, LearningItem]
    transfer: TransferItem

    def all_items(self) -> tuple[LearningItem | TransferItem, ...]:
        return (self.diagnostic, self.practice, *self.verify, self.transfer)


def _find_learning_item(items: list[LearningItem], item_id: str) -> LearningItem:
    for item in items:
        if item.item_id == item_id:
            return item
    raise KeyError(f"item {item_id!r} not found in content pack")


def _find_transfer_item(items: list[TransferItem], item_id: str) -> TransferItem:
    for item in items:
        if item.item_id == item_id:
            return item
    raise KeyError(f"transfer item {item_id!r} not found in content pack")


def resolve_items(content: ContentPack) -> ThinThreadItems:
    """Resolve the six hardcoded item IDs against a loaded content pack."""
    diagnostic = _find_learning_item(content.diagnostic_items, DIAGNOSTIC_ITEM_ID)
    practice = _find_learning_item(content.practice_items, PRACTICE_ITEM_ID)
    verify = tuple(
        _find_learning_item(content.practice_items, item_id) for item_id in VERIFY_ITEM_IDS
    )
    transfer = _find_transfer_item(content.transfer_items, TRANSFER_ITEM_ID)
    assert len(verify) == 3
    return ThinThreadItems(
        diagnostic=diagnostic, practice=practice, verify=verify, transfer=transfer
    )


def resolve_skill(content: ContentPack) -> Skill:
    for skill in content.skills:
        if skill.code == SKILL_CODE:
            return skill
    raise KeyError(f"skill {SKILL_CODE!r} not found in content pack")


def resolve_misconception(content: ContentPack) -> Misconception:
    for misconception in content.misconceptions:
        if misconception.code == MISCONCEPTION_CODE:
            return misconception
    raise KeyError(f"misconception {MISCONCEPTION_CODE!r} not found in content pack")


_UNIT_SUFFIXES = (" piece", " pieces", " length", " lengths")


def numeric_answer_text(value: str) -> str:
    """Strip a trailing authored unit word (e.g. ``"1/4 piece"`` ->
    ``"1/4"``) so the real
    :func:`~protege.learning_engine.answer_validator.validate_answer` can
    parse it as an exact fraction.

    This is call-site text normalization only -- it never touches the
    validator's own arithmetic (task instruction: "Use the existing P2
    learning engine exactly"). One of the six authored items
    (``i_0155``: ``"1/4 piece"``) carries a unit-word suffix the
    validator's fraction grammar does not model; applied uniformly to
    every item's answer text (a no-op for the other five), rather than as
    a special case keyed to one item id.
    """
    text = value.strip()
    for suffix in _UNIT_SUFFIXES:
        if text.endswith(suffix):
            return text[: -len(suffix)]
    return text


@dataclass(frozen=True)
class TeachBackTurnScript:
    """One scripted teach-back turn: what the child says, and whether this
    turn is scripted to resolve the misconception (for building the
    matching ``FakeProvider`` script in ``--provider fake`` mode; under
    ``--provider nvidia`` only ``child_text`` is used and resolution is
    whatever the real Diagnostician actually returns)."""

    child_text: str
    resolves: bool


@dataclass(frozen=True)
class Scenario:
    """One complete scripted P8 run.

    ``teach_back_turns`` is a script of *intended* turns; the engine stops
    early if a turn actually resolves (a real Diagnostician, or an NVIDIA
    call, may resolve earlier or later than scripted -- the engine follows
    whatever the real component says, per the FSM's own guard logic, never
    the script's ``resolves`` hint).
    """

    name: str
    teach_back_turns: tuple[TeachBackTurnScript, ...]
    diagnostic_correct: bool = True
    practice_correct: bool = True
    verify_correct: tuple[bool, bool, bool] = (True, True, True)
    transfer_correct: bool = True


def happy_path_scenario() -> Scenario:
    """Reproduces ARCHITECTURE.md §42's single-exchange teach-back: Sprout
    speaks once, the child's real correction resolves M003 immediately."""
    return Scenario(
        name="happy_path",
        teach_back_turns=(TeachBackTurnScript(RESOLVING_EXPLANATION_TEXT, resolves=True),),
    )


def recovery_scenario() -> Scenario:
    """Misconception-recovery path (P8 testing requirement #2): two
    non-resolving turns push ``stuck_turns`` to the COACH_ASSIST threshold
    (roadmap P7: 2 stuck turns), a deterministic authored hint is
    delivered, and the third turn resolves M003 -- exercising the real
    :func:`~protege.roles.beliefs.apply_diagnosis_to_beliefs` Bayes update
    on the two genuinely UNRESOLVED turns.
    """
    return Scenario(
        name="recovery",
        teach_back_turns=(
            TeachBackTurnScript(STUCK_EXPLANATION_TEXT, resolves=False),
            TeachBackTurnScript(STUCK_EXPLANATION_TEXT, resolves=False),
            TeachBackTurnScript(RESOLVING_EXPLANATION_TEXT, resolves=True),
        ),
    )
