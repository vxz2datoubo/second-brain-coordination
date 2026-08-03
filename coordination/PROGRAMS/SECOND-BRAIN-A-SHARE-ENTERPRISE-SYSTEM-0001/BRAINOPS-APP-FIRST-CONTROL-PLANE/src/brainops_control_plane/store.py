"""Small SQLite metadata/audit skeleton.  It stores only redacted metadata."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import threading
from typing import Any

from .models import Lease, ValidationError, redact, safe_database_path


class MetadataStore:
    def __init__(self, root: Path, filename: str = "brainops.sqlite") -> None:
        root.mkdir(parents=True, exist_ok=True)
        self.path = safe_database_path(root, filename)
        self._connection = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._initialize()

    def _initialize(self) -> None:
        self._connection.executescript(
            """
            PRAGMA journal_mode = WAL;
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS leases (
                lease_id TEXT PRIMARY KEY,
                route_id TEXT NOT NULL,
                route_epoch INTEGER NOT NULL,
                owner TEXT NOT NULL,
                fencing_generation INTEGER NOT NULL,
                acquired_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                released_at TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_lease_per_route_epoch
                ON leases(route_id, route_epoch) WHERE released_at IS NULL;
            """
        )

    def close(self) -> None:
        self._connection.close()

    def record_audit(self, event_type: str, payload: dict[str, Any], created_at: str) -> None:
        if not event_type or not isinstance(payload, dict):
            raise ValidationError("audit event must have an event type and object payload")
        safe_payload = json.dumps(redact(payload), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        with self._lock:
            self._connection.execute(
                "INSERT INTO audit_events(event_type, payload_json, created_at) VALUES (?, ?, ?)",
                (event_type, safe_payload, created_at),
            )

    def list_audit(self) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT event_id, event_type, payload_json, created_at FROM audit_events ORDER BY event_id"
        ).fetchall()
        return [
            {
                "event_id": row["event_id"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def acquire_lease(self, lease: Lease) -> bool:
        """Atomically acquire the sole active lease for a route epoch."""
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                self._connection.execute(
                    """INSERT INTO leases(
                        lease_id, route_id, route_epoch, owner, fencing_generation, acquired_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        lease.lease_id,
                        lease.route.route_id,
                        lease.route.route_epoch,
                        lease.owner.value,
                        lease.fencing_generation,
                        lease.acquired_at,
                        lease.expires_at,
                    ),
                )
                self._connection.execute("COMMIT")
                return True
            except sqlite3.IntegrityError:
                self._connection.execute("ROLLBACK")
                return False
            except Exception:
                self._connection.execute("ROLLBACK")
                raise

    def release_lease(self, lease_id: str, released_at: str) -> bool:
        with self._lock:
            result = self._connection.execute(
                "UPDATE leases SET released_at = ? WHERE lease_id = ? AND released_at IS NULL",
                (released_at, lease_id),
            )
        return result.rowcount == 1

    def active_lease_exists(self, route_id: str, route_epoch: int) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM leases WHERE route_id = ? AND route_epoch = ? AND released_at IS NULL",
            (route_id, route_epoch),
        ).fetchone()
        return row is not None
