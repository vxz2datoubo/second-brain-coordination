from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

from control_tower import (
    NON_EXECUTABLE_STATUSES,
    PROGRAM_REGISTRY,
    Finding,
    classify_collision,
    load_yaml,
)

GPT_WORKERS_REGISTRY = "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
AGENT_TYPE = "GPT_ENGINEERING_WORKER"
CHECK_ID = "CT-WS"

ACTIVATION_ACTIVE = "ACTIVE"
ACTIVATION_RESERVED = "RESERVED"
ACTIVATION_RELEASED = "RELEASED"
CLOSURE_RELEASED = "RELEASED"


@dataclass(frozen=True)
class WorkerSlot:
    worker_slot_id: str
    agent_type: str
    executor_role: str
    model_id: str | None
    task_id: str | None
    route_epoch: int | str | None
    issue: int | str | None
    pr: int | str | None
    branch: str | None
    status: str | None
    execution_allowed: bool
    completion_signal: str | None
    write_paths: tuple[str, ...]
    read_paths: tuple[str, ...]
    interfaces: tuple[Any, ...]
    read_domains: tuple[str, ...]
    write_domains: tuple[str, ...]
    authority_claims: tuple[str, ...]
    resource_class: str | None
    provenance: dict[str, Any] | None
    reviewer_role: str | None
    reviewer_separation: str | None
    activation_state: str | None
    closure_state: str | None
    fingerprint: str


def _first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _slot_normalized(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "worker_slot_id": _first(raw, "worker_slot_id", "lease_id", "slot_id"),
        "agent_type": _first(raw, "agent_type", "canonical_agent_type") or AGENT_TYPE,
        "executor_role": _first(raw, "executor_role", "role") or AGENT_TYPE,
        "model_id": _first(raw, "model_id"),
        "task_id": _first(raw, "task_id", "active_task_id"),
        "route_epoch": _first(raw, "route_epoch", "epoch"),
        "issue": _first(raw, "issue", "active_issue"),
        "pr": _first(raw, "pr", "implementation_pr", "active_pull_request", "pull_request"),
        "branch": _first(raw, "branch", "implementation_branch", "planned_branch"),
        "status": _first(raw, "status"),
        "execution_allowed": bool(raw.get("execution_allowed", False)),
        "completion_signal": _first(raw, "completion_signal"),
        "write_paths": [str(item) for item in (raw.get("write_paths") or [])],
        "read_paths": [str(item) for item in (raw.get("read_paths") or [])],
        "interfaces": list(raw.get("interfaces") or []),
        "read_domains": [str(item) for item in (raw.get("read_domains") or [])],
        "write_domains": [str(item) for item in (raw.get("write_domains") or [])],
        "authority_claims": [str(item) for item in (raw.get("authority_claims") or [])],
        "resource_class": _first(raw, "resource_class"),
        "provenance": raw.get("provenance") if isinstance(raw.get("provenance"), dict) else None,
        "reviewer_role": _first(raw, "reviewer_role"),
        "reviewer_separation": _first(raw, "reviewer_separation", "execution_identity_not_acceptance_authority"),
        "activation_state": _first(raw, "activation_state"),
        "closure_state": _first(raw, "closure_state"),
    }


