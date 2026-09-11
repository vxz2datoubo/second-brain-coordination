from __future__ import annotations

import hashlib
import json
import re
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
from worker_lifecycle import (
    LIFECYCLE_ACTIVE,
    LIFECYCLE_RESERVED,
    LIFECYCLE_UNKNOWN,
    audit_worker_registry_lifecycle,
    registry_schema_supported,
    resolve_worker_lifecycle,
)

GPT_WORKERS_REGISTRY = "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
CLAIMS_FILE = "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml"
R3_MAINTENANCE_ADOPTION_FILE = "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION.yaml"
R4_MAINTENANCE_ADOPTION_FILE = "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION-R4.yaml"
MAINTENANCE_ADOPTION_FILE = "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION-R5.yaml"
R6_MAINTENANCE_ADOPTION_FILE = "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION-R6.yaml"
R7_MAINTENANCE_ADOPTION_FILE = "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION-R7.yaml"
R8_MAINTENANCE_ADOPTION_FILE = "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION-R8.yaml"
MAINTENANCE_TOMBSTONES_FILE = "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-TERMINAL-TOMBSTONES.yaml"
R144_TASK_BRIEF_FILE = "coordination/TASK-BRIEFS/CODEX-CONTROL-TOWER-GPT-ENGINEERING-WORKER-FIRST-CLASS-R144.yaml"
AGENT_TYPE = "GPT_ENGINEERING_WORKER"
CHECK_ID = "CT-WS"
EXPECTED_REGISTRY_ID = "ACTIVE-GPT-ENGINEERING-WORKERS-0001"
EXPECTED_MAINTENANCE_AUTHORITY_TYPE = "GPT_ARCHITECTURE_OWNER_CORRECTIVE_MAINTENANCE_ADOPTION"
EXPECTED_MAINTENANCE_AUTHORITY_ID = "R144-GPT-ARCHITECTURE-OWNER-MAINTENANCE-ADOPTION-R5-0001"
EXPECTED_PREDECESSOR_AUTHORITY_ID = "R144-GPT-ARCHITECTURE-OWNER-MAINTENANCE-ADOPTION-R4-0001"
EXPECTED_MAINTENANCE_PR = 408
EXPECTED_MAINTENANCE_TRIGGER_REVIEW = 4974860616
EXPECTED_MAINTENANCE_INPUT_HEAD = "8a2eb5c41f9b67328211569ac7c8d4c71d0cf6d1"
EXPECTED_RELEASED_SCOPE_STATUS = "NO_FURTHER_MODIFIER_WRITES_AUTHORIZED_BY_THIS_ARTIFACT"
EXPECTED_TOMBSTONE_REGISTRY_ID = "R144-GPT-MAINTENANCE-TERMINAL-TOMBSTONES-0001"
EXPECTED_TOMBSTONE_SEMANTICS = "MONOTONIC_TERMINAL_AUTHORITY_IDS / DELETE_OR_REWRITE_FAILS_CLOSED"
R6_AUTHORITY_ID = "R144-GPT-ARCHITECTURE-OWNER-MAINTENANCE-ADOPTION-R6-0001"
R7_AUTHORITY_ID = "R144-GPT-ARCHITECTURE-OWNER-MAINTENANCE-ADOPTION-R7-0001"

R4_TERMINAL_RECORD = {
    "authority_id": EXPECTED_PREDECESSOR_AUTHORITY_ID,
    "authority_file": R4_MAINTENANCE_ADOPTION_FILE,
    "terminal_state": "RELEASED",
    "release_commit": "8a2eb5c41f9b67328211569ac7c8d4c71d0cf6d1",
    "released_scope_status": EXPECTED_RELEASED_SCOPE_STATUS,
    "reactivation_allowed": False,
    "terminality_source_review": 4974860616,
}
R5_TERMINAL_RECORD = {
    "authority_id": EXPECTED_MAINTENANCE_AUTHORITY_ID,
    "authority_file": MAINTENANCE_ADOPTION_FILE,
    "terminal_state": "RELEASED",
    "release_parent_head": "bf212c4413cef72506a841c177c972b52af60acc",
    "released_scope_status": EXPECTED_RELEASED_SCOPE_STATUS,
    "reactivation_allowed": False,
    "terminality_source_review": 4974860616,
}
R6_TERMINAL_RECORD = {
    "authority_id": R6_AUTHORITY_ID,
    "authority_file": R6_MAINTENANCE_ADOPTION_FILE,
    "terminal_state": "RELEASED",
    "release_parent_head": "04124e233dc813cca4054851ef6a470b342d82fe",
    "released_scope_status": EXPECTED_RELEASED_SCOPE_STATUS,
    "reactivation_allowed": False,
    "terminality_source_review": 5108092436,
}
R7_TERMINAL_RECORD = {
    "authority_id": R7_AUTHORITY_ID,
    "authority_file": R7_MAINTENANCE_ADOPTION_FILE,
    "terminal_state": "RELEASED",
    "release_parent_head": "91d8838da370496ecd2678633a7293cc5d161ec4",
    "released_scope_status": EXPECTED_RELEASED_SCOPE_STATUS,
    "reactivation_allowed": False,
    "terminality_source_review": 5160695113,
}
BASE_EXPECTED_TERMINAL_RECORDS: dict[str, dict[str, Any]] = {
    EXPECTED_PREDECESSOR_AUTHORITY_ID: R4_TERMINAL_RECORD,
    EXPECTED_MAINTENANCE_AUTHORITY_ID: R5_TERMINAL_RECORD,
    R6_AUTHORITY_ID: R6_TERMINAL_RECORD,
}

ACTIVE_CLAIM_STATE = "ACTIVE_IMPLEMENTATION"
RESERVED_CLAIM_STATE = "RESERVED_IMPLEMENTATION_NON_EXECUTABLE"
_STRING_SEQUENCE_FIELDS = (
    "write_paths",
    "read_paths",
    "read_domains",
    "write_domains",
    "authority_claims",
)
_LIST_FIELDS = (*_STRING_SEQUENCE_FIELDS, "interfaces")
_LIVE_REQUIRED_FIELDS = (
    "worker_slot_id",
    "agent_type",
    "executor_role",
    "model_id",
    "task_id",
    "route_epoch",
    "issue",
    "pr",
    "branch",
    "status",
    "resource_class",
    "reviewer_role",
    "reviewer_separation",
)
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class WorkerSlot:
    worker_slot_id: str | None
    agent_type: str | None
    executor_role: str | None
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


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _safe_string_list(raw: dict[str, Any], key: str) -> list[str]:
    value = raw.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _safe_interfaces(raw: dict[str, Any]) -> list[Any]:
    value = raw.get("interfaces")
    return list(value) if isinstance(value, list) else []


