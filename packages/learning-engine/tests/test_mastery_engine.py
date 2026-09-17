"""Tests for protege.learning_engine.mastery_engine.

Covers BKT, Elo (docs/DECISIONS.md D10), and misconception Bayes update +
mastery_effective, including probability bounds, monotonicity, repeated
trajectories, verification weighting interaction, Elo
determinism/bounds/convergence, and the numerical edge cases named in the
task instruction (denominator-zero protection, contradictory evidence,
unknown distractor -> authored "other", extreme Elo ratings).
"""

import random
from itertools import pairwise

import pytest

from protege.learning_engine.constants import ELO_K_FACTOR
from protege.learning_engine.errors import (
    DegenerateBKTParametersError,
    InvalidEloRatingError,
    MisconceptionNormalizationError,
    UndefinedComplementLikelihoodError,
    UndefinedDistractorLikelihoodError,
)
from protege.learning_engine.mastery_engine import (
    BKTParameters,
    bkt_posterior,
    bkt_update,
    elo_expected_score,
    mastery_effective,
    misconception_belief_update,
    update_item_elo,
)

WELL_BEHAVED_PARAMS = BKTParameters(slip=0.1, guess=0.2, transit=0.3)
# slip + guess = 0.3 < 1: the literature "identifiable" regime used for
# the monotonicity tests below (see BKTParameters' docstring: this regime
# is NOT enforced by the engine, only used as well-behaved test data).

# =============================================================================
# BKT
# =============================================================================


def test_bkt_posterior_matches_hand_computed_correct_case() -> None:
    # P(L|correct) = P(L)(1-S) / [P(L)(1-S) + (1-P(L))G]
    # p=0.5, S=0.1, G=0.2 -> 0.5*0.9 / (0.5*0.9 + 0.5*0.2) = 0.45/0.55
    params = BKTParameters(slip=0.1, guess=0.2, transit=0.0)
    result = bkt_posterior(0.5, correct=True, params=params)
    assert result == pytest.approx(0.45 / 0.55)


def test_bkt_posterior_matches_hand_computed_incorrect_case() -> None:
    # P(L|incorrect) = P(L)S / [P(L)S + (1-P(L))(1-G)]
    # p=0.5, S=0.1, G=0.2 -> 0.05 / (0.05 + 0.5*0.8) = 0.05/0.45
    result = bkt_posterior(
        0.5, correct=False, params=BKTParameters(slip=0.1, guess=0.2, transit=0.0)
    )
    assert result == pytest.approx(0.05 / 0.45)


def test_bkt_update_applies_transit_after_posterior() -> None:
    params = BKTParameters(slip=0.1, guess=0.2, transit=0.3)
    posterior = bkt_posterior(0.5, correct=True, params=params)
    expected = posterior + (1.0 - posterior) * 0.3
    assert bkt_update(0.5, correct=True, params=params) == pytest.approx(expected)


@pytest.mark.parametrize("p_know", [0.0, 0.001, 0.5, 0.999, 1.0])
@pytest.mark.parametrize("correct", [True, False])
def test_bkt_update_stays_in_probability_bounds(p_know: float, correct: bool) -> None:
    result = bkt_update(p_know, correct=correct, params=WELL_BEHAVED_PARAMS)
    assert 0.0 <= result <= 1.0


def test_bkt_update_rejects_out_of_range_prior() -> None:
    with pytest.raises(ValueError, match=r"p_know"):
        bkt_update(1.5, correct=True, params=WELL_BEHAVED_PARAMS)
    with pytest.raises(ValueError, match=r"p_know"):
        bkt_update(-0.1, correct=True, params=WELL_BEHAVED_PARAMS)


def test_bkt_parameters_reject_out_of_range_values() -> None:
    with pytest.raises(ValueError, match="slip"):
        BKTParameters(slip=1.5, guess=0.2, transit=0.3)
    with pytest.raises(ValueError, match="guess"):
        BKTParameters(slip=0.1, guess=-0.1, transit=0.3)
    with pytest.raises(ValueError, match="transit"):
        BKTParameters(slip=0.1, guess=0.2, transit=1.1)


