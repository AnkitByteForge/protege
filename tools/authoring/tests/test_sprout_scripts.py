"""Sprout scripts satisfy the §7.3 word cap and the §8.4/§17 leak constraint.

The 30-word cap is enforced by the P1 ``SproutScript`` contract itself at
load time (a violation raises during ``load_content_pack``); the tests here
additionally assert it explicitly against the real content so a future
authoring change that raises the cap in ``packages/contracts`` cannot
silently let an over-long script through unnoticed by this suite.
"""

from __future__ import annotations

import pytest

from protege.authoring.loader import load_content_pack
from protege.authoring.validators import _check_answer_leakage, _check_sprout_constraints


@pytest.fixture(scope="module")
def pack():
    return load_content_pack()


def test_every_sprout_script_is_at_most_thirty_words(pack) -> None:
    for script in pack.sprout_scripts:
        assert len(script.utterance.split()) <= 30, script.script_id


def test_every_sprout_script_maps_to_a_misconception(pack) -> None:
    for script in pack.sprout_scripts:
        assert script.misconception_code is not None, script.script_id


def test_six_scripts_per_misconception(pack) -> None:
    from collections import Counter

    counts = Counter(s.misconception_code for s in pack.sprout_scripts)
    for misconception in pack.misconceptions:
        assert counts[misconception.code] == 6, misconception.code


def test_no_answer_leakage_in_real_content(pack) -> None:
    assert _check_answer_leakage(pack) == []


def test_no_forbidden_vocabulary_in_real_content(pack) -> None:
    assert _check_sprout_constraints(pack) == []


def test_every_misconception_has_a_nonempty_sprout_forbidden_list(pack) -> None:
    for misconception in pack.misconceptions:
        assert misconception.sprout_forbidden, misconception.code
