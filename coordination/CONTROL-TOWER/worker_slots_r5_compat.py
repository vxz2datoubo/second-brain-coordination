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

GPT_WORKERS_REGISTRY = "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
CLAIMS_FILE = "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml"
R3_MAINTENANCE_ADOPTION_FILE = "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION.yaml"
R4_MAINTENANCE_ADOPTION_FILE = "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION-R4.yaml"
MAINTENANCE_ADOPTION_FILE = "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION-R5.yaml"
MAINTENANCE_TOMBSTONES_FILE = "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-TERMINAL-TOMBSTONES.yaml"
R144_TASK_BRIEF_FILE = "coordination/TASK-BRIEFS/CODEX-CONTROL-TOWER-GPT-ENGINEERING-WORKER-FIRST-CLASS-R144.yaml"
AGENT_TYPE = "GPT_ENGINEERING_WORKER"
CHECK_ID = "CT-WS"
EXPECTED_SCHEMA_VERSION = "1.0"
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
EXPECTED_TERMINAL_RECORDS: dict[str, dict[str, Any]] = {
    EXPECTED_PREDECESSOR_AUTHORITY_ID: R4_TERMINAL_RECORD,
    EXPECTED_MAINTENANCE_AUTHORITY_ID: R5_TERMINAL_RECORD,
}

ACTIVATION_ACTIVE = "ACTIVE"
ACTIVATION_RESERVED = "RESERVED"
ACTIVATION_RELEASED = "RELEASED"
CLOSURE_RELEASED = "RELEASED"
ACTIVE_CLAIM_STATE = "ACTIVE_IMPLEMENTATION"
RESERVED_CLAIM_STATE = "RESERVED_IMPLEMENTATION_NON_EXECUTABLE"
ALLOWED_ACTIVATION_STATES = frozenset({ACTIVATION_ACTIVE, ACTIVATION_RESERVED, ACTIVATION_RELEASED})
ALLOWED_CLOSURE_STATES = frozenset({CLOSURE_RELEASED})

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
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


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


def _load_registry_doc(repo_root: Path) -> tuple[dict[str, Any] | None, str | None]:
    root = repo_root.resolve()
    path = root / GPT_WORKERS_REGISTRY
    if not path.exists():
        return None, None
    try:
        return load_yaml(path), None
    except (OSError, ValueError, TypeError):
        return None, "WORKER_REGISTRY_NOT_MAPPING"