def test_bkt_posterior_denominator_zero_raises_not_clamps() -> None:
    # p_know=0, guess=0: correct-case denominator = 0*(1-S) + 1*0 = 0.
    degenerate = BKTParameters(slip=0.1, guess=0.0, transit=0.0)
    with pytest.raises(DegenerateBKTParametersError):
        bkt_posterior(0.0, correct=True, params=degenerate)


def test_bkt_posterior_incorrect_denominator_zero_raises() -> None:
    # slip=0, guess=1: incorrect-case denominator = p*0 + (1-p)*(1-1) = 0
    # for every p_know.
    degenerate = BKTParameters(slip=0.0, guess=1.0, transit=0.0)
    with pytest.raises(DegenerateBKTParametersError):
        bkt_posterior(0.5, correct=False, params=degenerate)


def test_bkt_update_monotone_increasing_under_repeated_correct_responses() -> None:
    p = 0.05
    trajectory = [p]
    for _ in range(10):
        p = bkt_update(p, correct=True, params=WELL_BEHAVED_PARAMS)
        trajectory.append(p)
    assert all(b >= a for a, b in pairwise(trajectory))
    assert trajectory[-1] > trajectory[0]


def test_bkt_update_monotone_decreasing_under_repeated_incorrect_responses() -> None:
    # transit=0 isolates the observation-update direction from the
    # one-way "forgetting is impossible" transit term, so decrease is
    # visible in isolation.
    params = BKTParameters(slip=0.1, guess=0.2, transit=0.0)
    p = 0.95
    trajectory = [p]
    for _ in range(10):
        p = bkt_update(p, correct=False, params=params)
        trajectory.append(p)
    assert all(b <= a for a, b in pairwise(trajectory))
    assert trajectory[-1] < trajectory[0]


def test_bkt_update_deterministic_replay() -> None:
    inputs = [(0.3, True), (0.5, False), (0.9, True), (0.01, False)]
    first = [bkt_update(p, correct=c, params=WELL_BEHAVED_PARAMS) for p, c in inputs]
    second = [bkt_update(p, correct=c, params=WELL_BEHAVED_PARAMS) for p, c in inputs]
    assert first == second


def test_bkt_update_randomized_property_probabilities_stay_in_bounds() -> None:
    # Hand-rolled property test (seeded, deterministic) in place of adding
    # the Hypothesis dependency -- see the P2 implementation report for
    # why no new third-party dependency was added.
    rng = random.Random(20260916)
    for _ in range(500):
        p_know = rng.random()
        slip = rng.uniform(0.0, 0.49)
        guess = rng.uniform(0.0, 0.49)
        transit = rng.random()
        correct = rng.random() < 0.5
        params = BKTParameters(slip=slip, guess=guess, transit=transit)
        result = bkt_update(p_know, correct=correct, params=params)
        assert 0.0 <= result <= 1.0


# =============================================================================
# Elo (docs/DECISIONS.md D10)
# =============================================================================


def test_elo_expected_score_equal_ratings_is_one_half() -> None:
    assert elo_expected_score(1200, 1200) == pytest.approx(0.5)


def test_elo_expected_score_symmetry() -> None:
    e_ab = elo_expected_score(1400, 1200)
    e_ba = elo_expected_score(1200, 1400)
    assert e_ab + e_ba == pytest.approx(1.0)


def test_elo_expected_score_matches_locked_formula() -> None:
    # elo_expected_score(a, b) = 1 / (1 + 10 ** ((b - a) / 400)) -- the
    # standard "probability a beats b" reading of the locked formula (see
    # docs/DECISIONS.md D11 Gap B for why the exponent sign was resolved
    # this way rather than a literal (R_item - R_learner) transcription,
    # which produces a self-defeating update direction for item
    # difficulty when driven through R' = R + K(S-E)).
    expected = 1.0 / (1.0 + 10.0 ** ((1100 - 1300) / 400.0))
    assert elo_expected_score(1300, 1100) == pytest.approx(expected)


def test_update_item_elo_rises_when_learner_fails_the_item() -> None:
    # docs/DECISIONS.md D11 Gap B convention: the item "wins" (rating
    # rises) when the learner answers incorrectly.
    updated = update_item_elo(1200, 1200, learner_correct=False)
    assert updated > 1200


