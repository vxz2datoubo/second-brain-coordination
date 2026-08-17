"""Offline, deterministic, synthetic-only Stage-A IAGL supervisor.

This module deliberately has no network, subprocess, scheduler, webhook, or
domain-write capability.  Its SQLite store is local working state only and is
never a source of canonical governance or domain truth.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Mapping, Sequence


class SupervisorError(RuntimeError):
    """A fail-closed supervisor refusal."""


class Priority(IntEnum):
    P0_USER_OR_HIGH_RISK = 0
    P1_EXACT_HEAD_REVIEW = 1
    P2_BLOCKER_OR_DRIFT = 2
    P3_BOUNDED_IMPROVEMENT = 3
    P4_RESEARCH = 4


class SupervisorState(str, Enum):
    BOOT = "BOOT"
    GLOBAL_RECONCILIATION = "GLOBAL_RECONCILIATION"
    CHECK_PRIORITY = "CHECK_PRIORITY"
    WORK_SLICE = "WORK_SLICE"
    SAFEPOINT_CHECKPOINT = "SAFEPOINT_CHECKPOINT"
    PAUSED_FOR_HIGHER_PRIORITY = "PAUSED_FOR_HIGHER_PRIORITY"
    REVIEW = "REVIEW"
    USER_GATE = "USER_GATE"
    EVALUATE = "EVALUATE"
    LEARN = "LEARN"
    RESUME_VALIDATION = "RESUME_VALIDATION"
    RESUME = "RESUME"
    IDLE_NO_ELIGIBLE_WORK = "IDLE_NO_ELIGIBLE_WORK"
    FAILED_CLOSED = "FAILED_CLOSED"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class GovernanceMode(str, Enum):
    USER_CONTROLLED = "USER_CONTROLLED"
    AUTONOMOUS = "AUTONOMOUS"
    PAUSED = "PAUSED"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class Decision(str, Enum):
    EXECUTE_SYNTHETIC = "EXECUTE_SYNTHETIC"
    USER_GATE = "USER_GATE"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"
    IDLE = "IDLE"
    PREEMPT = "PREEMPT"


_ALLOWED_TRANSITIONS: dict[SupervisorState, set[SupervisorState]] = {
    SupervisorState.BOOT: {SupervisorState.GLOBAL_RECONCILIATION, SupervisorState.FAILED_CLOSED},
    SupervisorState.GLOBAL_RECONCILIATION: {SupervisorState.CHECK_PRIORITY, SupervisorState.FAILED_CLOSED},
    SupervisorState.CHECK_PRIORITY: {
        SupervisorState.WORK_SLICE,
        SupervisorState.USER_GATE,
        SupervisorState.IDLE_NO_ELIGIBLE_WORK,
        SupervisorState.FAILED_CLOSED,
        SupervisorState.EMERGENCY_STOP,
    },
    SupervisorState.WORK_SLICE: {SupervisorState.SAFEPOINT_CHECKPOINT, SupervisorState.REVIEW, SupervisorState.FAILED_CLOSED},
    SupervisorState.SAFEPOINT_CHECKPOINT: {SupervisorState.PAUSED_FOR_HIGHER_PRIORITY, SupervisorState.REVIEW, SupervisorState.FAILED_CLOSED},
    SupervisorState.PAUSED_FOR_HIGHER_PRIORITY: {SupervisorState.RESUME_VALIDATION, SupervisorState.USER_GATE},
    SupervisorState.RESUME_VALIDATION: {SupervisorState.RESUME, SupervisorState.FAILED_CLOSED, SupervisorState.USER_GATE},
    SupervisorState.RESUME: {SupervisorState.WORK_SLICE, SupervisorState.FAILED_CLOSED},
    SupervisorState.REVIEW: {SupervisorState.EVALUATE, SupervisorState.FAILED_CLOSED},
    SupervisorState.EVALUATE: {SupervisorState.LEARN, SupervisorState.FAILED_CLOSED},
    SupervisorState.LEARN: {SupervisorState.CHECK_PRIORITY, SupervisorState.IDLE_NO_ELIGIBLE_WORK},
    SupervisorState.USER_GATE: {SupervisorState.GLOBAL_RECONCILIATION, SupervisorState.IDLE_NO_ELIGIBLE_WORK},
    SupervisorState.IDLE_NO_ELIGIBLE_WORK: {SupervisorState.GLOBAL_RECONCILIATION},
    SupervisorState.FAILED_CLOSED: set(),
    SupervisorState.EMERGENCY_STOP: set(),
}


def canonical_digest(value: Any) -> str:
    """Hash a JSON-safe value without trusting caller supplied digest fields."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class NormalizedEvent:
    event_id: str
    event_class: str
    source: str
    repository: str
    observed_at: int
    target_ref: str
    target_identity: str
    payload_digest: str
    idempotency_key: str
    priority_hint: Priority

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "NormalizedEvent":
        required = ("event_id", "event_class", "source", "repository", "observed_at", "target_ref", "target_identity", "payload", "idempotency_key")
        missing = [key for key in required if key not in raw]
        if missing:
            raise SupervisorError(f"EVENT_MISSING_REQUIRED_FIELDS:{','.join(missing)}")
        if not all(isinstance(raw[key], str) and raw[key] for key in ("event_id", "event_class", "source", "repository", "target_ref", "target_identity", "idempotency_key")):
            raise SupervisorError("EVENT_INVALID_IDENTITY")
        if not isinstance(raw["observed_at"], int) or raw["observed_at"] < 0:
            raise SupervisorError("EVENT_INVALID_OBSERVED_AT")
        try:
            priority = Priority(int(raw.get("priority_hint", Priority.P4_RESEARCH)))
        except (TypeError, ValueError) as error:
            raise SupervisorError("EVENT_INVALID_PRIORITY") from error
        return cls(
            event_id=raw["event_id"], event_class=raw["event_class"], source=raw["source"],
            repository=raw["repository"], observed_at=raw["observed_at"], target_ref=raw["target_ref"],
            target_identity=raw["target_identity"], payload_digest=canonical_digest(raw["payload"]),
            idempotency_key=raw["idempotency_key"], priority_hint=priority,
        )


