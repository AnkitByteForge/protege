"""Shared P8 test helper.

Deliberately named ``_helpers``, not ``conftest``: none of this
monorepo's test directories use ``__init__.py`` packages (matching the
same leading-underscore convention already used by
``packages/roles/tests/_eval_harness.py`` and
``packages/session-fsm/tests/_golden_trace_fixtures.py``), so a *second*
file literally named ``conftest.py`` would collide with every other test
directory's own ``conftest.py`` under Python's flat top-level module
cache the moment another test module does a bare ``from conftest import
...`` (confirmed: ``packages/roles/tests/test_sprout_fidelity.py`` does
exactly that) -- ``get_content()`` is therefore a plain cached function,
not a pytest fixture.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache

from protege.authoring.loader import ContentPack, load_content_pack
from protege.llm.providers.fake import FakeOutcome
from protege.thin_thread.engine import ThinThreadResult, run_thin_thread
from protege.thin_thread.fake_script import build_fake_script
from protege.thin_thread.router_setup import build_router
from protege.thin_thread.scenario import Scenario, resolve_misconception


@lru_cache(maxsize=1)
def get_content() -> ContentPack:
    return load_content_pack()


def run_with_fake(
    scenario: Scenario,
    content: ContentPack,
    *,
    extra_outcomes: Sequence[FakeOutcome] = (),
    trace_sink=None,
) -> ThinThreadResult:
    """Run one scenario end to end against a fresh, deterministic
    :class:`~protege.llm.providers.fake.FakeProvider`.

    ``extra_outcomes`` are appended after the scenario's own scripted
    teach-back outcomes -- used by tests that need to force a schema
    failure or malformed response on top of the normal script.
    """
    misconception = resolve_misconception(content)
    base_script = build_fake_script(
        scenario, misconception=misconception, sprout_scripts=content.sprout_scripts
    )
    script = [*base_script, *extra_outcomes]
    router = build_router("fake", script=script)
    return run_thin_thread(scenario, router, content=content, trace_sink=trace_sink)
