"""P8 testing requirement #9: real-role interfaces can be injected /
replaced with FakeProvider-based deterministic tests.

Confirms the thin thread is driven by the actual P5/P6 role
implementations (not a stand-in), wired to a hand-built ``ModelRouter``
constructed without going through the CLI or ``router_setup.build_router``
at all -- proving the engine only depends on the ``ModelRouter``
abstraction, not on any concrete provider.
"""

from __future__ import annotations

from _helpers import get_content

from protege.contracts import DiagnosisResult
from protege.llm.providers.fake import FakeProvider
from protege.llm.router import ModelRouter
from protege.roles.sprout import SproutGenerationResult
from protege.thin_thread.engine import run_thin_thread
from protege.thin_thread.fake_script import build_fake_script
from protege.thin_thread.scenario import happy_path_scenario, resolve_misconception


def test_engine_accepts_a_hand_built_router_and_uses_real_role_modules() -> None:
    content = get_content()
    scenario = happy_path_scenario()
    misconception = resolve_misconception(content)
    script = build_fake_script(
        scenario, misconception=misconception, sprout_scripts=content.sprout_scripts
    )
    router = ModelRouter({"nvidia": FakeProvider(script=script)})  # no router_setup involved

    result = run_thin_thread(scenario, router, content=content)

    assert len(result.sprout_attempts) == 1
    assert isinstance(result.sprout_attempts[0], SproutGenerationResult)
    assert len(result.diagnoses) == 1
    assert isinstance(result.diagnoses[0], DiagnosisResult)
