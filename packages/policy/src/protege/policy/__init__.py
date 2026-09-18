"""PROTÉGÉ policy engine, safety shield & trajectory log (roadmap P11).

Zero LLM calls (no import of ``protege.llm``, ``protege.roles.sprout``, or
``protege.roles.diagnostician`` anywhere in this package -- verified by
``tests/test_no_llm_dependency.py``). Chooses the next learning action from
rules over a 14-dim context vector, runs it through an unconditional
deterministic safety shield, and packages the result as a P9-persistable
``protege.contracts.PolicyDecision`` -- see ``engine.py`` for the full
pipeline and every other module's docstring for its one responsibility.
"""

from .context import (
    STATE_VECTOR_DIMENSION_NAMES,
    PolicyContext,
    build_state_vector,
    encode_grade_band,
    mean_confidence,
)
from .engine import ITEM_SERVING_ACTIONS, decide
from .item_selection import ItemSelectionResult, select_item_by_target_elo, target_item_rating
from .reward import RewardComponents, compute_reward
from .rules import counterfactual_choice, low_readiness_action, propose_action, rank_actions
from .shield import ShieldResult, evaluate_shield

__version__ = "0.1.0"

__all__ = [  # noqa: RUF022
    # Context / state vector
    "PolicyContext",
    "STATE_VECTOR_DIMENSION_NAMES",
    "build_state_vector",
    "encode_grade_band",
    "mean_confidence",
    # Rule policy
    "propose_action",
    "counterfactual_choice",
    "rank_actions",
    "low_readiness_action",
    # Safety shield
    "ShieldResult",
    "evaluate_shield",
    # Elo item selection
    "ItemSelectionResult",
    "target_item_rating",
    "select_item_by_target_elo",
    # Reward
    "RewardComponents",
    "compute_reward",
    # Engine
    "ITEM_SERVING_ACTIONS",
    "decide",
]
