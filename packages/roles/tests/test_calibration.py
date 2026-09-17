from __future__ import annotations

from protege.roles.calibration import (
    DEFAULT_CALIBRATION,
    CalibrationParams,
    calibrate_confidence,
    fit_calibration,
)


def test_default_calibration_is_identity() -> None:
    assert CalibrationParams(scale=1.0, bias=0.0) == DEFAULT_CALIBRATION
    for raw in (0.0, 0.25, 0.62, 1.0):
        assert calibrate_confidence(raw) == raw


def test_calibrate_confidence_clamps_to_unit_interval() -> None:
    params = CalibrationParams(scale=2.0, bias=0.5)
    assert calibrate_confidence(0.9, params) == 1.0
    assert calibrate_confidence(-1.0, CalibrationParams(scale=1.0, bias=-2.0)) == 0.0


def test_fit_calibration_returns_default_for_fewer_than_two_pairs() -> None:
    assert fit_calibration([]) == DEFAULT_CALIBRATION
    assert fit_calibration([(0.9, True)]) == DEFAULT_CALIBRATION


def test_fit_calibration_returns_default_for_zero_variance_inputs() -> None:
    assert fit_calibration([(0.5, True), (0.5, False), (0.5, True)]) == DEFAULT_CALIBRATION


def test_fit_calibration_reduces_error_versus_identity_on_overconfident_scores() -> None:
    # A model that always says 0.95 but is right only 1/3 of the time is
    # badly overconfident -- a real fit must reduce squared calibration
    # error versus leaving the raw (identity) confidence unchanged.
    overconfident = [(0.95, False), (0.95, False), (0.95, True)]
    fitted = fit_calibration(overconfident)
    identity_error = sum((raw - (1.0 if correct else 0.0)) ** 2 for raw, correct in overconfident)
    fitted_error = sum(
        (calibrate_confidence(raw, fitted) - (1.0 if correct else 0.0)) ** 2
        for raw, correct in overconfident
    )
    assert fitted_error < identity_error
    assert fitted != DEFAULT_CALIBRATION