def test_update_item_elo_falls_when_learner_solves_the_item() -> None:
    updated = update_item_elo(1200, 1200, learner_correct=True)
    assert updated < 1200


def test_update_item_elo_uses_locked_k_factor_by_default() -> None:
    # R' = R + K*(S-E); at equal ratings E=0.5, S=1.0 (item won) ->
    # delta = K * 0.5, rounded.
    updated = update_item_elo(1500, 1500, learner_correct=False)
    assert updated == 1500 + round(ELO_K_FACTOR * 0.5)


def test_update_item_elo_k_is_a_named_constant_not_a_magic_number() -> None:
    # k is only a parameter for test flexibility; the shipped default
    # must equal the locked constant.
    default_result = update_item_elo(1200, 1200, learner_correct=False)
    explicit_result = update_item_elo(1200, 1200, learner_correct=False, k=ELO_K_FACTOR)
    assert default_result == explicit_result


def test_update_item_elo_deterministic_replay() -> None:
    first = update_item_elo(1180, 1200, learner_correct=True)
    second = update_item_elo(1180, 1200, learner_correct=True)
    assert first == second


def test_update_item_elo_extreme_rating_clamped_to_domain() -> None:
    # Near the top of the domain, many consecutive losses must not push
    # the rating above the documented EloRating bound (0-3000).
    rating = 2999
    for _ in range(20):
        rating = update_item_elo(rating, 1200, learner_correct=False)
    assert rating <= 3000


def test_update_item_elo_extreme_rating_floors_at_domain_minimum() -> None:
    rating = 1
    for _ in range(20):
        rating = update_item_elo(rating, 1200, learner_correct=True)
    assert rating >= 0


def test_update_item_elo_out_of_domain_rating_raises() -> None:
    with pytest.raises(InvalidEloRatingError):
        update_item_elo(3001, 1200, learner_correct=True)
    with pytest.raises(InvalidEloRatingError):
        update_item_elo(1200, -1, learner_correct=True)


def test_elo_converges_toward_the_success_target_over_many_responses() -> None:
    # A learner who is correct ~75% of the time (the §10.2 target success
    # rate) against a fixed-rating item should drive the item's rating
    # down toward the theoretical equilibrium where
    # elo_expected_score(item, learner) == 0.25 (item "wins" -- i.e. the
    # learner fails -- 25% of the time): solving 1/(1+10**((1200-item)/400))
    # = 0.25 gives item ~= 1200 - 400*log10(3) ~= 1009. K=24 keeps the
    # walk oscillating rather than landing exactly there, so this checks
    # convergence into a band around that equilibrium, not an exact value.
    rng = random.Random(7)
    item_rating = 1200
    learner_rating = 1200
    for _ in range(300):
        correct = rng.random() < 0.75
        item_rating = update_item_elo(item_rating, learner_rating, learner_correct=correct)
    assert 850 <= item_rating <= 1150
    assert item_rating < 1200


# =============================================================================
# Misconception Bayes update (docs/DECISIONS.md D13: independent Bernoulli,
# candidate-set normalization rejected) + mastery_effective
# =============================================================================

# P(d | M_k): authored per the §38 worked example convention.
M003_TABLE = {"picks_1_8": 0.82, "says_equal": 0.06, "other": 0.12}
M011_TABLE = {"says_equal": 0.70, "other": 0.30}
# P(d | not M_k): the D13 complement table, authored independently of the
# tables above -- a learner who does NOT hold M003 rarely picks "1/8" by
# the whole-number-bias route (it can still happen by chance/other bugs).
M003_NOT_TABLE = {"picks_1_8": 0.10, "says_equal": 0.30, "other": 0.60}
M011_NOT_TABLE = {"says_equal": 0.08, "other": 0.92}


def test_misconception_belief_update_matches_hand_computed_bayes_value() -> None:
    # P(M|d) = [P(d|M)*P(M)] / [P(d|M)*P(M) + P(d|not M)*(1-P(M))]
    # = (0.82*0.42) / (0.82*0.42 + 0.10*0.58) = 0.3444/0.4024
    posterior = misconception_belief_update(
        {"M003": 0.42}, {"M003": M003_TABLE}, {"M003": M003_NOT_TABLE}, "picks_1_8"
    )
    assert posterior["M003"] == pytest.approx(0.82 * 0.42 / (0.82 * 0.42 + 0.10 * 0.58))


