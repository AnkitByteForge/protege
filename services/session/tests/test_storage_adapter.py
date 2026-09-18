"""P9 exit gate 17: the local ``StorageAdapter`` implementation works.
No Postgres required -- pure filesystem behaviour.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from protege.session_service.settings import Settings
from protege.session_service.storage.adapter import (
    LocalFilesystemStorageAdapter,
    StorageKeyError,
    build_storage_adapter,
)


def test_put_get_roundtrip(tmp_path: Path) -> None:
    adapter = LocalFilesystemStorageAdapter(tmp_path)
    adapter.put("sprout/M003/utterance_01.mp3", b"audio-bytes")

    assert adapter.exists("sprout/M003/utterance_01.mp3") is True
    assert adapter.get("sprout/M003/utterance_01.mp3") == b"audio-bytes"


def test_get_missing_key_raises(tmp_path: Path) -> None:
    adapter = LocalFilesystemStorageAdapter(tmp_path)

    with pytest.raises(StorageKeyError):
        adapter.get("does/not/exist.bin")


def test_delete_removes_key(tmp_path: Path) -> None:
    adapter = LocalFilesystemStorageAdapter(tmp_path)
    adapter.put("a/b.txt", b"x")

    adapter.delete("a/b.txt")

    assert adapter.exists("a/b.txt") is False


def test_path_traversal_key_is_rejected(tmp_path: Path) -> None:
    adapter = LocalFilesystemStorageAdapter(tmp_path)

    with pytest.raises(ValueError, match="unsafe"):
        adapter.put("../escape.txt", b"x")
    with pytest.raises(ValueError, match="unsafe"):
        adapter.put("/absolute.txt", b"x")


def test_build_storage_adapter_resolves_local_backend(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, storage_backend="local", storage_local_root=str(tmp_path))

    adapter = build_storage_adapter(settings)

    assert isinstance(adapter, LocalFilesystemStorageAdapter)
    adapter.put("k", b"v")
    assert adapter.get("k") == b"v"


def test_build_storage_adapter_rejects_unknown_backend() -> None:
    settings = Settings(_env_file=None, storage_backend="s3")

    with pytest.raises(ValueError, match="unknown storage_backend"):
        build_storage_adapter(settings)
