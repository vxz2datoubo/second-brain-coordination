"""Offline, deterministic, synthetic-only IAGL Stage-A supervisor.

SQLite is only bounded task-local working state. It never supplies canonical
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
    BOOT = "BOOT"; GLOBAL_RECONCILIATION = "GLOBAL_RECONCILIATION"; CHECK_PRIORITY = "CHECK_PRIORITY"
    WORK_SLICE = "WORK_SLICE"; SAFEPOINT_CHECKPOINT = "SAFEPOINT_CHECKPOINT"; PAUSED_FOR_HIGHER_PRIORITY = "PAUSED_FOR_HIGHER_PRIORITY"
    REVIEW = "REVIEW"; USER_GATE = "USER_GATE"; EVALUATE = "EVALUATE"; LEARN = "LEARN"
    RESUME_VALIDATION = "RESUME_VALIDATION"; RESUME = "RESUME"; IDLE_NO_ELIGIBLE_WORK = "IDLE_NO_ELIGIBLE_WORK"
    FAILED_CLOSED = "FAILED_CLOSED"; EMERGENCY_STOP = "EMERGENCY_STOP"


class GovernanceMode(str, Enum):
    USER_CONTROLLED = "USER_CONTROLLED"; AUTONOMOUS = "AUTONOMOUS"; PAUSED = "PAUSED"; EMERGENCY_STOP = "EMERGENCY_STOP"


class Decision(str, Enum):
    EXECUTED = "EXECUTED"; PREEMPTED = "PREEMPTED"; REVIEW_REQUIRED = "REVIEW_REQUIRED"; BLOCKED = "BLOCKED"
    USER_GATE = "USER_GATE"; IDLE = "IDLE"; UNKNOWN = "UNKNOWN"


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

_P0_EVENT_CLASSES = {
    "USER_COMMAND", "SECRET_PERMISSION", "SECRET_REQUEST", "PERMISSION_REQUEST",
    "PRODUCTION", "PRODUCTION_REQUEST", "TRADING_FUNDS", "TRADING_REQUEST",
    "DESTRUCTIVE_HISTORY", "DESTRUCTIVE_REQUEST", "USER_GOVERNANCE_CHANGED",
}
_P1_EVENT_CLASSES = {
    "PR_HEAD_CHANGED", "WORKFLOW_COMPLETED", "REVIEW_REQUESTED", "REVIEW_SUBMITTED",
    "CODEX_PR_READY", "REMEDIATION_READY", "CI_COMPLETED_FOR_REVIEW_HEAD",
}
_P2_EVENT_CLASSES = {
    "TASK_ROUTE_CHANGED", "CLAIM_OR_LEASE_CHANGED", "ROUTE_DRIFT", "CLAIM_COLLISION",
    "SECURITY_REGRESSION", "FALSE_GREEN", "ACTIVE_BLOCKER",
}
_P3_EVENT_CLASSES = {"SIGNAL_MATERIALITY_CHANGED"}
_P4_EVENT_CLASSES = {"WATCHDOG_TICK"}
_HIGH_RISK_PAYLOAD_TOKENS = {
    "secret", "credential", "api_key", "apikey", "permission", "github_permission",
    "production", "deploy", "deployment", "trading", "trade", "order", "fund", "funds",
    "destructive", "force_push", "force-push", "rebase", "reset", "private_key", "token",
}
_INVALID_GOALS = {
    "improve system generally",
    "research indefinitely",
    "browse until something interesting appears",
}
_STAGE_A_TOOL_CEILING = frozenset({"stdlib-only"})
_STAGE_A_DATA_CEILING = frozenset({"PUBLIC_SAFE_SYNTHETIC"})
_STAGE_A_RISK_CEILING = frozenset({"P3_SYNTHETIC", "P4_SYNTHETIC"})
_STAGE_A_WRITEBACK_CEILING = frozenset({"NO_CANONICAL_WRITE"})
_FORBIDDEN_TOOL_TOKENS = ("network", "shell", "bash", "powershell", "cmd", "subprocess", "daemon", "socket", "requests", "curl", "wget", "webhook", "scheduler", "exec")
_FORBIDDEN_DATA_TOKENS = ("private", "raw", "conversation", "credential", "secret", "cookie", "token", "key", "media")
_FORBIDDEN_RISK_TOKENS = ("production", "trading", "fund", "destructive", "secret", "permission", "high_risk", "c3", "c4")
_FORBIDDEN_WRITEBACK_TOKENS = ("w3", "domain", "canonical", "production", "trade", "trading")
_REQUIRED_RESUME_PRECONDITIONS = {"FRESH_RECONCILIATION", "AUTONOMOUS", "NO_PENDING_P0", "MATCHING_SLICE", "NEW_FENCE"}


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _nonempty(values: Sequence[object]) -> bool:
    return all(isinstance(value, str) and bool(value) for value in values)


def _normalized(value: str) -> str:
    return value.strip().lower()


def _flatten_payload_tokens(value: Any) -> set[str]:
    tokens: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            tokens.update(_flatten_payload_tokens(str(key)))
            tokens.update(_flatten_payload_tokens(item))
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            tokens.update(_flatten_payload_tokens(item))
    elif isinstance(value, str):
        normalized = value.strip().lower().replace(" ", "_")
        tokens.add(normalized)
        for separator in ("/", ":", "=", ",", ";", "|"):
            normalized = normalized.replace(separator, "_")
        tokens.update(part for part in normalized.split("_") if part)
    return tokens


def _risk_markers(payload: Any) -> tuple[str, ...]:
    tokens = _flatten_payload_tokens(payload)
    markers = sorted(token for token in _HIGH_RISK_PAYLOAD_TOKENS if token in tokens)
    return tuple(markers)


def _class_priority_hint(event_class: str) -> Priority:
    normalized = event_class.strip().upper()
    if normalized in _P0_EVENT_CLASSES:
        return Priority.P0_USER_OR_HIGH_RISK
    if normalized in _P1_EVENT_CLASSES:
        return Priority.P1_EXACT_HEAD_REVIEW
    if normalized in _P2_EVENT_CLASSES:
        return Priority.P2_BLOCKER_OR_DRIFT
    if normalized in _P3_EVENT_CLASSES:
        return Priority.P3_BOUNDED_IMPROVEMENT
    if normalized in _P4_EVENT_CLASSES:
        return Priority.P4_RESEARCH
    return Priority.P2_BLOCKER_OR_DRIFT


def _slice_digest(slice_: "ImprovementSlice") -> str:
    return digest(_slice_to_json(slice_))


@dataclass(frozen=True)
class NormalizedEvent:
    event_id: str; event_class: str; source: str; repository: str; observed_at: int
    target_ref: str; target_identity: str; payload_digest: str; supplied_idempotency_key: str
    semantic_key: str; priority_hint: Priority; class_priority_hint: Priority; risk_markers: tuple[str, ...]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "NormalizedEvent":
        names = ("event_id", "event_class", "source", "repository", "observed_at", "target_ref", "target_identity", "payload", "idempotency_key")
        missing = [name for name in names if name not in raw]
        if missing or not _nonempty([raw[n] for n in names if n not in {"observed_at", "payload"}]):
            raise SupervisorError("EVENT_INVALID:" + ",".join(missing))
        if not isinstance(raw["observed_at"], int) or raw["observed_at"] < 0:
            raise SupervisorError("EVENT_INVALID_OBSERVED_AT")
        try:
            priority_hint = Priority(int(raw.get("priority_hint", Priority.P4_RESEARCH)))
        except (TypeError, ValueError) as exc:
            raise SupervisorError("EVENT_INVALID_PRIORITY") from exc
        payload_digest = digest(raw["payload"])
        event_class = str(raw["event_class"])
        semantic_key = digest({
            "repository": raw["repository"], "event_class": event_class.upper(),
            "target_ref": raw["target_ref"], "target_identity": raw["target_identity"],
            "payload": payload_digest,
        })
        return cls(
            raw["event_id"], event_class, raw["source"], raw["repository"], raw["observed_at"],
            raw["target_ref"], raw["target_identity"], payload_digest, raw["idempotency_key"],
            semantic_key, priority_hint, _class_priority_hint(event_class), _risk_markers(raw["payload"]),
        )


@dataclass(frozen=True)
class ReconciliationSnapshot:
    repository: str; exact_head: str; route_id: str; governance_mode: GovernanceMode
    allowed_write_paths: tuple[str, ...]; observed_at: int; pending_p0: bool = False
    domain_revision: str = "synthetic-domain-v1"; trusted: bool = True
    eligible_work_queue_complete: bool = False
    allowed_tools: tuple[str, ...] = ("stdlib-only",)
    allowed_data_classes: tuple[str, ...] = ("PUBLIC_SAFE_SYNTHETIC",)
    allowed_risk_classes: tuple[str, ...] = ("P3_SYNTHETIC", "P4_SYNTHETIC")
    allowed_writeback_plans: tuple[str, ...] = ("NO_CANONICAL_WRITE",)
    active_p2_event_keys: tuple[str, ...] = ()
    active_p2_classes: tuple[str, ...] = ()

    def validate(self, expected_repository: str) -> None:
        if not self.trusted or self.repository != expected_repository or not _nonempty((self.exact_head, self.route_id, self.domain_revision)):
            raise SupervisorError("RECONCILIATION_INCOMPLETE_OR_UNTRUSTED")
        if not self.allowed_write_paths or any(not item or item.startswith("/") or ".." in item.replace("\\", "/").split("/") for item in self.allowed_write_paths):
            raise SupervisorError("RECONCILIATION_INVALID_ALLOWLIST")
        if not all((self.allowed_tools, self.allowed_data_classes, self.allowed_risk_classes, self.allowed_writeback_plans)):
            raise SupervisorError("RECONCILIATION_POLICY_INCOMPLETE")
        if not set(self.allowed_tools).issubset(_STAGE_A_TOOL_CEILING):
            raise SupervisorError("RECONCILIATION_STAGE_A_TOOL_CEILING")
        if not set(self.allowed_data_classes).issubset(_STAGE_A_DATA_CEILING):
            raise SupervisorError("RECONCILIATION_STAGE_A_DATA_CEILING")
        if not set(self.allowed_risk_classes).issubset(_STAGE_A_RISK_CEILING):
            raise SupervisorError("RECONCILIATION_STAGE_A_RISK_CEILING")
        if not set(self.allowed_writeback_plans).issubset(_STAGE_A_WRITEBACK_CEILING):
            raise SupervisorError("RECONCILIATION_STAGE_A_WRITEBACK_CEILING")
        if any(not isinstance(item, str) or not item for item in self.active_p2_event_keys + self.active_p2_classes):
            raise SupervisorError("RECONCILIATION_P2_OBSERVATION_INVALID")

    def identity(self) -> str:
        return digest({
            "repository": self.repository, "head": self.exact_head, "route": self.route_id,
            "governance": self.governance_mode.value, "allowed": self.allowed_write_paths,
            "p0": self.pending_p0, "domain": self.domain_revision,
            "queue_complete": self.eligible_work_queue_complete,
            "allowed_tools": self.allowed_tools, "allowed_data_classes": self.allowed_data_classes,
            "allowed_risk_classes": self.allowed_risk_classes,
            "allowed_writeback_plans": self.allowed_writeback_plans,
            "active_p2_event_keys": self.active_p2_event_keys,
            "active_p2_classes": self.active_p2_classes,
        })


@dataclass(frozen=True)
class ReconciliationGrant:
    identity: str; generation: int


@dataclass(frozen=True)
class RetrievalProviderObservation:
    observation_id: str; provider_source: str; repository: str; exact_revision: str
    request_digest: str; authority_scope_ref: str; evidence_ref: str; complete_empty: bool

    def validate(self) -> None:
        if self.provider_source != "SYNTHETIC_RETRIEVAL_PROVIDER" or not self.complete_empty:
            raise SupervisorError("RETRIEVAL_PROVIDER_OBSERVATION_UNTRUSTED")
        if not _nonempty((self.observation_id, self.repository, self.exact_revision, self.request_digest, self.authority_scope_ref, self.evidence_ref)):
            raise SupervisorError("RETRIEVAL_PROVIDER_OBSERVATION_INCOMPLETE")

    def observation_digest(self) -> str:
        return digest(asdict(self))


class SyntheticRetrievalProvider:
    """Pre-seeded Stage-A provider boundary; issuance cannot create observations."""
    def __init__(self, observations: Sequence[RetrievalProviderObservation] = ()):
        self._observations: dict[tuple[str, str, str, str], RetrievalProviderObservation] = {}
        for observation in observations:
            observation.validate()
            key = (observation.repository, observation.exact_revision, observation.request_digest, observation.authority_scope_ref)
            if key in self._observations:
                raise SupervisorError("DUPLICATE_RETRIEVAL_PROVIDER_OBSERVATION")
            self._observations[key] = observation

    def observe_complete_empty(self, repository: str, exact_revision: str, request_digest: str, authority_scope_ref: str) -> RetrievalProviderObservation | None:
        return self._observations.get((repository, exact_revision, request_digest, authority_scope_ref))


@dataclass(frozen=True)
class RetrievalCompletenessProof:
    """Structural envelope; trusted semantics also require provider/store issuance."""
    repository: str; exact_revision: str; request_digest: str; authority_scope_ref: str
    evidence_ref: str; provider_observation_ref: str; provider_observation_digest: str
    reconciliation_identity: str; reconciliation_generation: int; complete_empty: bool
    issuance_ref: str = ""

    def structurally_matches(self, snapshot: ReconciliationSnapshot, grant: ReconciliationGrant, request_digest: str) -> bool:
        return bool(
            self.complete_empty
            and _nonempty((self.repository, self.exact_revision, self.request_digest, self.authority_scope_ref, self.evidence_ref, self.provider_observation_ref, self.provider_observation_digest, self.reconciliation_identity, self.issuance_ref))
            and self.repository == snapshot.repository
            and self.exact_revision == snapshot.exact_head
            and self.request_digest == request_digest
            and self.reconciliation_identity == grant.identity
            and self.reconciliation_generation == grant.generation
        )

    def proof_digest(self) -> str:
        return digest(asdict(self))


@dataclass(frozen=True)
class ImprovementSlice:
    """Frozen contract fields in public-safe synthetic forms plus R141 changed paths."""
    slice_id: str; priority: Priority; changed_paths: tuple[str, ...]
    source_signal_refs: tuple[str, ...]; problem_signature: str; goal: str; materiality: str; evidence_target: str
    allowed_tools: tuple[str, ...]; allowed_data_classes: tuple[str, ...]; risk_class: str
    time_budget_minutes: int; compute_budget: int; expected_artifact: str; falsifier: str
    stop_conditions: tuple[str, ...]; writeback_plan: str; owner: str
    estimated_cost: int = 1; evidence_value: int = 1; action_kind: str = "SYNTHETIC_FIXED_ACTION"
    authority_metadata: Mapping[str, Any] | None = None

    def validate(self, snapshot: ReconciliationSnapshot) -> None:
        strings = (self.slice_id, self.problem_signature, self.goal, self.materiality, self.evidence_target, self.risk_class, self.expected_artifact, self.falsifier, self.writeback_plan, self.owner)
        if not _nonempty(strings) or not self.source_signal_refs or not self.allowed_tools or not self.allowed_data_classes or not self.stop_conditions or self.time_budget_minutes <= 0 or self.compute_budget <= 0 or self.estimated_cost < 0 or self.evidence_value < 0 or self.action_kind != "SYNTHETIC_FIXED_ACTION":
            raise SupervisorError("SLICE_FROZEN_CONTRACT_INCOMPLETE")
        if self.priority not in {Priority.P3_BOUNDED_IMPROVEMENT, Priority.P4_RESEARCH}:
            raise SupervisorError("SLICE_PRIORITY_NOT_IMPROVEMENT_CLASS")
        if not self.changed_paths or not set(self.changed_paths).issubset(snapshot.allowed_write_paths):
            raise SupervisorError("SLICE_CHANGED_PATH_OUTSIDE_ALLOWLIST")
        if _normalized(self.goal) in _INVALID_GOALS:
            raise SupervisorError("SLICE_INVALID_GOAL")
        if any(any(token in _normalized(tool) for token in _FORBIDDEN_TOOL_TOKENS) for tool in self.allowed_tools) or not set(self.allowed_tools).issubset(_STAGE_A_TOOL_CEILING):
            raise SupervisorError("SLICE_FORBIDDEN_TOOL")
        if not set(self.allowed_tools).issubset(set(snapshot.allowed_tools)):
            raise SupervisorError("SLICE_TOOL_POLICY_DRIFT")
        if any(any(token in _normalized(data_class) for token in _FORBIDDEN_DATA_TOKENS) for data_class in self.allowed_data_classes) or not set(self.allowed_data_classes).issubset(_STAGE_A_DATA_CEILING):
            raise SupervisorError("SLICE_FORBIDDEN_DATA_CLASS")
        if not set(self.allowed_data_classes).issubset(set(snapshot.allowed_data_classes)):
            raise SupervisorError("SLICE_DATA_POLICY_DRIFT")
        if any(token in _normalized(self.risk_class) for token in _FORBIDDEN_RISK_TOKENS) or self.risk_class not in _STAGE_A_RISK_CEILING:
            raise SupervisorError("SLICE_FORBIDDEN_RISK_CLASS")
        if self.risk_class not in snapshot.allowed_risk_classes:
            raise SupervisorError("SLICE_RISK_POLICY_DRIFT")
        if self.writeback_plan not in _STAGE_A_WRITEBACK_CEILING:
            raise SupervisorError("SLICE_FORBIDDEN_WRITEBACK")
        if self.writeback_plan not in snapshot.allowed_writeback_plans:
            raise SupervisorError("SLICE_WRITEBACK_POLICY_DRIFT")
        if (self.authority_metadata or {}).get("authority") in {"trusted", "provider-issued"}:
            raise SupervisorError("CALLER_AUTHORITY_UNTRUSTED")


@dataclass(frozen=True)
class LeaseGrant:
    slice_id: str; owner: str; generation: int; fencing_token: str


@dataclass(frozen=True)
class ExecutionPlan:
    plan_id: str; snapshot: ReconciliationGrant; slice: ImprovementSlice


@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str; mission_id: str; slice_id: str; plan_id: str; slice_digest: str
    state: str; created_at: int; control_plane_snapshot_ref: str
    source_refs: tuple[str, ...]; evidence_digests: tuple[str, ...]
    completed_atomic_steps: tuple[str, ...]; open_unknowns: tuple[str, ...]; next_atomic_action: str
    budget_state: str; lease_state: str; fencing_token_ref: str; interruption_reason: str
    resume_preconditions: tuple[str, ...]; privacy_class: str
    snapshot_identity: str; reconciliation_generation: int; prior_lease_generation: int
    exact_head: str; route_id: str; domain_revision: str

    def validate(self) -> None:
        strings = (self.checkpoint_id, self.mission_id, self.slice_id, self.plan_id, self.slice_digest, self.state, self.control_plane_snapshot_ref, self.next_atomic_action, self.budget_state, self.lease_state, self.fencing_token_ref, self.interruption_reason, self.privacy_class, self.snapshot_identity, self.exact_head, self.route_id, self.domain_revision)
        if not _nonempty(strings) or not self.source_refs or not self.evidence_digests or not self.completed_atomic_steps or not self.open_unknowns or not self.resume_preconditions or self.reconciliation_generation <= 0 or self.prior_lease_generation <= 0:
            raise SupervisorError("CHECKPOINT_FROZEN_CONTRACT_INCOMPLETE")
        if self.privacy_class != "PUBLIC_SAFE_SYNTHETIC":
            raise SupervisorError("CHECKPOINT_PRIVACY_NOT_PUBLIC_SAFE")
        if not _REQUIRED_RESUME_PRECONDITIONS.issubset(set(self.resume_preconditions)):
            raise SupervisorError("CHECKPOINT_RESUME_PRECONDITIONS_INCOMPLETE")


@dataclass(frozen=True)
class ReviewWorkIdentity:
    semantic_event_key: str; target_head: str; reconciliation_identity: str; reconciliation_generation: int

    def key(self) -> str:
        return digest(asdict(self))


@dataclass(frozen=True)
class ReviewEvidence:
    target_head: str; ci_head: str; receipt_head: str; reviewer_source: str; work: ReviewWorkIdentity


@dataclass(frozen=True)
class SupervisorReceipt:
    decision: Decision; state: SupervisorState; reason: str; checkpoint_id: str | None = None
    process_compliance: str = "UNKNOWN"; outcome_quality: str = "UNKNOWN"


def _slice_to_json(slice_: ImprovementSlice) -> str:
    value = asdict(slice_); value["priority"] = int(slice_.priority)
    for name in ("changed_paths", "source_signal_refs", "allowed_tools", "allowed_data_classes", "stop_conditions"):
        value[name] = list(value[name])
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _slice_from_json(raw: str) -> ImprovementSlice:
    value = json.loads(raw); value["priority"] = Priority(value["priority"])
    for name in ("changed_paths", "source_signal_refs", "allowed_tools", "allowed_data_classes", "stop_conditions"):
        value[name] = tuple(value[name])
    return ImprovementSlice(**value)


def _event_to_json(event: NormalizedEvent) -> str:
    value = asdict(event); value["priority_hint"] = int(event.priority_hint); value["class_priority_hint"] = int(event.class_priority_hint); value["risk_markers"] = list(event.risk_markers)
    return json.dumps(value, sort_keys=True)


def _event_from_json(raw: str) -> NormalizedEvent:
    data = json.loads(raw); data["priority_hint"] = Priority(data["priority_hint"]); data["class_priority_hint"] = Priority(data["class_priority_hint"]); data["risk_markers"] = tuple(data["risk_markers"])
    return NormalizedEvent(**data)


class WorkingStateStore:
    """Durable, bounded, non-authoritative Stage-A working state."""
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True); self.connection = sqlite3.connect(path)
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS reconciliation (slot INTEGER PRIMARY KEY CHECK(slot=1), identity TEXT NOT NULL, generation INTEGER NOT NULL, snapshot TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (semantic_key TEXT PRIMARY KEY, event_json TEXT NOT NULL, priority INTEGER NOT NULL, adjudication_generation INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'PENDING');
        CREATE TABLE IF NOT EXISTS review_work (work_key TEXT PRIMARY KEY, semantic_key TEXT NOT NULL UNIQUE, target_head TEXT NOT NULL, identity TEXT NOT NULL, generation INTEGER NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS leases (slice_id TEXT PRIMARY KEY, owner TEXT NOT NULL, generation INTEGER NOT NULL, token TEXT NOT NULL, active INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS plans (plan_id TEXT PRIMARY KEY, identity TEXT NOT NULL, generation INTEGER NOT NULL, slice_json TEXT NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS checkpoints (checkpoint_id TEXT PRIMARY KEY, record TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS retrieval_proofs (issuance_ref TEXT PRIMARY KEY, proof_digest TEXT NOT NULL, provider_observation_digest TEXT NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS accounting (key TEXT PRIMARY KEY, value INTEGER NOT NULL);
        """); self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def record_reconciliation(self, snapshot: ReconciliationSnapshot) -> ReconciliationGrant:
        row = self.connection.execute("SELECT generation FROM reconciliation WHERE slot=1").fetchone()
        generation = (row[0] if row else 0) + 1; identity = snapshot.identity()
        stored = asdict(snapshot) | {"governance_mode": snapshot.governance_mode.value}
        for name in ("allowed_write_paths", "allowed_tools", "allowed_data_classes", "allowed_risk_classes", "allowed_writeback_plans", "active_p2_event_keys", "active_p2_classes"):
            stored[name] = list(stored[name])
        self.connection.execute(
            "INSERT INTO reconciliation VALUES (1,?,?,?) ON CONFLICT(slot) DO UPDATE SET identity=excluded.identity,generation=excluded.generation,snapshot=excluded.snapshot",
            (identity, generation, json.dumps(stored, sort_keys=True)),
        )
        grant = ReconciliationGrant(identity, generation)
        self._adjudicate_pending_events(snapshot, grant)
        self.connection.commit(); return grant

    def _adjudicate_pending_events(self, snapshot: ReconciliationSnapshot, grant: ReconciliationGrant) -> None:
        active_keys = set(snapshot.active_p2_event_keys)
        active_classes = {item.upper() for item in snapshot.active_p2_classes}
        rows = self.connection.execute("SELECT semantic_key,event_json,state FROM events WHERE state='PENDING'").fetchall()
        for semantic_key, raw, _state in rows:
            event = _event_from_json(raw); event_class = event.event_class.upper()
            if event.risk_markers or event_class in _P0_EVENT_CLASSES:
                priority, state = Priority.P0_USER_OR_HIGH_RISK, "PENDING"
            elif event_class in _P1_EVENT_CLASSES:
                if event.target_identity == snapshot.exact_head:
                    priority, state = Priority.P1_EXACT_HEAD_REVIEW, "PENDING"
                else:
                    priority, state = Priority.P1_EXACT_HEAD_REVIEW, "TRACE_ONLY"
            elif event_class in _P2_EVENT_CLASSES or event.class_priority_hint == Priority.P2_BLOCKER_OR_DRIFT:
                if semantic_key in active_keys or event_class in active_classes:
                    priority, state = Priority.P2_BLOCKER_OR_DRIFT, "PENDING"
                else:
                    priority, state = Priority.P2_BLOCKER_OR_DRIFT, "RESOLVED_TRACE"
            elif event_class in _P3_EVENT_CLASSES:
                priority, state = Priority.P3_BOUNDED_IMPROVEMENT, "PENDING"
            elif event_class in _P4_EVENT_CLASSES:
                priority, state = Priority.P4_RESEARCH, "PENDING"
            else:
                priority, state = Priority.P2_BLOCKER_OR_DRIFT, "RESOLVED_TRACE"
            self.connection.execute("UPDATE events SET priority=?, adjudication_generation=?, state=? WHERE semantic_key=?", (int(priority), grant.generation, state, semantic_key))

    def current_snapshot(self) -> tuple[ReconciliationGrant, ReconciliationSnapshot] | None:
        row = self.connection.execute("SELECT identity,generation,snapshot FROM reconciliation WHERE slot=1").fetchone()
        if not row:
            return None
        data = json.loads(row[2]); data["governance_mode"] = GovernanceMode(data["governance_mode"])
        for name in ("allowed_write_paths", "allowed_tools", "allowed_data_classes", "allowed_risk_classes", "allowed_writeback_plans", "active_p2_event_keys", "active_p2_classes"):
            data[name] = tuple(data[name])
        return ReconciliationGrant(row[0], row[1]), ReconciliationSnapshot(**data)

    def enqueue(self, event: NormalizedEvent) -> bool:
        provisional = Priority.P0_USER_OR_HIGH_RISK if event.risk_markers else Priority.P2_BLOCKER_OR_DRIFT
        try:
            self.connection.execute(
                "INSERT INTO events(semantic_key,event_json,priority,adjudication_generation,state) VALUES (?,?,?,?, 'PENDING')",
                (event.semantic_key, _event_to_json(event), int(provisional), 0),
            )
            self.connection.commit(); return True
        except sqlite3.IntegrityError:
            return False

    def has_unadjudicated_events(self, generation: int) -> bool:
        row = self.connection.execute("SELECT 1 FROM events WHERE state='PENDING' AND adjudication_generation<>? LIMIT 1", (generation,)).fetchone()
        return bool(row)

    def highest_event(self, generation: int) -> NormalizedEvent | None:
        row = self.connection.execute("SELECT event_json FROM events WHERE state='PENDING' AND adjudication_generation=? ORDER BY priority,semantic_key LIMIT 1", (generation,)).fetchone()
        return _event_from_json(row[0]) if row else None

    def highest_preemption_event(self, generation: int, work_priority: Priority) -> tuple[NormalizedEvent, Priority] | None:
        rows = self.connection.execute("SELECT event_json,priority,adjudication_generation FROM events WHERE state='PENDING' ORDER BY semantic_key").fetchall()
        candidates: list[tuple[Priority, str, NormalizedEvent]] = []
        for raw, priority_raw, adjudication_generation in rows:
            event = _event_from_json(raw)
            if adjudication_generation == generation:
                effective = Priority(priority_raw)
            else:
                effective = Priority.P0_USER_OR_HIGH_RISK if event.risk_markers else Priority.P2_BLOCKER_OR_DRIFT
            if effective < work_priority:
                candidates.append((effective, event.semantic_key, event))
        if not candidates:
            return None
        effective, _key, event = min(candidates, key=lambda item: (int(item[0]), item[1]))
        return event, effective

    def current_p1_event(self, exact_head: str, generation: int) -> NormalizedEvent | None:
        row = self.connection.execute("SELECT event_json FROM events WHERE priority=1 AND adjudication_generation=? AND state='PENDING' ORDER BY semantic_key LIMIT 1", (generation,)).fetchone()
        if not row:
            return None
        event = _event_from_json(row[0])
        return event if event.target_identity == exact_head else None

    def event_state(self, semantic_key: str) -> str | None:
        row = self.connection.execute("SELECT state FROM events WHERE semantic_key=?", (semantic_key,)).fetchone(); return row[0] if row else None

    def event_priority(self, semantic_key: str) -> Priority | None:
        row = self.connection.execute("SELECT priority FROM events WHERE semantic_key=?", (semantic_key,)).fetchone(); return Priority(row[0]) if row else None

    def create_review_work(self, event: NormalizedEvent, grant: ReconciliationGrant) -> ReviewWorkIdentity:
        work = ReviewWorkIdentity(event.semantic_key, event.target_identity, grant.identity, grant.generation)
        self.connection.execute("INSERT OR IGNORE INTO review_work VALUES (?,?,?,?,?,'READY')", (work.key(), work.semantic_event_key, work.target_head, work.reconciliation_identity, work.reconciliation_generation)); self.connection.commit(); return work

    def consume_review_work(self, work: ReviewWorkIdentity, grant: ReconciliationGrant) -> bool:
        cur = self.connection.execute(
            "UPDATE review_work SET state='CONSUMED' WHERE work_key=? AND semantic_key=? AND target_head=? AND identity=? AND generation=? AND state='READY'",
            (work.key(), work.semantic_event_key, work.target_head, grant.identity, grant.generation),
        )
        if cur.rowcount != 1:
            self.connection.rollback(); return False
        self.connection.execute("UPDATE events SET state='CONSUMED' WHERE semantic_key=? AND state='PENDING'", (work.semantic_event_key,)); self.connection.commit(); return True

    def acquire_lease(self, slice_id: str, owner: str) -> LeaseGrant | None:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute("SELECT generation,active FROM leases WHERE slice_id=?", (slice_id,)).fetchone()
            if row and row[1]:
                self.connection.execute("ROLLBACK"); return None
            generation = (row[0] if row else 0) + 1; token = str(uuid.uuid4())
            self.connection.execute(
                "INSERT INTO leases VALUES (?,?,?,?,1) ON CONFLICT(slice_id) DO UPDATE SET owner=excluded.owner,generation=excluded.generation,token=excluded.token,active=1",
                (slice_id, owner, generation, token),
            )
            self.connection.execute("COMMIT"); return LeaseGrant(slice_id, owner, generation, token)
        except Exception:
            self.connection.execute("ROLLBACK"); raise

    def _lease_matches(self, lease: LeaseGrant) -> bool:
        row = self.connection.execute("SELECT owner,generation,token,active FROM leases WHERE slice_id=?", (lease.slice_id,)).fetchone()
        return row == (lease.owner, lease.generation, lease.fencing_token, 1)

    def execution_is_active(self, plan: ExecutionPlan, lease: LeaseGrant) -> bool:
        current = self.current_snapshot(); plan_row = self.connection.execute("SELECT identity,generation,state FROM plans WHERE plan_id=?", (plan.plan_id,)).fetchone()
        return bool(plan.slice.slice_id == lease.slice_id and current and plan_row == (current[0].identity, current[0].generation, "EXECUTING") and self._lease_matches(lease))

    def release_lease(self, grant: LeaseGrant) -> bool:
        cur = self.connection.execute("UPDATE leases SET active=0 WHERE slice_id=? AND owner=? AND generation=? AND token=? AND active=1", (grant.slice_id, grant.owner, grant.generation, grant.fencing_token)); self.connection.commit(); return cur.rowcount == 1

    def create_plan(self, grant: ReconciliationGrant, slice_: ImprovementSlice) -> ExecutionPlan:
        plan_id = digest({"snapshot": grant.identity, "generation": grant.generation, "slice": _slice_to_json(slice_)})
        self.connection.execute("INSERT OR REPLACE INTO plans VALUES (?,?,?,?,?)", (plan_id, grant.identity, grant.generation, _slice_to_json(slice_), "READY")); self.connection.commit(); return ExecutionPlan(plan_id, grant, slice_)

    def checkpointed_slice(self, checkpoint: Checkpoint) -> ImprovementSlice | None:
        row = self.connection.execute("SELECT slice_json FROM plans WHERE plan_id=? AND identity=? AND generation=?", (checkpoint.plan_id, checkpoint.snapshot_identity, checkpoint.reconciliation_generation)).fetchone()
        if not row:
            return None
        slice_ = _slice_from_json(row[0])
        if slice_.slice_id != checkpoint.slice_id or _slice_digest(slice_) != checkpoint.slice_digest:
            return None
        return slice_

    def authorize_execution(self, plan: ExecutionPlan, lease: LeaseGrant, budget_limit: int) -> tuple[ImprovementSlice, ReconciliationSnapshot] | None:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            current = self.current_snapshot(); plan_row = self.connection.execute("SELECT identity,generation,slice_json,state FROM plans WHERE plan_id=?", (plan.plan_id,)).fetchone(); lease_row = self.connection.execute("SELECT owner,generation,token,active FROM leases WHERE slice_id=?", (lease.slice_id,)).fetchone()
            if not current or not plan_row or plan_row[3] != "READY" or not lease_row:
                self.connection.execute("ROLLBACK"); return None
            current_grant, snapshot = current; slice_ = _slice_from_json(plan_row[2]); used = self.value("budget_used")
            try:
                slice_.validate(snapshot)
            except SupervisorError:
                self.connection.execute("ROLLBACK"); return None
            valid = (
                plan.slice.slice_id == lease.slice_id and slice_.slice_id == lease.slice_id and _slice_digest(plan.slice) == _slice_digest(slice_)
                and plan_row[0] == current_grant.identity == plan.snapshot.identity
                and plan_row[1] == current_grant.generation == plan.snapshot.generation
                and lease_row == (lease.owner, lease.generation, lease.fencing_token, 1)
                and snapshot.governance_mode == GovernanceMode.AUTONOMOUS and not snapshot.pending_p0
                and used + slice_.estimated_cost <= budget_limit
            )
            if not valid:
                self.connection.execute("ROLLBACK"); return None
            self.connection.execute("UPDATE plans SET state='EXECUTING' WHERE plan_id=?", (plan.plan_id,)); self.connection.execute("INSERT INTO accounting VALUES ('budget_used',?) ON CONFLICT(key) DO UPDATE SET value=value+excluded.value", (slice_.estimated_cost,)); self.connection.execute("COMMIT"); return slice_, snapshot
        except Exception:
            self.connection.execute("ROLLBACK"); raise

    def value(self, key: str) -> int:
        row = self.connection.execute("SELECT value FROM accounting WHERE key=?", (key,)).fetchone(); return int(row[0]) if row else 0

    def set_value(self, key: str, value: int) -> None:
        self.connection.execute("INSERT INTO accounting VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value)); self.connection.commit()

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        checkpoint.validate(); self.connection.execute("INSERT OR REPLACE INTO checkpoints VALUES (?,?)", (checkpoint.checkpoint_id, json.dumps(asdict(checkpoint), sort_keys=True))); self.connection.commit()

    def load_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        row = self.connection.execute("SELECT record FROM checkpoints WHERE checkpoint_id=?", (checkpoint_id,)).fetchone()
        if not row:
            return None
        value = json.loads(row[0])
        for name in ("source_refs", "evidence_digests", "completed_atomic_steps", "open_unknowns", "resume_preconditions"):
            value[name] = tuple(value[name])
        checkpoint = Checkpoint(**value); checkpoint.validate(); return checkpoint

    def issue_retrieval_complete_empty(self, snapshot: ReconciliationSnapshot, grant: ReconciliationGrant, observation: RetrievalProviderObservation) -> RetrievalCompletenessProof:
        current = self.current_snapshot(); observation.validate()
        if not current or current[0] != grant or current[1] != snapshot:
            raise SupervisorError("RETRIEVAL_PROOF_ISSUANCE_REQUIRES_CURRENT_RECONCILIATION")
        if observation.repository != snapshot.repository or observation.exact_revision != snapshot.exact_head:
            raise SupervisorError("RETRIEVAL_PROVIDER_OBSERVATION_REVISION_MISMATCH")
        proof = RetrievalCompletenessProof(
            snapshot.repository, snapshot.exact_head, observation.request_digest, observation.authority_scope_ref,
            observation.evidence_ref, observation.observation_id, observation.observation_digest(),
            grant.identity, grant.generation, True, f"stage-a:{uuid.uuid4()}",
        )
        self.connection.execute("INSERT INTO retrieval_proofs VALUES (?,?,?,'ISSUED')", (proof.issuance_ref, proof.proof_digest(), observation.observation_digest())); self.connection.commit(); return proof

    def consume_retrieval_proof(self, proof: RetrievalCompletenessProof, snapshot: ReconciliationSnapshot, grant: ReconciliationGrant, request_digest: str) -> bool:
        if not proof.structurally_matches(snapshot, grant, request_digest):
            return False
        cur = self.connection.execute(
            "UPDATE retrieval_proofs SET state='CONSUMED' WHERE issuance_ref=? AND proof_digest=? AND provider_observation_digest=? AND state='ISSUED'",
            (proof.issuance_ref, proof.proof_digest(), proof.provider_observation_digest),
        )
        self.connection.commit(); return cur.rowcount == 1


class SyntheticSupervisor:
    def __init__(self, repository: str, store: WorkingStateStore, budget_limit: int = 8, no_value_limit: int = 10, retrieval_provider: SyntheticRetrievalProvider | None = None):
        self.repository, self.store, self.budget_limit, self.no_value_limit = repository, store, budget_limit, no_value_limit
        self.retrieval_provider = retrieval_provider or SyntheticRetrievalProvider(); self.state = SupervisorState.BOOT

    def transition(self, target: SupervisorState) -> None:
        if target not in _ALLOWED[self.state]:
            raise SupervisorError(f"ILLEGAL_TRANSITION:{self.state.value}->{target.value}")
        self.state = target

    def reconcile(self, snapshot: ReconciliationSnapshot) -> ReconciliationGrant:
        prior = self.store.current_snapshot()
        if self.state == SupervisorState.CHECK_PRIORITY:
            if prior and prior[1].governance_mode != snapshot.governance_mode:
                self.transition(SupervisorState.USER_GATE)
            else:
                self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK)
        self.transition(SupervisorState.GLOBAL_RECONCILIATION); snapshot.validate(self.repository)
        if snapshot.governance_mode == GovernanceMode.EMERGENCY_STOP:
            self.transition(SupervisorState.EMERGENCY_STOP); raise SupervisorError("EMERGENCY_STOP")
        grant = self.store.record_reconciliation(snapshot); self.transition(SupervisorState.CHECK_PRIORITY); return grant

    def ingest(self, raw: Mapping[str, Any]) -> tuple[NormalizedEvent, bool]:
        event = NormalizedEvent.from_mapping(raw)
        if event.repository != self.repository:
            raise SupervisorError("EVENT_REPOSITORY_MISMATCH")
        return event, self.store.enqueue(event)

    def choose(self, grant: ReconciliationGrant, candidates: Sequence[ImprovementSlice]) -> ExecutionPlan | ReviewWorkIdentity | SupervisorReceipt:
        current = self.store.current_snapshot()
        if not current or current[0] != grant:
            raise SupervisorError("STALE_RECONCILIATION_GRANT")
        _, snapshot = current
        if self.store.has_unadjudicated_events(grant.generation):
            self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK)
            return SupervisorReceipt(Decision.BLOCKED, self.state, "FRESH_RECONCILIATION_REQUIRED_FOR_PENDING_EVENT")
        pending = self.store.highest_event(grant.generation)
        pending_priority = self.store.event_priority(pending.semantic_key) if pending else None
        if snapshot.governance_mode != GovernanceMode.AUTONOMOUS or snapshot.pending_p0 or pending_priority == Priority.P0_USER_OR_HIGH_RISK:
            self.transition(SupervisorState.USER_GATE); return SupervisorReceipt(Decision.USER_GATE, self.state, "GOVERNANCE_OR_P0_GATE")
        event = self.store.current_p1_event(snapshot.exact_head, grant.generation)
        if event:
            self.transition(SupervisorState.REVIEW); return self.store.create_review_work(event, grant)
        pending = self.store.highest_event(grant.generation)
        if pending and self.store.event_priority(pending.semantic_key) == Priority.P2_BLOCKER_OR_DRIFT:
            self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK)
            return SupervisorReceipt(Decision.BLOCKED, self.state, "P2_ACTIVE_AWAITING_FRESH_RECONCILIATION")
        if not candidates:
            if snapshot.eligible_work_queue_complete:
                self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK); return SupervisorReceipt(Decision.IDLE, self.state, "TRUSTED_COMPLETE_EMPTY_WORK_QUEUE")
            return SupervisorReceipt(Decision.UNKNOWN, self.state, "ELIGIBLE_WORK_COMPLETENESS_UNPROVEN")
        if self.store.value("no_value_streak") >= self.no_value_limit:
            self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK); return SupervisorReceipt(Decision.IDLE, self.state, "VOI_STOP")
        selected = min(candidates, key=lambda s: (int(s.priority), s.slice_id)); selected.validate(snapshot)
        if self.store.value("budget_used") + selected.estimated_cost > self.budget_limit:
            self.transition(SupervisorState.IDLE_NO_ELIGIBLE_WORK); return SupervisorReceipt(Decision.IDLE, self.state, "BUDGET_EXHAUSTED_PRE_EXECUTION")
        return self.store.create_plan(grant, selected)

    def issue_retrieval_complete_empty_proof(self, grant: ReconciliationGrant, request_digest: str, authority_scope_ref: str) -> RetrievalCompletenessProof | None:
        current = self.store.current_snapshot()
        if not current or current[0] != grant:
            raise SupervisorError("RETRIEVAL_PROOF_ISSUANCE_REQUIRES_CURRENT_RECONCILIATION")
        observation = self.retrieval_provider.observe_complete_empty(self.repository, current[1].exact_head, request_digest, authority_scope_ref)
        if observation is None:
            return None
        return self.store.issue_retrieval_complete_empty(current[1], grant, observation)

    def resolve_recall(self, grant: ReconciliationGrant, request_digest: str, proof: RetrievalCompletenessProof | None) -> SupervisorReceipt:
        current = self.store.current_snapshot()
        if not current or current[0] != grant or proof is None:
            return SupervisorReceipt(Decision.UNKNOWN, self.state, "RETRIEVAL_COMPLETENESS_UNPROVEN", process_compliance="INCOMPLETE")
        if not proof.structurally_matches(current[1], grant, request_digest):
            return SupervisorReceipt(Decision.UNKNOWN, self.state, "RETRIEVAL_COMPLETENESS_UNPROVEN", process_compliance="INCOMPLETE")
        if not self.store.consume_retrieval_proof(proof, current[1], grant, request_digest):
            return SupervisorReceipt(Decision.UNKNOWN, self.state, "RETRIEVAL_COMPLETENESS_UNTRUSTED", process_compliance="UNTRUSTED")
        return SupervisorReceipt(Decision.IDLE, SupervisorState.IDLE_NO_ELIGIBLE_WORK, "TRUSTED_COMPLETE_EMPTY_RETRIEVAL", process_compliance="PASS")

    def execute(self, plan: ExecutionPlan, lease: LeaseGrant) -> SupervisorReceipt:
        if self.state != SupervisorState.CHECK_PRIORITY:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "EXECUTION_NOT_AT_RECONCILED_PRIORITY_BOUNDARY")
        if self.store.has_unadjudicated_events(plan.snapshot.generation):
            return SupervisorReceipt(Decision.BLOCKED, self.state, "FRESH_RECONCILIATION_REQUIRED_FOR_PENDING_EVENT")
        pending = self.store.highest_event(plan.snapshot.generation)
        if pending and (self.store.event_priority(pending.semantic_key) or Priority.P4_RESEARCH) < plan.slice.priority:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "HIGHER_PRIORITY_PENDING_AT_EXECUTION")
        authorized = self.store.authorize_execution(plan, lease, self.budget_limit)
        if not authorized:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "EXECUTION_BOUNDARY_REJECTED")
        self.transition(SupervisorState.WORK_SLICE); return SupervisorReceipt(Decision.EXECUTED, self.state, "SYNTHETIC_ATOMIC_ACTION", process_compliance="PASS", outcome_quality="UNKNOWN")

    def complete_atomic_slice(self, evidence_value: int) -> SupervisorReceipt:
        if self.state != SupervisorState.WORK_SLICE:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "NOT_IN_WORK_SLICE")
        self.transition(SupervisorState.EVALUATE); self.store.set_value("no_value_streak", 0 if evidence_value else self.store.value("no_value_streak") + 1)
        return SupervisorReceipt(Decision.EXECUTED, self.state, "EVALUATED", outcome_quality="UNKNOWN")

    def safepoint(self, plan: ExecutionPlan, lease: LeaseGrant) -> SupervisorReceipt:
        return self.checkpoint_for_preemption(plan, lease)

    def checkpoint_for_preemption(self, plan: ExecutionPlan, lease: LeaseGrant) -> SupervisorReceipt:
        if self.state != SupervisorState.WORK_SLICE:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "SAFEPOINT_NOT_IN_WORK_SLICE")
        current = self.store.current_snapshot()
        if not current:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "RECONCILIATION_MISSING_AT_SAFEPOINT")
        preemption = self.store.highest_preemption_event(current[0].generation, plan.slice.priority)
        if not preemption:
            return SupervisorReceipt(Decision.UNKNOWN, self.state, "NO_PREEMPTION")
        event, effective_priority = preemption
        if plan.slice.slice_id != lease.slice_id or not self.store.execution_is_active(plan, lease):
            return SupervisorReceipt(Decision.BLOCKED, self.state, "STALE_OR_CROSS_SLICE_FENCE")
        grant, snapshot = current; self.transition(SupervisorState.SAFEPOINT_CHECKPOINT)
        checkpoint = Checkpoint(
            checkpoint_id=digest({"plan": plan.plan_id, "slice_digest": _slice_digest(plan.slice), "event": event.semantic_key, "fence": lease.fencing_token}),
            mission_id="CODEX-IAGL-R141-STAGE-A-SYNTHETIC-SUPERVISOR", slice_id=plan.slice.slice_id,
            plan_id=plan.plan_id, slice_digest=_slice_digest(plan.slice), state=SupervisorState.SAFEPOINT_CHECKPOINT.value,
            created_at=snapshot.observed_at, control_plane_snapshot_ref=grant.identity,
            source_refs=(event.semantic_key,), evidence_digests=(event.payload_digest,),
            completed_atomic_steps=("SYNTHETIC_ATOMIC_ACTION",), open_unknowns=("OUTCOME_QUALITY_UNKNOWN",),
            next_atomic_action="FRESH_RECONCILE_AND_RESUME_OR_REPLAN", budget_state=f"used:{self.store.value('budget_used')}",
            lease_state=f"owner:{lease.owner};generation:{lease.generation}", fencing_token_ref=digest(lease.fencing_token),
            interruption_reason=f"priority:{int(effective_priority)}",
            resume_preconditions=("FRESH_RECONCILIATION", "AUTONOMOUS", "NO_PENDING_P0", "MATCHING_SLICE", "NEW_FENCE"),
            privacy_class="PUBLIC_SAFE_SYNTHETIC", snapshot_identity=grant.identity,
            reconciliation_generation=grant.generation, prior_lease_generation=lease.generation,
            exact_head=snapshot.exact_head, route_id=snapshot.route_id, domain_revision=snapshot.domain_revision,
        )
        self.store.save_checkpoint(checkpoint); self.store.release_lease(lease); self.transition(SupervisorState.PAUSED_FOR_HIGHER_PRIORITY)
        return SupervisorReceipt(Decision.PREEMPTED, self.state, "HIGHER_PRIORITY_PREEMPTION_AT_SAFEPOINT", checkpoint.checkpoint_id)

    def review(self, work: ReviewWorkIdentity, evidence: ReviewEvidence) -> SupervisorReceipt:
        if self.state == SupervisorState.PAUSED_FOR_HIGHER_PRIORITY:
            self.transition(SupervisorState.REVIEW)
        if self.state != SupervisorState.REVIEW:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "REVIEW_NOT_READY")
        current = self.store.current_snapshot()
        valid = bool(
            current and work == evidence.work
            and _nonempty((evidence.target_head, evidence.ci_head, evidence.receipt_head, evidence.reviewer_source))
            and work.target_head == evidence.target_head == evidence.ci_head == evidence.receipt_head == current[1].exact_head
            and work.reconciliation_identity == current[0].identity and work.reconciliation_generation == current[0].generation
            and self.store.consume_review_work(work, current[0])
        )
        if not valid:
            self.transition(SupervisorState.FAILED_CLOSED); return SupervisorReceipt(Decision.BLOCKED, self.state, "REVIEW_WORK_IDENTITY_OR_RECEIPT_MISMATCH")
        self.transition(SupervisorState.EVALUATE); return SupervisorReceipt(Decision.EXECUTED, self.state, "P1_REVIEW_EXACT_HEAD_VALID")

    def resume_or_replan(self, checkpoint_id: str, fresh: ReconciliationGrant, lease: LeaseGrant) -> SupervisorReceipt:
        try:
            checkpoint = self.store.load_checkpoint(checkpoint_id)
        except SupervisorError:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "CHECKPOINT_RESUME_PRECONDITIONS_INVALID")
        current = self.store.current_snapshot()
        if not checkpoint or not current or current[0] != fresh or fresh.generation <= checkpoint.reconciliation_generation:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "FRESH_RECONCILIATION_REQUIRED")
        _, snapshot = current
        if self.store.has_unadjudicated_events(fresh.generation):
            return SupervisorReceipt(Decision.BLOCKED, self.state, "FRESH_RECONCILIATION_REQUIRED_FOR_PENDING_EVENT")
        if (
            checkpoint.slice_id != lease.slice_id
            or snapshot.governance_mode != GovernanceMode.AUTONOMOUS
            or snapshot.pending_p0
            or checkpoint.route_id != snapshot.route_id
            or checkpoint.domain_revision != snapshot.domain_revision
            or not _REQUIRED_RESUME_PRECONDITIONS.issubset(set(checkpoint.resume_preconditions))
        ):
            return SupervisorReceipt(Decision.BLOCKED, self.state, "CHECKPOINT_DRIFT_OR_GOVERNANCE_OR_SLICE_GATE")
        slice_ = self.store.checkpointed_slice(checkpoint)
        if slice_ is None:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "CHECKPOINT_PLAN_OR_SLICE_IDENTITY_MISMATCH")
        try:
            slice_.validate(snapshot)
        except SupervisorError:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "CHECKPOINTED_SLICE_POLICY_DRIFT")
        pending = self.store.highest_event(fresh.generation)
        if pending and (self.store.event_priority(pending.semantic_key) or Priority.P4_RESEARCH) < slice_.priority:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "HIGHER_PRIORITY_PENDING_AT_RESUME")
        if self.state == SupervisorState.CHECK_PRIORITY:
            self.transition(SupervisorState.REVIEW); self.transition(SupervisorState.EVALUATE)
        if self.state == SupervisorState.EVALUATE:
            self.transition(SupervisorState.LEARN)
        if self.state != SupervisorState.LEARN:
            return SupervisorReceipt(Decision.BLOCKED, self.state, "RESUME_STATE_INVALID")
        self.transition(SupervisorState.RESUME_VALIDATION)
        if not self.store._lease_matches(lease) or lease.generation <= checkpoint.prior_lease_generation:
            self.transition(SupervisorState.FAILED_CLOSED); return SupervisorReceipt(Decision.BLOCKED, self.state, "STALE_OR_FORGED_OR_CROSS_SLICE_FENCE")
        self.transition(SupervisorState.RESUME); self.transition(SupervisorState.WORK_SLICE)
        return SupervisorReceipt(Decision.EXECUTED, self.state, "FRESH_RECONCILE_RESUME_OR_REPLAN", checkpoint_id)
