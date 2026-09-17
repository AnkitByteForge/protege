"""P8 testing requirement #7: Sprout never receives the correct answer.

Wraps the provider to record every message actually sent over the wire,
then asserts the diagnostic item's correct answer text never appears in
any Sprout-role prompt -- proving the withholding end to end through the
real ``SproutGenerator`` -> ``ModelRouter`` -> provider path, not just at
the ``build_sprout_messages`` unit-test level (already covered in
``packages/roles``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from _helpers import get_content

from protege.llm.providers.fake import FakeProvider
from protege.llm.router import ModelRouter
from protege.thin_thread.engine import run_thin_thread
from protege.thin_thread.fake_script import build_fake_script
from protege.thin_thread.scenario import (
    DIAGNOSTIC_ITEM_ID,
    happy_path_scenario,
    resolve_items,
    resolve_misconception,
)


@dataclass
class _RecordingProvider:
    inner: FakeProvider
    name: str = "nvidia"
    sent_message_texts: list[str] = field(default_factory=list)

    @property
    def base_url(self) -> str:
        return self.inner.base_url

    def complete(self, messages, **kwargs):
        self.sent_message_texts.extend(m.content for m in messages)
        return self.inner.complete(messages, **kwargs)


def test_diagnostic_items_correct_answer_never_reaches_a_sprout_prompt() -> None:
    content = get_content()
    scenario = happy_path_scenario()
    misconception = resolve_misconception(content)
    items = resolve_items(content)
    assert items.diagnostic.item_id == DIAGNOSTIC_ITEM_ID
    correct_answer = items.diagnostic.correct_answer  # "1/4"

    script = build_fake_script(
        scenario, misconception=misconception, sprout_scripts=content.sprout_scripts
    )
    recorder = _RecordingProvider(inner=FakeProvider(script=script))
    router = ModelRouter({"nvidia": recorder})

    run_thin_thread(scenario, router, content=content)

    assert recorder.sent_message_texts, "expected at least one real provider call"

    # Two substrings legitimately contain "1/4" without telling Sprout it is
    # the CORRECT one: the item stem itself ("Which is more pizza: 1/4 or
    # 1/8?" -- Sprout must see the problem being compared) and the authored
    # `sprout_forbidden` instruction ("stating 1/4 > 1/8 before resolution"
    # -- a *rule about what not to say*, not a revealed answer). Scrubbing
    # both out isolates the real question: does anything else in the
    # prompt -- in particular, an explicit correct-answer parameter -- ever
    # tell Sprout which value is right?
    item_stem = items.diagnostic.stem
    forbidden_text = ", ".join(misconception.sprout_forbidden)
    for text in recorder.sent_message_texts:
        scrubbed = text.replace(item_stem, "").replace(forbidden_text, "")
        assert correct_answer not in scrubbed, f"correct answer leaked into a prompt: {text!r}"