def _slot_normalized(raw: dict[str, Any]) -> dict[str, Any]:
    raw_execution_allowed = raw.get("execution_allowed")
    return {
        "worker_slot_id": _first(raw, "worker_slot_id", "lease_id", "slot_id"),
        "agent_type": _first(raw, "agent_type", "canonical_agent_type"),
        "executor_role": _first(raw, "executor_role", "role"),
        "model_id": _first(raw, "model_id"),
        "task_id": _first(raw, "task_id", "active_task_id"),
        "route_epoch": _first(raw, "route_epoch", "epoch"),
        "issue": _first(raw, "issue", "active_issue"),
        "pr": _first(raw, "pr", "implementation_pr", "active_pull_request", "pull_request"),
        "branch": _first(raw, "branch", "implementation_branch", "planned_branch"),
        "status": _first(raw, "status"),
        "execution_allowed": raw_execution_allowed if isinstance(raw_execution_allowed, bool) else False,
        "completion_signal": _first(raw, "completion_signal"),
        "write_paths": _safe_string_list(raw, "write_paths"),
        "read_paths": _safe_string_list(raw, "read_paths"),
        "interfaces": _safe_interfaces(raw),
        "read_domains": _safe_string_list(raw, "read_domains"),
        "write_domains": _safe_string_list(raw, "write_domains"),
        "authority_claims": _safe_string_list(raw, "authority_claims"),
        "resource_class": _first(raw, "resource_class"),
        "provenance": raw.get("provenance") if isinstance(raw.get("provenance"), dict) else None,
        "reviewer_role": _first(raw, "reviewer_role"),
        "reviewer_separation": _first(raw, "reviewer_separation", "execution_identity_not_acceptance_authority"),
        "activation_state": _first(raw, "activation_state"),
        "closure_state": _first(raw, "closure_state"),
    }


def normalize_worker_slot(raw: dict[str, Any]) -> WorkerSlot:
    normalized = _slot_normalized(raw)
    fingerprint = hashlib.sha256(_canonical(normalized).encode("utf-8")).hexdigest()
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


def _lifecycle_mapping(slot: WorkerSlot) -> dict[str, Any]:
    material = worker_slot_route_witness(slot)
    material.pop("fingerprint", None)
    return material


def _lifecycle(slot: WorkerSlot):
    return resolve_worker_lifecycle(_lifecycle_mapping(slot))


def _program_capacity_policy(repo_root: Path) -> dict[str, Any]:
    try:
        program = load_yaml(repo_root.resolve() / PROGRAM_REGISTRY)
    except (OSError, ValueError, TypeError):
        return {}
    capacity = program.get("portfolio_capacity_policy", {}) if isinstance(program, dict) else {}
    return capacity if isinstance(capacity, dict) else {}


def _registry_required(repo_root: Path) -> bool:
    capacity = _program_capacity_policy(repo_root)
    return any(
        key in capacity
        for key in (
            "gpt_engineering_worker_parallel_routes_allowed",
            "gpt_engineering_worker_active_slots_max",
        )
    )


def _load_yaml_mapping(repo_root: Path, relpath: str, error_code: str) -> tuple[dict[str, Any] | None, str | None]:
    path = repo_root.resolve() / relpath
    if not path.exists():
        return None, None
    try:
        return load_yaml(path), None
    except (OSError, ValueError, TypeError):
        return None, error_code


def _load_registry_doc(repo_root: Path) -> tuple[dict[str, Any] | None, str | None]:
    return _load_yaml_mapping(repo_root, GPT_WORKERS_REGISTRY, "WORKER_REGISTRY_NOT_MAPPING")


def _load_maintenance_adoption_doc(repo_root: Path) -> tuple[dict[str, Any] | None, str | None]:
    return _load_yaml_mapping(repo_root, MAINTENANCE_ADOPTION_FILE, "MAINTENANCE_ADOPTION_NOT_MAPPING")


def _load_predecessor_maintenance_doc(repo_root: Path) -> tuple[dict[str, Any] | None, str | None]:
    return _load_yaml_mapping(repo_root, R4_MAINTENANCE_ADOPTION_FILE, "MAINTENANCE_PREDECESSOR_NOT_MAPPING")


def _load_terminal_tombstones_doc(repo_root: Path) -> tuple[dict[str, Any] | None, str | None]:
    return _load_yaml_mapping(repo_root, MAINTENANCE_TOMBSTONES_FILE, "MAINTENANCE_TOMBSTONES_NOT_MAPPING")


def _load_r144_task_brief(repo_root: Path) -> tuple[dict[str, Any] | None, str | None]:
    return _load_yaml_mapping(repo_root, R144_TASK_BRIEF_FILE, "MAINTENANCE_TASK_BRIEF_NOT_MAPPING")


def _maintenance_required(repo_root: Path) -> bool:
    root = repo_root.resolve()
    return any(
        (root / path).exists()
        for path in (
            R3_MAINTENANCE_ADOPTION_FILE,
            R4_MAINTENANCE_ADOPTION_FILE,
            MAINTENANCE_ADOPTION_FILE,
            R6_MAINTENANCE_ADOPTION_FILE,
            R7_MAINTENANCE_ADOPTION_FILE,
            R8_MAINTENANCE_ADOPTION_FILE,
            MAINTENANCE_TOMBSTONES_FILE,
        )
    )


def terminal_tombstones_witness(repo_root: Path) -> dict[str, Any]:
    doc, error = _load_terminal_tombstones_doc(repo_root)
    if error:
        return {"present": True, "load_error": error, "raw": None}
    if doc is None:
        return {
            "present": False,
            "load_error": "MAINTENANCE_TOMBSTONES_MISSING" if _maintenance_required(repo_root) else None,
        }
    return {"present": True, "raw": doc}


