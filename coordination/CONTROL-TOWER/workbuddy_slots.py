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

EXECUTABLE_STATUSES = frozenset({"READY"})
KNOWN_SLOT_STATUSES = frozenset(set(NON_EXECUTABLE_STATUSES) | set(EXECUTABLE_STATUSES))
STRING_LIST_FIELDS = (
    "write_paths",
    "read_paths",
    "read_domains",
    "write_domains",
    "authority_claims",
    "exclusive_resources",
    "shared_read_resources",
    "mutable_runtime_resources",
    "credential_surfaces",
    "real_data_surfaces",
)
FORBIDDEN_AUTHORITY_FIELDS = (
    "order_or_trade_authority",
    "review_authority",
    "merge_authority",
    "acceptance_authority",
    "canonical_truth_authority",
    "canonical_knowledge_authority",
    "account_authority",
    "credential_authority",
    "broker_authority",
    "funds_authority",
    "position_authority",
)
ALLOWED_SLOT_FIELDS = frozenset(
    {
        "worker_slot_id",
        "slot_id",
        "agent_type",
        "executor_role",
        "task_id",
        "active_task_id",
        "route_epoch",
        "epoch",
        "active_issue",
        "issue",
        "source_issue",
        "pull_request",
        "pr",
        "implementation_pr",
        "branch",
        "implementation_branch",
        "status",
        "execution_allowed",
        "activation_state",
        "closure_state",
        "mode",
        "canonical_route",
        "work_claim",
        "task_lease",
        "executor_reservation",
        "prewrite_snapshot",
        "executable_batch",
        "completion_signal",
        "interfaces",
        "primary_compatibility_projection",
        "provenance",
        *STRING_LIST_FIELDS,
        *FORBIDDEN_AUTHORITY_FIELDS,
    }
)
ALLOWED_REGISTRY_FIELDS = frozenset(
    {
        "schema_version",
        "registry_id",
        "repository",
        "canonical_agent_type",
        "status",
        "parallel_routes_allowed",
        "active_slots_max",
        "nested_parallelism",
        "same_task_multiple_active_slots_allowed",
        "same_mutable_surface_writers_max",
        "unknown_collision_disposition",
        "compatibility_projection",
        "worker_slots",
        "migration_boundary",
    }
)
EXPECTED_COMPATIBILITY_PROJECTION = {
    "path": LEGACY_WORKBUDDY_PROJECTION,
    "mode": "PRIMARY_SLOT_COMPATIBILITY_PROJECTION",
    "canonical_authority_after_r579": False,
    "mismatch_disposition": "FAIL_CLOSED",
}


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
    prewrite_snapshot: str | None
    executable_batch: str | None
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
    review_authority: bool
    merge_authority: bool
    acceptance_authority: bool
    canonical_truth_authority: bool
    canonical_knowledge_authority: bool
    account_authority: bool
    credential_authority: bool
    broker_authority: bool
    funds_authority: bool
    position_authority: bool
    primary_compatibility_projection: bool


def _first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _nested(mapping: dict[str, Any], *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _string_list(raw: dict[str, Any], key: str) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list):
        return ()
    if not all(isinstance(item, str) for item in value):
        return ()
    return tuple(value)


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
        prewrite_snapshot=_first(raw, "prewrite_snapshot"),
        executable_batch=_first(raw, "executable_batch"),
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
        review_authority=raw.get("review_authority") is True,
        merge_authority=raw.get("merge_authority") is True,
        acceptance_authority=raw.get("acceptance_authority") is True,
        canonical_truth_authority=raw.get("canonical_truth_authority") is True,
        canonical_knowledge_authority=raw.get("canonical_knowledge_authority") is True,
        account_authority=raw.get("account_authority") is True,
        credential_authority=raw.get("credential_authority") is True,
        broker_authority=raw.get("broker_authority") is True,
        funds_authority=raw.get("funds_authority") is True,
        position_authority=raw.get("position_authority") is True,
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
    return str(slot.status or "").upper() in EXECUTABLE_STATUSES


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
    if left.branch and right.branch and left.branch == right.branch:
        return {
            "level": "O3",
            "reason": "SAME_MUTABLE_BRANCH_OWNERSHIP",
            "overlap": [left.branch],
        }

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
        right_exclusive & (left_exclusive | left_shared | left_mutable)
    )
    if exclusive_overlap:
        return {
            "level": "O3",
            "reason": "EXCLUSIVE_RESOURCE_COLLISION",
            "overlap": sorted(exclusive_overlap),
        }

    mutable_overlap = (left_mutable & (right_mutable | right_shared)) | (
        right_mutable & (left_mutable | left_shared)
    )
    if mutable_overlap:
        return {
            "level": "O3",
            "reason": "MUTABLE_RUNTIME_RESOURCE_COLLISION",
            "overlap": sorted(mutable_overlap),
        }

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