@dataclass(frozen=True)
class ReconciliationSnapshot:
    repository: str
    exact_head: str
    route_id: str
    governance_mode: GovernanceMode
    allowed_write_paths: tuple[str, ...]
    observed_at: int
    pending_p0: bool = False
    trusted: bool = True
    authority_revision: str = "synthetic-authority-v1"

    def validate(self, expected_repository: str) -> None:
        if not self.trusted:
            raise SupervisorError("RECONCILIATION_NOT_TRUSTED")
        if self.repository != expected_repository:
            raise SupervisorError("RECONCILIATION_REPOSITORY_MISMATCH")
        if not self.exact_head or not self.route_id or not self.authority_revision:
            raise SupervisorError("RECONCILIATION_INCOMPLETE")
        if any(not path or path.startswith("/") or ".." in path.replace("\\", "/").split("/") for path in self.allowed_write_paths):
            raise SupervisorError("RECONCILIATION_INVALID_ALLOWLIST")

    def identity(self) -> str:
        return canonical_digest({
            "repository": self.repository, "exact_head": self.exact_head, "route_id": self.route_id,
            "governance_mode": self.governance_mode.value, "allowed_write_paths": self.allowed_write_paths,
            "authority_revision": self.authority_revision,
        })


@dataclass(frozen=True)
class ImprovementSlice:
    slice_id: str
    priority: Priority
    changed_paths: tuple[str, ...]
    action_kind: str = "SYNTHETIC_FIXED_ACTION"
    estimated_cost: int = 1
    evidence_value: int = 1
    authority_metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self, snapshot: ReconciliationSnapshot) -> None:
        if not self.slice_id or self.estimated_cost < 0 or self.evidence_value < 0:
            raise SupervisorError("SLICE_INVALID")
        if self.action_kind != "SYNTHETIC_FIXED_ACTION":
            raise SupervisorError("ARBITRARY_EXECUTOR_BLOCKED")
        if not self.changed_paths or not set(self.changed_paths).issubset(set(snapshot.allowed_write_paths)):
            raise SupervisorError("SLICE_CHANGED_PATH_OUTSIDE_ALLOWLIST")
        # Caller metadata is descriptive only; it can never establish authority.
        if self.authority_metadata.get("authority") in {"trusted", "provider-issued"}:
            raise SupervisorError("CALLER_AUTHORITY_UNTRUSTED")


@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    slice_id: str
    sequence: int
    snapshot_identity: str
    exact_head: str
    route_id: str
    governance_mode: GovernanceMode
    fencing_token: str
    budget_used: int
    no_value_streak: int
    status: str
    created_at: int

    def to_record(self) -> str:
        value = asdict(self)
        value["governance_mode"] = self.governance_mode.value
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_record(cls, raw: str) -> "Checkpoint":
        value = json.loads(raw)
        value["governance_mode"] = GovernanceMode(value["governance_mode"])
        return cls(**value)


@dataclass(frozen=True)
class SupervisorReceipt:
    decision: Decision
    state: SupervisorState
    reason: str
    checkpoint_id: str | None = None
    process_compliance: str = "UNKNOWN"
    outcome_quality: str = "UNKNOWN"