def maintenance_adoption_witness(repo_root: Path) -> dict[str, Any]:
    doc, error = _load_maintenance_adoption_doc(repo_root)
    predecessor, predecessor_error = _load_predecessor_maintenance_doc(repo_root)
    tombstones = terminal_tombstones_witness(repo_root)
    current_generation: dict[str, Any] = {}
    for label, relpath in (("r7", R7_MAINTENANCE_ADOPTION_FILE), ("r8", R8_MAINTENANCE_ADOPTION_FILE)):
        generation_doc, generation_error = _load_yaml_mapping(
            repo_root, relpath, f"MAINTENANCE_{label.upper()}_NOT_MAPPING"
        )
        current_generation[label] = {
            "present": generation_doc is not None,
            "load_error": generation_error,
            "raw": generation_doc,
        }
    if error:
        return {
            "present": True,
            "load_error": error,
            "raw": None,
            "predecessor": {"present": predecessor is not None, "load_error": predecessor_error, "raw": predecessor},
            "terminal_tombstones": tombstones,
            "current_generation": current_generation,
        }
    result: dict[str, Any] = {
        "present": doc is not None,
        "raw": doc,
        "predecessor": {
            "present": predecessor is not None,
            "load_error": predecessor_error,
            "raw": predecessor,
        },
        "terminal_tombstones": tombstones,
        "current_generation": current_generation,
    }
    if doc is None and _maintenance_required(repo_root):
        result["load_error"] = "MAINTENANCE_ADOPTION_MISSING"
    return result


def worker_registry_witness(repo_root: Path) -> dict[str, Any]:
    doc, error = _load_registry_doc(repo_root)
    required = _registry_required(repo_root)
    maintenance = maintenance_adoption_witness(repo_root)
    if error:
        return {
            "present": True,
            "required": required,
            "load_error": error,
            "raw_registry": None,
            "maintenance_adoption": maintenance,
        }
    if doc is None:
        return {
            "present": False,
            "required": required,
            "load_error": "WORKER_REGISTRY_MISSING" if required else None,
            "maintenance_adoption": maintenance,
        }
    return {
        "present": True,
        "required": required,
        "raw_registry": doc,
        "maintenance_adoption": maintenance,
    }


def load_worker_slots(repo_root: Path) -> list[WorkerSlot]:
    doc, error = _load_registry_doc(repo_root)
    if error or doc is None:
        return []
    raw_slots = doc.get("worker_slots")
    if not isinstance(raw_slots, list):
        return []
    return [normalize_worker_slot(raw) for raw in raw_slots if isinstance(raw, dict)]


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def worker_slot_is_executable(slot: WorkerSlot) -> bool:
    resolution = _lifecycle(slot)
    if not resolution.executable or resolution.lifecycle_state != LIFECYCLE_ACTIVE:
        return False
    if slot.agent_type != AGENT_TYPE or slot.executor_role != AGENT_TYPE:
        return False
    required = (
        slot.worker_slot_id,
        slot.model_id,
        slot.task_id,
        slot.route_epoch,
        slot.issue,
        slot.pr,
        slot.branch,
        slot.status,
        slot.resource_class,
        slot.reviewer_role,
        slot.reviewer_separation,
    )
    if any(_is_missing(value) for value in required):
        return False
    if not slot.write_paths or not isinstance(slot.provenance, dict) or not slot.provenance:
        return False
    if slot.reviewer_role == slot.executor_role:
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


def _normalized_sequence(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return sorted(_canonical(item) for item in value)


def _claim_slot_id(claim: dict[str, Any]) -> str | None:
    binding = claim.get("route_binding")
    top_level = claim.get("worker_slot_id")
    bound = binding.get("worker_slot_id") if isinstance(binding, dict) else None
    chosen = top_level if top_level is not None else bound
    return str(chosen) if chosen is not None else None


def _raw_slot_schema_findings(raw: dict[str, Any], index: int) -> list[Finding]:
    findings: list[Finding] = []
    raw_execution_allowed = raw.get("execution_allowed")
    if not isinstance(raw_execution_allowed, bool):
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKER_SLOT_EXECUTION_ALLOWED_TYPE_INVALID",
                "execution_allowed is authority-bearing and must be a real YAML boolean; strings/numbers are never coerced.",
                {"index": index, "actual": raw_execution_allowed, "actual_type": type(raw_execution_allowed).__name__},
            )
        )
    for field in ("activation_state", "closure_state"):
        value = raw.get(field)
        if value is not None and not isinstance(value, str):
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_LIFECYCLE_FIELD_TYPE_INVALID",
                    "Lifecycle projection fields must be strings or null; semantics are resolved only by worker_lifecycle.py.",
                    {"index": index, "field": field, "actual_type": type(value).__name__},
                )
            )
    for field, value in {
        "agent_type": _first(raw, "agent_type", "canonical_agent_type"),
        "executor_role": _first(raw, "executor_role", "role"),
    }.items():
        if not isinstance(value, str) or not value.strip():
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_IDENTITY_FIELD_MISSING",
                    "Live execution identity fields must be explicit; the validator never invents GPT identity defaults.",
                    {"index": index, "field": field, "actual": value},
                )
            )
    for key in _LIST_FIELDS:
        value = raw.get(key, [])
        if not isinstance(value, list):
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_LIST_FIELD_TYPE_INVALID",
                    "Worker slot surface fields must preserve their declared list shape.",
                    {"index": index, "field": key, "actual_type": type(value).__name__},
                )
            )
        elif key in _STRING_SEQUENCE_FIELDS and any(not isinstance(item, str) for item in value):
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_STRING_LIST_ITEM_INVALID",
                    "Worker slot path/domain/authority list entries must be strings.",
                    {"index": index, "field": key},
                )
            )
    provenance = raw.get("provenance")
    if provenance is not None and not isinstance(provenance, dict):
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKER_SLOT_PROVENANCE_TYPE_INVALID",
                "Worker slot provenance must be an explicit mapping.",
                {"index": index, "actual_type": type(provenance).__name__},
            )
        )
    aliases = {"route_epoch": "epoch", "issue": "active_issue", "pr": "implementation_pr"}
    for key in ("route_epoch", "issue", "pr"):
        value = _first(raw, key, aliases[key])
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, str))):
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_ROUTE_SCALAR_TYPE_INVALID",
                    "Route epoch/Issue/PR identity fields must be integer or explicit string identifiers, never booleans/containers.",
                    {"index": index, "field": key, "actual_type": type(value).__name__},
                )
            )
    return findings