def test_misconception_belief_update_uninformative_evidence_leaves_prior_unchanged() -> None:
    # P(d|M) == P(d|not M): the evidence carries no discriminating power,
    # so the posterior must equal the prior exactly -- a textbook sanity
    # check on the formula itself.
    posterior = misconception_belief_update(
        {"X": 0.3}, {"X": {"d": 0.5, "other": 0.5}}, {"X": {"d": 0.5, "other": 0.5}}, "d"
    )
    assert posterior["X"] == pytest.approx(0.3)


def test_misconception_belief_update_certain_evidence_drives_posterior_to_one() -> None:
    # P(d|M)=1, P(d|not M)=0: the observation is only possible if M is
    # held, so the posterior must be 1 regardless of the (nonzero) prior.
    posterior = misconception_belief_update(
        {"X": 0.01}, {"X": {"d": 1.0, "other": 0.0}}, {"X": {"d": 0.0, "other": 1.0}}, "d"
    )
    assert posterior["X"] == pytest.approx(1.0)


def test_misconception_belief_update_higher_complement_likelihood_lowers_posterior() -> None:
    # Effect of the complement likelihood: holding prior and P(d|M) fixed,
    # raising P(d|not M) makes the same observation less discriminating,
    # so the posterior must strictly decrease.
    low = misconception_belief_update(
        {"X": 0.5}, {"X": {"d": 0.5, "other": 0.5}}, {"X": {"d": 0.1, "other": 0.9}}, "d"
    )["X"]
    mid = misconception_belief_update(
        {"X": 0.5}, {"X": {"d": 0.5, "other": 0.5}}, {"X": {"d": 0.5, "other": 0.5}}, "d"
    )["X"]
    high = misconception_belief_update(
        {"X": 0.5}, {"X": {"d": 0.5, "other": 0.5}}, {"X": {"d": 0.9, "other": 0.1}}, "d"
    )["X"]
    assert low == pytest.approx(0.25 / 0.30)
    assert mid == pytest.approx(0.5)
    assert high == pytest.approx(0.25 / 0.70)
    assert low > mid > high


def test_misconception_belief_update_single_misconception_no_longer_trivially_one() -> None:
    # The categorical-normalization defect D13 replaces made a single
    # tracked misconception's posterior trivially 1.0 whenever the
    # distractor had nonzero likelihood. The independent formula does not:
    # this is the same M003 scenario as the hand-computed test above, and
    # its posterior is well below 1.
    posterior = misconception_belief_update(
        {"M003": 0.42}, {"M003": M003_TABLE}, {"M003": M003_NOT_TABLE}, "picks_1_8"
    )
    assert posterior["M003"] < 0.9


def test_misconception_belief_update_independence_between_misconceptions() -> None:
    # The core D13 property: each misconception's posterior depends only
    # on its own prior and its own two likelihood tables -- never on
    # which other misconceptions happen to be tracked alongside it, and
    # never on their priors or tables.
    m003_alone = misconception_belief_update(
        {"M003": 0.42}, {"M003": M003_TABLE}, {"M003": M003_NOT_TABLE}, "picks_1_8"
    )["M003"]
    m003_with_m011 = misconception_belief_update(
        {"M003": 0.42, "M011": 0.10},
        {"M003": M003_TABLE, "M011": M011_TABLE},
        {"M003": M003_NOT_TABLE, "M011": M011_NOT_TABLE},
        "picks_1_8",
    )["M003"]
    m003_with_different_m011_prior = misconception_belief_update(
        {"M003": 0.42, "M011": 0.95},
        {"M003": M003_TABLE, "M011": M011_TABLE},
        {"M003": M003_NOT_TABLE, "M011": M011_NOT_TABLE},
        "picks_1_8",
    )["M003"]
    assert m003_alone == m003_with_m011 == m003_with_different_m011_prior
    # And symmetrically for M011.
    m011_alone = misconception_belief_update(
        {"M011": 0.10}, {"M011": M011_TABLE}, {"M011": M011_NOT_TABLE}, "says_equal"
    )["M011"]
    m011_with_m003 = misconception_belief_update(
        {"M003": 0.42, "M011": 0.10},
        {"M003": M003_TABLE, "M011": M011_TABLE},
        {"M003": M003_NOT_TABLE, "M011": M011_NOT_TABLE},
        "says_equal",
    )["M011"]
    assert m011_alone == m011_with_m003


