"""SQLite snapshot and verified rollback support adapted from PR #46."""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from .memory_store import MemoryStore


class SnapshotManager:
    @staticmethod
    def create(store: MemoryStore, snapshot_path: Path) -> dict[str, Any]:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        destination = sqlite3.connect(snapshot_path)
        try:
            store.conn.backup(destination)
        finally:
            destination.close()
        digest = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
        return {"snapshot_path": str(snapshot_path), "sha256": digest, "knowledge_version": store.latest_revision_id()}

    @staticmethod
    def restore(snapshot_path: Path, target_db_path: Path, expected_sha256: str) -> None:
        actual = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
        if actual != expected_sha256:
            raise ValueError("snapshot_hash_mismatch")
        if snapshot_path.resolve() == target_db_path.resolve():
            raise ValueError("snapshot_target_must_differ")
        target_db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snapshot_path, target_db_path)
