"""Mastery estimation: BKT, Elo item difficulty, and misconception Bayes
updates (``PROTEGE_ARCHITECTURE.md`` §10.1, §10.2; docs/DECISIONS.md D10,
D11).

Three independent mechanics, per §10.1's "ten separated quantities" table
-- deliberately kept separate rather than merged into one state object,
matching how ``MasteryEstimate`` and ``MisconceptionBelief`` are two
separate persisted rows
(``packages/contracts/src/protege/contracts/learning_state.py``):

1. :func:`bkt_update` -- per-skill mastery ``P(L_s)``, Bayesian Knowledge
   Tracing.
2. :func:`update_item_elo` -- per-item difficulty (docs/DECISIONS.md D10:
   locked standard logistic Elo, K=24).
3. :func:`misconception_belief_update` -- per-misconception belief
   ``P(M_k)``, an **independent** Bayes update on distractor choice
   (docs/DECISIONS.md D10: authored ``"other"`` fallback for an unlisted
   distractor; docs/DECISIONS.md D13: the full independent-Bernoulli
   formula, superseding the candidate-set normalization D11 Gap A
   originally recorded and adversarial review rejected).

:func:`mastery_effective` combines (1) and (3) per §10.1 rule 1. It is a
*derived* quantity only -- roadmap P2: "Do not merge mastery_effective
into stored contract state if the docs describe it as derived" -- so it
is a pure function of its two inputs and is never itself persisted or
cached by this package.

No document specifies numeric defaults for BKT's slip/guess/transit
(``PROTEGE_ARCHITECTURE.md`` §10.2 gives the formula only). Like
``Misconception.distractor_likelihood``, these are authored, per-skill
content, so :class:`BKTParameters` is always a required caller-supplied
argument here, never a hardcoded default -- this package does not
silently choose a value the canonical documents do not specify, the same
principle docs/DECISIONS.md D10 states for Elo/Bayes, applied consistently
to BKT's own parameters.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from .constants import ELO_K_FACTOR, ELO_SCALE, MAX_ELO_RATING, MIN_ELO_RATING
from .errors import (
    DegenerateBKTParametersError,
    InvalidEloRatingError,
    MisconceptionNormalizationError,
    UndefinedComplementLikelihoodError,
    UndefinedDistractorLikelihoodError,
)
from .probability import validate_probability

# =============================================================================
# BKT -- per-skill mastery (ARCHITECTURE.md §10.2)
# =============================================================================


@dataclass(frozen=True)
class BKTParameters:
    """Per-skill authored BKT parameters (slip, guess, transit). Never
    defaulted by this package -- callers (content authoring, P3) supply
    these; P2 only implements the formula.

    BKT's literature-standard identifiability condition ``slip + guess <
    1`` is deliberately NOT enforced here: no PROTÉGÉ document requires
    it, and enforcing an unrequested constraint would be inventing
    validation beyond the canonical spec. Parameters outside that regime
    are still mathematically well-defined (just not intuitively
    monotone) -- see the "monotonicity" tests, which exercise a
    well-behaved parameter set and document the constraint as a property
    of *that* test data, not an engine-enforced rule.
    """

    slip: float
    guess: float
    transit: float

    def __post_init__(self) -> None:
        for name, value in (
            ("slip", self.slip),
            ("guess", self.guess),
            ("transit", self.transit),
        ):
            validate_probability(f"BKTParameters.{name}", value)


def bkt_posterior(p_know: float, *, correct: bool, params: BKTParameters) -> float:
    """``P(L|correct)`` or ``P(L|incorrect)``, per §10.2:

        P(L|correct)   = P(L)(1-S) / [P(L)(1-S) + (1-P(L))G]
        P(L|incorrect) = P(L)S     / [P(L)S     + (1-P(L))(1-G)]

    Raises :class:`DegenerateBKTParametersError` if the denominator is
    zero (e.g. ``p_know=0`` with ``guess=0`` on a correct observation) --
    never silently returns ``NaN`` or a clamped value.
    """
    validate_probability("p_know", p_know)
    if correct:
        numerator = p_know * (1.0 - params.slip)
        denominator = numerator + (1.0 - p_know) * params.guess
    else:
        numerator = p_know * params.slip
        denominator = numerator + (1.0 - p_know) * (1.0 - params.guess)
    if denominator == 0.0:
        raise DegenerateBKTParametersError(
            "BKT observation-posterior denominator is zero for "
            f"p_know={p_know}, correct={correct}, slip={params.slip}, "
            f"guess={params.guess} -- the formula is undefined for this "
            "combination. Not silently clamped; the prior or BKT "
            "parameters are misconfigured for this observation."
        )
    return numerator / denominator


def bkt_update(p_know: float, *, correct: bool, params: BKTParameters) -> float:
    """The full BKT step: ``P(L') = P(L|obs) + (1 - P(L|obs)) * T``."""
    posterior = bkt_posterior(p_know, correct=correct, params=params)
    return posterior + (1.0 - posterior) * params.transit


# =============================================================================
# Elo -- per-item difficulty (docs/DECISIONS.md D10, D11)
# =============================================================================


def _validate_elo_rating(name: str, rating: int) -> None:
    if not MIN_ELO_RATING <= rating <= MAX_ELO_RATING:
        raise InvalidEloRatingError(
            f"{name}={rating} outside the EloRating domain [{MIN_ELO_RATING}, {MAX_ELO_RATING}]"
        )


def elo_expected_score(rating_a: int, rating_b: int) -> float:
    """``E = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))`` -- the
    generic, symmetric logistic Elo expected score of ``a`` against ``b``
    (docs/DECISIONS.md D10). Purely mathematical: no item/learner
    semantics attached here (see :func:`update_item_elo` for that)."""
    _validate_elo_rating("rating_a", rating_a)
    _validate_elo_rating("rating_b", rating_b)
    exponent: float = (rating_b - rating_a) / ELO_SCALE
    power: float = 10.0**exponent
    return 1.0 / (1.0 + power)


def update_item_elo(
    item_rating: int,
    learner_rating: int,
    *,
    learner_correct: bool,
    k: int = ELO_K_FACTOR,
) -> int:
    """Update an item's Elo difficulty rating after one response.

    docs/DECISIONS.md D11 Gap B: this adopts the conventional
    item-difficulty-Elo reading -- the item "wins" (its rating rises)
    when the learner answers *incorrectly*, and "loses" (rating falls)
    when the learner answers *correctly*. No PROTÉGÉ document states this
    convention explicitly; it is the standard meaning of "item difficulty
    Elo" as a named technique, flagged in D11 for review.

    docs/DECISIONS.md D11 Gap C: ``learner_rating`` is an opaque,
    caller-supplied Elo-scale integer. This package does not define how
    it is derived from a learner's BKT ``P(L)`` -- no document specifies
    that mapping.

    ``k`` defaults to the locked :data:`~protege.learning_engine.constants.ELO_K_FACTOR`
    (docs/DECISIONS.md D10) and is only a parameter so tests can exercise
    the formula at other K values without a second hardcoded literal.

    The result is clamped to the documented ``EloRating`` domain
    ([0, 3000], matching ``protege.contracts.ids.EloRating``) -- this is
    a domain-range bound on a rating scale, tested explicitly for extreme
    inputs, not a hidden correctness hack (contrast with
    ``probability.validate_probability``, which never clamps).
    """
    _validate_elo_rating("item_rating", item_rating)
    _validate_elo_rating("learner_rating", learner_rating)
    observed_score = 0.0 if learner_correct else 1.0
    expected = elo_expected_score(item_rating, learner_rating)
    updated = item_rating + k * (observed_score - expected)
    return max(MIN_ELO_RATING, min(MAX_ELO_RATING, round(updated)))


# =============================================================================
# Misconception Bayes update + mastery_effective
# (ARCHITECTURE.md §10.1 rule 1, §10.2; docs/DECISIONS.md D13)
# =============================================================================

OTHER_DISTRACTOR_KEY = "other"
"""The authored fallback bucket key used when an observed distractor has
no specific entry in a misconception's ``distractor_likelihood`` OR
complement-likelihood table (docs/DECISIONS.md D10, D13). Each table's
``"other"`` fallback is looked up **only within that same table** -- the
two tables are conditioned on opposite events (holding vs. not holding
M_k) and are authored, and fall back, completely independently of each
other. Matches the convention already used in authored content, e.g. the
§38 worked example's ``distractor_likelihood``:
``{"picks_1_8": 0.82, "says_equal": 0.06, "other": 0.12}``."""


def _lookup_likelihood(
    misconception_code: str,
    tables: Mapping[str, Mapping[str, float]],
    observed_distractor: str,
    *,
    error_cls: type[UndefinedDistractorLikelihoodError | UndefinedComplementLikelihoodError],
    table_label: str,
) -> float:
    """Shared lookup for one misconception's likelihood table, with the
    D10 ``"other"`` fallback. Used identically for both
    ``distractor_likelihood`` (P(d|M_k)) and
    ``distractor_likelihood_if_not_misconception`` (P(d|not M_k)) --
    each call only ever touches the one table it was given, so a fallback
    or a miss in one table can never read from, or be confused with, the
    other (docs/DECISIONS.md D13: "existing 'other' entries remain local
    to their own conditional table").
    """
    table = tables.get(misconception_code)
    if table is None:
        raise error_cls(
            f"misconception {misconception_code!r} has no authored "
            f"{table_label} table at all (docs/DECISIONS.md D13: missing "
            "complement data must fail closed -- P2 does not proceed "
            "without it)."
        )
    if observed_distractor in table:
        return table[observed_distractor]
    if OTHER_DISTRACTOR_KEY in table:
        return table[OTHER_DISTRACTOR_KEY]
    raise error_cls(
        f"misconception {misconception_code!r} has no authored {table_label} "
        f"likelihood for distractor {observed_distractor!r} and no "
        f"{OTHER_DISTRACTOR_KEY!r} fallback entry in that table "
        "(docs/DECISIONS.md D10/D13: the authored table is authoritative -- "
        "P2 does not invent a value here)."
    )


def misconception_belief_update(
    priors: Mapping[str, float],
    likelihoods: Mapping[str, Mapping[str, float]],
    complement_likelihoods: Mapping[str, Mapping[str, float]],
    observed_distractor: str,
) -> dict[str, float]:
    """Independently Bayes-update every tracked misconception's belief
    given one observed (incorrect-response) distractor choice
    (docs/DECISIONS.md D13 -- the full independent-Bernoulli update,
    superseding the candidate-set normalization D11 Gap A originally
    recorded and adversarial review rejected).

    Scoped, per §10.2's "Misconception, given the child chose distractor
    d," to incorrect responses where a specific distractor was chosen --
    it is not called on correct responses (a correct response carries no
    distractor to reason from; resolving a misconception via the
    Diagnostician's own signal is P6/P7 territory, out of P2 scope).

    For each misconception ``M_k`` in ``priors``, computed **completely
    independently of every other tracked misconception** -- no
    normalization across candidates, per D13:

        P(M_k | d) = [P(d|M_k) * P(M_k)] /
                     [P(d|M_k) * P(M_k) + P(d|not M_k) * (1 - P(M_k))]

    ``likelihoods[code]`` supplies ``P(d | M_k)`` (``Misconception.
    distractor_likelihood`` -- unchanged meaning from D10).
    ``complement_likelihoods[code]`` supplies ``P(d | not M_k)``
    (``Misconception.distractor_likelihood_if_not_misconception``, D13).
    A missing table, or a missing distractor key with no ``"other"``
    fallback, in *either* table raises immediately
    (:class:`UndefinedDistractorLikelihoodError` /
    :class:`UndefinedComplementLikelihoodError`) rather than defaulting,
    inferring, or learning a value -- "missing complement data must fail
    closed" (D13).

    Returns a new mapping; inputs are never mutated (§43 principle 15:
    evidence/state is append-only, never rewritten in place). Holds no
    state between calls -- every output depends only on this call's
    arguments.
    """
    if not priors:
        # No misconceptions being tracked for this item: a valid, empty
        # result.
        return {}

    posteriors: dict[str, float] = {}
    for code, prior in priors.items():
        validate_probability(f"priors[{code}]", prior)
        p_d_given_mk = _lookup_likelihood(
            code,
            likelihoods,
            observed_distractor,
            error_cls=UndefinedDistractorLikelihoodError,
            table_label="distractor_likelihood",
        )
        validate_probability(f"likelihoods[{code}][{observed_distractor}]", p_d_given_mk)
        p_d_given_not_mk = _lookup_likelihood(
            code,
            complement_likelihoods,
            observed_distractor,
            error_cls=UndefinedComplementLikelihoodError,
            table_label="distractor_likelihood_if_not_misconception",
        )
        validate_probability(
            f"complement_likelihoods[{code}][{observed_distractor}]", p_d_given_not_mk
        )

        numerator = p_d_given_mk * prior
        denominator = numerator + p_d_given_not_mk * (1.0 - prior)
        if denominator == 0.0:
            raise MisconceptionNormalizationError(
                f"misconception {code!r}: P(d|M_k)*P(M_k) + P(d|not M_k)*(1-P(M_k)) "
                "is zero for the given prior and likelihoods -- no posterior is "
                "mathematically defined for this observation."
            )
        posteriors[code] = numerator / denominator
    return posteriors


def mastery_effective(p_known: float, misconception_beliefs: Mapping[str, float]) -> float:
    """``mastery_effective = P(L_s) * Π(1 - P(M_k))`` (§10.1 rule 1).

    Derived only -- never persisted as ``MasteryEstimate`` state (roadmap
    P2). An empty ``misconception_beliefs`` mapping returns ``p_known``
    unchanged (the empty product is 1).
    """
    validate_probability("p_known", p_known)
    product = 1.0
    for code, belief in misconception_beliefs.items():
        validate_probability(f"misconception_beliefs[{code}]", belief)
        product *= 1.0 - belief
    return p_known * product