def _slot_shape_findings(raw: dict[str, Any], index: int) -> list[Finding]:
    findings: list[Finding] = []
    unknown = sorted(set(raw) - ALLOWED_SLOT_FIELDS)
    if unknown:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_SLOT_UNKNOWN_FIELD",
                "WorkBuddy slot contains fields outside the closed v1 schema.",
                {"index": index, "unknown_fields": unknown},
            )
        )

    for key in STRING_LIST_FIELDS:
        value = raw.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKBUDDY_COLLISION_FIELD_MALFORMED",
                    "Collision/security list fields must be explicit lists of non-empty strings.",
                    {"index": index, "field": key, "value_type": type(value).__name__},
                )
            )

    interfaces = raw.get("interfaces")
    if not isinstance(interfaces, list):
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_INTERFACES_MALFORMED",
                "interfaces must be a list.",
                {"index": index, "value_type": type(interfaces).__name__},
            )
        )
    else:
        for item_index, item in enumerate(interfaces):
            if isinstance(item, str):
                if not item.strip():
                    findings.append(
                        Finding(
                            CHECK_ID,
                            "ERROR",
                            "WORKBUDDY_INTERFACE_ENTRY_MALFORMED",
                            "String interface entries must be non-empty.",
                            {"index": index, "interface_index": item_index},
                        )
                    )
                continue
            if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
                findings.append(
                    Finding(
                        CHECK_ID,
                        "ERROR",
                        "WORKBUDDY_INTERFACE_ENTRY_MALFORMED",
                        "Interface entries must be non-empty strings or mappings with a non-empty name.",
                        {"index": index, "interface_index": item_index},
                    )
                )
                continue
            mode = item.get("mode", "read")
            if mode not in {"read", "write"}:
                findings.append(
                    Finding(
                        CHECK_ID,
                        "ERROR",
                        "WORKBUDDY_INTERFACE_MODE_UNKNOWN",
                        "Interface mode must be read or write.",
                        {"index": index, "interface_index": item_index, "mode": mode},
                    )
                )
            if "frozen" in item and not isinstance(item.get("frozen"), bool):
                findings.append(
                    Finding(
                        CHECK_ID,
                        "ERROR",
                        "WORKBUDDY_INTERFACE_FROZEN_FLAG_INVALID",
                        "Interface frozen must be boolean when present.",
                        {"index": index, "interface_index": item_index},
                    )
                )

    for field in FORBIDDEN_AUTHORITY_FIELDS:
        if field not in raw or not isinstance(raw.get(field), bool):
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKBUDDY_AUTHORITY_FIELD_MISSING_OR_INVALID",
                    "Authority fields are schema-required booleans in v1.",
                    {"index": index, "field": field},
                )
            )
        elif raw.get(field) is True:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKBUDDY_FORBIDDEN_AUTHORITY_MINT",
                    "The WorkBuddy routing registry cannot mint privileged business or governance authority.",
                    {"index": index, "field": field},
                )
            )

    if not isinstance(raw.get("primary_compatibility_projection"), bool):
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_PRIMARY_COMPATIBILITY_FLAG_INVALID",
                "primary_compatibility_projection must be an explicit boolean.",
                {"index": index},
            )
        )

    return findings


