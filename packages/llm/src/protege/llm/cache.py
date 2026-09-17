"""In-process prompt-hash response cache.

Addendum §2.3: "Cache every eval result to disk keyed by prompt hash."
Addendum §9 point 7: "Sprout utterances and eval results are cached by
content hash." This module provides the generic router-level cache; a
role-specific keying scheme (e.g. Sprout's
``(misconception_id, turn_index, item_id)``, addendum §2.3/§30) is layered
on top by P5 and is out of scope here.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from collections.abc import Sequence

from .base import LLMResult, Message


def hash_prompt(
    provider_name: str,
    role: str,
    model_id: str,
    messages: Sequence[Message],
    schema_title: str,
) -> str:
    """Deterministic cache key.

    Same ``provider_name`` + ``role`` + ``model_id`` + ``messages`` +
    ``schema_title`` always produces the same key — in this or any process,
    with no randomness and no wall-clock dependency.

    ``provider_name`` is a required, distinct input (not folded into
    ``model_id``) so that two different providers which happen to reuse an
    identical ``model_id`` string — a real near-term case once an overflow
    provider is registered (addendum §2.3) — can never collide on the same
    cache entry.
    """
    payload = {
        "provider": provider_name,
        "role": role,
        "model_id": model_id,
        "schema": schema_title,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class PromptCache:
    """A bounded in-process LRU cache from prompt hash to ``(raw text, LLMResult)``.

    Unbounded growth is a real risk across many distinct prompts in a
    12-minute session; ``max_size`` keeps memory flat.
    """

    def __init__(self, max_size: int = 512) -> None:
        self._max_size = max_size
        self._lock = threading.Lock()
        self._store: OrderedDict[str, tuple[str, LLMResult]] = OrderedDict()

    def get(self, key: str) -> tuple[str, LLMResult] | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            self._store.move_to_end(key)
            return entry

    def put(self, key: str, text: str, result: LLMResult) -> None:
        with self._lock:
            self._store[key] = (text, result)
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def __len__(self) -> int:
        return len(self._store)
