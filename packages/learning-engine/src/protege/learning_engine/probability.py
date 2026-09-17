"""Shared probability-domain validation.

A plain runtime guard shared by ``mastery_engine.py`` and
``threshold_service.py`` -- not a ``protege.contracts`` dependency
(docs/DECISIONS.md D6/D8; this package does not couple to Pydantic).
"""


def validate_probability(name: str, value: float) -> float:
    """Raise ``ValueError`` if ``value`` is outside [0, 1]; otherwise
    return it unchanged (never clamps -- an out-of-range probability is a
    caller bug, not a value to silently correct)."""
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value}")
    return value
