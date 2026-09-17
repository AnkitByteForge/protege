"""Regression tests for the two P5-owned prompt fixes derived from the
real-model pilot's retained samples (root cause: sentence structure drives
reading-level rejections; naming both compared fractions in digit form
drives answer-leak rejections). Neither fix touches P2's validators --
these tests pin down the EXISTING, unmodified P2 behavior that motivated
each fix, plus the prompt content itself, so a future change cannot
silently regress either without a test failing.

No network calls: everything here is deterministic, offline analysis of
strings against the real, unmodified P2 functions and the prompt template
file on disk.
"""

from __future__ import annotations

import pytest

from protege.learning_engine.educational_validator import answer_leaked, reading_level_ok
from protege.roles.sprout import load_prompt_template

# --- Prompt content: the fix is actually present and is the default -------


def test_default_prompt_version_is_v2() -> None:
    assert load_prompt_template() == load_prompt_template("v2")


def test_v1_is_preserved_unchanged_for_reproducibility() -> None:
    v1 = load_prompt_template("v1")
    assert "{item_stem}" not in v1  # sanity: still the known v1 shape
    assert v1 != load_prompt_template("v2")


def test_v2_instructs_short_sentences_over_one_long_causal_sentence() -> None:
    template = load_prompt_template("v2")
    assert "SEVERAL SHORT sentences" in template
    assert "because" in template.lower()  # names the pattern to avoid


def test_v2_instructs_word_form_for_the_other_compared_amount() -> None:
    template = load_prompt_template("v2")
    normalized = " ".join(template.lower().split())
    assert "words only" in normalized
    assert "never write the other amount's number or fraction" in normalized


# --- Reading-level regression: sentence STRUCTURE, not vocabulary ----------
#
# Root cause (confirmed against the pilot's retained samples): every
# rejected sample was ONE long sentence chaining clauses with "because" /
# "so" / "even if"; every accepted sample was several short, exclamatory
# sentences conveying equivalent content. The Flesch-Kincaid words-per-
# sentence term is what swings the grade, not word difficulty -- these
# pairs deliberately reuse simple, common words on BOTH sides to isolate
# structure as the variable.


@pytest.mark.parametrize(
    ("long_causal", "short_exclamatory"),
    [
        (
            "I see a three and a four written on top and bottom, like two "
            "separate counts, not one piece of the rectangle.",
            "I see a three and a four! Two counts, not one!",
        ),
        (
            "I think it's still one fourth because there are four pieces "
            "and one is shaded, even if they look different.",
            "Look, four pieces! One is shaded! That's one fourth!",
        ),
        (
            "If you double both the top and the bottom, you get a "
            "different piece, so it looks bigger than before to me.",
            "You doubled the top and the bottom! That looks bigger to me!",
        ),
        (
            "I would share the counters into equal piles because the top "
            "number tells us how many groups to make, then I keep one pile.",
            "I split the piles into two groups! Keep one pile! Done!",
        ),
    ],
)
def test_short_exclamatory_phrasing_passes_where_long_causal_phrasing_fails(
    long_causal: str, short_exclamatory: str
) -> None:
    assert not reading_level_ok(long_causal), (
        f"expected the long, causally-chained sentence to fail: {long_causal!r}"
    )
    assert reading_level_ok(short_exclamatory), (
        f"expected the short, exclamatory rephrasing to pass: {short_exclamatory!r}"
    )


# --- Answer-leakage regression: naming BOTH compared fractions digitally --
#
# Root cause (confirmed against the pilot's retained M003/M005 samples,
# without exception): every leaking utterance wrote BOTH compared
# fractions in digit/slash form while justifying a comparison. Since the
# correct answer is withheld from Sprout's context entirely (critical
# rule), Sprout cannot know which of the two named amounts is "the
# answer" -- the generalizable fix is content-blind: state your own answer
# digitally, refer to the other amount in words only. These tests use
# DIFFERENT fraction pairs and DIFFERENT wording than any of the pilot's
# 14 observed strings, to prove the pattern -- not the specific strings --
# is what's being guarded against.


@pytest.mark.parametrize(
    ("utterance", "correct_answer"),
    [
        # M003-shape (1/8 vs 1/4), wording never seen in the pilot.
        ("My answer feels right because 1/8 has a bigger bottom number than 1/4.", "1/4"),
        # M005-shape (5/6 vs 1/2), wording never seen in the pilot.
        (
            "Since six pieces is a bigger number than two pieces, "
            "5/6 has to be the smaller amount here.",
            "5/6",
        ),
        # A wholly different pair (2/3 vs 1/5), never observed in any run.
        ("2/3 looks small next to 1/5 because three is a small number.", "1/5"),
    ],
)
def test_naming_both_compared_fractions_digitally_leaks_regardless_of_wording(
    utterance: str, correct_answer: str
) -> None:
    assert answer_leaked(utterance, correct_answer)


@pytest.mark.parametrize(
    ("utterance", "correct_answer"),
    [
        # Same misconceptions/pairs as above, but following the v2 rule:
        # own answer by digits, the OTHER amount in words only.
        ("I think 1/8 is bigger! The other one just has a smaller bottom number.", "1/4"),
        ("Six is bigger than two, so five-sixths must be the smaller one!", "5/6"),
        ("2/3 looks small next to the other fraction because three is a small number.", "1/5"),
    ],
)
def test_naming_only_your_own_answer_digitally_does_not_leak(
    utterance: str, correct_answer: str
) -> None:
    assert not answer_leaked(utterance, correct_answer)
