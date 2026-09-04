from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from control_tower import Finding, NON_EXECUTABLE_STATUSES, classify_collision, load_yaml

WORKBUDDY_REGISTRY = "coordination/ACTIVE-WORKBUDDY-TASKS.yaml"
LEGACY_WORKBUDDY_PROJECTION = "coordination/ACTIVE-WORKBUDDY-TASK.yaml"
EXPECTED_SCHEMA_VERSION = "1.0"
EXPECTED_REGISTRY_ID = "ACTIVE-WORKBUDDY-TASKS-0001"
AGENT_TYPE = "WORKBUDDY"
CHECK_ID = "CT-WB-SLOTS"


@dataclass(frozen=True)
class WorkBuddySlot:
    worker_slot_id: str | None
    agent_type: str | None
    executor_role: str | None
    task_id: str | None
    route_epoch: int | str | None
    issue: int | str | None
    pr: int | str | None
    branch: str | None
    status: str | None
    execution_allowed: bool
    activation_state: str | None
    closure_state: str | None
    canonical_route: str | None
    work_claim: str | None
    task_lease: str | None
    executor_reservation: str | None
    completion_signal: str | None
    write_paths: tuple[str, ...]
    read_paths: tuple[str, ...]
    interfaces: tuple[Any, ...]
    read_domains: tuple[str, ...]
    write_domains: tuple[str, ...]
    authority_claims: tuple[str, ...]
    exclusive_resources: tuple[str, ...]
    shared_read_resources: tuple[str, ...]
    mutable_runtime_resources: tuple[str, ...]
    credential_surfaces: tuple[str, ...]
    real_data_surfaces: tuple[str, ...]
    order_or_trade_authority: bool
    primary_compatibility_projection: bool


def _first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _string_list(raw: dict[str, Any], key: str) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _interfaces(raw: dict[str, Any]) -> tuple[Any, ...]:
    value = raw.get("interfaces")
    return tuple(value) if isinstance(value, list) else ()


def normalize_workbuddy_slot(raw: dict[str, Any]) -> WorkBuddySlot:
    return WorkBuddySlot(
        worker_slot_id=_first(raw, "worker_slot_id", "slot_id"),
        agent_type=_first(raw, "agent_type"),
        executor_role=_first(raw, "executor_role"),
        task_id=_first(raw, "task_id", "active_task_id"),
        route_epoch=_first(raw, "route_epoch", "epoch"),
        issue=_first(raw, "active_issue", "issue"),
        pr=_first(raw, "pull_request", "pr", "implementation_pr"),
        branch=_first(raw, "branch", "implementation_branch"),
        status=_first(raw, "status"),
        execution_allowed=raw.get("execution_allowed") is True,
        activation_state=_first(raw, "activation_state"),
        closure_state=_first(raw, "closure_state"),
        canonical_route=_first(raw, "canonical_route"),
        work_claim=_first(raw, "work_claim"),
        task_lease=_first(raw, "task_lease"),
        executor_reservation=_first(raw, "executor_reservation"),
        completion_signal=_first(raw, "completion_signal"),
        write_paths=_string_list(raw, "write_paths"),
        read_paths=_string_list(raw, "read_paths"),
        interfaces=_interfaces(raw),
        read_domains=_string_list(raw, "read_domains"),
        write_domains=_string_list(raw, "write_domains"),
        authority_claims=_string_list(raw, "authority_claims"),
        exclusive_resources=_string_list(raw, "exclusive_resources"),
        shared_read_resources=_string_list(raw, "shared_read_resources"),
        mutable_runtime_resources=_string_list(raw, "mutable_runtime_resources"),
        credential_surfaces=_string_list(raw, "credential_surfaces"),
        real_data_surfaces=_string_list(raw, "real_data_surfaces"),
        order_or_trade_authority=raw.get("order_or_trade_authority") is True,
        primary_compatibility_projection=raw.get("primary_compatibility_projection") is True,
    )


def load_workbuddy_registry(repo_root: Path) -> dict[str, Any]:
    return load_yaml(repo_root.resolve() / WORKBUDDY_REGISTRY)


def load_workbuddy_slots(repo_root: Path) -> list[WorkBuddySlot]:
    registry = load_workbuddy_registry(repo_root)
    raw_slots = registry.get("worker_slots")
    if not isinstance(raw_slots, list):
        return []
    return [normalize_workbuddy_slot(item) for item in raw_slots if isinstance(item, dict)]