def _load_yaml_mapping(repo_root: Path, relpath: str, error_code: str) -> tuple[dict[str, Any] | None, str | None]:
    path = repo_root.resolve() / relpath
    if not path.exists():
        return None, None
    try:
        return load_yaml(path), None
    except (OSError, ValueError, TypeError):
        return None, error_code


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
    if error:
        return {
            "present": True,
            "load_error": error,
            "raw": None,
            "predecessor": {"present": predecessor is not None, "load_error": predecessor_error, "raw": predecessor},
            "terminal_tombstones": tombstones,
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


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def worker_slot_is_executable(slot: WorkerSlot) -> bool:
    if slot.activation_state != ACTIVATION_ACTIVE:
        return False
    if slot.agent_type != AGENT_TYPE or slot.executor_role != AGENT_TYPE:
        return False
    if slot.execution_allowed is not True:
        return False
    if slot.closure_state == CLOSURE_RELEASED:
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

    identity_fields = {
        "agent_type": _first(raw, "agent_type", "canonical_agent_type"),
        "executor_role": _first(raw, "executor_role", "role"),
    }
    for field, value in identity_fields.items():
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

    for key in ("route_epoch", "issue", "pr"):
        value = _first(raw, key, {"route_epoch": "epoch", "issue": "active_issue", "pr": "implementation_pr"}[key])
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


def _terminal_tombstone_findings(repo_root: Path) -> list[Finding]:
    doc, error = _load_terminal_tombstones_doc(repo_root)
    if error:
        return [
            Finding(
                CHECK_ID,
                "ERROR",
                error,
                "Terminal maintenance-authority tombstones must be a machine-readable canonical mapping.",
                {"path": MAINTENANCE_TOMBSTONES_FILE},
            )
        ]
    if doc is None:
        if _maintenance_required(repo_root):
            return [
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_TOMBSTONES_MISSING",
                    "R144 R5 requires the monotonic terminal-authority tombstone registry; deleting it fails closed.",
                    {"path": MAINTENANCE_TOMBSTONES_FILE},
                )
            ]
        return []

    findings: list[Finding] = []
    expected_identity = {
        "schema_version": "1.0",
        "registry_id": EXPECTED_TOMBSTONE_REGISTRY_ID,
        "semantics": EXPECTED_TOMBSTONE_SEMANTICS,
    }
    for field, expected in expected_identity.items():
        if doc.get(field) != expected:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_TOMBSTONE_REGISTRY_IDENTITY_INVALID",
                    "Terminal-authority tombstone registry identity/semantics drifted from the R144 R5 contract.",
                    {"field": field, "actual": doc.get(field), "required": expected},
                )
            )

    raw_records = doc.get("terminal_authorities")
    if not isinstance(raw_records, list):
        return findings + [
            Finding(
                CHECK_ID,
                "ERROR",
                "MAINTENANCE_TOMBSTONE_RECORDS_NOT_LIST",
                "terminal_authorities must be a list of exact monotonic tombstone records.",
                {"actual_type": type(raw_records).__name__},
            )
        ]

    records: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(raw_records):
        if not isinstance(raw, dict):
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_TOMBSTONE_RECORD_NOT_MAPPING",
                    "Every terminal-authority tombstone must be a mapping.",
                    {"index": index, "actual_type": type(raw).__name__},
                )
            )
            continue
        authority_id = raw.get("authority_id")
        if not isinstance(authority_id, str) or not authority_id:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_TOMBSTONE_AUTHORITY_ID_INVALID",
                    "Every tombstone requires a non-empty authority_id.",
                    {"index": index, "actual": authority_id},
                )
            )
            continue
        if authority_id in records:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_TOMBSTONE_DUPLICATE_AUTHORITY_ID",
                    "A terminal authority ID may appear only once in the monotonic tombstone registry.",
                    {"authority_id": authority_id},
                )
            )
            continue
        records[authority_id] = raw

    missing_expected = sorted(set(EXPECTED_TERMINAL_RECORDS) - set(records))
    if missing_expected:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "MAINTENANCE_TOMBSTONE_EXPECTED_ID_MISSING",
                "A previously terminal authority ID cannot be erased from the canonical tombstone registry.",
                {"missing_authority_ids": missing_expected},
            )
        )

    for authority_id, expected_record in EXPECTED_TERMINAL_RECORDS.items():
        actual = records.get(authority_id)
        if actual is None:
            continue
        for field, expected in expected_record.items():
            if actual.get(field) != expected:
                findings.append(
                    Finding(
                        CHECK_ID,
                        "ERROR",
                        "MAINTENANCE_TOMBSTONE_BINDING_MISMATCH",
                        "Terminal authority tombstone fields are exact authority material and may not drift.",
                        {"authority_id": authority_id, "field": field, "actual": actual.get(field), "required": expected},
                    )
                )

    for authority_id, record in records.items():
        authority_file = record.get("authority_file")
        terminal_state = record.get("terminal_state")
        if not isinstance(authority_file, str) or not authority_file:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_TOMBSTONE_AUTHORITY_FILE_INVALID",
                    "Tombstones must bind an exact authority artifact path.",
                    {"authority_id": authority_id, "actual": authority_file},
                )
            )
            continue
        if terminal_state != "RELEASED" or record.get("reactivation_allowed") is not False:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_TOMBSTONE_TERMINAL_SEMANTICS_INVALID",
                    "Tombstones must encode RELEASED and reactivation_allowed=false.",
                    {"authority_id": authority_id, "terminal_state": terminal_state, "reactivation_allowed": record.get("reactivation_allowed")},
                )
            )
            continue
        authority_doc, authority_error = _load_yaml_mapping(
            repo_root,
            authority_file,
            "MAINTENANCE_TOMBSTONED_AUTHORITY_NOT_MAPPING",
        )
        if authority_error or authority_doc is None:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    authority_error or "MAINTENANCE_TOMBSTONED_AUTHORITY_MISSING",
                    "A terminal tombstone must remain bound to its durable authority artifact.",
                    {"authority_id": authority_id, "path": authority_file},
                )
            )
            continue
        if authority_doc.get("authority_id") != authority_id:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_TOMBSTONED_AUTHORITY_ID_MISMATCH",
                    "Tombstone and authority artifact must carry the same exact authority ID.",
                    {"authority_id": authority_id, "actual": authority_doc.get("authority_id")},
                )
            )
            continue
        if authority_doc.get("state") == "ACTIVE":
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_TERMINAL_AUTHORITY_REACTIVATION",
                    "A tombstoned authority ID is monotonically terminal and may never become ACTIVE again, even if every release receipt field is deleted.",
                    {"authority_id": authority_id, "path": authority_file},
                )
            )
        elif authority_doc.get("state") != terminal_state:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_TOMBSTONED_AUTHORITY_STATE_MISMATCH",
                    "A tombstoned authority artifact must remain in its terminal RELEASED state.",
                    {"authority_id": authority_id, "actual": authority_doc.get("state"), "required": terminal_state},
                )
            )
    return findings