def _expected_terminal_records(repo_root: Path) -> dict[str, dict[str, Any]]:
    expected = dict(BASE_EXPECTED_TERMINAL_RECORDS)
    if (repo_root.resolve() / R7_MAINTENANCE_ADOPTION_FILE).exists():
        expected[R7_AUTHORITY_ID] = R7_TERMINAL_RECORD
    return expected


def _terminal_tombstone_findings(repo_root: Path) -> list[Finding]:
    doc, error = _load_terminal_tombstones_doc(repo_root)
    if error:
        return [Finding(CHECK_ID, "ERROR", error, "Terminal maintenance-authority tombstones must be a machine-readable canonical mapping.", {"path": MAINTENANCE_TOMBSTONES_FILE})]
    if doc is None:
        if _maintenance_required(repo_root):
            return [Finding(CHECK_ID, "ERROR", "MAINTENANCE_TOMBSTONES_MISSING", "Maintenance requires the monotonic terminal-authority tombstone registry; deleting it fails closed.", {"path": MAINTENANCE_TOMBSTONES_FILE})]
        return []

    findings: list[Finding] = []
    for field, expected in {
        "schema_version": "1.0",
        "registry_id": EXPECTED_TOMBSTONE_REGISTRY_ID,
        "semantics": EXPECTED_TOMBSTONE_SEMANTICS,
    }.items():
        if doc.get(field) != expected:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_TOMBSTONE_REGISTRY_IDENTITY_INVALID", "Terminal-authority tombstone registry identity/semantics drifted.", {"field": field, "actual": doc.get(field), "required": expected}))

    raw_records = doc.get("terminal_authorities")
    if not isinstance(raw_records, list):
        return findings + [Finding(CHECK_ID, "ERROR", "MAINTENANCE_TOMBSTONE_RECORDS_NOT_LIST", "terminal_authorities must be a list of exact monotonic tombstone records.", {"actual_type": type(raw_records).__name__})]

    records: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(raw_records):
        if not isinstance(raw, dict):
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_TOMBSTONE_RECORD_NOT_MAPPING", "Every terminal-authority tombstone must be a mapping.", {"index": index, "actual_type": type(raw).__name__}))
            continue
        authority_id = raw.get("authority_id")
        if not isinstance(authority_id, str) or not authority_id:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_TOMBSTONE_AUTHORITY_ID_INVALID", "Every tombstone requires a non-empty authority_id.", {"index": index, "actual": authority_id}))
            continue
        if authority_id in records:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_TOMBSTONE_DUPLICATE_AUTHORITY_ID", "A terminal authority ID may appear only once.", {"authority_id": authority_id}))
            continue
        records[authority_id] = raw

    expected_records = _expected_terminal_records(repo_root)
    missing_expected = sorted(set(expected_records) - set(records))
    if missing_expected:
        findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_TOMBSTONE_EXPECTED_ID_MISSING", "A previously terminal authority ID cannot be erased.", {"missing_authority_ids": missing_expected}))

    for authority_id, expected_record in expected_records.items():
        actual = records.get(authority_id)
        if actual is None:
            continue
        for field, expected in expected_record.items():
            if actual.get(field) != expected:
                findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_TOMBSTONE_BINDING_MISMATCH", "Terminal authority tombstone fields are exact authority material and may not drift.", {"authority_id": authority_id, "field": field, "actual": actual.get(field), "required": expected}))

    for authority_id, record in records.items():
        authority_file = record.get("authority_file")
        terminal_state = record.get("terminal_state")
        if not isinstance(authority_file, str) or not authority_file:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_TOMBSTONE_AUTHORITY_FILE_INVALID", "Tombstones must bind an exact authority artifact path.", {"authority_id": authority_id, "actual": authority_file}))
            continue
        if terminal_state != "RELEASED" or record.get("reactivation_allowed") is not False:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_TOMBSTONE_TERMINAL_SEMANTICS_INVALID", "Tombstones must encode RELEASED and reactivation_allowed=false.", {"authority_id": authority_id, "terminal_state": terminal_state, "reactivation_allowed": record.get("reactivation_allowed")}))
            continue
        authority_doc, authority_error = _load_yaml_mapping(repo_root, authority_file, "MAINTENANCE_TOMBSTONED_AUTHORITY_NOT_MAPPING")
        if authority_error or authority_doc is None:
            findings.append(Finding(CHECK_ID, "ERROR", authority_error or "MAINTENANCE_TOMBSTONED_AUTHORITY_MISSING", "A terminal tombstone must remain bound to its durable authority artifact.", {"authority_id": authority_id, "path": authority_file}))
            continue
        if authority_doc.get("authority_id") != authority_id:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_TOMBSTONED_AUTHORITY_ID_MISMATCH", "Tombstone and authority artifact must carry the same exact authority ID.", {"authority_id": authority_id, "actual": authority_doc.get("authority_id")}))
            continue
        if authority_doc.get("state") == "ACTIVE":
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_TERMINAL_AUTHORITY_REACTIVATION", "A tombstoned authority ID is monotonically terminal and may never become ACTIVE again.", {"authority_id": authority_id, "path": authority_file}))
        elif authority_doc.get("state") != terminal_state:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_TOMBSTONED_AUTHORITY_STATE_MISMATCH", "A tombstoned authority artifact must remain RELEASED.", {"authority_id": authority_id, "actual": authority_doc.get("state"), "required": terminal_state}))
    return findings


