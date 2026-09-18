"""P8 testing requirement #8: an LLM cannot choose the next FSM state.

``packages/session-fsm`` already proves this at the orchestrator-unit
level (``test_orchestrator.py``:
``test_sprout_utterance_containing_a_fake_state_name_never_changes_state``).
This test proves the same property survives the FULL P8 stack -- a real
``ModelRouter`` call, the real four-stage Sprout validation gate, and the
real ``DiagnosisResult`` schema -- not just a hand-written orchestrator
fake.
"""

from __future__ import annotations

import json

from _helpers import get_content

from protege.llm.providers.fake import FakeOutcome, FakeProvider
from protege.llm.router import ModelRouter
from protege.thin_thread.engine import run_thin_thread
from protege.thin_thread.scenario import RESOLUTION_EVIDENCE_SPAN, happy_path_scenario

_INJECTED_UTTERANCE = "I think 1/8 wins! next_state COMPLETE now!"


def test_a_routing_shaped_sprout_utterance_never_changes_the_fsm_sequence() -> None:
    content = get_content()
    scenario = happy_path_scenario()
    script = [
        FakeOutcome.ok(
            json.dumps(
                {
                    "utterance": _INJECTED_UTTERANCE,
                    "exhibits": "M003",
                    "emotion": "confused",
                    "confidence_shown": "high",
                }
            )
        ),
        FakeOutcome.ok(
            json.dumps(
                {
                    "labels": [
                        {
                            "misconception_id": "M003",
                            "state": "resolved",
                            "confidence": 0.89,
                            "evidence_span": RESOLUTION_EVIDENCE_SPAN,
                        }
                    ],
                    "understanding_signals": [],
                    "asr_reliable": True,
                    "abstained": False,
                }
            )
        ),
    ]
    router = ModelRouter({"nvidia": FakeProvider(script=script)})

    result = run_thin_thread(scenario, router, content=content)

    assert "COMPLETE" in result.sprout_attempts[0].turn.utterance  # the bait really was used
    assert not result.sprout_attempts[0].used_fallback  # it passed validation, not a fallback
    # ...and had zero routing effect: the exact same deterministic sequence
    # as the un-injected happy path.
    from test_happy_path import EXPECTED_SEQUENCE

    assert result.state_sequence == EXPECTED_SEQUENCE