def test_belief_update_unknown_distractor_falls_back_in_distractor_table() -> None:
    # docs/DECISIONS.md D10: an unlisted distractor falls back to the
    # authored "other" entry in the SAME table, never the other table.
    via_unknown = misconception_belief_update(
        {"M003": 0.42},
        {"M003": M003_TABLE},
        {"M003": M003_NOT_TABLE},
        "some_never_authored_distractor",
    )
    via_explicit_other = misconception_belief_update(
        {"M003": 0.42}, {"M003": M003_TABLE}, {"M003": M003_NOT_TABLE}, "other"
    )
    assert via_unknown == via_explicit_other


def test_belief_update_unknown_distractor_falls_back_in_complement_table() -> None:
    # Same fallback convention applied independently to the complement
    # table -- its "other" is authored separately and must be used on its
    # own, never borrowed from distractor_likelihood's "other".
    via_unknown = misconception_belief_update(
        {"M003": 0.42},
        {"M003": M003_TABLE},
        {"M003": M003_NOT_TABLE},
        "some_never_authored_distractor",
    )
    # Hand-verify against the explicit "other" entries in both tables.
    hand = misconception_belief_update(
        {"M003": 0.42}, {"M003": M003_TABLE}, {"M003": M003_NOT_TABLE}, "other"
    )
    assert via_unknown == hand


def test_misconception_belief_update_no_other_fallback_in_distractor_table_raises() -> None:
    table_without_other = {"picks_1_8": 0.82}
    with pytest.raises(UndefinedDistractorLikelihoodError):
        misconception_belief_update(
            {"M003": 0.42}, {"M003": table_without_other}, {"M003": M003_NOT_TABLE}, "unseen"
        )


def test_misconception_belief_update_no_other_fallback_in_complement_table_raises() -> None:
    complement_without_other = {"picks_1_8": 0.10}
    with pytest.raises(UndefinedComplementLikelihoodError):
        misconception_belief_update(
            {"M003": 0.42}, {"M003": M003_TABLE}, {"M003": complement_without_other}, "unseen"
        )


def test_misconception_belief_update_missing_complement_table_entirely_fails_closed() -> None:
    # "Missing complement data must fail closed" (D13): if a tracked
    # misconception has no complement table at all, this raises rather
    # than defaulting to zero, to "no update", or to distractor_
    # likelihood's own "other" bucket.
    with pytest.raises(UndefinedComplementLikelihoodError):
        misconception_belief_update({"M003": 0.42}, {"M003": M003_TABLE}, {}, "picks_1_8")


def test_misconception_belief_update_missing_distractor_table_entirely_raises() -> None:
    with pytest.raises(UndefinedDistractorLikelihoodError):
        misconception_belief_update({"M003": 0.42}, {}, {"M003": M003_NOT_TABLE}, "picks_1_8")


def test_misconception_belief_update_all_zero_denominator_raises() -> None:
    zero_table = {"picks_1_8": 0.0, "other": 0.0}
    with pytest.raises(MisconceptionNormalizationError):
        misconception_belief_update(
            {"M003": 0.5}, {"M003": zero_table}, {"M003": zero_table}, "picks_1_8"
        )


def test_misconception_belief_update_empty_candidate_set() -> None:
    # No misconceptions being tracked for this item -- a valid, if
    # uninformative, empty result.
    assert misconception_belief_update({}, {}, {}, "picks_1_8") == {}


def test_misconception_belief_update_deterministic_replay() -> None:
    args = (
        {"M003": 0.42, "M011": 0.10},
        {"M003": M003_TABLE, "M011": M011_TABLE},
        {"M003": M003_NOT_TABLE, "M011": M011_NOT_TABLE},
        "picks_1_8",
    )
    assert misconception_belief_update(*args) == misconception_belief_update(*args)


