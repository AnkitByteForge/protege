"""Confidence calibration for the P6 Diagnostician (roadmap P6; ECE/Brier
gates, docs/DECISIONS.md D3).

The model's raw self-reported ``confidence`` is not automatically
well-calibrated (this is precisely what ECE/Brier on the golden set
measure). :class:`CalibrationParams` is a simple affine map, fit by
:func:`fit_calibration` from ``(raw_confidence, was_correct)`` pairs via
ordinary least squares -- the smallest calibration model that is still a
real, data-fit transform rather than an identity no-op, and cheap enough to
refit from a 120-item golden set with no extra dependency (no sklearn).

The default is the identity transform (``scale=1.0, bias=0.0``): a caller
that never fits calibration data gets the model's raw confidence back
unchanged, never a silently-invented adjustment.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationParams:
    """``calibrated = clip(scale * raw + bias, 0, 1)``."""

    scale: float = 1.0
    bias: float = 0.0


DEFAULT_CALIBRATION = CalibrationParams()
"""Identity transform -- the uncalibrated default."""


def calibrate_confidence(raw: float, params: CalibrationParams = DEFAULT_CALIBRATION) -> float:
    """Apply ``params`` to one raw confidence, clamped to ``[0, 1]``.

    Clamping here is a range bound on a probability-typed output (matching
    ``protege.contracts.ids.Probability``), not a hidden correctness hack --
    contrast with ``protege.learning_engine.probability.validate_probability``,
    which never clamps an *input*.
    """
    return max(0.0, min(1.0, params.scale * raw + params.bias))


def fit_calibration(pairs: Sequence[tuple[float, bool]]) -> CalibrationParams:
    """Fit ``scale``/``bias`` by ordinary least squares of
    ``outcome ~ scale * raw + bias`` over ``(raw_confidence, was_correct)``
    pairs (e.g. one golden-set evaluation pass).

    Returns :data:`DEFAULT_CALIBRATION` (the identity transform) for fewer
    than 2 pairs or for degenerate (zero-variance) inputs, rather than
    dividing by zero or fabricating a fit from insufficient data.
    """
    n = len(pairs)
    if n < 2:
        return DEFAULT_CALIBRATION

    xs = [raw for raw, _ in pairs]
    ys = [1.0 if correct else 0.0 for _, correct in pairs]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    variance = sum((x - mean_x) ** 2 for x in xs)
    if variance == 0.0:
        return DEFAULT_CALIBRATION

    scale = covariance / variance
    bias = mean_y - scale * mean_x
    return CalibrationParams(scale=scale, bias=bias)
