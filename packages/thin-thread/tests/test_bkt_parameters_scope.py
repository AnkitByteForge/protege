"""P8 exit-gate audit 1: BKT parameters.

``protege.learning_engine.mastery_engine.BKTParameters`` is, by design,
always a required caller-supplied argument -- P2 never hardcodes a
default (see that module's own docstring). No authored content anywhere
in ``content/math/fractions/v1`` supplies slip/guess/transit for S004
(confirmed below), so P8's ``scenario.BKT_PARAMETERS`` is a scoped,
clearly-labeled placeholder, not a duplication of a value P2 or P3
already define. This test makes that justification falsifiable: if a
future P3 change ever DOES author BKT parameters for S004, this test
starts failing and P8's placeholder must be reconciled with it, rather
than silently continuing to shadow real authored content.
"""

from __future__ import annotations

from _helpers import get_content

from protege.thin_thread.scenario import SKILL_CODE


def test_content_pack_authors_no_bkt_parameters_for_s004() -> None:
    content = get_content()
    skill = next(s for s in content.skills if s.code == SKILL_CODE)
    # Skill (and every other P1 contract touching S004/M003) has no
    # slip/guess/transit-shaped field at all -- BKTParameters truly has
    # no authored source to be duplicating.
    assert not any(hasattr(skill, name) for name in ("slip", "guess", "transit", "bkt_parameters"))


def test_bkt_parameters_constant_is_confined_to_the_thin_thread_package() -> None:
    """Guards against ``BKT_PARAMETERS`` quietly becoming a de facto
    system-wide default: nothing outside ``packages/thin-thread`` may
    reference it."""
    from pathlib import Path

    _EXCLUDED_PARTS = {"thin-thread", "__pycache__", ".venv", ".git", "node_modules"}

    repo_root = Path(__file__).resolve().parents[3]
    hits = []
    for directory in ("packages", "services", "tools", "content"):
        for path in (repo_root / directory).rglob("*.py"):
            if _EXCLUDED_PARTS.intersection(path.parts):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "BKT_PARAMETERS" in text:
                hits.append(path)
    assert hits == [], f"BKT_PARAMETERS leaked outside packages/thin-thread: {hits}"