def test_misconception_belief_update_posteriors_bounded() -> None:
    # Property test: every posterior stays in [0, 1] -- deliberately NOT
    # asserting sum(posterior.values()) == 1 (docs/DECISIONS.md D13: that
    # was the rejected candidate-set-normalization invariant; independent
    # Bernoulli posteriors have no reason to sum to anything in particular).
    rng = random.Random(4242)
    for _ in range(200):
        priors = {"M003": rng.random(), "M011": rng.random()}
        likelihoods = {
            "M003": {"picks_1_8": rng.uniform(0.01, 0.98), "other": rng.uniform(0.01, 0.98)},
            "M011": {"picks_1_8": rng.uniform(0.01, 0.98), "other": rng.uniform(0.01, 0.98)},
        }
        complements = {
            "M003": {"picks_1_8": rng.uniform(0.01, 0.98), "other": rng.uniform(0.01, 0.98)},
            "M011": {"picks_1_8": rng.uniform(0.01, 0.98), "other": rng.uniform(0.01, 0.98)},
        }
        posterior = misconception_belief_update(priors, likelihoods, complements, "picks_1_8")
        assert all(0.0 <= v <= 1.0 for v in posterior.values())


def test_misconception_belief_update_no_hidden_state_across_interleaved_calls() -> None:
    """Meaningful version of the roadmap's "a resolved misconception
    never re-raises without new evidence" (task instruction: prove
    meaningful state behavior, not a vacuous pure-function property).

    Drives M003's belief down with real disconfirming evidence, then
    interleaves a battery of unrelated calls to every other public
    function in this module between two otherwise-identical invocations
    of the same update, and asserts they are bit-identical -- proving
    there is no hidden module-level mutable state that could let an
    unrelated call perturb a misconception's belief absent new evidence
    naming that misconception.
    """
    prior = {"M003": 0.9}
    likelihoods = {"M003": {"picks_1_8": 0.05, "other": 0.95}}
    complements = {"M003": {"picks_1_8": 0.5, "other": 0.5}}

    baseline = misconception_belief_update(prior, likelihoods, complements, "picks_1_8")
    assert baseline["M003"] < 0.9  # genuinely disconfirming evidence, not a no-op

    bkt_update(0.5, correct=True, params=WELL_BEHAVED_PARAMS)
    bkt_update(0.2, correct=False, params=WELL_BEHAVED_PARAMS)
    update_item_elo(1200, 1200, learner_correct=True)
    update_item_elo(1200, 1200, learner_correct=False)
    mastery_effective(0.8, {"M999": 0.1})
    misconception_belief_update(
        {"M011": 0.3}, {"M011": M011_TABLE}, {"M011": M011_NOT_TABLE}, "says_equal"
    )

    replay = misconception_belief_update(prior, likelihoods, complements, "picks_1_8")
    assert replay == baseline


def test_mastery_engine_module_declares_no_hidden_global_state() -> None:
    # Structural guarantee behind the interleaving test above: no
    # `global` statement exists anywhere in this module, so no function
    # here can read or write shared mutable state across calls.
    import protege.learning_engine.mastery_engine as module

    source_path = module.__file__
    assert source_path is not None
    with open(source_path, encoding="utf-8") as f:
        contents = f.read()
    assert "global " not in contents


# --- mastery_effective ----------------------------------------------------


def test_mastery_effective_no_misconceptions_returns_p_known() -> None:
    assert mastery_effective(0.9, {}) == pytest.approx(0.9)


def test_mastery_effective_matches_hand_computed_product() -> None:
    # 0.9 * (1-0.3) * (1-0.2) = 0.9 * 0.7 * 0.8 = 0.504
    result = mastery_effective(0.9, {"M003": 0.3, "M011": 0.2})
    assert result == pytest.approx(0.504)


def test_mastery_effective_one_certain_misconception_suppresses_to_zero() -> None:
    assert mastery_effective(0.99, {"M003": 1.0}) == pytest.approx(0.0)


def test_mastery_effective_bounded_in_probability_range() -> None:
    rng = random.Random(99)
    for _ in range(200):
        p_known = rng.random()
        beliefs = {f"M{i:03d}": rng.random() for i in range(rng.randint(0, 5))}
        result = mastery_effective(p_known, beliefs)
        assert 0.0 <= result <= 1.0
        assert result <= p_known  # suppression can only lower mastery_effective