def _required_slot_identity_findings(slot: WorkBuddySlot) -> list[Finding]:
    findings: list[Finding] = []
    required = {
        "worker_slot_id": slot.worker_slot_id,
        "agent_type": slot.agent_type,
        "executor_role": slot.executor_role,
        "task_id": slot.task_id,
        "route_epoch": slot.route_epoch,
        "issue": slot.issue,
        "branch": slot.branch,
        "status": slot.status,
        "canonical_route": slot.canonical_route,
        "work_claim": slot.work_claim,
        "task_lease": slot.task_lease,
        "executor_reservation": slot.executor_reservation,
        "prewrite_snapshot": slot.prewrite_snapshot,
        "executable_batch": slot.executable_batch,
        "completion_signal": slot.completion_signal,
    }
    missing = [
        key
        for key, value in required.items()
        if value is None or (isinstance(value, str) and not value.strip())
    ]
    if missing:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_EXECUTABLE_SLOT_IDENTITY_INCOMPLETE",
                "Executable WorkBuddy slot is missing required identity or governed binding fields.",
                {"slot": slot.worker_slot_id, "missing": missing},
            )
        )
    return findings


def _load_bound_mapping(repo_root: Path, relpath: str) -> tuple[dict[str, Any] | None, str | None]:
    path = repo_root / relpath
    if not path.exists():
        return None, "NOT_FOUND"
    try:
        raw = load_yaml(path)
    except (OSError, ValueError, TypeError):
        return None, "UNREADABLE"
    return raw, None


def _bound_doc_identity(ref_name: str, raw: dict[str, Any]) -> dict[str, Any]:
    if ref_name == "canonical_route":
        return {
            "task_id": _first(raw, "task_id", "active_task_id"),
            "route_epoch": _first(raw, "route_epoch", "epoch"),
            "issue": _first(raw, "active_issue", "issue"),
            "branch": _first(raw, "implementation_branch", "branch")
            or _nested(raw, "execution", "implementation_branch"),
        }
    if ref_name == "work_claim":
        return {
            "task_id": _first(raw, "task_id", "active_task_id"),
            "route_epoch": _first(raw, "route_epoch", "epoch"),
            "issue": _first(raw, "active_issue", "issue"),
            "branch": _first(raw, "branch", "implementation_branch"),
        }
    if ref_name in {"task_lease", "executor_reservation"}:
        return {
            "task_id": _first(raw, "task_id", "active_task_id"),
            "route_epoch": _first(raw, "route_epoch", "epoch"),
            "issue": _first(raw, "active_issue", "issue"),
            "branch": _first(raw, "implementation_branch", "branch"),
        }
    if ref_name == "prewrite_snapshot":
        return {
            "task_id": _first(raw, "task_id", "active_task_id"),
            "route_epoch": _first(raw, "route_epoch", "epoch"),
            "issue": _first(raw, "active_issue", "issue"),
        }
    if ref_name == "executable_batch":
        route_authority = raw.get("route_authority") if isinstance(raw.get("route_authority"), dict) else {}
        return {
            "task_id": _first(route_authority, "task_id", "active_task_id"),
            "route_epoch": _first(route_authority, "route_epoch", "epoch"),
            "issue": _first(route_authority, "active_issue", "issue"),
        }
    return {}