def _maintenance_adoption_findings(repo_root: Path) -> list[Finding]:
    doc, error = _load_maintenance_adoption_doc(repo_root)
    required = _maintenance_required(repo_root)
    if error:
        return [
            Finding(
                CHECK_ID,
                "ERROR",
                error,
                "GPT corrective maintenance/adoption authority must be a machine-readable mapping.",
                {"path": MAINTENANCE_ADOPTION_FILE},
            )
        ]
    if doc is None:
        if required:
            return [
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_ADOPTION_MISSING",
                    "R144 R5 requires its fresh maintenance/adoption authority artifact; deleting it cannot silently remove governance.",
                    {"path": MAINTENANCE_ADOPTION_FILE},
                )
            ]
        return []

    findings: list[Finding] = []
    required_scalars = {
        "schema_version": "1.0",
        "authority_id": EXPECTED_MAINTENANCE_AUTHORITY_ID,
        "authority_type": EXPECTED_MAINTENANCE_AUTHORITY_TYPE,
        "issuer": "USER",
        "actor": "GPT_ARCHITECTURE_OWNER",
    }
    for field, expected in required_scalars.items():
        if doc.get(field) != expected:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_ADOPTION_IDENTITY_INVALID",
                    "Corrective maintenance/adoption authority identity does not match the exact R144 R5 contract.",
                    {"field": field, "actual": doc.get(field), "required": expected},
                )
            )

    task_brief, task_brief_error = _load_r144_task_brief(repo_root)
    if task_brief_error or task_brief is None:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                task_brief_error or "MAINTENANCE_TASK_BRIEF_MISSING",
                "R144 maintenance exact binding requires the stable canonical R144 task brief.",
                {"path": R144_TASK_BRIEF_FILE},
            )
        )
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
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_ADOPTION_BINDING_MISMATCH",
                    "Maintenance/adoption authority must mechanically match the exact R144 R5 task/epoch/Issue/PR/branch/review/adopted-head binding.",
                    {"field": field, "actual": doc.get(field), "required": expected},
                )
            )

    for field in ("adopted_candidate_input_head", "activation_parent_head"):
        value = doc.get(field)
        if not isinstance(value, str) or not _HEX40.fullmatch(value):
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_ADOPTION_INPUT_HEAD_INVALID",
                    "Maintenance/adoption head bindings must be exact 40-hex commit identities.",
                    {"field": field, "actual": value},
                )
            )

    predecessor_ref = doc.get("predecessor_authority")
    expected_predecessor_ref = {
        "path": R4_MAINTENANCE_ADOPTION_FILE,
        "authority_id": EXPECTED_PREDECESSOR_AUTHORITY_ID,
        "required_state": "RELEASED",
        "required_terminal_scope_status": EXPECTED_RELEASED_SCOPE_STATUS,
    }
    if predecessor_ref != expected_predecessor_ref:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "MAINTENANCE_ADOPTION_PREDECESSOR_BINDING_INVALID",
                "R5 must be a new authority identity chained to the released/tombstoned R4 authority; R4 may not be reactivated in place.",
                {"actual": predecessor_ref, "required": expected_predecessor_ref},
            )
        )

    predecessor_doc, predecessor_error = _load_predecessor_maintenance_doc(repo_root)
    if predecessor_error or predecessor_doc is None:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                predecessor_error or "MAINTENANCE_PREDECESSOR_MISSING",
                "R5 requires the retained R4 maintenance authority as a released predecessor record.",
                {"path": R4_MAINTENANCE_ADOPTION_FILE},
            )
        )
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
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_ADOPTION_PREDECESSOR_NOT_RELEASED",
                    "The R4 authority must remain a released predecessor before the new R5 authority can operate.",
                    {"actual": predecessor_actual, "required": predecessor_expected},
                )
            )

    state = doc.get("state")
    if state not in {"ACTIVE", "RELEASED"}:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "MAINTENANCE_ADOPTION_STATE_INVALID",
                "Maintenance/adoption authority state must be ACTIVE or RELEASED.",
                {"actual": state},
            )
        )

    state_machine = doc.get("state_machine")
    expected_state_machine = {
        "active_scope_status": "BOUNDED_CORRECTIVE_MAINTENANCE_OPEN",
        "released_scope_status_required": EXPECTED_RELEASED_SCOPE_STATUS,
        "released_is_terminal_for_authority_id": True,
        "next_activation_requires_new_user_issued_authority_id": True,
        "terminality_must_not_depend_on_mutable_release_receipt_presence": True,
    }
    if state_machine != expected_state_machine:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "MAINTENANCE_ADOPTION_STATE_MACHINE_INVALID",
                "R5 maintenance authority must declare the exact monotonic ACTIVE→RELEASED terminal-state contract.",
                {"actual": state_machine, "required": expected_state_machine},
            )
        )

    release_fields = ("release_reason", "released_scope_status", "release_transition")
    if state == "ACTIVE":
        present_release_fields = [field for field in release_fields if field in doc]
        if present_release_fields:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_ADOPTION_REACTIVATION_FORBIDDEN",
                    "An authority identity carrying release markers cannot be switched back to ACTIVE; a new user-issued authority_id is required.",
                    {"release_fields_present": present_release_fields},
                )
            )
    elif state == "RELEASED":
        if _is_missing(doc.get("release_reason")):
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_ADOPTION_RELEASE_RECEIPT_MISSING",
                    "RELEASED maintenance authority requires a non-empty release_reason.",
                    {},
                )
            )
        if doc.get("released_scope_status") != EXPECTED_RELEASED_SCOPE_STATUS:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_ADOPTION_RELEASE_SCOPE_INVALID",
                    "RELEASED must mechanically mean this authority grants no further modifier writes.",
                    {"actual": doc.get("released_scope_status"), "required": EXPECTED_RELEASED_SCOPE_STATUS},
                )
            )
        expected_transition = {
            "from_state": "ACTIVE",
            "to_state": "RELEASED",
            "terminal_for_authority_id": True,
            "next_activation_requires_new_user_issued_authority_id": True,
        }
        if doc.get("release_transition") != expected_transition:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_ADOPTION_RELEASE_TRANSITION_INVALID",
                    "RELEASED requires an explicit terminal ACTIVE→RELEASED transition; reactivation must use a new authority identity.",
                    {"actual": doc.get("release_transition"), "required": expected_transition},
                )
            )

    must_be_false = (
        "execution_allowed",
        "runtime_write_allowed",
        "trade_allowed",
        "merge_authority",
        "acceptance_authority",
        "self_review_allowed",
        "retroactive_workbuddy_authorization",
    )
    for field in must_be_false:
        value = doc.get(field)
        if not isinstance(value, bool) or value is not False:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_ADOPTION_UNSAFE_AUTHORITY",
                    "Corrective maintenance/adoption may never grant runtime execution, trading, merge, acceptance, self-review or retroactive authority.",
                    {"field": field, "actual": value},
                )
            )

    for field in ("independent_review_required", "same_pr_required", "fresh_exact_head_ci_required"):
        value = doc.get(field)
        if not isinstance(value, bool) or value is not True:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "MAINTENANCE_ADOPTION_GUARD_MISSING",
                    "Bounded maintenance/adoption requires same-PR continuity, fresh exact-head CI and separate independent review.",
                    {"field": field, "actual": value},
                )
            )

    allowed = doc.get("allowed_write_paths")
    if not isinstance(allowed, list) or not allowed or any(not isinstance(item, str) or not item for item in allowed):
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "MAINTENANCE_ADOPTION_WRITE_SCOPE_INVALID",
                "Maintenance/adoption authority must declare a non-empty bounded list of write paths.",
                {"actual": allowed},
            )
        )

    provenance = doc.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "MAINTENANCE_ADOPTION_PROVENANCE_MISSING",
                "Maintenance/adoption authority requires explicit truthful provenance and may not manufacture retroactive executor identity.",
                {},
            )
        )
    return findings


