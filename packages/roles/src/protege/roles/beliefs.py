"""Wires a Diagnostician result into the P2 misconception Bayes update
(roadmap P6: "Diagnostician feeds misconception beliefs via the P2 learning
engine").

:func:`apply_diagnosis_to_beliefs` is a **pure function**: it returns an
updated ``{misconception_code: p_holds}`` mapping and persists nothing.
Roadmap P6: "Diagnostician NEVER writes mastery directly" -- applying the
returned mapping to a learner's actual persisted ``misconception_beliefs``
is a future orchestrator's (P7/P9's) job, out of P6's scope, which has no
persistence layer to write to yet.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from protege.contracts import (
    DiagnosisResult,
    Misconception,
    MisconceptionState,
    MissingComplementLikelihoodError,
)
from protege.learning_engine import misconception_belief_update

from .constants import OTHER_OBSERVED_BEHAVIOR


def apply_diagnosis_to_beliefs(
    diagnosis: DiagnosisResult,
    *,
    misconception_set: Sequence[Misconception],
    priors: Mapping[str, float],
) -> dict[str, float]:
    """Bayes-update ``priors`` for every UNRESOLVED label in ``diagnosis``.

    Each update calls ``protege.learning_engine.mastery_engine.
    misconception_belief_update`` -- the real P2 API (docs/DECISIONS.md
    D10, D13) -- independently per misconception (one single-candidate call
    per diagnosed code), matching D13's independent-Bernoulli model: an
    update to one code's belief never touches another tracked code's prior.

    The Diagnostician's evidence is not decomposed into one of a
    misconception's specific authored ``distractor_likelihood`` behavior
    keys (that decomposition is what the rule-based fallback's authored
    ``Distractor.maps_to``/``likelihood`` already represents, from a
    different authored source); this uses the ``"other"`` key uniformly,
    which is precisely docs/DECISIONS.md D10's documented convention for
    "an observed distractor [with] no specific entry" in the table.

    A ``resolved`` label, an abstained diagnosis, a code absent from
    ``priors``, or a misconception with no authored
    ``distractor_likelihood_if_not_misconception`` (D13: legacy content
    predating that field) leaves that code's prior untouched in the
    returned mapping -- only genuinely new UNRESOLVED evidence, with the
    complement likelihood D13 requires, moves a belief.
    """
    updated = dict(priors)
    if diagnosis.abstained:
        return updated

    misconceptions_by_code = {m.code: m for m in misconception_set}
    for label in diagnosis.labels:
        if label.state != MisconceptionState.UNRESOLVED:
            continue
        code = label.misconception_code
        if code not in updated:
            continue
        misconception = misconceptions_by_code.get(code)
        if misconception is None:
            continue
        try:
            complement = misconception.require_complement_likelihood()
        except MissingComplementLikelihoodError:
            continue
        posterior = misconception_belief_update(
            {code: updated[code]},
            {code: misconception.distractor_likelihood},
            {code: complement},
            OTHER_OBSERVED_BEHAVIOR,
        )
        updated.update(posterior)
    return updated