def _bound_state_findings(slot: WorkBuddySlot, ref_name: str, relpath: str, raw: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []

    def require_equal(field: str, actual: Any, expected: Any) -> None:
        if actual != expected:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKBUDDY_BOUND_REF_STATE_INVALID",
                    "Bound WorkBuddy authorization document is missing or has an invalid active-state field.",
                    {
                        "slot": slot.worker_slot_id,
                        "ref": ref_name,
                        "path": relpath,
                        "field": field,
                        "expected": expected,
                        "actual": actual,
                    },
                )
            )

    if ref_name == "canonical_route":
        require_equal("target_agent", raw.get("target_agent"), AGENT_TYPE)
        require_equal("status", raw.get("status"), "READY")
        require_equal("execution_allowed", raw.get("execution_allowed"), True)
        require_equal("release_state", raw.get("release_state"), "ACTIVE_READBACK_CONFIRMED")
        require_equal("execution.implementation_branch", _nested(raw, "execution", "implementation_branch"), slot.branch)
        require_equal("execution.executable_batch", _nested(raw, "execution", "executable_batch"), slot.executable_batch)
        bindings = raw.get("bindings") if isinstance(raw.get("bindings"), dict) else {}
        for key, expected in (
            ("work_claim", slot.work_claim),
            ("task_lease", slot.task_lease),
            ("executor_reservation", slot.executor_reservation),
            ("prewrite_snapshot", slot.prewrite_snapshot),
        ):
            require_equal(f"bindings.{key}", bindings.get(key), expected)
        if slot.primary_compatibility_projection:
            require_equal("bindings.active_task", bindings.get("active_task"), LEGACY_WORKBUDDY_PROJECTION)

    elif ref_name == "work_claim":
        require_equal("agent", raw.get("agent"), AGENT_TYPE)
        require_equal("claim_state", raw.get("claim_state"), "ACTIVE")
        require_equal("status_observed", raw.get("status_observed"), "READY")
        require_equal("execution_allowed_observed", raw.get("execution_allowed_observed"), True)

    elif ref_name == "task_lease":
        require_equal("agent_type", raw.get("agent_type"), AGENT_TYPE)
        require_equal("lease_state", raw.get("lease_state"), "ACTIVE")
        require_equal("execution_allowed", raw.get("execution_allowed"), True)
        require_equal("substantive_write_allowed", raw.get("substantive_write_allowed"), True)
        freshness = raw.get("freshness") if isinstance(raw.get("freshness"), dict) else {}
        for key, expected in (
            ("route", slot.canonical_route),
            ("work_claim", slot.work_claim),
            ("executor_reservation", slot.executor_reservation),
            ("prewrite_snapshot", slot.prewrite_snapshot),
            ("executable_batch", slot.executable_batch),
        ):
            require_equal(f"freshness.{key}", freshness.get(key), expected)
        if slot.primary_compatibility_projection:
            require_equal("freshness.active_task", freshness.get("active_task"), LEGACY_WORKBUDDY_PROJECTION)
        else:
            require_equal("freshness.active_registry", freshness.get("active_registry"), WORKBUDDY_REGISTRY)

    elif ref_name == "executor_reservation":
        require_equal("executor_agent_type", raw.get("executor_agent_type"), AGENT_TYPE)
        require_equal("reservation_state", raw.get("reservation_state"), "ACTIVE")
        require_equal(
            "reservation_effect.execution_identity_reserved",
            _nested(raw, "reservation_effect", "execution_identity_reserved"),
            True,
        )
        require_equal(
            "reservation_effect.substantive_write_authorized_now",
            _nested(raw, "reservation_effect", "substantive_write_authorized_now"),
            True,
        )
        require_equal("review_authority", raw.get("review_authority"), False)
        require_equal("merge_authority", raw.get("merge_authority"), False)

    elif ref_name == "prewrite_snapshot":
        require_equal(
            "activation_gate.snapshot_precedes_workbuddy_branch",
            _nested(raw, "activation_gate", "snapshot_precedes_workbuddy_branch"),
            True,
        )
        require_equal(
            "activation_gate.requires_post_branch_fresh_readback",
            _nested(raw, "activation_gate", "requires_post_branch_fresh_readback"),
            True,
        )
        require_equal(
            "activation_gate.activation_commit_required",
            _nested(raw, "activation_gate", "activation_commit_required"),
            True,
        )
        require_equal(
            "ordered_batch.executable_ref",
            _nested(raw, "ordered_batch", "executable_ref"),
            slot.executable_batch,
        )

    elif ref_name == "executable_batch":
        require_equal("authority", raw.get("authority"), "CANONICAL_BOUND_BATCH_EXECUTABLE")
        require_equal("route_authority.execution_allowed", _nested(raw, "route_authority", "execution_allowed"), True)
        for key, expected in (
            ("route_ref", slot.canonical_route),
            ("claim_ref", slot.work_claim),
            ("lease_ref", slot.task_lease),
            ("snapshot_ref", slot.prewrite_snapshot),
        ):
            require_equal(f"route_authority.{key}", _nested(raw, "route_authority", key), expected)

    return findings


