"""``StorageAdapter`` abstraction (roadmap P9/addendum §8, §9 point 18):
local filesystem in development, an S3/R2-compatible interface boundary for
later deployment. No cloud infrastructure is provisioned in P9."""

from .adapter import LocalFilesystemStorageAdapter, StorageAdapter, build_storage_adapter

__all__ = ["LocalFilesystemStorageAdapter", "StorageAdapter", "build_storage_adapter"]