def workbuddy_active_slots_max(repo_root: Path) -> int:
    try:
        registry = load_workbuddy_registry(repo_root)
    except (OSError, ValueError, TypeError):
        return 0
    raw = registry.get("active_slots_max")
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        return 0
    return raw


def workbuddy_slot_is_executable(slot: WorkBuddySlot) -> bool:
    if not slot.execution_allowed:
        return False
    if str(slot.activation_state or "").upper() != "ACTIVE":
        return False
    if slot.closure_state not in (None, "", "OPEN"):
        return False
    if slot.status is None:
        return False
    return str(slot.status).upper() not in NON_EXECUTABLE_STATUSES


def _normalize_scope(path: str) -> str:
    value = path.replace("\\", "/").strip()
    while value.startswith("./"):
        value = value[2:]
    for suffix in ("/**", "/*"):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
    return value.rstrip("/") or "."


def _collision_input(slot: WorkBuddySlot) -> dict[str, Any]:
    return {
        "write_paths": [_normalize_scope(item) for item in slot.write_paths],
        "read_paths": [_normalize_scope(item) for item in slot.read_paths],
        "interfaces": list(slot.interfaces),
        "read_domains": list(slot.read_domains),
        "write_domains": list(slot.write_domains),
        "authority_claims": list(slot.authority_claims),
    }


def classify_workbuddy_collision(left: WorkBuddySlot, right: WorkBuddySlot) -> dict[str, Any]:
    left_cred = set(left.credential_surfaces)
    right_cred = set(right.credential_surfaces)
    if left_cred & right_cred:
        return {
            "level": "O4",
            "reason": "CREDENTIAL_SURFACE_COLLISION",
            "overlap": sorted(left_cred & right_cred),
        }

    left_real = set(left.real_data_surfaces)
    right_real = set(right.real_data_surfaces)
    if left_real & right_real:
        return {
            "level": "O3",
            "reason": "REAL_DATA_SURFACE_COLLISION_REQUIRES_EXPLICIT_SHARED_READ_POLICY",
            "overlap": sorted(left_real & right_real),
        }

    left_exclusive = set(left.exclusive_resources)
    right_exclusive = set(right.exclusive_resources)
    left_shared = set(left.shared_read_resources)
    right_shared = set(right.shared_read_resources)
    left_mutable = set(left.mutable_runtime_resources)
    right_mutable = set(right.mutable_runtime_resources)

    exclusive_overlap = (left_exclusive & (right_exclusive | right_shared | right_mutable)) | (
        right_exclusive & (left_shared | left_mutable)
    )
    if exclusive_overlap:
        return {"level": "O3", "reason": "EXCLUSIVE_RESOURCE_COLLISION", "overlap": sorted(exclusive_overlap)}

    mutable_overlap = (left_mutable & (right_mutable | right_shared)) | (right_mutable & left_shared)
    if mutable_overlap:
        return {"level": "O3", "reason": "MUTABLE_RUNTIME_RESOURCE_COLLISION", "overlap": sorted(mutable_overlap)}

    return classify_collision(_collision_input(left), _collision_input(right))


def _slot_identity(slot: WorkBuddySlot) -> dict[str, Any]:
    return {
        "task_id": slot.task_id,
        "route_epoch": slot.route_epoch,
        "issue": slot.issue,
        "pr": slot.pr,
        "branch": slot.branch,
        "status": slot.status,
        "execution_allowed": slot.execution_allowed,
        "completion_signal": slot.completion_signal,
    }


def _legacy_identity(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": _first(raw, "task_id", "active_task_id"),
        "route_epoch": _first(raw, "route_epoch", "epoch"),
        "issue": _first(raw, "active_issue", "issue"),
        "pr": _first(raw, "pull_request", "pr", "implementation_pr"),
        "branch": _first(raw, "implementation_branch", "branch"),
        "status": _first(raw, "status"),
        "execution_allowed": raw.get("execution_allowed") is True,
        "completion_signal": _first(raw, "completion_signal"),
    }


