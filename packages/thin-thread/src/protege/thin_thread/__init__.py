"""PROTÉGÉ P8 -- the thin vertical thread.

Wires the real Session FSM/orchestrator (P7), Sprout (P5), Diagnostician
(P6), and the deterministic learning engine (P2) into one executable
session proving LEARN -> TEACH -> PROVE end to end:

    FSM -> Sprout -> Diagnostician -> deterministic learning update
    -> independent verification -> mastery decision -> evidence-backed claim

Entry point: ``python -m protege.thin_thread``.
"""

from .engine import ThinThreadResult, run_thin_thread
from .router_setup import build_router
from .scenario import Scenario, happy_path_scenario, recovery_scenario

__version__ = "0.1.0"

__all__ = [
    "Scenario",
    "ThinThreadResult",
    "build_router",
    "happy_path_scenario",
    "recovery_scenario",
    "run_thin_thread",
]
