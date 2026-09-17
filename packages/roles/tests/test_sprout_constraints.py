from __future__ import annotations

import pytest

from protege.authoring.loader import ContentPack
from protege.contracts import Misconception
from protege.roles.errors import NoCandidatePoolError
from protege.roles.sprout import compile_constraints, select_candidate_pool


def _misconception(content_pack: ContentPack, code: str) -> Misconception:
    return next(m for m in content_pack.misconceptions if m.code == code)


def test_compile_constraints_carries_forbidden_phrases_and_never_the_answer(
    content_pack: ContentPack,
) -> None:
    m003 = _misconception(content_pack, "M003")
    constraints = compile_constraints(m003)
    assert constraints.misconception_id == "M003"
    assert constraints.max_words == 30
    assert set(constraints.forbidden_phrases) == set(m003.sprout_forbidden)
    # The compiled constraints object has no field that could carry a
    # correct answer at all -- there is no such attribute to check for.
    assert not hasattr(constraints, "correct_answer")


def test_select_candidate_pool_returns_only_matching_scripts(content_pack: ContentPack) -> None:
    pool = select_candidate_pool(content_pack.sprout_scripts, "M003")
    assert len(pool) == 6
    assert all(script.misconception_code == "M003" for script in pool)


def test_select_candidate_pool_every_misconception_has_at_least_six_candidates(
    content_pack: ContentPack,
) -> None:
    """Roadmap P3: '6 candidate Sprout utterances per misconception.'"""
    for misconception in content_pack.misconceptions:
        pool = select_candidate_pool(content_pack.sprout_scripts, misconception.code)
        assert len(pool) >= 6


def test_select_candidate_pool_raises_for_an_unknown_misconception(
    content_pack: ContentPack,
) -> None:
    with pytest.raises(NoCandidatePoolError):
        select_candidate_pool(content_pack.sprout_scripts, "M999")