def _registry_findings(repo_root: Path) -> list[Finding]:
    root = repo_root.resolve()
    doc, error = _load_registry_doc(root)
    findings: list[Finding] = []
    required = _registry_required(root)
    if error:
        return [
            Finding(
                CHECK_ID,
                "ERROR",
                error,
                "GPT Engineering Worker registry must be a YAML mapping; malformed authority input cannot degrade to an empty registry.",
                {"path": GPT_WORKERS_REGISTRY},
            )
        ]
    if doc is None:
        if required:
            return [
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_REGISTRY_MISSING",
                    "R144-enabled Control Tower requires the canonical GPT Engineering Worker registry; missing authority source means NO EXECUTION.",
                    {"path": GPT_WORKERS_REGISTRY},
                )
            ]
        return findings

    expected = {
        "schema_version": EXPECTED_SCHEMA_VERSION,
        "registry_id": EXPECTED_REGISTRY_ID,
        "agent_type": AGENT_TYPE,
    }
    for field, required_value in expected.items():
        if doc.get(field) != required_value:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_REGISTRY_IDENTITY_INVALID",
                    "GPT Engineering Worker registry identity/schema does not match the canonical contract.",
                    {"field": field, "actual": doc.get(field), "required": required_value},
                )
            )

    if not isinstance(doc.get("parallel_routes_allowed"), bool):
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKER_REGISTRY_PARALLEL_POLICY_INVALID",
                "parallel_routes_allowed must be an explicit boolean authority value.",
                {"actual": doc.get("parallel_routes_allowed")},
            )
        )

    raw_slots = doc.get("worker_slots")
    if not isinstance(raw_slots, list):
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKER_REGISTRY_SLOTS_NOT_LIST",
                "worker_slots must be a list; malformed registry input must fail closed instead of becoming an empty active set.",
                {"actual_type": type(raw_slots).__name__},
            )
        )
    else:
        for index, raw in enumerate(raw_slots):
            if not isinstance(raw, dict):
                findings.append(
                    Finding(
                        CHECK_ID,
                        "ERROR",
                        "WORKER_REGISTRY_SLOT_NOT_MAPPING",
                        "Every worker_slots entry must be a mapping; invalid entries may not be silently dropped.",
                        {"index": index, "actual_type": type(raw).__name__},
                    )
                )
                continue
            findings.extend(_raw_slot_schema_findings(raw, index))

    capacity_policy = _program_capacity_policy(root)
    canonical_parallel = capacity_policy.get("gpt_engineering_worker_parallel_routes_allowed")
    if not isinstance(canonical_parallel, bool):
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKER_REGISTRY_PROGRAM_PARALLEL_POLICY_MISSING",
                "Program capacity policy must explicitly govern GPT Engineering Worker parallel routes.",
                {"actual": canonical_parallel},
            )
        )
    elif doc.get("parallel_routes_allowed") is not canonical_parallel:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKER_REGISTRY_PARALLEL_POLICY_DRIFT",
                "Worker registry parallel policy must match the canonical Program capacity policy.",
                {"registry": doc.get("parallel_routes_allowed"), "program": canonical_parallel},
            )
        )

    nested = capacity_policy.get("nested_parallelism")
    if nested != "FORBIDDEN":
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKER_REGISTRY_NESTED_PARALLELISM_POLICY_INVALID",
                "GPT Engineering Worker first-class execution requires the canonical nested_parallelism=FORBIDDEN guard.",
                {"actual": nested},
            )
        )
    return findings


