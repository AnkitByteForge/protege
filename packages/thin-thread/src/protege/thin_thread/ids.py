"""Deterministic identifier allocation for the P8 thin thread.

Roadmap P8 has no persistence layer (P9's job) and no event bus, so this
module is the thin thread's own tiny stand-in for "an event/evidence id got
assigned somewhere real": a plain, in-memory, monotonically increasing
counter per prefix. No randomness (no ``uuid4``) -- deterministic replay
(the P8 testing requirement "deterministic replay produces the same
state/event sequence") depends on two runs of the same scripted
:class:`~protege.thin_thread.scenario.Scenario` producing byte-identical
IDs, not just the same FSM state sequence.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IdAllocator:
    """Allocates ``"<prefix>_%03d"`` ids, one counter per prefix.

    A fresh instance always starts every counter at 1 -- two
    :class:`IdAllocator` instances driven through the same call sequence
    produce identical ids, which is exactly what the replay test checks.
    """

    _counters: dict[str, int] = field(default_factory=dict)

    def next(self, prefix: str) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}_{self._counters[prefix]:03d}"