class WorkingStateStore:
    """Task-local durable state; it is explicitly non-authoritative."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS seen_events (
                idempotency_key TEXT PRIMARY KEY,
                event_digest TEXT NOT NULL,
                seen_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS leases (
                lease_name TEXT PRIMARY KEY,
                fencing_token TEXT NOT NULL,
                owner TEXT NOT NULL,
                active INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                record TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS accounting (
                account_key TEXT PRIMARY KEY,
                integer_value INTEGER NOT NULL
            );
        """)
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def record_event_once(self, event: NormalizedEvent) -> bool:
        digest = canonical_digest(asdict(event) | {"priority_hint": int(event.priority_hint)})
        try:
            self._connection.execute("INSERT INTO seen_events VALUES (?, ?, ?)", (event.idempotency_key, digest, event.observed_at))
            self._connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def acquire_lease(self, lease_name: str, owner: str) -> str | None:
        row = self._connection.execute("SELECT fencing_token, active FROM leases WHERE lease_name=?", (lease_name,)).fetchone()
        if row and row[1]:
            return None
        token = str(uuid.uuid4())
        self._connection.execute(
            "INSERT INTO leases(lease_name, fencing_token, owner, active) VALUES (?, ?, ?, 1) "
            "ON CONFLICT(lease_name) DO UPDATE SET fencing_token=excluded.fencing_token, owner=excluded.owner, active=1",
            (lease_name, token, owner),
        )
        self._connection.commit()
        return token

    def release_lease(self, lease_name: str, token: str) -> bool:
        cursor = self._connection.execute("UPDATE leases SET active=0 WHERE lease_name=? AND fencing_token=? AND active=1", (lease_name, token))
        self._connection.commit()
        return cursor.rowcount == 1

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        self._connection.execute("INSERT OR REPLACE INTO checkpoints VALUES (?, ?)", (checkpoint.checkpoint_id, checkpoint.to_record()))
        self._connection.commit()

    def load_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        row = self._connection.execute("SELECT record FROM checkpoints WHERE checkpoint_id=?", (checkpoint_id,)).fetchone()
        return Checkpoint.from_record(row[0]) if row else None

    def increment(self, key: str, amount: int = 1) -> int:
        self._connection.execute(
            "INSERT INTO accounting(account_key, integer_value) VALUES (?, ?) "
            "ON CONFLICT(account_key) DO UPDATE SET integer_value=integer_value + excluded.integer_value", (key, amount)
        )
        self._connection.commit()
        return self.value(key)

    def value(self, key: str) -> int:
        row = self._connection.execute("SELECT integer_value FROM accounting WHERE account_key=?", (key,)).fetchone()
        return int(row[0]) if row else 0