def _slot_required_field_findings(slot: WorkerSlot) -> list[Finding]:
    findings: list[Finding] = []
    if slot.activation_state not in ALLOWED_ACTIVATION_STATES:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKER_SLOT_ACTIVATION_STATE_INVALID",
                "Worker slot activation_state must be ACTIVE, RESERVED or RELEASED.",
                {"worker_slot_id": slot.worker_slot_id, "activation_state": slot.activation_state},
            )
        )
    if slot.closure_state is not None and slot.closure_state not in ALLOWED_CLOSURE_STATES:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKER_SLOT_CLOSURE_STATE_INVALID",
                "Worker slot closure_state uses an unsupported value.",
                {"worker_slot_id": slot.worker_slot_id, "closure_state": slot.closure_state},
            )
        )

    if slot.activation_state in {ACTIVATION_ACTIVE, ACTIVATION_RESERVED}:
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
                findings.append(
                    Finding(
                        CHECK_ID,
                        "ERROR",
                        "WORKER_SLOT_LIVE_BINDING_INCOMPLETE",
                        "ACTIVE/RESERVED worker slots must carry complete explicit route, identity, provenance and reviewer-separation binding.",
                        {"worker_slot_id": slot.worker_slot_id, "missing_field": field},
                    )
                )
        if not slot.write_paths:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_WRITE_SURFACE_MISSING",
                    "ACTIVE/RESERVED worker slots must declare a bounded write surface.",
                    {"worker_slot_id": slot.worker_slot_id},
                )
            )
        if not isinstance(slot.provenance, dict) or not slot.provenance:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_PROVENANCE_MISSING",
                    "ACTIVE/RESERVED worker slots require explicit provenance; unavailable fields must be recorded as UNKNOWN rather than omitted.",
                    {"worker_slot_id": slot.worker_slot_id},
                )
            )
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

    lanes = {
        str(item.get("lane_id")): item
        for item in (registry.get("program_lanes", []) or [])
        if isinstance(item, dict) and item.get("lane_id")
    }

    for slot in slots:
        required_claim_state = None
        if slot.activation_state == ACTIVATION_ACTIVE:
            required_claim_state = ACTIVE_CLAIM_STATE
        elif slot.activation_state == ACTIVATION_RESERVED:
            required_claim_state = RESERVED_CLAIM_STATE
        if required_claim_state is None:
            continue

        candidates: list[dict[str, Any]] = []
        for claim in raw_claims:
            if not isinstance(claim, dict):
                continue
            if claim.get("execution_agent") != AGENT_TYPE:
                continue
            if str(claim.get("claim_state")) != required_claim_state:
                continue
            if _claim_slot_id(claim) == slot.worker_slot_id:
                candidates.append(claim)

        if len(candidates) != 1:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_EXACT_CLAIM_CARDINALITY",
                    "Every ACTIVE/RESERVED GPT worker slot must be bound by exactly one matching Work Claim; orphan or multiply-claimed execution leases fail closed.",
                    {
                        "worker_slot_id": slot.worker_slot_id,
                        "required_claim_state": required_claim_state,
                        "matching_claims": len(candidates),
                    },
                )
            )
            continue

        claim = candidates[0]
        binding = claim.get("route_binding") if isinstance(claim.get("route_binding"), dict) else {}
        identity_expected = {
            "worker_slot_id": slot.worker_slot_id,
            "task_id": slot.task_id,
            "route_epoch": slot.route_epoch,
            "issue": slot.issue,
            "pr": slot.pr,
            "branch": slot.branch,
        }
        identity_claimed = {
            "worker_slot_id": binding.get("worker_slot_id"),
            "task_id": binding.get("task_id"),
            "route_epoch": binding.get("route_epoch"),
            "issue": binding.get("issue"),
            "pr": binding.get("pr"),
            "branch": binding.get("branch"),
        }
        if claim.get("worker_slot_id") != slot.worker_slot_id or identity_claimed != identity_expected:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_ACTIVE_CLAIM_BINDING_DRIFT",
                    "Worker slot and its exact Work Claim disagree on slot/task/epoch/issue/PR/branch identity.",
                    {
                        "worker_slot_id": slot.worker_slot_id,
                        "claim_worker_slot_id": claim.get("worker_slot_id"),
                        "claimed": identity_claimed,
                        "expected": identity_expected,
                    },
                )
            )

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
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_CLAIM_SURFACE_DRIFT",
                    "Worker slot execution surface must exactly match its Work Claim so collision/resource governance cannot be bypassed.",
                    {"worker_slot_id": slot.worker_slot_id, "slot": slot_surface, "claim": claim_surface},
                )
            )

        if slot.resource_class and "HEAVY" in str(slot.resource_class).upper():
            lane = lanes.get(str(claim.get("lane_id")), {})
            if not bool(lane.get("heavy_execution_authorized", False)):
                findings.append(
                    Finding(
                        CHECK_ID,
                        "ERROR",
                        "WORKER_SLOT_HEAVY_WITHOUT_LANE_AUTHORIZATION",
                        "A heavy GPT worker slot must be attached to a Program Lane with heavy_execution_authorized=true; the global heavy-stage gate remains authoritative.",
                        {"worker_slot_id": slot.worker_slot_id, "lane_id": claim.get("lane_id")},
                    )
                )
    return findings


