"""Offline, deterministic, synthetic-only IAGL Stage-A supervisor.

The SQLite database is task-local working state.  It never supplies canonical
governance, domain truth, credentials, network access, or an external executor.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Mapping, Sequence


class SupervisorError(RuntimeError):
    """Fail-closed mechanism refusal."""


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
    EXECUTED = "EXECUTED"
    PREEMPTED = "PREEMPTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"
    USER_GATE = "USER_GATE"
    IDLE = "IDLE"
    UNKNOWN = "UNKNOWN"


# Exact frozen IAGL-RUNTIME-CONTRACTS.yaml transition table.
_ALLOWED: dict[SupervisorState, set[SupervisorState]] = {
    SupervisorState.BOOT: {SupervisorState.GLOBAL_RECONCILIATION, SupervisorState.EMERGENCY_STOP},
    SupervisorState.GLOBAL_RECONCILIATION: {SupervisorState.CHECK_PRIORITY, SupervisorState.FAILED_CLOSED, SupervisorState.EMERGENCY_STOP},
    SupervisorState.CHECK_PRIORITY: {SupervisorState.USER_GATE, SupervisorState.REVIEW, SupervisorState.WORK_SLICE, SupervisorState.IDLE_NO_ELIGIBLE_WORK, SupervisorState.EMERGENCY_STOP},
    SupervisorState.WORK_SLICE: {SupervisorState.SAFEPOINT_CHECKPOINT, SupervisorState.EVALUATE, SupervisorState.FAILED_CLOSED, SupervisorState.EMERGENCY_STOP},
    SupervisorState.SAFEPOINT_CHECKPOINT: {SupervisorState.PAUSED_FOR_HIGHER_PRIORITY, SupervisorState.WORK_SLICE, SupervisorState.EVALUATE, SupervisorState.FAILED_CLOSED},
    SupervisorState.PAUSED_FOR_HIGHER_PRIORITY: {SupervisorState.REVIEW, SupervisorState.USER_GATE, SupervisorState.GLOBAL_RECONCILIATION},
    SupervisorState.REVIEW: {SupervisorState.EVALUATE, SupervisorState.USER_GATE, SupervisorState.FAILED_CLOSED},
    SupervisorState.USER_GATE: {SupervisorState.GLOBAL_RECONCILIATION, SupervisorState.EMERGENCY_STOP},
    SupervisorState.EVALUATE: {SupervisorState.LEARN, SupervisorState.GLOBAL_RECONCILIATION, SupervisorState.FAILED_CLOSED},
    SupervisorState.LEARN: {SupervisorState.RESUME_VALIDATION, SupervisorState.CHECK_PRIORITY, SupervisorState.FAILED_CLOSED},
    SupervisorState.RESUME_VALIDATION: {SupervisorState.RESUME, SupervisorState.CHECK_PRIORITY, SupervisorState.FAILED_CLOSED},
    SupervisorState.RESUME: {SupervisorState.WORK_SLICE, SupervisorState.CHECK_PRIORITY, SupervisorState.FAILED_CLOSED},
    SupervisorState.IDLE_NO_ELIGIBLE_WORK: {SupervisorState.GLOBAL_RECONCILIATION, SupervisorState.EMERGENCY_STOP},
    SupervisorState.FAILED_CLOSED: {SupervisorState.GLOBAL_RECONCILIATION, SupervisorState.EMERGENCY_STOP},
    SupervisorState.EMERGENCY_STOP: set(),
}


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


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
    supplied_idempotency_key: str
    semantic_key: str
    priority_hint: Priority

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "NormalizedEvent":
        fields = ("event_id", "event_class", "source", "repository", "observed_at", "target_ref", "target_identity", "payload", "idempotency_key")
        missing = [name for name in fields if name not in raw]
        if missing or any(not isinstance(raw[name], str) or not raw[name] for name in fields if name not in {"observed_at", "payload"}):
            raise SupervisorError("EVENT_INVALID:" + ",".join(missing))
        if not isinstance(raw["observed_at"], int) or raw["observed_at"] < 0:
            raise SupervisorError("EVENT_INVALID_OBSERVED_AT")
        try:
            priority = Priority(int(raw.get("priority_hint", Priority.P4_RESEARCH)))
        except (TypeError, ValueError) as exc:
            raise SupervisorError("EVENT_INVALID_PRIORITY") from exc
        payload_digest = digest(raw["payload"])
        # The source and caller idempotency key are trace only.  A watchdog and
        # webhook with the same current target state receive one executable key.
        semantic_key = digest({"repository": raw["repository"], "target_ref": raw["target_ref"], "target_identity": raw["target_identity"], "payload": payload_digest})
        return cls(raw["event_id"], raw["event_class"], raw["source"], raw["repository"], raw["observed_at"], raw["target_ref"], raw["target_identity"], payload_digest, raw["idempotency_key"], semantic_key, priority)


@dataclass(frozen=True)
class ReconciliationSnapshot:
    repository: str
    exact_head: str
    route_id: str
    governance_mode: GovernanceMode
    allowed_write_paths: tuple[str, ...]
    observed_at: int
    pending_p0: bool = False
    domain_revision: str = "synthetic-domain-v1"
    trusted: bool = True

    def validate(self, expected_repository: str) -> None:
        if not self.trusted or self.repository != expected_repository or not self.exact_head or not self.route_id or not self.domain_revision:
            raise SupervisorError("RECONCILIATION_INCOMPLETE_OR_UNTRUSTED")
        if any(not item or item.startswith("/") or ".." in item.replace("\\", "/").split("/") for item in self.allowed_write_paths):
            raise SupervisorError("RECONCILIATION_INVALID_ALLOWLIST")

    def identity(self) -> str:
        return digest({"repository": self.repository, "head": self.exact_head, "route": self.route_id, "governance": self.governance_mode.value, "allowed": self.allowed_write_paths, "p0": self.pending_p0, "domain": self.domain_revision})


@dataclass(frozen=True)
class ReconciliationGrant:
    identity: str
    generation: int


@dataclass(frozen=True)
class ImprovementSlice:
    slice_id: str
    priority: Priority
    changed_paths: tuple[str, ...]
    estimated_cost: int = 1
    evidence_value: int = 1
    action_kind: str = "SYNTHETIC_FIXED_ACTION"
    authority_metadata: Mapping[str, Any] | None = None

    def validate(self, snapshot: ReconciliationSnapshot) -> None:
        if not self.slice_id or self.estimated_cost < 0 or self.evidence_value < 0 or self.action_kind != "SYNTHETIC_FIXED_ACTION":
            raise SupervisorError("SLICE_INVALID_OR_ARBITRARY_EXECUTOR")
        if not self.changed_paths or not set(self.changed_paths).issubset(snapshot.allowed_write_paths):
            raise SupervisorError("SLICE_CHANGED_PATH_OUTSIDE_ALLOWLIST")
        if (self.authority_metadata or {}).get("authority") in {"trusted", "provider-issued"}:
            raise SupervisorError("CALLER_AUTHORITY_UNTRUSTED")


@dataclass(frozen=True)
class LeaseGrant:
    slice_id: str
    owner: str
    generation: int
    fencing_token: str


@dataclass(frozen=True)
class ExecutionPlan:
    plan_id: str
    snapshot: ReconciliationGrant
    slice: ImprovementSlice


@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    slice_id: str
    snapshot_identity: str
    reconciliation_generation: int
    prior_lease_generation: int
    prior_fencing_token: str
    exact_head: str
    route_id: str
    domain_revision: str
    created_at: int


@dataclass(frozen=True)
class ReviewEvidence:
    target_head: str
    ci_head: str
    receipt_head: str
    reviewer_source: str


@dataclass(frozen=True)
class SupervisorReceipt:
    decision: Decision
    state: SupervisorState
    reason: str
    checkpoint_id: str | None = None
    process_compliance: str = "UNKNOWN"
    outcome_quality: str = "UNKNOWN"


def _slice_to_json(slice_: ImprovementSlice) -> str:
    value = asdict(slice_)
    value["priority"] = int(slice_.priority)
    return json.dumps(value, sort_keys=True)


def _slice_from_json(raw: str) -> ImprovementSlice:
    value = json.loads(raw)
    value["priority"] = Priority(value["priority"])
    value["changed_paths"] = tuple(value["changed_paths"])
    return ImprovementSlice(**value)


class WorkingStateStore:
    """Durable, bounded, non-authoritative Stage-A working state."""
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS reconciliation (slot INTEGER PRIMARY KEY CHECK(slot=1), identity TEXT NOT NULL, generation INTEGER NOT NULL, snapshot TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (semantic_key TEXT PRIMARY KEY, event_json TEXT NOT NULL, priority INTEGER NOT NULL, consumed INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS leases (slice_id TEXT PRIMARY KEY, owner TEXT NOT NULL, generation INTEGER NOT NULL, token TEXT NOT NULL, active INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS plans (plan_id TEXT PRIMARY KEY, identity TEXT NOT NULL, generation INTEGER NOT NULL, slice_json TEXT NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS checkpoints (checkpoint_id TEXT PRIMARY KEY, record TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS accounting (key TEXT PRIMARY KEY, value INTEGER NOT NULL);
        """)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def record_reconciliation(self, snapshot: ReconciliationSnapshot) -> ReconciliationGrant:
        row = self.connection.execute("SELECT generation FROM reconciliation WHERE slot=1").fetchone()
        generation = (row[0] if row else 0) + 1
        identity = snapshot.identity()
        stored = asdict(snapshot) | {"governance_mode": snapshot.governance_mode.value, "allowed_write_paths": list(snapshot.allowed_write_paths)}
        self.connection.execute("INSERT INTO reconciliation VALUES (1,?,?,?) ON CONFLICT(slot) DO UPDATE SET identity=excluded.identity,generation=excluded.generation,snapshot=excluded.snapshot", (identity, generation, json.dumps(stored, sort_keys=True)))
        self.connection.commit()
        return ReconciliationGrant(identity, generation)

    def current_snapshot(self) -> tuple[ReconciliationGrant, ReconciliationSnapshot] | None:
        row = self.connection.execute("SELECT identity,generation,snapshot FROM reconciliation WHERE slot=1").fetchone()
        if not row:
            return None
        data = json.loads(row[2]); data["governance_mode"] = GovernanceMode(data["governance_mode"]); data["allowed_write_paths"] = tuple(data["allowed_write_paths"])
        return ReconciliationGrant(row[0], row[1]), ReconciliationSnapshot(**data)

    def enqueue(self, event: NormalizedEvent) -> bool:
        try:
            self.connection.execute("INSERT INTO events(semantic_key,event_json,priority,consumed) VALUES (?,?,?,0)", (event.semantic_key, json.dumps(asdict(event) | {"priority_hint": int(event.priority_hint)}, sort_keys=True), int(event.priority_hint)))
            self.connection.commit(); return True
        except sqlite3.IntegrityError:
            return False

    def highest_event(self) -> NormalizedEvent | None:
        row = self.connection.execute("SELECT event_json FROM events WHERE consumed=0 ORDER BY priority,semantic_key LIMIT 1").fetchone()
        if not row: return None
        data = json.loads(row[0]); data["priority_hint"] = Priority(data["priority_hint"])
        return NormalizedEvent(**data)

    def consume_event(self, semantic_key: str) -> None:
        self.connection.execute("UPDATE events SET consumed=1 WHERE semantic_key=?", (semantic_key,)); self.connection.commit()

    def consume_event_for_target(self, target_identity: str) -> None:
        rows = self.connection.execute("SELECT semantic_key,event_json FROM events WHERE consumed=0").fetchall()
        for semantic_key, raw in rows:
            if json.loads(raw)["target_identity"] == target_identity:
                self.connection.execute("UPDATE events SET consumed=1 WHERE semantic_key=?", (semantic_key,))
        self.connection.commit()

    def acquire_lease(self, slice_id: str, owner: str) -> LeaseGrant | None:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute("SELECT generation,active FROM leases WHERE slice_id=?", (slice_id,)).fetchone()
            if row and row[1]: self.connection.execute("ROLLBACK"); return None
            generation = (row[0] if row else 0) + 1; token = str(uuid.uuid4())
            self.connection.execute("INSERT INTO leases VALUES (?,?,?,?,1) ON CONFLICT(slice_id) DO UPDATE SET owner=excluded.owner,generation=excluded.generation,token=excluded.token,active=1", (slice_id, owner, generation, token))
            self.connection.execute("COMMIT"); return LeaseGrant(slice_id, owner, generation, token)
        except Exception:
            self.connection.execute("ROLLBACK"); raise

    def execution_is_active(self, plan: ExecutionPlan, lease: LeaseGrant) -> bool:
        current = self.current_snapshot()
        plan_row = self.connection.execute("SELECT identity,generation,state FROM plans WHERE plan_id=?", (plan.plan_id,)).fetchone()
        lease_row = self.connection.execute("SELECT owner,generation,token,active FROM leases WHERE slice_id=?", (lease.slice_id,)).fetchone()
        return bool(current and plan_row == (current[0].identity, current[0].generation, "EXECUTING") and lease_row == (lease.owner, lease.generation, lease.fencing_token, 1))

    def release_lease(self, grant: LeaseGrant) -> bool:
        cur = self.connection.execute("UPDATE leases SET active=0 WHERE slice_id=? AND owner=? AND generation=? AND token=? AND active=1", (grant.slice_id, grant.owner, grant.generation, grant.fencing_token)); self.connection.commit(); return cur.rowcount == 1

    def create_plan(self, grant: ReconciliationGrant, slice_: ImprovementSlice) -> ExecutionPlan:
        plan_id = digest({"snapshot": grant.identity, "generation": grant.generation, "slice": _slice_to_json(slice_)})
        self.connection.execute("INSERT OR REPLACE INTO plans VALUES (?,?,?,?,?)", (plan_id, grant.identity, grant.generation, _slice_to_json(slice_), "READY")); self.connection.commit()
        return ExecutionPlan(plan_id, grant, slice_)

    def authorize_execution(self, plan: ExecutionPlan, lease: LeaseGrant, budget_limit: int) -> tuple[ImprovementSlice, ReconciliationSnapshot] | None:
        """Atomically bind current reconciliation, governance, lease/fence, plan and budget."""
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            current = self.current_snapshot(); plan_row = self.connection.execute("SELECT identity,generation,slice_json,state FROM plans WHERE plan_id=?", (plan.plan_id,)).fetchone(); lease_row = self.connection.execute("SELECT owner,generation,token,active FROM leases WHERE slice_id=?", (lease.slice_id,)).fetchone()
            if not current or not plan_row or plan_row[3] != "READY" or not lease_row:
                self.connection.execute("ROLLBACK"); return None
            current_grant, snapshot = current; slice_ = _slice_from_json(plan_row[2]); used = self.value("budget_used")
            valid = (plan_row[0] == current_grant.identity == plan.snapshot.identity and plan_row[1] == current_grant.generation == plan.snapshot.generation and lease_row == (lease.owner, lease.generation, lease.fencing_token, 1) and snapshot.governance_mode == GovernanceMode.AUTONOMOUS and not snapshot.pending_p0 and used + slice_.estimated_cost <= budget_limit)
            if not valid:
                self.connection.execute("ROLLBACK"); return None
            self.connection.execute("UPDATE plans SET state='EXECUTING' WHERE plan_id=?", (plan.plan_id,))
            self.connection.execute("INSERT INTO accounting VALUES ('budget_used',?) ON CONFLICT(key) DO UPDATE SET value=value+excluded.value", (slice_.estimated_cost,))
            self.connection.execute("COMMIT"); return slice_, snapshot
        except Exception:
            self.connection.execute("ROLLBACK"); raise

    def value(self, key: str) -> int:
        row = self.connection.execute("SELECT value FROM accounting WHERE key=?", (key,)).fetchone(); return int(row[0]) if row else 0

    def set_value(self, key: str, value: int) -> None:
        self.connection.execute("INSERT INTO accounting VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value)); self.connection.commit()

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        value = asdict(checkpoint); self.connection.execute("INSERT OR REPLACE INTO checkpoints VALUES (?,?)", (checkpoint.checkpoint_id, json.dumps(value, sort_keys=True))); self.connection.commit()

    def load_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        row = self.connection.execute("SELECT record FROM checkpoints WHERE checkpoint_id=?", (checkpoint_id,)).fetchone(); return Checkpoint(**json.loads(row[0])) if row else None


class SyntheticSupervisor:
    def __init__(self, repository: str, store: WorkingStateStore, budget_limit: int = 8, no_value_limit: int = 10):
        self.repository, self.store, self.budget_limit, self.no_value_limit = repository, store, budget_limit, no_value_limit
        self.state = SupervisorState.BOOT

    def transition(self, target: SupervisorState) -> None:
        if target not in _ALLOWED[self.state]: raise SupervisorError(f"ILLEGAL_TRANSITION:{self.state.value}->{target.value}")
        self.state = target

    def reconcile(self, snapshot: ReconciliationSnapshot) -> ReconciliationGrant:
        self.transition(SupervisorState.GLOBAL_RECONCILIATION); snapshot.validate(self.repository)
        if snapshot.governance_mode == GovernanceMode.EMERGENCY_STOP:
            self.transition(SupervisorState.EMERGENCY_STOP); raise SupervisorError("EMERGENCY_STOP")
        grant = self.store.record_reconciliation(snapshot); self.transition(SupervisorState.CHECK_PRIORITY); return grant

    def ingest(self, raw: Mapping[str, Any]) -> tuple[NormalizedEvent, bool]:
        event = NormalizedEvent.from_mapping(raw)
        if event.repository != self.repository: raise SupervisorError("EVENT_REPOSITORY_MISMATCH")
        return event, self.store.enqueue(event)

    def choose(self, grant: ReconciliationGrant, candidates: Sequence[ImprovementSlice]) -> ExecutionPlan | SupervisorReceipt:
        current = self.store.current_snapshot()
        if not current or current[0] != grant: raise SupervisorError("STALE_RECONCILIATION_GRANT")
        _, snapshot = current; pending = self.store.highest_event()
        if snapshot.governance_mode != GovernanceMode.AUTONOMOUS or snapshot.pending_p0 or (pending and pending.priority_hint == Priority.P0_USER_OR_HIGH_RISK):
            self.transition(SupervisorState.USER_GATE); return SupervisorReceipt(Decision.USER_GATE, self.state, "GOVERNANCE_OR_P0_GATE")
        if pending and pending.priority_hint == Priority.P1_EXACT_HEAD_REVIEW:
            self.transition(SupervisorState.REVIEW); return SupervisorReceipt(Decision.REVIEW_REQUIRED, self.state, "P1_EVENT_REQUIRES_REVIEW")
        if not candidates:
            self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK); return SupervisorReceipt(Decision.IDLE, self.state, "NO_ELIGIBLE_WORK")
        if self.store.value("no_value_streak") >= self.no_value_limit:
            self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK); return SupervisorReceipt(Decision.IDLE, self.state, "VOI_STOP")
        selected = min(candidates, key=lambda s: (int(s.priority), s.slice_id)); selected.validate(snapshot)
        if self.store.value("budget_used") + selected.estimated_cost > self.budget_limit:
            self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK); return SupervisorReceipt(Decision.IDLE, self.state, "BUDGET_EXHAUSTED_PRE_EXECUTION")
        return self.store.create_plan(grant, selected)

    def execute(self, plan: ExecutionPlan, lease: LeaseGrant) -> SupervisorReceipt:
        if self.state != SupervisorState.CHECK_PRIORITY:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "EXECUTION_NOT_AT_RECONCILED_PRIORITY_BOUNDARY")
        authorized = self.store.authorize_execution(plan, lease, self.budget_limit)
        if not authorized: return SupervisorReceipt(Decision.BLOCKED, self.state, "EXECUTION_BOUNDARY_REJECTED")
        _, _snapshot = authorized; self.transition(SupervisorState.WORK_SLICE)
        return SupervisorReceipt(Decision.EXECUTED, self.state, "SYNTHETIC_ATOMIC_ACTION", process_compliance="PASS", outcome_quality="UNKNOWN")

    def complete_atomic_slice(self, evidence_value: int) -> SupervisorReceipt:
        if self.state != SupervisorState.WORK_SLICE: return SupervisorReceipt(Decision.BLOCKED, self.state, "NOT_IN_WORK_SLICE")
        self.transition(SupervisorState.EVALUATE)
        self.store.set_value("no_value_streak", 0 if evidence_value else self.store.value("no_value_streak") + 1)
        return SupervisorReceipt(Decision.EXECUTED, self.state, "EVALUATED", outcome_quality="UNKNOWN")

    def safepoint(self, plan: ExecutionPlan, lease: LeaseGrant) -> SupervisorReceipt:
        return self.checkpoint_for_preemption(plan, lease)

    def checkpoint_for_preemption(self, plan: ExecutionPlan, lease: LeaseGrant) -> SupervisorReceipt:
        if self.state != SupervisorState.WORK_SLICE:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "SAFEPOINT_NOT_IN_WORK_SLICE")
        event = self.store.highest_event(); current = self.store.current_snapshot()
        if not event or not current or event.priority_hint >= plan.slice.priority: return SupervisorReceipt(Decision.UNKNOWN, self.state, "NO_PREEMPTION")
        if not self.store.execution_is_active(plan, lease): return SupervisorReceipt(Decision.BLOCKED, self.state, "STALE_OR_FORGED_FENCE")
        grant, snapshot = current; self.transition(SupervisorState.SAFEPOINT_CHECKPOINT)
        checkpoint = Checkpoint(digest({"plan": plan.plan_id, "event": event.semantic_key, "fence": lease.fencing_token}), plan.slice.slice_id, grant.identity, grant.generation, lease.generation, lease.fencing_token, snapshot.exact_head, snapshot.route_id, snapshot.domain_revision, snapshot.observed_at)
        self.store.save_checkpoint(checkpoint); self.store.release_lease(lease)
        self.transition(SupervisorState.PAUSED_FOR_HIGHER_PRIORITY)
        return SupervisorReceipt(Decision.PREEMPTED, self.state, "P1_PREEMPTION_AT_SAFEPOINT", checkpoint.checkpoint_id)

    def review(self, evidence: ReviewEvidence) -> SupervisorReceipt:
        if self.state == SupervisorState.PAUSED_FOR_HIGHER_PRIORITY: self.transition(SupervisorState.REVIEW)
        if self.state != SupervisorState.REVIEW: return SupervisorReceipt(Decision.BLOCKED, self.state, "REVIEW_NOT_READY")
        current = self.store.current_snapshot()
        if not current or not evidence.target_head or evidence.target_head != evidence.ci_head or evidence.target_head != evidence.receipt_head or evidence.target_head != current[1].exact_head or not evidence.reviewer_source:
            self.transition(SupervisorState.FAILED_CLOSED); return SupervisorReceipt(Decision.BLOCKED, self.state, "REVIEW_EXACT_HEAD_RECEIPT_MISMATCH")
        self.store.consume_event_for_target(evidence.target_head)
        self.transition(SupervisorState.EVALUATE); return SupervisorReceipt(Decision.EXECUTED, self.state, "P1_REVIEW_EXACT_HEAD_VALID")

    def resume_or_replan(self, checkpoint_id: str, fresh: ReconciliationGrant, lease: LeaseGrant) -> SupervisorReceipt:
        checkpoint = self.store.load_checkpoint(checkpoint_id); current = self.store.current_snapshot()
        if not checkpoint or not current or current[0] != fresh: return SupervisorReceipt(Decision.BLOCKED, self.state, "FRESH_RECONCILIATION_REQUIRED")
        _, snapshot = current
        if snapshot.governance_mode != GovernanceMode.AUTONOMOUS or snapshot.pending_p0 or checkpoint.route_id != snapshot.route_id or checkpoint.domain_revision != snapshot.domain_revision:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "CHECKPOINT_DRIFT_OR_GOVERNANCE_GATE")
        if self.state == SupervisorState.CHECK_PRIORITY: self.transition(SupervisorState.REVIEW); self.transition(SupervisorState.EVALUATE)
        if self.state == SupervisorState.EVALUATE: self.transition(SupervisorState.LEARN)
        if self.state != SupervisorState.LEARN: return SupervisorReceipt(Decision.BLOCKED, self.state, "RESUME_STATE_INVALID")
        self.transition(SupervisorState.RESUME_VALIDATION)
        row = self.store.connection.execute("SELECT owner,generation,token,active FROM leases WHERE slice_id=?", (lease.slice_id,)).fetchone()
        if row != (lease.owner, lease.generation, lease.fencing_token, 1) or lease.generation <= checkpoint.prior_lease_generation:
            self.transition(SupervisorState.FAILED_CLOSED); return SupervisorReceipt(Decision.BLOCKED, self.state, "STALE_OR_FORGED_FENCE")
        self.transition(SupervisorState.RESUME); self.transition(SupervisorState.WORK_SLICE)
        return SupervisorReceipt(Decision.EXECUTED, self.state, "FRESH_RECONCILE_RESUME_OR_REPLAN", checkpoint_id)