def _bound_identity_findings(repo_root: Path, slot: WorkBuddySlot) -> list[Finding]:
    findings: list[Finding] = []
    refs = {
        "work_claim": slot.work_claim,
        "task_lease": slot.task_lease,
        "executor_reservation": slot.executor_reservation,
        "canonical_route": slot.canonical_route,
    }
    for ref_name, relpath in refs.items():
        if not relpath:
            findings.append(
                Finding(CHECK_ID, "ERROR", "WORKBUDDY_BOUND_REF_MISSING", "Active WorkBuddy slot lacks a required bound reference.", {"slot": slot.worker_slot_id, "ref": ref_name})
            )
            continue
        path = repo_root / relpath
        if not path.exists():
            findings.append(
                Finding(CHECK_ID, "ERROR", "WORKBUDDY_BOUND_REF_NOT_FOUND", "Active WorkBuddy slot points to a missing governed reference.", {"slot": slot.worker_slot_id, "ref": ref_name, "path": relpath})
            )
            continue
        try:
            raw = load_yaml(path)
        except (OSError, ValueError, TypeError):
            findings.append(
                Finding(CHECK_ID, "ERROR", "WORKBUDDY_BOUND_REF_UNREADABLE", "Active WorkBuddy slot reference is unreadable or not a YAML mapping.", {"slot": slot.worker_slot_id, "ref": ref_name, "path": relpath})
            )
            continue
        ref_task = _first(raw, "task_id", "active_task_id")
        ref_epoch = _first(raw, "route_epoch", "epoch")
        ref_issue = _first(raw, "active_issue", "issue")
        ref_branch = _first(raw, "implementation_branch", "branch")
        drift = {}
        for key, expected, actual in (
            ("task_id", slot.task_id, ref_task),
            ("route_epoch", slot.route_epoch, ref_epoch),
            ("issue", slot.issue, ref_issue),
            ("branch", slot.branch, ref_branch),
        ):
            if actual is not None and expected != actual:
                drift[key] = {"slot": expected, "ref": actual}
        if drift:
            findings.append(
                Finding(CHECK_ID, "ERROR", "WORKBUDDY_BOUND_REF_IDENTITY_DRIFT", "Bound WorkBuddy route/claim/lease/reservation identity disagrees with the registry slot.", {"slot": slot.worker_slot_id, "ref": ref_name, "path": relpath, "drift": drift})
            )
    return findings


