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
    ValidationError,
    parse_rfc3339_utc,
    redact,
    require_identifier,
    safe_database_path,
)
from .proofs import ApprovalVerificationResult, RouteProofVerification


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
                selected_owner TEXT NOT NULL DEFAULT 'NONE',
                payload_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS one_shot_execution_outcomes (
                event_id TEXT PRIMARY KEY REFERENCES canary_events(event_id),
                task_id TEXT NOT NULL,
                route_epoch INTEGER NOT NULL,
                canary_id TEXT NOT NULL,
                approval_nonce TEXT NOT NULL,
                selected_owner TEXT NOT NULL,
                non_attempted_owner TEXT NOT NULL,
                terminal_state TEXT NOT NULL CHECK(terminal_state IN ('PENDING', 'SUCCEEDED', 'FAILED')),
                terminal_reason TEXT,
                attempted_at TEXT NOT NULL,
                terminal_at TEXT,
                normal_dispatch_disabled INTEGER NOT NULL CHECK(normal_dispatch_disabled = 1),
                UNIQUE(task_id, route_epoch, canary_id, approval_nonce)
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
            CREATE TABLE IF NOT EXISTS approval_consumptions (
                task_id TEXT NOT NULL,
                route_epoch INTEGER NOT NULL,
                canary_id TEXT NOT NULL,
                approval_nonce TEXT NOT NULL,
                repository TEXT NOT NULL,
                issue_number INTEGER NOT NULL,
                comment_id INTEGER NOT NULL,
                actor TEXT NOT NULL,
                issued_at TEXT NOT NULL,
                body_sha256 TEXT NOT NULL,
                approval_ref TEXT NOT NULL,
                binding_payload_sha256 TEXT NOT NULL,
                consumed_at TEXT NOT NULL,
                PRIMARY KEY(task_id, route_epoch, canary_id, approval_nonce)
            );
            CREATE TABLE IF NOT EXISTS verified_route_state_evidence (
                evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id TEXT NOT NULL,
                route_epoch INTEGER NOT NULL,
                repository TEXT NOT NULL,
                ref TEXT NOT NULL,
                main_commit_sha1 TEXT NOT NULL,
                main_tree_sha1 TEXT NOT NULL,
                active_task_path TEXT NOT NULL,
                active_task_blob_sha1 TEXT NOT NULL,
                active_task_content_sha256 TEXT NOT NULL,
                coordination_path TEXT NOT NULL,
                coordination_blob_sha1 TEXT NOT NULL,
                coordination_content_sha256 TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                verified_at TEXT NOT NULL,
                UNIQUE(
                    route_id, route_epoch, repository, ref, main_commit_sha1,
                    active_task_blob_sha1, active_task_content_sha256,
                    coordination_blob_sha1, coordination_content_sha256
                )
            );
            """
        )
        columns = {row["name"] for row in self._connection.execute("PRAGMA table_info(verified_route_state_evidence)")}
        if "main_tree_sha1" not in columns:
            self._connection.execute("ALTER TABLE verified_route_state_evidence ADD COLUMN main_tree_sha1 TEXT")
        canary_columns = {row["name"] for row in self._connection.execute("PRAGMA table_info(canary_events)")}
        if "selected_owner" not in canary_columns:
            self._connection.execute("ALTER TABLE canary_events ADD COLUMN selected_owner TEXT NOT NULL DEFAULT 'NONE'")

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
        activation: Any,
        approval_verification: ApprovalVerificationResult,
        route_proof: RouteProofVerification,
        created_at: str,
        *,
        selected_owner: str = "NONE",
        non_attempted_owner: str = "NONE",
        one_shot_execution: bool = False,
    ) -> bool:
        """Atomically consume approval, reserve one event, and retain route proof.

        A unique approval nonce prevents a second event even when the caller
        changes the event ID, idempotency key, or payload hash. Only hashes and
        public metadata are stored; no approval/comment/event body is accepted.
        """
        parse_rfc3339_utc(created_at, "canary event created_at")
        require_identifier(selected_owner, "selected canary owner")
        require_identifier(non_attempted_owner, "non-attempted canary owner")
        if selected_owner == non_attempted_owner and one_shot_execution:
            raise ValidationError("one-shot canary owners must be mutually exclusive")
        approval = getattr(activation, "approval", None)
        if approval is None:
            raise ValidationError("canary reservation requires a bound approval")
        if event.route != activation.route:
            raise ValidationError("canary event and activation must bind the same route")
        if event.canary_id != activation.canary_id or event.idempotency_key != activation.idempotency_key:
            raise ValidationError("canary event must bind the activation canary and idempotency key")
        approval_error = approval.validates(activation, created_at)
        if approval_error is not None:
            raise ValidationError(approval_error)
        verification_error = approval_verification.validates(approval, created_at)
        if verification_error is not None:
            raise ValidationError(verification_error)
        route_error = route_proof.validates(event.route)
        if route_error is not None:
            raise ValidationError(route_error)
        evidence = approval_verification.evidence
        route_evidence = route_proof.evidence
        assert evidence is not None
        assert route_evidence is not None
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                self._connection.execute(
                    """INSERT INTO approval_consumptions(
                        task_id, route_epoch, canary_id, approval_nonce,
                        repository, issue_number, comment_id, actor, issued_at,
                        body_sha256, approval_ref, binding_payload_sha256, consumed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        activation.task_id,
                        activation.expected_epoch,
                        activation.canary_id,
                        activation.approval_nonce,
                        evidence.repository,
                        evidence.issue_number,
                        evidence.comment_id,
                        evidence.actor,
                        evidence.issued_at,
                        evidence.body_sha256,
                        evidence.approval_ref,
                        evidence.binding_payload_sha256,
                        created_at,
                    ),
                )
                self._connection.execute(
                    """INSERT INTO canary_events(
                        event_id, idempotency_key, route_id, route_epoch, canary_id, selected_owner, payload_hash, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event.event_id,
                        event.idempotency_key,
                        event.route.route_id,
                        event.route.route_epoch,
                        event.canary_id,
                        selected_owner,
                        event.payload_hash,
                        created_at,
                    ),
                )
                if one_shot_execution:
                    self._connection.execute(
                        """INSERT INTO one_shot_execution_outcomes(
                            event_id, task_id, route_epoch, canary_id, approval_nonce,
                            selected_owner, non_attempted_owner, terminal_state, attempted_at, normal_dispatch_disabled
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, 1)""",
                        (
                            event.event_id,
                            activation.task_id,
                            activation.expected_epoch,
                            activation.canary_id,
                            activation.approval_nonce,
                            selected_owner,
                            non_attempted_owner,
                            created_at,
                        ),
                    )
                self._connection.execute(
                    """INSERT INTO verified_route_state_evidence(
                        route_id, route_epoch, repository, ref, main_commit_sha1, main_tree_sha1,
                        active_task_path, active_task_blob_sha1, active_task_content_sha256,
                        coordination_path, coordination_blob_sha1, coordination_content_sha256,
                        observed_at, verified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(
                        route_id, route_epoch, repository, ref, main_commit_sha1,
                        active_task_blob_sha1, active_task_content_sha256,
                        coordination_blob_sha1, coordination_content_sha256
                    ) DO NOTHING""",
                    (
                        route_evidence.route.route_id,
                        route_evidence.route.route_epoch,
                        route_evidence.repository,
                        route_evidence.ref,
                        route_evidence.main_commit_sha1,
                        route_evidence.main_tree_sha1,
                        route_evidence.active_task.path,
                        route_evidence.active_task.blob_sha1,
                        route_evidence.active_task.content_sha256,
                        route_evidence.coordination.path,
                        route_evidence.coordination.blob_sha1,
                        route_evidence.coordination.content_sha256,
                        route_evidence.observed_at,
                        route_proof.verified_at,
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
            """SELECT event_id, idempotency_key, route_id, route_epoch, canary_id, selected_owner, payload_hash, created_at
               FROM canary_events ORDER BY created_at, event_id"""
        ).fetchall()
        return [dict(row) for row in rows]

    def finalize_one_shot_execution(
        self,
        event_id: str,
        terminal_state: str,
        terminal_reason: str,
        terminal_at: str,
    ) -> bool:
        """Close one already-consumed attempt without ever re-enabling dispatch."""
        require_identifier(event_id, "one-shot event_id")
        if terminal_state not in {"SUCCEEDED", "FAILED"}:
            raise ValidationError("one-shot terminal state must be SUCCEEDED or FAILED")
        require_identifier(terminal_reason, "one-shot terminal reason")
        parse_rfc3339_utc(terminal_at, "one-shot terminal_at")
        with self._lock:
            result = self._connection.execute(
                """UPDATE one_shot_execution_outcomes
                   SET terminal_state = ?, terminal_reason = ?, terminal_at = ?
                   WHERE event_id = ? AND terminal_state = 'PENDING' AND normal_dispatch_disabled = 1""",
                (terminal_state, terminal_reason, terminal_at, event_id),
            )
        return result.rowcount == 1

    def list_one_shot_execution_outcomes(self) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """SELECT event_id, task_id, route_epoch, canary_id, approval_nonce,
               selected_owner, non_attempted_owner, terminal_state, terminal_reason,
               attempted_at, terminal_at, normal_dispatch_disabled
               FROM one_shot_execution_outcomes ORDER BY attempted_at, event_id"""
        ).fetchall()
        return [dict(row) for row in rows]

    def list_route_state_evidence(self) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """SELECT route_id, route_epoch, active_task_hash, coordination_hash, observed_at
               FROM route_state_evidence ORDER BY evidence_id"""
        ).fetchall()
        return [dict(row) for row in rows]

    def list_approval_consumptions(self) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """SELECT task_id, route_epoch, canary_id, approval_nonce, repository,
               issue_number, comment_id, actor, issued_at, body_sha256, approval_ref,
               binding_payload_sha256, consumed_at
               FROM approval_consumptions ORDER BY consumed_at, task_id, canary_id"""
        ).fetchall()
        return [dict(row) for row in rows]

    def list_verified_route_state_evidence(self) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """SELECT route_id, route_epoch, repository, ref, main_commit_sha1, main_tree_sha1,
               active_task_path, active_task_blob_sha1, active_task_content_sha256,
               coordination_path, coordination_blob_sha1, coordination_content_sha256,
               observed_at, verified_at
               FROM verified_route_state_evidence ORDER BY evidence_id"""
        ).fetchall()
        return [dict(row) for row in rows]
