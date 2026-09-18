"""Round-trips ``protege.session.machine.SessionContext`` through the JSONB
checkpoint at ``sessions.context_snapshot`` (see that column's docstring).

A plain field-by-field mapping, not ``dataclasses.asdict``/a generic
(de)serializer: ``SessionContext`` is a small, closed, roadmap-owned
dataclass (``packages/session-fsm``), and an explicit mapping here fails
loudly (``KeyError``/``TypeError``) on a shape mismatch instead of silently
dropping or misreading a field if that dataclass ever changes shape.
"""

from __future__ import annotations

from collections.abc import Mapping

from protege.session.machine import S, SessionContext

JSONDict = dict[str, object]

_SCALAR_FIELDS: tuple[str, ...] = (
    "p_known",
    "resolution_belief",
    "loops",
    "consecutive_errors",
    "items_attempted",
    "teach_back_turns",
    "misconception_resolved",
    "stuck_turns",
    "verify_items_attempted",
    "verify_correct_count",
    "transfer_attempted",
    "mastery_delta",
)


def _as_str(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"expected a str, got {value!r}")
    return value


def _as_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise TypeError(f"expected an int-like value, got {value!r}")
    return int(value)


def _as_float(value: object) -> float:
    if not isinstance(value, int | float | str):
        raise TypeError(f"expected a float-like value, got {value!r}")
    return float(value)


def _as_bool(value: object) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"expected a bool, got {value!r}")
    return value


def context_to_dict(context: SessionContext) -> JSONDict:
    data: JSONDict = {"current": str(context.current)}
    for field_name in _SCALAR_FIELDS:
        data[field_name] = getattr(context, field_name)
    return data


def context_from_dict(data: Mapping[str, object]) -> SessionContext:
    return SessionContext(
        current=S(_as_str(data["current"])),
        p_known=_as_float(data["p_known"]),
        resolution_belief=_as_float(data["resolution_belief"]),
        loops=_as_int(data["loops"]),
        consecutive_errors=_as_int(data["consecutive_errors"]),
        items_attempted=_as_int(data["items_attempted"]),
        teach_back_turns=_as_int(data["teach_back_turns"]),
        misconception_resolved=_as_bool(data["misconception_resolved"]),
        stuck_turns=_as_int(data["stuck_turns"]),
        verify_items_attempted=_as_int(data["verify_items_attempted"]),
        verify_correct_count=_as_int(data["verify_correct_count"]),
        transfer_attempted=_as_bool(data["transfer_attempted"]),
        mastery_delta=_as_float(data["mastery_delta"]),
    )