def normalize_worker_slot(raw: dict[str, Any]) -> WorkerSlot:
    normalized = _slot_normalized(raw)
    fingerprint = hashlib.sha256(
        json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return WorkerSlot(
        worker_slot_id=normalized["worker_slot_id"],
        agent_type=normalized["agent_type"],
        executor_role=normalized["executor_role"],
        model_id=normalized["model_id"],
        task_id=normalized["task_id"],
        route_epoch=normalized["route_epoch"],
        issue=normalized["issue"],
        pr=normalized["pr"],
        branch=normalized["branch"],
        status=normalized["status"],
        execution_allowed=normalized["execution_allowed"],
        completion_signal=normalized["completion_signal"],
        write_paths=tuple(normalized["write_paths"]),
        read_paths=tuple(normalized["read_paths"]),
        interfaces=tuple(normalized["interfaces"]),
        read_domains=tuple(normalized["read_domains"]),
        write_domains=tuple(normalized["write_domains"]),
        authority_claims=tuple(normalized["authority_claims"]),
        resource_class=normalized["resource_class"],
        provenance=normalized["provenance"],
        reviewer_role=normalized["reviewer_role"],
        reviewer_separation=normalized["reviewer_separation"],
        activation_state=normalized["activation_state"],
        closure_state=normalized["closure_state"],
        fingerprint=fingerprint,
    )


def load_worker_slots(repo_root: Path) -> list[WorkerSlot]:
    root = repo_root.resolve()
    path = root / GPT_WORKERS_REGISTRY
    if not path.exists():
        return []
    doc = load_yaml(path)
    raw_slots = list(doc.get("worker_slots") or [])
    return [normalize_worker_slot(raw) for raw in raw_slots if isinstance(raw, dict)]


def worker_slot_route_witness(slot: WorkerSlot) -> dict[str, Any]:
    return {
        "worker_slot_id": slot.worker_slot_id,
        "agent_type": slot.agent_type,
        "executor_role": slot.executor_role,
        "model_id": slot.model_id,
        "task_id": slot.task_id,
        "route_epoch": slot.route_epoch,
        "issue": slot.issue,
        "pr": slot.pr,
        "branch": slot.branch,
        "status": slot.status,
        "execution_allowed": slot.execution_allowed,
        "completion_signal": slot.completion_signal,
        "write_paths": list(slot.write_paths),
        "read_paths": list(slot.read_paths),
        "interfaces": list(slot.interfaces),
        "read_domains": list(slot.read_domains),
        "write_domains": list(slot.write_domains),
        "authority_claims": list(slot.authority_claims),
        "resource_class": slot.resource_class,
        "provenance": slot.provenance,
        "reviewer_role": slot.reviewer_role,
        "reviewer_separation": slot.reviewer_separation,
        "activation_state": slot.activation_state,
        "closure_state": slot.closure_state,
        "fingerprint": slot.fingerprint,
    }


def worker_slot_is_executable(slot: WorkerSlot) -> bool:
    if not slot.execution_allowed:
        return False
    if slot.closure_state == CLOSURE_RELEASED or slot.activation_state == ACTIVATION_RELEASED:
        return False
    if slot.status is None:
        return False
    return str(slot.status).upper() not in NON_EXECUTABLE_STATUSES


def _slot_claim_surface(slot: WorkerSlot) -> dict[str, Any]:
    return {
        "write_paths": list(slot.write_paths),
        "read_paths": list(slot.read_paths),
        "interfaces": list(slot.interfaces),
        "read_domains": list(slot.read_domains),
        "write_domains": list(slot.write_domains),
        "authority_claims": list(slot.authority_claims),
    }


def worker_slot_findings(repo_root: Path) -> list[Finding]:
    root = repo_root.resolve()
    slots = load_worker_slots(root)
    findings: list[Finding] = []

    for slot in slots:
        if not slot.worker_slot_id:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_ID_MISSING",
                    "GPT Engineering Worker slot lacks a stable worker_slot_id/lease identity.",
                    {"fingerprint": slot.fingerprint},
                )
            )

    for slot in slots:
        if slot.agent_type != AGENT_TYPE or slot.executor_role != AGENT_TYPE:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_IMPERSONATION",
                    "GPT Engineering Worker slot declares a non-GPT agent identity; GPT worker must not impersonate CODEX/QCLAW/WORKBUDDY.",
                    {
                        "worker_slot_id": slot.worker_slot_id,
                        "agent_type": slot.agent_type,
                        "executor_role": slot.executor_role,
                    },
                )
            )

    for slot in slots:
        if slot.reviewer_role and slot.reviewer_role == slot.executor_role:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_SELF_REVIEW",
                    "GPT Engineering Worker slot grants itself acceptance authority; execution identity must differ from reviewer role.",
                    {"worker_slot_id": slot.worker_slot_id, "reviewer_role": slot.reviewer_role},
                )
            )

    seen: dict[str, list[str]] = {}
    for slot in slots:
        if not slot.worker_slot_id:
            continue
        seen.setdefault(slot.worker_slot_id, []).append(slot.task_id or "UNKNOWN_TASK")
    for slot_id, tasks in seen.items():
        if len(tasks) > 1:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_DUPLICATE_ID",
                    "Same GPT worker slot/lease identity is bound to more than one entry (silent overwrite / double booking).",
                    {"worker_slot_id": slot_id, "tasks": tasks},
                )
            )

    for slot in slots:
        if slot.closure_state == CLOSURE_RELEASED or slot.activation_state == ACTIVATION_RELEASED:
            if slot.execution_allowed or slot.activation_state == ACTIVATION_ACTIVE:
                findings.append(
                    Finding(
                        CHECK_ID,
                        "ERROR",
                        "WORKER_SLOT_CLOSED_HAS_LEASE",
                        "A closed/released GPT worker slot retains an execution lease.",
                        {"worker_slot_id": slot.worker_slot_id, "task_id": slot.task_id},
                    )
                )

    for slot in slots:
        if slot.activation_state == ACTIVATION_ACTIVE and not worker_slot_is_executable(slot):
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_ACTIVE_NOT_EXECUTABLE",
                    "A GPT worker slot marked ACTIVE is bound to a non-executable route.",
                    {
                        "worker_slot_id": slot.worker_slot_id,
                        "status": slot.status,
                        "execution_allowed": slot.execution_allowed,
                    },
                )
            )

    active_executable = [slot for slot in slots if worker_slot_is_executable(slot)]
    registry = load_yaml(root / PROGRAM_REGISTRY)
    capacity_policy = registry.get("portfolio_capacity_policy", {}) or {}
    default_capacity = 1
    capacity = capacity_policy.get("gpt_engineering_worker_active_slots_max", default_capacity)
    if not isinstance(capacity, int) or capacity < 1:
        capacity = default_capacity
    if len(active_executable) > capacity:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKER_SLOT_CAPACITY_EXCEEDED",
                "More GPT Engineering Worker slots are executable than configured capacity allows.",
                {
                    "active_slots": [slot.worker_slot_id for slot in active_executable],
                    "limit": capacity,
                },
            )
        )

    for left, right in combinations(active_executable, 2):
        collision = classify_collision(_slot_claim_surface(left), _slot_claim_surface(right))
        if collision["level"] in {"O3", "O4"}:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_COLLISION",
                    "Two active GPT worker slots collide on a mutable surface or authority.",
                    {
                        "pair": [left.worker_slot_id, right.worker_slot_id],
                        "collision": collision,
                    },
                )
            )

    return findings


def validate_worker_slots(repo_root: Path) -> dict[str, Any]:
    slots = load_worker_slots(repo_root)
    findings = worker_slot_findings(repo_root)
    errors = [asdict(item) for item in findings if item.severity == "ERROR"]
    warnings = [asdict(item) for item in findings if item.severity == "WARN"]
    return {
        "schema_version": "1.0",
        "agent_type": AGENT_TYPE,
        "worker_slots": [worker_slot_route_witness(slot) for slot in slots],
        "active_executable_slots": [slot.worker_slot_id for slot in slots if worker_slot_is_executable(slot)],
        "errors": errors,
        "warnings": warnings,
        "worker_slot_structural_check": "PASS" if not errors else "FAIL",
    }
