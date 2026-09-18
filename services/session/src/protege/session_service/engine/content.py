"""Process-wide content pack access (roadmap P10 exit criterion: "Thin
Thread over HTTP" -- P10 exposes the exact same authored skill/misconception/
items P8's ``protege.thin_thread`` already resolves through the real P3
content-pack loader, never a re-authored or generalized content-selection
layer; item/content *selection* policy is P11's future job, out of P10's
scope).

Cached with ``lru_cache`` so the (file-based) content pack is parsed once
per process, matching ``protege.thin_thread.engine``'s own
``content if content is not None else load_content_pack()`` default.
"""

from __future__ import annotations

from functools import lru_cache

from protege.authoring.loader import ContentPack, load_content_pack
from protege.contracts import Misconception, Skill
from protege.learning_engine import BKTParameters
from protege.thin_thread.scenario import (
    ThinThreadItems,
    resolve_items,
    resolve_misconception,
    resolve_skill,
)

SESSION_BKT_PARAMS = BKTParameters(slip=0.15, guess=0.35, transit=0.10)
"""P10's own scoped slip/guess/transit placeholder for S004/M003, the live
thin-thread replay's only authored skill/misconception. Declared
independently from (though numerically identical to) the same-shaped
constant ``packages/thin-thread``'s own scenario module keeps for its
demo run -- that package guards its constant (see its own
``tests/test_bkt_parameters_scope.py``) against being referenced anywhere
outside itself, precisely so it can never quietly become a de facto
system-wide default. P10 is a persistent service, not that package's demo
script, so it needs -- and gets -- its own placeholder with the same "no
canonical document specifies slip/guess/transit for S004;
``protege.learning_engine.BKTParameters`` is always caller-supplied by
design" status. A future content-authoring phase ratifying real per-skill
values should replace this constant and the thin-thread package's copy
together."""


@lru_cache(maxsize=1)
def get_content_pack() -> ContentPack:
    return load_content_pack()


@lru_cache(maxsize=1)
def get_thin_thread_items() -> ThinThreadItems:
    return resolve_items(get_content_pack())


@lru_cache(maxsize=1)
def get_misconception() -> Misconception:
    return resolve_misconception(get_content_pack())


@lru_cache(maxsize=1)
def get_skill() -> Skill:
    return resolve_skill(get_content_pack())