def _bound_identity_findings(repo_root: Path, slot: WorkBuddySlot) -> list[Finding]:
    findings: list[Finding] = []
    refs = {
        "canonical_route": slot.canonical_route,
        "work_claim": slot.work_claim,
        "task_lease": slot.task_lease,
        "executor_reservation": slot.executor_reservation,
        "prewrite_snapshot": slot.prewrite_snapshot,
        "executable_batch": slot.executable_batch,
    }
    expected_identity = {
        "task_id": slot.task_id,
        "route_epoch": slot.route_epoch,
        "issue": slot.issue,
        "branch": slot.branch,
    }

    for ref_name, relpath in refs.items():
        if not isinstance(relpath, str) or not relpath.strip():
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKBUDDY_BOUND_REF_MISSING",
                    "Executable WorkBuddy slot lacks a required governed reference.",
                    {"slot": slot.worker_slot_id, "ref": ref_name},
                )
            )
            continue

        raw, load_error = _load_bound_mapping(repo_root, relpath)
        if load_error:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    f"WORKBUDDY_BOUND_REF_{load_error}",
                    "Executable WorkBuddy slot bound document is unavailable or unreadable.",
                    {"slot": slot.worker_slot_id, "ref": ref_name, "path": relpath},
                )
            )
            continue
        assert raw is not None

        actual_identity = _bound_doc_identity(ref_name, raw)
        required_keys = ("task_id", "route_epoch", "issue")
        if ref_name in {"canonical_route", "work_claim", "task_lease", "executor_reservation"}:
            required_keys += ("branch",)

        missing = [key for key in required_keys if actual_identity.get(key) is None]
        if missing:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKBUDDY_BOUND_REF_IDENTITY_INCOMPLETE",
                    "Bound WorkBuddy document is missing required identity fields.",
                    {"slot": slot.worker_slot_id, "ref": ref_name, "path": relpath, "missing": missing},
                )
            )
        drift = {
            key: {"slot": expected_identity[key], "ref": actual_identity.get(key)}
            for key in required_keys
            if actual_identity.get(key) is not None and actual_identity.get(key) != expected_identity[key]
        }
        if drift:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKBUDDY_BOUND_REF_IDENTITY_DRIFT",
                    "Bound WorkBuddy document identity disagrees with the registry slot.",
                    {"slot": slot.worker_slot_id, "ref": ref_name, "path": relpath, "drift": drift},
                )
            )
        findings.extend(_bound_state_findings(slot, ref_name, relpath, raw))

    return findings


def _registry_contract_findings(registry: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    unknown = sorted(set(registry) - ALLOWED_REGISTRY_FIELDS)
    if unknown:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_REGISTRY_UNKNOWN_FIELD",
                "WorkBuddy registry contains fields outside the closed v1 schema.",
                {"unknown_fields": unknown},
            )
        )

    if registry.get("parallel_routes_allowed") is not True:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_PARALLEL_ROUTES_NOT_ENABLED",
                "Multi-slot registry must explicitly enable bounded parallel routes.",
                {},
            )
        )
    if registry.get("nested_parallelism") is not False:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_NESTED_PARALLELISM_UNAUTHORIZED",
                "Schema v1 does not authorize nested parallelism.",
                {"nested_parallelism": registry.get("nested_parallelism")},
            )
        )
    if registry.get("same_task_multiple_active_slots_allowed") is not False:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_SAME_TASK_OVERRIDE_FORBIDDEN",
                "Schema v1 cannot enable duplicate active slots for the same task through a caller-editable flag.",
                {
                    "same_task_multiple_active_slots_allowed": registry.get(
                        "same_task_multiple_active_slots_allowed"
                    )
                },
            )
        )
    if registry.get("same_mutable_surface_writers_max") != 1:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_MUTABLE_WRITER_LIMIT_INVALID",
                "Schema v1 requires a single writer for each mutable surface.",
                {"same_mutable_surface_writers_max": registry.get("same_mutable_surface_writers_max")},
            )
        )
    if registry.get("unknown_collision_disposition") != "FAIL_CLOSED":
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_UNKNOWN_COLLISION_NOT_FAIL_CLOSED",
                "Unknown collision disposition must fail closed.",
                {"unknown_collision_disposition": registry.get("unknown_collision_disposition")},
            )
        )

    compatibility = registry.get("compatibility_projection")
    if not isinstance(compatibility, dict):
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_COMPATIBILITY_METADATA_INVALID",
                "compatibility_projection must be a mapping.",
                {},
            )
        )
    else:
        for key, expected in EXPECTED_COMPATIBILITY_PROJECTION.items():
            if compatibility.get(key) != expected:
                findings.append(
                    Finding(
                        CHECK_ID,
                        "ERROR",
                        "WORKBUDDY_COMPATIBILITY_METADATA_INVALID",
                        "Compatibility projection metadata does not match the governed migration contract.",
                        {"field": key, "expected": expected, "actual": compatibility.get(key)},
                    )
                )
        primary_slot_id = compatibility.get("primary_slot_id")
        if not isinstance(primary_slot_id, str) or not primary_slot_id.strip():
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKBUDDY_COMPATIBILITY_PRIMARY_SLOT_ID_INVALID",
                    "compatibility_projection.primary_slot_id must be a non-empty slot id.",
                    {"actual": primary_slot_id},
                )
            )

    return findings


