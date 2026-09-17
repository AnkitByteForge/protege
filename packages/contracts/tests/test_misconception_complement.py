"""P(d | not M_k) — the complement likelihood required to normalize the
§10.2 Bayes update (D13, locked on ``feature/p2-learning``'s
``docs/DECISIONS.md``).

Covers the three-part backward-compatible strategy:
- the bare contract stays nullable, so the §38 ``M003`` fixture keeps
  validating verbatim (P1's exit criterion);
- ``Misconception.validate_authored`` is the strict entry point new (P3) v1
  content must go through;
- ``Misconception.require_complement_likelihood`` is the strict runtime
  accessor P2's Bayes update must go through, raising
  ``MissingComplementLikelihoodError`` instead of silently proceeding.
"""

import builders
import pytest
from pydantic import ValidationError

from protege.contracts import Misconception, MissingComplementLikelihoodError

LEGACY_M003 = {
    "code": "M003",
    "title": "Larger denominator means larger fraction",
    "cognitive_origin": "Whole-number bias transferred to the denominator.",
    "distractor_likelihood": {"picks_1_8": 0.82, "says_equal": 0.06, "other": 0.12},
    "prevalence_prior": 0.42,
}


def test_legacy_misconception_validates_without_complement_likelihood() -> None:
    """§38's M003 predates this field; the bare contract must still accept it."""
    model = Misconception.model_validate(LEGACY_M003)
    assert model.distractor_likelihood_if_not_misconception is None


def test_complement_likelihood_is_independent_of_distractor_likelihood_other() -> None:
    """The existing ``distractor_likelihood["other"]`` must never be reused as,
    or conflated with, the complement distribution."""
    model = builders.build_misconception_with_complement()
    assert model.distractor_likelihood["other"] == 0.12
    assert model.distractor_likelihood_if_not_misconception is not None
    assert model.distractor_likelihood_if_not_misconception["other"] == 0.75
    complement = model.distractor_likelihood_if_not_misconception
    assert model.distractor_likelihood["other"] != complement["other"]


def test_validate_authored_accepts_content_with_complement_likelihood() -> None:
    authored = builders.build_misconception_with_complement().model_dump()
    model = Misconception.validate_authored(authored)
    assert model.distractor_likelihood_if_not_misconception is not None


def test_validate_authored_rejects_legacy_shaped_content() -> None:
    """New v1 content must supply the complement — the §38 exemption applies
    only to the bare ``model_validate`` path, not to authoring."""
    with pytest.raises(ValueError, match="distractor_likelihood_if_not_misconception"):
        Misconception.validate_authored(LEGACY_M003)


def test_bare_model_validate_does_not_enforce_authoring_strictness() -> None:
    """``model_validate`` on its own must never raise for a missing
    complement likelihood — that would break the §38 exit criterion. Only
    ``validate_authored`` enforces the v1 requirement."""
    Misconception.model_validate(LEGACY_M003)  # must not raise


def test_require_complement_likelihood_returns_dict_when_present() -> None:
    model = builders.build_misconception_with_complement()
    assert model.require_complement_likelihood() == model.distractor_likelihood_if_not_misconception


def test_require_complement_likelihood_raises_specific_error_when_absent() -> None:
    """P2's runtime Bayes update must fail loudly, not silently proceed,
    when a misconception has no authored complement likelihood."""
    model = Misconception.model_validate(LEGACY_M003)
    with pytest.raises(MissingComplementLikelihoodError) as excinfo:
        model.require_complement_likelihood()
    assert excinfo.value.misconception_code == "M003"


def test_missing_complement_likelihood_error_is_a_value_error() -> None:
    """Consistent with every other contract-level validation failure
    (ValidationError subclasses ValueError too), so callers can catch broadly
    or specifically."""
    assert issubclass(MissingComplementLikelihoodError, ValueError)


def test_validation_error_still_raised_for_malformed_complement_likelihood() -> None:
    """Ordinary field-level constraints (probability bounds) still apply to
    the new field via the normal ``model_validate`` path."""
    bad = {**LEGACY_M003, "distractor_likelihood_if_not_misconception": {"picks_1_8": 1.5}}
    with pytest.raises(ValidationError):
        Misconception.model_validate(bad)
