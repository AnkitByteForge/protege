"""Tests for the in-process prompt-hash response cache."""

from protege.llm.base import LLMResult, Message
from protege.llm.cache import PromptCache, hash_prompt


def _result(text: str = "{}") -> LLMResult:
    return LLMResult(
        text=text,
        provider="fake",
        model_id="m1",
        tokens_in=1,
        tokens_out=1,
        latency_ms=1,
        finish_reason="stop",
    )


def test_hash_prompt_is_deterministic() -> None:
    messages = [Message("user", "hi")]
    assert hash_prompt("nvidia", "SPROUT", "m1", messages, "SproutTurn") == hash_prompt(
        "nvidia", "SPROUT", "m1", messages, "SproutTurn"
    )


def test_hash_prompt_is_sensitive_to_every_input() -> None:
    base = hash_prompt("nvidia", "SPROUT", "m1", [Message("user", "hi")], "SproutTurn")
    assert base != hash_prompt("nvidia", "SPROUT", "m1", [Message("user", "bye")], "SproutTurn")
    assert base != hash_prompt("nvidia", "SPROUT", "m2", [Message("user", "hi")], "SproutTurn")
    assert base != hash_prompt("nvidia", "COACH", "m1", [Message("user", "hi")], "SproutTurn")
    assert base != hash_prompt("nvidia", "SPROUT", "m1", [Message("user", "hi")], "CoachHint")


def test_hash_prompt_distinguishes_provider_identity() -> None:
    """P1-2 regression: same role/model/messages/schema but a different
    provider must produce a different cache key — otherwise two providers
    that happen to reuse an identical `model_id` string (a real near-term
    case once an overflow provider is registered, addendum §2.3) could
    serve each other's cached responses."""
    messages = [Message("user", "hi")]
    nvidia_key = hash_prompt("nvidia", "SPROUT", "shared-model-id", messages, "SproutTurn")
    overflow_key = hash_prompt("overflow", "SPROUT", "shared-model-id", messages, "SproutTurn")
    assert nvidia_key != overflow_key


def test_put_get_roundtrip() -> None:
    cache = PromptCache(max_size=2)
    result = _result()
    cache.put("k1", "{}", result)
    assert cache.get("k1") == ("{}", result)


def test_get_missing_key_returns_none() -> None:
    cache = PromptCache()
    assert cache.get("missing") is None


def test_lru_eviction_drops_the_least_recently_used_entry() -> None:
    cache = PromptCache(max_size=2)
    cache.put("a", "{}", _result())
    cache.put("b", "{}", _result())
    cache.put("c", "{}", _result())  # evicts "a"
    assert cache.get("a") is None
    assert cache.get("b") is not None
    assert cache.get("c") is not None
    assert len(cache) == 2


def test_get_refreshes_recency() -> None:
    cache = PromptCache(max_size=2)
    cache.put("a", "{}", _result())
    cache.put("b", "{}", _result())
    cache.get("a")  # "a" is now more recently used than "b"
    cache.put("c", "{}", _result())  # should evict "b", not "a"
    assert cache.get("a") is not None
    assert cache.get("b") is None
    assert cache.get("c") is not None