def worker_slot_findings(repo_root: Path) -> list[Finding]:
    root = repo_root.resolve()
    findings: list[Finding] = []
    findings.extend(_registry_findings(root))
    findings.extend(_terminal_tombstone_findings(root))
    findings.extend(_maintenance_adoption_findings(root))
    slots = load_worker_slots(root)

    for slot in slots:
        findings.extend(_slot_required_field_findings(slot))
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
        if slot.agent_type != AGENT_TYPE or slot.executor_role != AGENT_TYPE:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_IMPERSONATION",
                    "GPT Engineering Worker slot declares a missing/non-GPT agent identity; GPT worker must not impersonate CODEX/QCLAW/WORKBUDDY and identity is never defaulted.",
                    {
                        "worker_slot_id": slot.worker_slot_id,
                        "agent_type": slot.agent_type,
                        "executor_role": slot.executor_role,
                    },
                )
            )
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
        if slot.activation_state == ACTIVATION_RESERVED and slot.execution_allowed:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_RESERVED_EXECUTABLE",
                    "A RESERVED worker slot may reserve a surface but may not carry an executable lease.",
                    {"worker_slot_id": slot.worker_slot_id},
                )
            )
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
        if slot.activation_state == ACTIVATION_ACTIVE and not worker_slot_is_executable(slot):
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_ACTIVE_NOT_EXECUTABLE",
                    "A GPT worker slot marked ACTIVE must satisfy every strict executable prerequisite; malformed authority never normalizes into a lease.",
                    {
                        "worker_slot_id": slot.worker_slot_id,
                        "status": slot.status,
                        "execution_allowed": slot.execution_allowed,
                    },
                )
            )

    active_executable = [slot for slot in slots if worker_slot_is_executable(slot)]
    capacity_policy = _program_capacity_policy(root)
    if _registry_required(root) or (root / GPT_WORKERS_REGISTRY).exists():
        capacity = capacity_policy.get("gpt_engineering_worker_active_slots_max")
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_CAPACITY_POLICY_INVALID",
                    "Program capacity policy must provide a positive bounded gpt_engineering_worker_active_slots_max value.",
                    {"actual": capacity},
                )
            )
            capacity = 0
        if len(active_executable) > capacity:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_CAPACITY_EXCEEDED",
                    "More GPT Engineering Worker slots are executable than configured capacity allows.",
                    {"active_slots": [slot.worker_slot_id for slot in active_executable], "limit": capacity},
                )
            )

        if capacity_policy.get("nested_parallelism") == "FORBIDDEN":
            task_slots: dict[str, list[str | None]] = {}
            for slot in active_executable:
                if slot.task_id:
                    task_slots.setdefault(str(slot.task_id), []).append(slot.worker_slot_id)
            for task_id, slot_ids in task_slots.items():
                if len(slot_ids) > 1:
                    findings.append(
                        Finding(
                            CHECK_ID,
                            "ERROR",
                            "WORKER_SLOT_NESTED_PARALLELISM_FORBIDDEN",
                            "One task may not hold multiple active GPT worker slots while nested_parallelism is FORBIDDEN.",
                            {"task_id": task_id, "worker_slots": slot_ids},
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
                    {"pair": [left.worker_slot_id, right.worker_slot_id], "collision": collision},
                )
            )

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
    maintenance_errors = [
        item for item in errors if str(item.get("code", "")).startswith("MAINTENANCE_")
    ]
    maintenance_raw = maintenance_witness.get("raw") if isinstance(maintenance_witness, dict) else None
    maintenance_state = maintenance_raw.get("state") if isinstance(maintenance_raw, dict) else None
    maintenance_write_allowed = maintenance_state == "ACTIVE" and not maintenance_errors
    return {
        "schema_version": "1.4",
        "agent_type": AGENT_TYPE,
        "worker_registry": registry_witness,
        "worker_registry_fingerprint": hashlib.sha256(_canonical(registry_witness).encode("utf-8")).hexdigest(),
        "maintenance_adoption": maintenance_witness,
        "maintenance_terminal_tombstones": tombstone_witness,
        "maintenance_authority_id": maintenance_raw.get("authority_id") if isinstance(maintenance_raw, dict) else None,
        "maintenance_authority_state": maintenance_state,
        "maintenance_write_allowed": maintenance_write_allowed,
        "maintenance_adoption_structural_check": "PASS" if not maintenance_errors else "FAIL",
        "worker_slots": [worker_slot_route_witness(slot) for slot in slots],
        "active_executable_slots": [slot.worker_slot_id for slot in slots if worker_slot_is_executable(slot)],
        "errors": errors,
        "warnings": warnings,
        "worker_slot_structural_check": "PASS" if not errors else "FAIL",
    }