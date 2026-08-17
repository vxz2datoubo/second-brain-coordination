"""Offline, deterministic, synthetic-only IAGL Stage-A supervisor.

This module is the single current instantiable supervisor/store implementation.
SQLite is bounded task-local working state only; it never supplies canonical
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
    "CODEX_PR_READY", "REMEDIATION_READY", "CI_COMPLETED_FOR_REVIEW_HEAD", "RECONCILIATION_HEAD_DELTA",
}
_P2_EVENT_CLASSES = {
    "TASK_ROUTE_CHANGED", "CLAIM_OR_LEASE_CHANGED", "ROUTE_DRIFT", "CLAIM_COLLISION",
    "SECURITY_REGRESSION", "FALSE_GREEN", "ACTIVE_BLOCKER",
}
_P3_EVENT_CLASSES = {"SIGNAL_MATERIALITY_CHANGED"}
_P4_EVENT_CLASSES = {"WATCHDOG_TICK"}
_HEAD_OBSERVATION_CLASSES = {"PR_HEAD_CHANGED", "WATCHDOG_TICK", "RECONCILIATION_HEAD_DELTA"}
_HIGH_RISK_PAYLOAD_TOKENS = {
    "secret", "credential", "api_key", "apikey", "permission", "github_permission",
    "production", "deploy", "deployment", "trading", "trade", "order", "fund", "funds",
    "destructive", "force_push", "force-push", "rebase", "reset", "private_key", "token",
}
_INVALID_GOALS = {"improve system generally", "research indefinitely", "browse until something interesting appears"}
_STAGE_A_TOOL_CEILING = frozenset({"stdlib-only"})
_STAGE_A_DATA_CEILING = frozenset({"PUBLIC_SAFE_SYNTHETIC"})
_STAGE_A_RISK_CEILING = frozenset({"P3_SYNTHETIC", "P4_SYNTHETIC"})
_STAGE_A_WRITEBACK_CEILING = frozenset({"NO_CANONICAL_WRITE"})
_FORBIDDEN_TOOL_TOKENS = ("network", "shell", "bash", "powershell", "cmd", "subprocess", "daemon", "socket", "requests", "curl", "wget", "webhook", "scheduler", "exec")
_FORBIDDEN_DATA_TOKENS = ("private", "raw", "conversation", "credential", "secret", "cookie", "token", "key", "media")
_FORBIDDEN_RISK_TOKENS = ("production", "trading", "fund", "destructive", "secret", "permission", "high_risk", "c3", "c4")
_REQUIRED_RESUME_PRECONDITIONS = {"FRESH_RECONCILIATION", "AUTONOMOUS", "NO_PENDING_P0", "MATCHING_SLICE", "NEW_FENCE"}
_P0_DISPOSITIONS = {"DENIED", "RESOLVED_NO_ACTION", "APPROVED_SEPARATE_GATED_ACTION"}
_P2_OBSERVATION_STATES = {"PARTIAL_OBSERVATION", "UNKNOWN", "AUTHORITATIVE_COMPLETE"}
_STARVATION_THRESHOLD = 2


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
    return tuple(sorted(token for token in _HIGH_RISK_PAYLOAD_TOKENS if token in tokens))


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


def _head_semantic_key(repository: str, target_ref: str, target_identity: str) -> str:
    return digest({"repository": repository, "semantic_kind": "HEAD_OBSERVATION", "target_ref": target_ref, "target_identity": target_identity})


def _reconciliation_p2_class_key(repository: str, route_id: str, event_class: str) -> str:
    return digest({"repository": repository, "semantic_kind": "RECONCILIATION_P2", "route": route_id, "event_class": event_class.upper()})



__all__ = tuple(name for name in globals() if not name.startswith("__"))
