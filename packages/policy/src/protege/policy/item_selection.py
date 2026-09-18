"""Elo item selection targeting ~0.75 predicted success (roadmap P11 §7;
ARCHITECTURE.md §11.2: "item selection by Elo match targeting ~0.75
success").

Reuses P2's real Elo machinery (``protege.learning_engine.mastery_engine.
elo_expected_score``) -- never reimplemented here (roadmap P11 §7: "Do not
reimplement Elo. Reuse the existing deterministic functions/interfaces.").
This module only inverts that one function to find the item rating a given
learner rating implies a 0.75 success chance against, and picks whichever
authored candidate is closest to it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from protege.contracts import EloRating, LearningItem
from protege.learning_engine.constants import ELO_SCALE, MAX_ELO_RATING, MIN_ELO_RATING
from protege.learning_engine.errors import InvalidEloRatingError
from protege.learning_engine.mastery_engine import elo_expected_score

from .constants import ELO_TARGET_SUCCESS_PROBABILITY

__all__ = ["ItemSelectionResult", "select_item_by_target_elo", "target_item_rating"]


def target_item_rating(
    learner_rating: EloRating, *, target_success: float = ELO_TARGET_SUCCESS_PROBABILITY
) -> int:
    """The item Elo rating at which this learner's predicted success is
    exactly ``target_success``, inverting P2's own logistic Elo formula
    (docs/DECISIONS.md D10):

        target_success = elo_expected_score(learner_rating, item_rating)
                        = 1 / (1 + 10 ** ((item_rating - learner_rating) / ELO_SCALE))

        =>  item_rating = learner_rating + ELO_SCALE * log10(1/target_success - 1)

    For ``target_success = 0.75`` this is ``learner_rating - ~191``: the
    served item is *easier* than the learner, exactly as "targeting 0.75
    success" (rather than a 0.50 even match) requires.

    Clamped to the same ``[MIN_ELO_RATING, MAX_ELO_RATING]`` domain
    :func:`~protege.learning_engine.mastery_engine.update_item_elo` clamps
    to (docs/DECISIONS.md D10; ``protege.contracts.ids.EloRating``) -- a
    learner far outside the rating scale still gets a well-defined, in-
    domain target rather than an unusable negative or >3000 result.
    """
    if not 0.0 < target_success < 1.0:
        raise ValueError(f"target_success must be in (0, 1), got {target_success}")
    if not MIN_ELO_RATING <= learner_rating <= MAX_ELO_RATING:
        raise InvalidEloRatingError(
            f"learner_rating={learner_rating} outside the EloRating domain "
            f"[{MIN_ELO_RATING}, {MAX_ELO_RATING}]"
        )
    offset = ELO_SCALE * math.log10(1.0 / target_success - 1.0)
    raw = learner_rating + offset
    # int(...): packages/learning-engine has no py.typed marker (see
    # pyproject.toml's mypy overrides), so MIN_ELO_RATING/MAX_ELO_RATING
    # type-check as Any here -- an explicit cast keeps this function's own
    # return type honestly `int` rather than re-exporting that Any.
    return int(max(MIN_ELO_RATING, min(MAX_ELO_RATING, round(raw))))


@dataclass(frozen=True)
class ItemSelectionResult:
    item: LearningItem
    target_rating: int
    predicted_success: float


def select_item_by_target_elo(
    candidates: Sequence[LearningItem],
    learner_rating: EloRating,
    *,
    target_success: float = ELO_TARGET_SUCCESS_PROBABILITY,
) -> ItemSelectionResult:
    """Pick whichever ``candidates`` item's Elo rating is closest to
    :func:`target_item_rating`'s answer for this learner. Candidates with
    ``elo is None`` (not yet Elo-calibrated, docs/DECISIONS.md D10: "Elo,
    updated online -- no cold-start item calibration needed") are skipped
    rather than treated as a rating of 0, which would make an uncalibrated
    item look artificially "easy" and always win the selection.

    Deterministic: ties (two candidates equidistant from the target) break
    on list order, the first taken -- ``min`` is stable, matching Python's
    documented sort/min stability.
    """
    scored = [item for item in candidates if item.elo is not None]
    if not scored:
        raise ValueError("no candidate item has an Elo rating -- cannot target a success rate")
    target = target_item_rating(learner_rating, target_success=target_success)
    chosen = min(scored, key=lambda item: abs((item.elo or 0) - target))
    predicted_success = elo_expected_score(learner_rating, chosen.elo or 0)
    return ItemSelectionResult(
        item=chosen, target_rating=target, predicted_success=predicted_success
    )
