"""Small SQLite metadata/audit skeleton.  It stores only redacted metadata."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import threading
from typing import Any

from .models import (
    CanaryEvent,
    find_secret_values,
    Lease,
    RouteStateEvidence,
    ValidationError,
    parse_rfc3339_utc,
    redact,
    safe_database_path,
)


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
            CREATE TABLE IF NOT EXISTS route_fences (
                route_id TEXT NOT NULL,
                route_epoch INTEGER NOT NULL,
                max_fencing_generation INTEGER NOT NULL,
                PRIMARY KEY(route_id, route_epoch)
            );
            CREATE TABLE IF NOT EXISTS canary_events (
                event_id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                route_id TEXT NOT NULL,
                route_epoch INTEGER NOT NULL,
                canary_id TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS route_state_evidence (
                evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id TEXT NOT NULL,
                route_epoch INTEGER NOT NULL,
                active_task_hash TEXT NOT NULL,
                coordination_hash TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                UNIQUE(route_id, route_epoch, active_task_hash, coordination_hash)
            );
            """
        )

    def close(self) -> None:
        self._connection.close()

    def record_audit(self, event_type: str, payload: dict[str, Any], created_at: str) -> None:
        if not event_type or not isinstance(payload, dict):
            raise ValidationError("audit event must have an event type and object payload")
        findings = find_secret_values(payload)
        safe_object = redact(payload)
        if findings:
            safe_object["_value_secret_findings"] = [
                {"path": finding.path, "category": finding.category} for finding in findings
            ]
        safe_payload = json.dumps(safe_object, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
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

    def expire_stale_leases(self, observed_at: str) -> int:
        """Release expired leases using a caller-supplied, reproducible clock."""
        parse_rfc3339_utc(observed_at, "lease expiry observation time")
        with self._lock:
            return self._expire_stale_leases_locked(observed_at)

    def _expire_stale_leases_locked(self, observed_at: str) -> int:
        result = self._connection.execute(
            """UPDATE leases SET released_at = ?
               WHERE released_at IS NULL AND expires_at <= ?""",
            (observed_at, observed_at),
        )
        return int(result.rowcount)

    def acquire_lease(self, lease: Lease, observed_at: str | None = None) -> bool:
        """Acquire a lease only with a monotonic fencing generation.

        `observed_at` is deliberately caller supplied.  Legacy callers that do
        not provide it use the lease acquisition timestamp, never wall-clock time.
        """
        observed_at = observed_at or lease.acquired_at
        parse_rfc3339_utc(observed_at, "lease observation time")
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                self._expire_stale_leases_locked(observed_at)
                fence = self._connection.execute(
                    "SELECT max_fencing_generation FROM route_fences WHERE route_id = ? AND route_epoch = ?",
                    (lease.route.route_id, lease.route.route_epoch),
                ).fetchone()
                if fence is not None and lease.fencing_generation <= int(fence["max_fencing_generation"]):
                    self._connection.execute("ROLLBACK")
                    return False
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
                self._connection.execute(
                    """INSERT INTO route_fences(route_id, route_epoch, max_fencing_generation)
                       VALUES (?, ?, ?)
                       ON CONFLICT(route_id, route_epoch) DO UPDATE SET
                           max_fencing_generation = excluded.max_fencing_generation""",
                    (lease.route.route_id, lease.route.route_epoch, lease.fencing_generation),
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

    def active_lease_exists(self, route_id: str, route_epoch: int, observed_at: str | None = None) -> bool:
        with self._lock:
            if observed_at is not None:
                parse_rfc3339_utc(observed_at, "lease observation time")
                self._expire_stale_leases_locked(observed_at)
            row = self._connection.execute(
                "SELECT 1 FROM leases WHERE route_id = ? AND route_epoch = ? AND released_at IS NULL",
                (route_id, route_epoch),
            ).fetchone()
        return row is not None

    def reserve_canary_event(
        self,
        event: CanaryEvent,
        route_state: RouteStateEvidence,
        created_at: str,
    ) -> bool:
        """Persist one event and its synchronized route proof in one transaction.

        The unique event ID and idempotency key prevent a second external effect.
        Only hashes and public-safe metadata are stored; no event body is accepted.
        """
        parse_rfc3339_utc(created_at, "canary event created_at")
        if event.route != route_state.route:
            raise ValidationError("canary event and route-state evidence must bind the same route")
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                self._connection.execute(
                    """INSERT INTO canary_events(
                        event_id, idempotency_key, route_id, route_epoch, canary_id, payload_hash, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event.event_id,
                        event.idempotency_key,
                        event.route.route_id,
                        event.route.route_epoch,
                        event.canary_id,
                        event.payload_hash,
                        created_at,
                    ),
                )
                self._connection.execute(
                    """INSERT INTO route_state_evidence(
                        route_id, route_epoch, active_task_hash, coordination_hash, observed_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(route_id, route_epoch, active_task_hash, coordination_hash) DO NOTHING""",
                    (
                        route_state.route.route_id,
                        route_state.route.route_epoch,
                        route_state.active_task_hash,
                        route_state.coordination_hash,
                        route_state.observed_at,
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

    def list_canary_events(self) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """SELECT event_id, idempotency_key, route_id, route_epoch, canary_id, payload_hash, created_at
               FROM canary_events ORDER BY created_at, event_id"""
        ).fetchall()
        return [dict(row) for row in rows]

    def list_route_state_evidence(self) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """SELECT route_id, route_epoch, active_task_hash, coordination_hash, observed_at
               FROM route_state_evidence ORDER BY evidence_id"""
        ).fetchall()
        return [dict(row) for row in rows]