def workbuddy_slot_findings(repo_root: Path) -> list[Finding]:
    root = repo_root.resolve()
    findings: list[Finding] = []
    try:
        registry = load_workbuddy_registry(root)
    except FileNotFoundError:
        return [Finding(CHECK_ID, "ERROR", "WORKBUDDY_REGISTRY_MISSING", "Canonical WorkBuddy multi-slot registry is missing.", {"path": WORKBUDDY_REGISTRY})]
    except (OSError, ValueError, TypeError) as exc:
        return [Finding(CHECK_ID, "ERROR", "WORKBUDDY_REGISTRY_UNREADABLE", "Canonical WorkBuddy multi-slot registry is unreadable.", {"path": WORKBUDDY_REGISTRY, "error": type(exc).__name__})]

    if registry.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_REGISTRY_SCHEMA_UNSUPPORTED", "WorkBuddy registry schema version is not supported.", {"expected": EXPECTED_SCHEMA_VERSION, "actual": registry.get("schema_version")}))
    if registry.get("registry_id") != EXPECTED_REGISTRY_ID:
        findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_REGISTRY_ID_MISMATCH", "WorkBuddy registry identity is not canonical.", {"expected": EXPECTED_REGISTRY_ID, "actual": registry.get("registry_id")}))
    if registry.get("canonical_agent_type") != AGENT_TYPE:
        findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_AGENT_TYPE_MISMATCH", "WorkBuddy registry canonical agent type is invalid.", {"actual": registry.get("canonical_agent_type")}))
    if registry.get("parallel_routes_allowed") is not True:
        findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_PARALLEL_ROUTES_NOT_ENABLED", "Multi-slot registry must explicitly enable bounded parallel routes.", {}))

    raw_slots = registry.get("worker_slots")
    if not isinstance(raw_slots, list):
        findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_SLOTS_NOT_LIST", "WorkBuddy worker_slots must be a list.", {}))
        return findings

    slots = [normalize_workbuddy_slot(item) for item in raw_slots if isinstance(item, dict)]
    if len(slots) != len(raw_slots):
        findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_SLOT_NOT_MAPPING", "Every WorkBuddy slot must be a mapping.", {}))

    ids = [slot.worker_slot_id for slot in slots]
    if any(not item for item in ids) or len(set(ids)) != len(ids):
        findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_SLOT_ID_INVALID_OR_DUPLICATE", "WorkBuddy slot IDs must be present and unique.", {"slot_ids": ids}))

    executable = [slot for slot in slots if workbuddy_slot_is_executable(slot)]
    max_slots = workbuddy_active_slots_max(root)
    if max_slots < 1:
        findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_ACTIVE_SLOT_LIMIT_INVALID", "WorkBuddy active slot capacity must be a positive integer.", {"active_slots_max": registry.get("active_slots_max")}))
    elif len(executable) > max_slots:
        findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_ACTIVE_SLOT_CAPACITY_EXCEEDED", "Executable WorkBuddy slots exceed the governed registry capacity.", {"active": [slot.worker_slot_id for slot in executable], "limit": max_slots}))

    if registry.get("same_task_multiple_active_slots_allowed") is not True:
        seen_tasks: dict[str, list[str]] = {}
        for slot in executable:
            if slot.task_id:
                seen_tasks.setdefault(slot.task_id, []).append(str(slot.worker_slot_id))
        for task_id, slot_ids in seen_tasks.items():
            if len(slot_ids) > 1:
                findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_SAME_TASK_DOUBLE_SLOT", "One WorkBuddy task occupies multiple executable slots while nested parallelism is not explicitly authorized.", {"task_id": task_id, "slots": slot_ids}))

    for slot in executable:
        if slot.agent_type != AGENT_TYPE:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_SLOT_AGENT_TYPE_INVALID", "Executable WorkBuddy slot has the wrong agent type.", {"slot": slot.worker_slot_id, "agent_type": slot.agent_type}))
        if slot.order_or_trade_authority:
            findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_SLOT_TRADE_AUTHORITY_FORBIDDEN", "The WorkBuddy routing registry cannot itself grant order or trade authority.", {"slot": slot.worker_slot_id}))
        findings.extend(_bound_identity_findings(root, slot))

    for index, left in enumerate(executable):
        for right in executable[index + 1 :]:
            collision = classify_workbuddy_collision(left, right)
            if collision.get("level") in {"O3", "O4"}:
                findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_EXECUTABLE_SLOT_COLLISION", "Two executable WorkBuddy slots collide on a mutable/resource/authority surface.", {"left": left.worker_slot_id, "right": right.worker_slot_id, "collision": collision}))

    primary = [slot for slot in slots if slot.primary_compatibility_projection]
    if len(primary) != 1:
        findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_PRIMARY_COMPATIBILITY_SLOT_INVALID", "Exactly one slot must project to the legacy singular WorkBuddy task file during migration.", {"primary_slots": [slot.worker_slot_id for slot in primary]}))
    else:
        legacy_path = root / LEGACY_WORKBUDDY_PROJECTION
        if not legacy_path.exists():
            findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_LEGACY_PROJECTION_MISSING", "Legacy WorkBuddy compatibility projection is missing during migration.", {"path": LEGACY_WORKBUDDY_PROJECTION}))
        else:
            legacy = load_yaml(legacy_path)
            expected = _slot_identity(primary[0])
            actual = _legacy_identity(legacy)
            drift = {key: {"registry": expected[key], "legacy": actual[key]} for key in expected if expected[key] != actual[key]}
            if drift:
                findings.append(Finding(CHECK_ID, "ERROR", "WORKBUDDY_COMPATIBILITY_PROJECTION_DRIFT", "Legacy singular WorkBuddy projection disagrees with the canonical primary slot.", {"slot": primary[0].worker_slot_id, "drift": drift}))

    return findings


def workbuddy_slot_witness(slot: WorkBuddySlot) -> dict[str, Any]:
    return asdict(slot)


def validate_workbuddy_slots(repo_root: Path) -> dict[str, Any]:
    findings = workbuddy_slot_findings(repo_root)
    slots = load_workbuddy_slots(repo_root)
    return {
        "schema_version": "1.0",
        "registry": WORKBUDDY_REGISTRY,
        "active_slots_max": workbuddy_active_slots_max(repo_root),
        "slots": [workbuddy_slot_witness(slot) for slot in slots],
        "errors": [asdict(item) for item in findings if item.severity == "ERROR"],
        "warnings": [asdict(item) for item in findings if item.severity == "WARN"],
        "structural_check": "PASS" if not any(item.severity == "ERROR" for item in findings) else "FAIL",
    }