def _maintenance_adoption_findings(repo_root: Path) -> list[Finding]:
    doc, error = _load_maintenance_adoption_doc(repo_root)
    required = _maintenance_required(repo_root)
    if error:
        return [Finding(CHECK_ID, "ERROR", error, "GPT corrective maintenance/adoption authority must be a machine-readable mapping.", {"path": MAINTENANCE_ADOPTION_FILE})]
    if doc is None:
        if required:
            return [Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_MISSING", "R144 R5 requires its retained maintenance/adoption authority artifact.", {"path": MAINTENANCE_ADOPTION_FILE})]
        return []

    findings: list[Finding] = []
    for field, expected in {
        "schema_version": "1.0",
        "authority_id": EXPECTED_MAINTENANCE_AUTHORITY_ID,
        "authority_type": EXPECTED_MAINTENANCE_AUTHORITY_TYPE,
        "issuer": "USER",
        "actor": "GPT_ARCHITECTURE_OWNER",
    }.items():
        if doc.get(field) != expected:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_IDENTITY_INVALID", "Corrective maintenance/adoption authority identity does not match the exact R144 R5 contract.", {"field": field, "actual": doc.get(field), "required": expected}))

    task_brief, task_brief_error = _load_r144_task_brief(repo_root)
    if task_brief_error or task_brief is None:
        findings.append(Finding(CHECK_ID, "ERROR", task_brief_error or "MAINTENANCE_TASK_BRIEF_MISSING", "R144 maintenance exact binding requires the stable canonical task brief.", {"path": R144_TASK_BRIEF_FILE}))
        task_brief = {}
    expected_binding = {
        "task_id": task_brief.get("task_id"),
        "route_epoch": task_brief.get("route_epoch"),
        "issue": task_brief.get("issue"),
        "pr": EXPECTED_MAINTENANCE_PR,
        "branch": task_brief.get("planned_branch"),
        "trigger_review": EXPECTED_MAINTENANCE_TRIGGER_REVIEW,
        "adopted_candidate_input_head": EXPECTED_MAINTENANCE_INPUT_HEAD,
        "activation_parent_head": EXPECTED_MAINTENANCE_INPUT_HEAD,
    }
    for field, expected in expected_binding.items():
        if _is_missing(expected) or doc.get(field) != expected:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_BINDING_MISMATCH", "Maintenance/adoption authority must mechanically match the exact R144 R5 binding.", {"field": field, "actual": doc.get(field), "required": expected}))
    for field in ("adopted_candidate_input_head", "activation_parent_head"):
        value = doc.get(field)
        if not isinstance(value, str) or not _HEX40.fullmatch(value):
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_INPUT_HEAD_INVALID", "Maintenance/adoption head bindings must be exact 40-hex commit identities.", {"field": field, "actual": value}))

    expected_predecessor_ref = {
        "path": R4_MAINTENANCE_ADOPTION_FILE,
        "authority_id": EXPECTED_PREDECESSOR_AUTHORITY_ID,
        "required_state": "RELEASED",
        "required_terminal_scope_status": EXPECTED_RELEASED_SCOPE_STATUS,
    }
    if doc.get("predecessor_authority") != expected_predecessor_ref:
        findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_PREDECESSOR_BINDING_INVALID", "R5 must remain chained to the released R4 authority.", {"actual": doc.get("predecessor_authority"), "required": expected_predecessor_ref}))

    predecessor_doc, predecessor_error = _load_predecessor_maintenance_doc(repo_root)
    if predecessor_error or predecessor_doc is None:
        findings.append(Finding(CHECK_ID, "ERROR", predecessor_error or "MAINTENANCE_PREDECESSOR_MISSING", "R5 requires the retained R4 authority.", {"path": R4_MAINTENANCE_ADOPTION_FILE}))
    else:
        predecessor_actual = {
            "authority_id": predecessor_doc.get("authority_id"),
            "state": predecessor_doc.get("state"),
            "released_scope_status": predecessor_doc.get("released_scope_status"),
        }
        predecessor_expected = {
            "authority_id": EXPECTED_PREDECESSOR_AUTHORITY_ID,
            "state": "RELEASED",
            "released_scope_status": EXPECTED_RELEASED_SCOPE_STATUS,
        }
        if predecessor_actual != predecessor_expected:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_PREDECESSOR_NOT_RELEASED", "R4 must remain released before R5 can operate.", {"actual": predecessor_actual, "required": predecessor_expected}))

    state = doc.get("state")
    if state not in {"ACTIVE", "RELEASED"}:
        findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_STATE_INVALID", "Maintenance state must be ACTIVE or RELEASED.", {"actual": state}))
    expected_state_machine = {
        "active_scope_status": "BOUNDED_CORRECTIVE_MAINTENANCE_OPEN",
        "released_scope_status_required": EXPECTED_RELEASED_SCOPE_STATUS,
        "released_is_terminal_for_authority_id": True,
        "next_activation_requires_new_user_issued_authority_id": True,
        "terminality_must_not_depend_on_mutable_release_receipt_presence": True,
    }
    if doc.get("state_machine") != expected_state_machine:
        findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_STATE_MACHINE_INVALID", "R5 maintenance authority must retain the exact monotonic state contract.", {"actual": doc.get("state_machine"), "required": expected_state_machine}))

    release_fields = ("release_reason", "released_scope_status", "release_transition")
    if state == "ACTIVE":
        present = [field for field in release_fields if field in doc]
        if present:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_REACTIVATION_FORBIDDEN", "An authority carrying release markers cannot be switched back to ACTIVE.", {"release_fields_present": present}))
    elif state == "RELEASED":
        if _is_missing(doc.get("release_reason")):
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_RELEASE_RECEIPT_MISSING", "RELEASED maintenance authority requires release_reason.", {}))
        if doc.get("released_scope_status") != EXPECTED_RELEASED_SCOPE_STATUS:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_RELEASE_SCOPE_INVALID", "RELEASED grants no further modifier writes.", {"actual": doc.get("released_scope_status"), "required": EXPECTED_RELEASED_SCOPE_STATUS}))
        expected_transition = {
            "from_state": "ACTIVE",
            "to_state": "RELEASED",
            "terminal_for_authority_id": True,
            "next_activation_requires_new_user_issued_authority_id": True,
        }
        if doc.get("release_transition") != expected_transition:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_RELEASE_TRANSITION_INVALID", "RELEASED requires explicit terminal ACTIVE->RELEASED transition.", {"actual": doc.get("release_transition"), "required": expected_transition}))

    for field in (
        "execution_allowed",
        "runtime_write_allowed",
        "trade_allowed",
        "merge_authority",
        "acceptance_authority",
        "self_review_allowed",
        "retroactive_workbuddy_authorization",
    ):
        if doc.get(field) is not False:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_UNSAFE_AUTHORITY", "Corrective maintenance may never grant runtime/trade/review/merge authority.", {"field": field, "actual": doc.get(field)}))
    for field in ("independent_review_required", "same_pr_required", "fresh_exact_head_ci_required"):
        if doc.get(field) is not True:
            findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_GUARD_MISSING", "Maintenance requires same-PR continuity, exact-head CI and independent review.", {"field": field, "actual": doc.get(field)}))
    allowed = doc.get("allowed_write_paths")
    if not isinstance(allowed, list) or not allowed or any(not isinstance(item, str) or not item for item in allowed):
        findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_WRITE_SCOPE_INVALID", "Maintenance must declare bounded write paths.", {"actual": allowed}))
    provenance = doc.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        findings.append(Finding(CHECK_ID, "ERROR", "MAINTENANCE_ADOPTION_PROVENANCE_MISSING", "Maintenance requires truthful provenance.", {}))
    return findings


def _generation_authority_findings(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for label, relpath in (("R7", R7_MAINTENANCE_ADOPTION_FILE), ("R8", R8_MAINTENANCE_ADOPTION_FILE)):
        doc, error = _load_yaml_mapping(repo_root, relpath, f"MAINTENANCE_{label}_NOT_MAPPING")
        if error:
            findings.append(Finding(CHECK_ID, "ERROR", error, f"{label} maintenance authority must be a mapping.", {"path": relpath}))
            continue
        if doc is None:
            continue
        if doc.get("authority_type") != EXPECTED_MAINTENANCE_AUTHORITY_TYPE or doc.get("issuer") != "USER" or doc.get("actor") != "GPT_ARCHITECTURE_OWNER":
            findings.append(Finding(CHECK_ID, "ERROR", f"MAINTENANCE_{label}_IDENTITY_INVALID", f"{label} maintenance authority identity is invalid.", {"path": relpath}))
        if doc.get("state") not in {"ACTIVE", "RELEASED"}:
            findings.append(Finding(CHECK_ID, "ERROR", f"MAINTENANCE_{label}_STATE_INVALID", f"{label} maintenance state must be ACTIVE or RELEASED.", {"actual": doc.get("state")}))
        for field in ("execution_allowed", "runtime_write_allowed", "trade_allowed", "merge_authority", "acceptance_authority", "self_review_allowed"):
            if doc.get(field) is not False:
                findings.append(Finding(CHECK_ID, "ERROR", f"MAINTENANCE_{label}_UNSAFE_AUTHORITY", f"{label} maintenance may not grant runtime/trade/review/merge authority.", {"field": field, "actual": doc.get(field)}))
        if doc.get("independent_review_required") is not True or doc.get("fresh_exact_head_ci_required") is not True:
            findings.append(Finding(CHECK_ID, "ERROR", f"MAINTENANCE_{label}_GUARD_MISSING", f"{label} maintenance requires exact-head CI and independent review.", {}))
        if doc.get("state") == "RELEASED":
            if doc.get("released_scope_status") != EXPECTED_RELEASED_SCOPE_STATUS:
                findings.append(Finding(CHECK_ID, "ERROR", f"MAINTENANCE_{label}_RELEASE_SCOPE_INVALID", f"{label} RELEASED must grant no further writes.", {"actual": doc.get("released_scope_status")}))
            transition = doc.get("release_transition")
            if not isinstance(transition, dict) or transition.get("to_state") != "RELEASED" or transition.get("terminal_for_authority_id") is not True:
                findings.append(Finding(CHECK_ID, "ERROR", f"MAINTENANCE_{label}_RELEASE_TRANSITION_INVALID", f"{label} release must be terminal.", {"actual": transition}))
    return findings


def _registry_findings(repo_root: Path) -> list[Finding]:
    root = repo_root.resolve()
    doc, error = _load_registry_doc(root)
    findings: list[Finding] = []
    required = _registry_required(root)
    if error:
        return [Finding(CHECK_ID, "ERROR", error, "GPT Engineering Worker registry must be a YAML mapping.", {"path": GPT_WORKERS_REGISTRY})]
    if doc is None:
        if required:
            return [Finding(CHECK_ID, "ERROR", "WORKER_REGISTRY_MISSING", "Control Tower requires the canonical GPT Engineering Worker registry.", {"path": GPT_WORKERS_REGISTRY})]
        return findings

    if not registry_schema_supported(doc.get("schema_version")):
        findings.append(Finding(CHECK_ID, "ERROR", "WORKER_REGISTRY_IDENTITY_INVALID", "GPT worker registry schema is not supported by canonical worker_lifecycle.py.", {"field": "schema_version", "actual": doc.get("schema_version"), "required": "canonical 1.5 or governed legacy compatibility"}))
    for field, expected in {"registry_id": EXPECTED_REGISTRY_ID, "agent_type": AGENT_TYPE}.items():
        if doc.get(field) != expected:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_REGISTRY_IDENTITY_INVALID", "GPT worker registry identity does not match the canonical contract.", {"field": field, "actual": doc.get(field), "required": expected}))

    if not isinstance(doc.get("parallel_routes_allowed"), bool):
        findings.append(Finding(CHECK_ID, "ERROR", "WORKER_REGISTRY_PARALLEL_POLICY_INVALID", "parallel_routes_allowed must be boolean.", {"actual": doc.get("parallel_routes_allowed")}))
    raw_slots = doc.get("worker_slots")
    if not isinstance(raw_slots, list):
        findings.append(Finding(CHECK_ID, "ERROR", "WORKER_REGISTRY_SLOTS_NOT_LIST", "worker_slots must be a list.", {"actual_type": type(raw_slots).__name__}))
    else:
        for index, raw in enumerate(raw_slots):
            if not isinstance(raw, dict):
                findings.append(Finding(CHECK_ID, "ERROR", "WORKER_REGISTRY_SLOT_NOT_MAPPING", "Every worker_slots entry must be a mapping.", {"index": index, "actual_type": type(raw).__name__}))
                continue
            findings.extend(_raw_slot_schema_findings(raw, index))

    capacity_policy = _program_capacity_policy(root)
    canonical_parallel = capacity_policy.get("gpt_engineering_worker_parallel_routes_allowed")
    if not isinstance(canonical_parallel, bool):
        findings.append(Finding(CHECK_ID, "ERROR", "WORKER_REGISTRY_PROGRAM_PARALLEL_POLICY_MISSING", "Program capacity policy must govern GPT parallel routes.", {"actual": canonical_parallel}))
    elif doc.get("parallel_routes_allowed") is not canonical_parallel:
        findings.append(Finding(CHECK_ID, "ERROR", "WORKER_REGISTRY_PARALLEL_POLICY_DRIFT", "Worker registry parallel policy must match Program capacity policy.", {"registry": doc.get("parallel_routes_allowed"), "program": canonical_parallel}))
    if capacity_policy.get("nested_parallelism") != "FORBIDDEN":
        findings.append(Finding(CHECK_ID, "ERROR", "WORKER_REGISTRY_NESTED_PARALLELISM_POLICY_INVALID", "nested_parallelism must remain FORBIDDEN.", {"actual": capacity_policy.get("nested_parallelism")}))
    return findings


def _slot_required_field_findings(slot: WorkerSlot) -> list[Finding]:
    findings: list[Finding] = []
    resolution = _lifecycle(slot)
    if resolution.lifecycle_state == LIFECYCLE_UNKNOWN:
        findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_LIFECYCLE_UNKNOWN", "worker_lifecycle.py could not prove a safe lifecycle state; execution and free-capacity claims fail closed.", {"worker_slot_id": slot.worker_slot_id, "lifecycle_findings": list(resolution.findings)}))
        return findings
    if resolution.lifecycle_state in {LIFECYCLE_ACTIVE, LIFECYCLE_RESERVED}:
        values = {
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
            "resource_class": slot.resource_class,
            "reviewer_role": slot.reviewer_role,
            "reviewer_separation": slot.reviewer_separation,
        }
        for field in _LIVE_REQUIRED_FIELDS:
            if _is_missing(values[field]):
                findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_LIVE_BINDING_INCOMPLETE", "ACTIVE/RESERVED slots require complete explicit route/identity/reviewer binding.", {"worker_slot_id": slot.worker_slot_id, "missing_field": field}))
        if not slot.write_paths:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_WRITE_SURFACE_MISSING", "ACTIVE/RESERVED slots require bounded write paths.", {"worker_slot_id": slot.worker_slot_id}))
        if not isinstance(slot.provenance, dict) or not slot.provenance:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_PROVENANCE_MISSING", "ACTIVE/RESERVED slots require explicit provenance.", {"worker_slot_id": slot.worker_slot_id}))
    return findings


def _slot_claim_findings(repo_root: Path, slots: list[WorkerSlot], registry: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    try:
        claims_doc = load_yaml(repo_root / CLAIMS_FILE)
    except (OSError, ValueError, TypeError):
        claims_doc = {}
    raw_claims = claims_doc.get("claims") if isinstance(claims_doc, dict) else None
    if not isinstance(raw_claims, list):
        raw_claims = []
    lanes = {str(item.get("lane_id")): item for item in (registry.get("program_lanes", []) or []) if isinstance(item, dict) and item.get("lane_id")}

    for slot in slots:
        resolution = _lifecycle(slot)
        required_claim_state = None
        if resolution.lifecycle_state == LIFECYCLE_ACTIVE:
            required_claim_state = ACTIVE_CLAIM_STATE
        elif resolution.lifecycle_state == LIFECYCLE_RESERVED:
            required_claim_state = RESERVED_CLAIM_STATE
        if required_claim_state is None:
            continue

        candidates = [
            claim for claim in raw_claims
            if isinstance(claim, dict)
            and claim.get("execution_agent") == AGENT_TYPE
            and str(claim.get("claim_state")) == required_claim_state
            and _claim_slot_id(claim) == slot.worker_slot_id
        ]
        if len(candidates) != 1:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_EXACT_CLAIM_CARDINALITY", "Every ACTIVE/RESERVED GPT worker slot must have exactly one matching Work Claim.", {"worker_slot_id": slot.worker_slot_id, "required_claim_state": required_claim_state, "matching_claims": len(candidates)}))
            continue
        claim = candidates[0]
        binding = claim.get("route_binding") if isinstance(claim.get("route_binding"), dict) else {}
        expected_identity = {
            "worker_slot_id": slot.worker_slot_id,
            "task_id": slot.task_id,
            "route_epoch": slot.route_epoch,
            "issue": slot.issue,
            "pr": slot.pr,
            "branch": slot.branch,
        }
        claimed_identity = {
            "worker_slot_id": binding.get("worker_slot_id"),
            "task_id": binding.get("task_id"),
            "route_epoch": binding.get("route_epoch"),
            "issue": binding.get("issue"),
            "pr": binding.get("pr"),
            "branch": binding.get("branch"),
        }
        if claim.get("worker_slot_id") != slot.worker_slot_id or claimed_identity != expected_identity:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_ACTIVE_CLAIM_BINDING_DRIFT", "Worker slot and Work Claim route identity disagree.", {"worker_slot_id": slot.worker_slot_id, "claimed": claimed_identity, "expected": expected_identity}))
        slot_surface = {
            "write_paths": _normalized_sequence(slot.write_paths),
            "read_paths": _normalized_sequence(slot.read_paths),
            "interfaces": _normalized_sequence(slot.interfaces),
            "read_domains": _normalized_sequence(slot.read_domains),
            "write_domains": _normalized_sequence(slot.write_domains),
            "authority_claims": _normalized_sequence(slot.authority_claims),
            "resource_class": slot.resource_class,
        }
        claim_surface = {
            "write_paths": _normalized_sequence(claim.get("write_paths")),
            "read_paths": _normalized_sequence(claim.get("read_paths")),
            "interfaces": _normalized_sequence(claim.get("interfaces")),
            "read_domains": _normalized_sequence(claim.get("read_domains")),
            "write_domains": _normalized_sequence(claim.get("write_domains")),
            "authority_claims": _normalized_sequence(claim.get("authority_claims")),
            "resource_class": claim.get("resource_class"),
        }
        if slot_surface != claim_surface:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_CLAIM_SURFACE_DRIFT", "Worker slot execution surface must exactly match its Work Claim.", {"worker_slot_id": slot.worker_slot_id, "slot": slot_surface, "claim": claim_surface}))
        if slot.resource_class and "HEAVY" in str(slot.resource_class).upper():
            lane = lanes.get(str(claim.get("lane_id")), {})
            if not bool(lane.get("heavy_execution_authorized", False)):
                findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_HEAVY_WITHOUT_LANE_AUTHORIZATION", "Heavy GPT slot requires lane heavy_execution_authorized=true.", {"worker_slot_id": slot.worker_slot_id, "lane_id": claim.get("lane_id")}))
    return findings


def worker_slot_findings(repo_root: Path) -> list[Finding]:
    root = repo_root.resolve()
    findings: list[Finding] = []
    findings.extend(_registry_findings(root))
    findings.extend(_terminal_tombstone_findings(root))
    findings.extend(_maintenance_adoption_findings(root))
    findings.extend(_generation_authority_findings(root))
    slots = load_worker_slots(root)

    for slot in slots:
        findings.extend(_slot_required_field_findings(slot))
        resolution = _lifecycle(slot)
        if not slot.worker_slot_id:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_ID_MISSING", "GPT worker slot lacks stable worker_slot_id.", {"fingerprint": slot.fingerprint}))
        if slot.agent_type != AGENT_TYPE or slot.executor_role != AGENT_TYPE:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_IMPERSONATION", "GPT worker must carry explicit GPT identity and may not impersonate another executor.", {"worker_slot_id": slot.worker_slot_id, "agent_type": slot.agent_type, "executor_role": slot.executor_role}))
        if slot.reviewer_role and slot.reviewer_role == slot.executor_role:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_SELF_REVIEW", "Execution identity must differ from reviewer role.", {"worker_slot_id": slot.worker_slot_id, "reviewer_role": slot.reviewer_role}))
        if resolution.lifecycle_state == LIFECYCLE_RESERVED and slot.execution_allowed:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_RESERVED_EXECUTABLE", "A reserved slot may not carry an executable lease.", {"worker_slot_id": slot.worker_slot_id}))
        if resolution.lifecycle_state == LIFECYCLE_UNKNOWN and slot.execution_allowed and str(slot.activation_state or "").upper() in {"RELEASED", "CLOSED", "FROZEN"}:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_CLOSED_HAS_LEASE", "A closed/released/frozen slot retains an execution lease.", {"worker_slot_id": slot.worker_slot_id, "task_id": slot.task_id}))
        if resolution.lifecycle_state == LIFECYCLE_ACTIVE and not worker_slot_is_executable(slot):
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_ACTIVE_NOT_EXECUTABLE", "An ACTIVE slot must satisfy every strict executable prerequisite.", {"worker_slot_id": slot.worker_slot_id, "status": slot.status, "execution_allowed": slot.execution_allowed}))

    seen: dict[str, list[str]] = {}
    for slot in slots:
        if slot.worker_slot_id:
            seen.setdefault(slot.worker_slot_id, []).append(slot.task_id or "UNKNOWN_TASK")
    for slot_id, tasks in seen.items():
        if len(tasks) > 1:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_DUPLICATE_ID", "Same worker slot identity is double-booked.", {"worker_slot_id": slot_id, "tasks": tasks}))

    capacity_policy = _program_capacity_policy(root)
    if _registry_required(root) or (root / GPT_WORKERS_REGISTRY).exists():
        capacity = capacity_policy.get("gpt_engineering_worker_active_slots_max")
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_CAPACITY_POLICY_INVALID", "Program capacity policy must provide a positive GPT slot limit.", {"actual": capacity}))
        lifecycle_audit = audit_worker_registry_lifecycle(root)
        if "GPT_WORKER_OCCUPIED_CAPACITY_EXCEEDED" in lifecycle_audit.findings:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_CAPACITY_EXCEEDED", "Canonical lifecycle occupancy exceeds configured capacity.", {"occupied_slots": list(lifecycle_audit.occupied_capacity_slots), "limit": lifecycle_audit.configured_capacity_limit}))

    active_executable = [slot for slot in slots if worker_slot_is_executable(slot)]
    if capacity_policy.get("nested_parallelism") == "FORBIDDEN":
        task_slots: dict[str, list[str | None]] = {}
        for slot in active_executable:
            if slot.task_id:
                task_slots.setdefault(str(slot.task_id), []).append(slot.worker_slot_id)
        for task_id, slot_ids in task_slots.items():
            if len(slot_ids) > 1:
                findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_NESTED_PARALLELISM_FORBIDDEN", "One task may not hold multiple active GPT worker slots.", {"task_id": task_id, "worker_slots": slot_ids}))
    for left, right in combinations(active_executable, 2):
        collision = classify_collision(_slot_claim_surface(left), _slot_claim_surface(right))
        if collision["level"] in {"O3", "O4"}:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKER_SLOT_COLLISION", "Two active GPT worker slots collide on mutable surface/authority.", {"pair": [left.worker_slot_id, right.worker_slot_id], "collision": collision}))

    try:
        registry = load_yaml(root / PROGRAM_REGISTRY)
    except (OSError, ValueError, TypeError):
        registry = {}
    if isinstance(registry, dict):
        findings.extend(_slot_claim_findings(root, slots, registry))
    return findings


def validate_worker_slots(repo_root: Path) -> dict[str, Any]:
    slots = load_worker_slots(repo_root)
    findings = worker_slot_findings(repo_root)
    errors = [asdict(item) for item in findings if item.severity == "ERROR"]
    warnings = [asdict(item) for item in findings if item.severity == "WARN"]
    registry_witness = worker_registry_witness(repo_root)
    maintenance_witness = maintenance_adoption_witness(repo_root)
    tombstone_witness = terminal_tombstones_witness(repo_root)
    maintenance_errors = [item for item in errors if str(item.get("code", "")).startswith("MAINTENANCE_")]
    maintenance_raw = maintenance_witness.get("raw") if isinstance(maintenance_witness, dict) else None
    maintenance_state = maintenance_raw.get("state") if isinstance(maintenance_raw, dict) else None
    lifecycle_audit = audit_worker_registry_lifecycle(repo_root)
    return {
        "schema_version": "1.5",
        "agent_type": AGENT_TYPE,
        "worker_registry": registry_witness,
        "worker_registry_fingerprint": hashlib.sha256(_canonical(registry_witness).encode("utf-8")).hexdigest(),
        "maintenance_adoption": maintenance_witness,
        "maintenance_terminal_tombstones": tombstone_witness,
        "maintenance_authority_id": maintenance_raw.get("authority_id") if isinstance(maintenance_raw, dict) else None,
        "maintenance_authority_state": maintenance_state,
        "maintenance_write_allowed": maintenance_state == "ACTIVE" and not maintenance_errors,
        "maintenance_adoption_structural_check": "PASS" if not maintenance_errors else "FAIL",
        "worker_slots": [worker_slot_route_witness(slot) for slot in slots],
        "active_executable_slots": [slot.worker_slot_id for slot in slots if worker_slot_is_executable(slot)],
        "lifecycle_audit": lifecycle_audit.to_dict(),
        "errors": errors,
        "warnings": warnings,
        "worker_slot_structural_check": "PASS" if not errors else "FAIL",
    }