def workbuddy_slot_findings(repo_root: Path) -> list[Finding]:
    root = repo_root.resolve()
    findings: list[Finding] = []
    try:
        registry = load_workbuddy_registry(root)
    except FileNotFoundError:
        return [
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_REGISTRY_MISSING",
                "Canonical WorkBuddy multi-slot registry is missing.",
                {"path": WORKBUDDY_REGISTRY},
            )
        ]
    except (OSError, ValueError, TypeError) as exc:
        return [
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_REGISTRY_UNREADABLE",
                "Canonical WorkBuddy multi-slot registry is unreadable.",
                {"path": WORKBUDDY_REGISTRY, "error": type(exc).__name__},
            )
        ]

    if registry.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_REGISTRY_SCHEMA_UNSUPPORTED",
                "WorkBuddy registry schema version is not supported.",
                {"expected": EXPECTED_SCHEMA_VERSION, "actual": registry.get("schema_version")},
            )
        )
    if registry.get("registry_id") != EXPECTED_REGISTRY_ID:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_REGISTRY_ID_MISMATCH",
                "WorkBuddy registry identity is not canonical.",
                {"expected": EXPECTED_REGISTRY_ID, "actual": registry.get("registry_id")},
            )
        )
    if registry.get("canonical_agent_type") != AGENT_TYPE:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_AGENT_TYPE_MISMATCH",
                "WorkBuddy registry canonical agent type is invalid.",
                {"actual": registry.get("canonical_agent_type")},
            )
        )
    findings.extend(_registry_contract_findings(registry))

    raw_slots = registry.get("worker_slots")
    if not isinstance(raw_slots, list):
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_SLOTS_NOT_LIST",
                "WorkBuddy worker_slots must be a list.",
                {},
            )
        )
        return findings

    for index, raw in enumerate(raw_slots):
        if not isinstance(raw, dict):
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKBUDDY_SLOT_NOT_MAPPING",
                    "Every WorkBuddy slot must be a mapping.",
                    {"index": index},
                )
            )
            continue
        findings.extend(_slot_shape_findings(raw, index))

    slots = [normalize_workbuddy_slot(item) for item in raw_slots if isinstance(item, dict)]
    ids = [slot.worker_slot_id for slot in slots]
    if any(not item for item in ids) or len(set(ids)) != len(ids):
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_SLOT_ID_INVALID_OR_DUPLICATE",
                "WorkBuddy slot IDs must be present and unique.",
                {"slot_ids": ids},
            )
        )

    for slot in slots:
        status = str(slot.status or "").upper()
        if status not in KNOWN_SLOT_STATUSES:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKBUDDY_SLOT_STATUS_UNKNOWN",
                    "Unknown WorkBuddy slot status is not executable and is invalid under the closed v1 lifecycle contract.",
                    {"slot": slot.worker_slot_id, "status": slot.status},
                )
            )

    executable = [slot for slot in slots if workbuddy_slot_is_executable(slot)]
    max_slots = workbuddy_active_slots_max(root)
    if max_slots < 1:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_ACTIVE_SLOT_LIMIT_INVALID",
                "WorkBuddy active slot capacity must be a positive integer.",
                {"active_slots_max": registry.get("active_slots_max")},
            )
        )
    elif len(executable) > max_slots:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_ACTIVE_SLOT_CAPACITY_EXCEEDED",
                "Executable WorkBuddy slots exceed the governed registry capacity.",
                {"active": [slot.worker_slot_id for slot in executable], "limit": max_slots},
            )
        )

    seen_tasks: dict[str, list[str]] = {}
    for slot in executable:
        if slot.task_id:
            seen_tasks.setdefault(slot.task_id, []).append(str(slot.worker_slot_id))
    for task_id, slot_ids in seen_tasks.items():
        if len(slot_ids) > 1:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKBUDDY_SAME_TASK_DOUBLE_SLOT",
                    "One WorkBuddy task occupies multiple executable slots; schema v1 has no nested-parallel authority.",
                    {"task_id": task_id, "slots": slot_ids},
                )
            )

    for slot in executable:
        findings.extend(_required_slot_identity_findings(slot))
        if slot.agent_type != AGENT_TYPE:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKBUDDY_SLOT_AGENT_TYPE_INVALID",
                    "Executable WorkBuddy slot has the wrong agent type.",
                    {"slot": slot.worker_slot_id, "agent_type": slot.agent_type},
                )
            )
        findings.extend(_bound_identity_findings(root, slot))

    for index, left in enumerate(executable):
        for right in executable[index + 1 :]:
            collision = classify_workbuddy_collision(left, right)
            if collision.get("level") in {"O3", "O4"}:
                findings.append(
                    Finding(
                        CHECK_ID,
                        "ERROR",
                        "WORKBUDDY_EXECUTABLE_SLOT_COLLISION",
                        "Two executable WorkBuddy slots collide on a mutable/resource/authority surface.",
                        {
                            "left": left.worker_slot_id,
                            "right": right.worker_slot_id,
                            "collision": collision,
                        },
                    )
                )

    primary = [slot for slot in slots if slot.primary_compatibility_projection]
    if len(primary) != 1:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKBUDDY_PRIMARY_COMPATIBILITY_SLOT_INVALID",
                "Exactly one slot must project to the legacy singular WorkBuddy task file during migration.",
                {"primary_slots": [slot.worker_slot_id for slot in primary]},
            )
        )
    else:
        compatibility = registry.get("compatibility_projection")
        if isinstance(compatibility, dict) and compatibility.get("primary_slot_id") != primary[0].worker_slot_id:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKBUDDY_COMPATIBILITY_PRIMARY_SLOT_DRIFT",
                    "Compatibility metadata primary_slot_id disagrees with the designated primary slot.",
                    {
                        "metadata": compatibility.get("primary_slot_id"),
                        "slot": primary[0].worker_slot_id,
                    },
                )
            )
        legacy_path = root / LEGACY_WORKBUDDY_PROJECTION
        if not legacy_path.exists():
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKBUDDY_LEGACY_PROJECTION_MISSING",
                    "Legacy WorkBuddy compatibility projection is missing during migration.",
                    {"path": LEGACY_WORKBUDDY_PROJECTION},
                )
            )
        else:
            legacy = load_yaml(legacy_path)
            expected = _slot_identity(primary[0])
            actual = _legacy_identity(legacy)
            drift = {
                key: {"registry": expected[key], "legacy": actual[key]}
                for key in expected
                if expected[key] != actual[key]
            }
            if drift:
                findings.append(
                    Finding(
                        CHECK_ID,
                        "ERROR",
                        "WORKBUDDY_COMPATIBILITY_PROJECTION_DRIFT",
                        "Legacy singular WorkBuddy projection disagrees with the canonical primary slot.",
                        {"slot": primary[0].worker_slot_id, "drift": drift},
                    )
                )

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
