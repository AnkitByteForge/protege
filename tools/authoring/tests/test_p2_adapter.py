"""The P2 reading-level boundary: P3 never implements its own formula.

Reading-level validation is P2's responsibility (``packages/learning-engine``
``educational_validator``). This package only defines the narrow interface it
expects and a null default that abstains — see ``p2_adapter.py``.
"""

from __future__ import annotations

from protege.authoring.p2_adapter import (
    READING_LEVEL_STATUS_PENDING,
    NullReadingLevelPort,
    ReadingLevelPort,
)


def test_null_port_always_abstains() -> None:
    port = NullReadingLevelPort()
    assert port.check("any text at all", 3.5) is None
    assert port.check("", 3.5) is None


def test_null_port_satisfies_the_protocol() -> None:
    assert isinstance(NullReadingLevelPort(), ReadingLevelPort)


def test_pending_status_constant_is_descriptive() -> None:
    assert "P2" in READING_LEVEL_STATUS_PENDING