class SyntheticSupervisor:
    """A bounded, synchronous mechanism model, never an external executor."""

    def __init__(self, repository: str, store: WorkingStateStore, budget_limit: int = 8, no_value_limit: int = 2):
        self.repository = repository
        self.store = store
        self.budget_limit = budget_limit
        self.no_value_limit = no_value_limit
        self.state = SupervisorState.BOOT

    def transition(self, target: SupervisorState) -> None:
        if target not in _ALLOWED_TRANSITIONS[self.state]:
            raise SupervisorError(f"ILLEGAL_TRANSITION:{self.state.value}->{target.value}")
        self.state = target

    def reconcile(self, snapshot: ReconciliationSnapshot) -> None:
        self.transition(SupervisorState.GLOBAL_RECONCILIATION)
        snapshot.validate(self.repository)
        if snapshot.governance_mode == GovernanceMode.EMERGENCY_STOP:
            self.transition(SupervisorState.CHECK_PRIORITY)
            self.transition(SupervisorState.EMERGENCY_STOP)
            raise SupervisorError("EMERGENCY_STOP")
        self.transition(SupervisorState.CHECK_PRIORITY)

    def ingest(self, raw_event: Mapping[str, Any]) -> tuple[NormalizedEvent, bool]:
        event = NormalizedEvent.from_mapping(raw_event)
        if event.repository != self.repository:
            raise SupervisorError("EVENT_REPOSITORY_MISMATCH")
        return event, self.store.record_event_once(event)

    def choose(self, snapshot: ReconciliationSnapshot, candidates: Sequence[ImprovementSlice]) -> SupervisorReceipt | ImprovementSlice:
        if snapshot.governance_mode == GovernanceMode.PAUSED:
            return SupervisorReceipt(Decision.UNKNOWN, SupervisorState.CHECK_PRIORITY, "GOVERNANCE_PAUSED")
        if snapshot.governance_mode == GovernanceMode.USER_CONTROLLED:
            self.transition(SupervisorState.USER_GATE)
            return SupervisorReceipt(Decision.USER_GATE, self.state, "USER_CONTROLLED_NO_AUTO_EXECUTION")
        if snapshot.pending_p0:
            self.transition(SupervisorState.USER_GATE)
            return SupervisorReceipt(Decision.USER_GATE, self.state, "P0_PENDING")
        if self.store.value("budget_used") >= self.budget_limit:
            self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK)
            return SupervisorReceipt(Decision.IDLE, self.state, "BUDGET_EXHAUSTED")
        if self.store.value("no_value_streak") >= self.no_value_limit:
            self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK)
            return SupervisorReceipt(Decision.IDLE, self.state, "VOI_NO_VALUE_STOP")
        if not candidates:
            self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK)
            return SupervisorReceipt(Decision.IDLE, self.state, "NO_ELIGIBLE_WORK")
        selected = min(candidates, key=lambda item: (int(item.priority), item.slice_id))
        selected.validate(snapshot)
        return selected

    def checkpoint(self, snapshot: ReconciliationSnapshot, slice_: ImprovementSlice, fencing_token: str, sequence: int, status: str) -> Checkpoint:
        self.transition(SupervisorState.SAFEPOINT_CHECKPOINT)
        checkpoint = Checkpoint(
            checkpoint_id=canonical_digest({
                "snapshot": snapshot.identity(), "slice_id": slice_.slice_id,
                "fencing_token": fencing_token, "sequence": sequence, "status": status,
            }),
            slice_id=slice_.slice_id, sequence=sequence,
            snapshot_identity=snapshot.identity(), exact_head=snapshot.exact_head, route_id=snapshot.route_id,
            governance_mode=snapshot.governance_mode, fencing_token=fencing_token,
            budget_used=self.store.value("budget_used"), no_value_streak=self.store.value("no_value_streak"),
            status=status, created_at=snapshot.observed_at,
        )
        self.store.save_checkpoint(checkpoint)
        return checkpoint

    def execute_synthetic(self, snapshot: ReconciliationSnapshot, slice_: ImprovementSlice, fencing_token: str, preempt_for: Priority | None = None) -> SupervisorReceipt:
        slice_.validate(snapshot)
        if self.state != SupervisorState.CHECK_PRIORITY:
            raise SupervisorError("EXECUTE_REQUIRES_RECONCILED_PRIORITY_STATE")
        self.transition(SupervisorState.WORK_SLICE)
        if preempt_for is not None and preempt_for < slice_.priority:
            checkpoint = self.checkpoint(snapshot, slice_, fencing_token, sequence=1, status="PREEMPTED")
            self.transition(SupervisorState.PAUSED_FOR_HIGHER_PRIORITY)
            return SupervisorReceipt(Decision.PREEMPT, self.state, "HIGHER_PRIORITY_AT_SAFEPOINT", checkpoint.checkpoint_id)
        self.store.increment("budget_used", slice_.estimated_cost)
        if slice_.evidence_value:
            self.store.increment("no_value_streak", -self.store.value("no_value_streak"))
        else:
            self.store.increment("no_value_streak")
        self.transition(SupervisorState.REVIEW)
        return SupervisorReceipt(Decision.EXECUTE_SYNTHETIC, self.state, "SYNTHETIC_FIXED_ACTION_COMPLETE", process_compliance="PASS", outcome_quality="UNKNOWN")

    def resume(self, checkpoint_id: str, fresh_snapshot: ReconciliationSnapshot) -> SupervisorReceipt:
        if self.state != SupervisorState.PAUSED_FOR_HIGHER_PRIORITY:
            raise SupervisorError("RESUME_REQUIRES_PAUSED_STATE")
        self.transition(SupervisorState.RESUME_VALIDATION)
        checkpoint = self.store.load_checkpoint(checkpoint_id)
        if checkpoint is None:
            self.transition(SupervisorState.FAILED_CLOSED)
            return SupervisorReceipt(Decision.BLOCKED, self.state, "CHECKPOINT_NOT_FOUND")
        fresh_snapshot.validate(self.repository)
        if (checkpoint.snapshot_identity != fresh_snapshot.identity() or checkpoint.exact_head != fresh_snapshot.exact_head or
                checkpoint.route_id != fresh_snapshot.route_id or checkpoint.governance_mode != fresh_snapshot.governance_mode):
            self.transition(SupervisorState.FAILED_CLOSED)
            return SupervisorReceipt(Decision.BLOCKED, self.state, "STALE_CHECKPOINT_RECONCILIATION_DRIFT")
        self.transition(SupervisorState.RESUME)
        self.transition(SupervisorState.WORK_SLICE)
        return SupervisorReceipt(Decision.EXECUTE_SYNTHETIC, self.state, "FRESH_RECONCILE_RESUME", checkpoint_id)
