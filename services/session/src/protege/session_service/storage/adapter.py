"""``StorageAdapter``: the interface boundary between application code and
"where blobs live" (addendum §8: "Storage is behind a ``StorageAdapter``
interface from day one so the local filesystem and S3/R2 are
interchangeable"). P9 ships exactly one implementation,
:class:`LocalFilesystemStorageAdapter`, matching the addendum's local-dev
diagram (``./local_storage``, "filesystem, S3-shaped adapter").

**The interface boundary for later deployment** (roadmap P9 requirement) is
the :class:`StorageAdapter` protocol itself: an S3/R2-compatible adapter
(``boto3``/an R2-compatible client) implements these same four methods --
``put``/``get``/``exists``/``delete`` over a ``key: str`` -- and every
caller (a future proof-artifact/TTS-cache job) is written against the
protocol, never against a concrete adapter. No cloud SDK is added as a
dependency here (roadmap: "Do not add actual cloud infrastructure in P9");
adding a concrete S3/R2 class is exactly the "one file changes" swap the
addendum's production-evolution table already describes for storage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from ..settings import Settings, get_settings


@runtime_checkable
class StorageAdapter(Protocol):
    """Put/get immutable blobs by key (ARCHITECTURE.md §6: "give me that
    blob by name"). Never queried by content -- callers own their own key
    scheme (e.g. ``sprout/M003/utterance_01.mp3``, addendum §6)."""

    def put(self, key: str, data: bytes) -> None: ...
    def get(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> None: ...


class StorageKeyError(KeyError):
    """``key`` does not exist in this adapter."""


class LocalFilesystemStorageAdapter:
    """Development/test implementation: one file per key under ``root``.

    ``key`` may contain ``/`` (matching the addendum's own key examples,
    e.g. ``sprout/M003/utterance_01.mp3``) -- each segment becomes a
    subdirectory, created on write. Path traversal (``..`` segments, an
    absolute-looking key) is rejected outright rather than silently
    resolved, since a caller-supplied key must never be able to escape
    ``root``.
    """

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        if not key or key.startswith("/") or ".." in Path(key).parts:
            raise ValueError(f"unsafe storage key: {key!r}")
        path = (self._root / key).resolve()
        if self._root not in path.parents and path != self._root:
            raise ValueError(f"unsafe storage key: {key!r}")
        return path

    def put(self, key: str, data: bytes) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.is_file():
            raise StorageKeyError(key)
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        path.unlink(missing_ok=True)


def build_storage_adapter(settings: Settings | None = None) -> StorageAdapter:
    """Resolve the configured adapter (``Settings.storage_backend``).
    ``"local"`` is the only backend P9 implements; any other value fails
    loudly rather than silently falling back, since a misconfigured
    deployment target should never quietly write to local disk."""
    resolved = settings if settings is not None else get_settings()
    if resolved.storage_backend == "local":
        return LocalFilesystemStorageAdapter(resolved.storage_local_root)
    raise ValueError(
        f"unknown storage_backend={resolved.storage_backend!r}; "
        "only 'local' is implemented in P9 (see StorageAdapter's module docstring "
        "for the S3/R2 interface boundary)"
    )
