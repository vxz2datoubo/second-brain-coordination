from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import worker_slots_r5_compat as _r5
from worker_lifecycle import (
    CANONICAL_REGISTRY_SCHEMA_VERSION,
    LIFECYCLE_ACTIVE,
    LIFECYCLE_UNKNOWN,
    WorkerLifecycleResolution,
    registry_schema_supported,
    resolve_worker_lifecycle,
)

# R6 is a migration adapter, not a replacement for the R144/R5 security surface.
# Re-export the complete pre-R6 module first, then override only schema/lifecycle/capacity
# semantics. The compatibility module is pinned to the exact canonical R5 blob.
for _name, _value in vars(_r5).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

_R5_REGISTRY_FINDINGS = _r5._registry_findings
_R5_SLOT_REQUIRED_FIELD_FINDINGS = _r5._slot_required_field_findings
_R5_WORKER_SLOT_IS_EXECUTABLE = _r5.worker_slot_is_executable
_R5_WORKER_SLOT_FINDINGS = _r5.worker_slot_findings
_R5_VALIDATE_WORKER_SLOTS = _r5.validate_worker_slots
_R5_WORKER_REGISTRY_WITNESS = _r5.worker_registry_witness

EXPECTED_SCHEMA_VERSION = CANONICAL_REGISTRY_SCHEMA_VERSION
R6_MAINTENANCE_ADOPTION_FILE = "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION-R6.yaml"
R6_EXPECTED_AUTHORITY_ID = "R144-GPT-ARCHITECTURE-OWNER-MAINTENANCE-ADOPTION-R6-0001"
R6_EXPECTED_TASK_ID = "GPT-CONTROL-TOWER-WORKER-LIFECYCLE-SCHEMA-R6"
R6_EXPECTED_ISSUE = 565
R6_EXPECTED_BRANCH = "gpt/r565-control-tower-worker-lifecycle-r6"
R6_EXPECTED_PARENT = "a9669e31a9b59c72fff66d6d364c92d4eec51f49"
R6_USER_AUTH_COMMENT = 5518053874
R6_PREWRITE_SNAPSHOT_COMMENT = 5518085070
R6_SCOPE_REFINEMENT_COMMENT = 5518609051
R6_COMPAT_PATH = "coordination/CONTROL-TOWER/worker_slots_r5_compat.py"
R6_COMPAT_BLOB = "00a863a79a35524cb6db950529dabc9ff32761fa"
R6_RELEASED_SCOPE = "NO_FURTHER_MODIFIER_WRITES_AUTHORIZED_BY_THIS_ARTIFACT"


def _slot_mapping(slot: WorkerSlot) -> dict[str, Any]:
    payload = worker_slot_route_witness(slot)
    payload.pop("fingerprint", None)
    return payload


def worker_slot_lifecycle_resolution(slot: WorkerSlot) -> WorkerLifecycleResolution:
    return resolve_worker_lifecycle(_slot_mapping(slot))


def _registry_findings(repo_root: Path) -> list[Finding]:
    findings = list(_R5_REGISTRY_FINDINGS(repo_root))
    doc, error = _r5._load_registry_doc(repo_root.resolve())
    if error or doc is None:
        return findings

    version = doc.get("schema_version")
    if version == CANONICAL_REGISTRY_SCHEMA_VERSION:
        findings = [
            item
            for item in findings
            if not (
                item.code == "WORKER_REGISTRY_IDENTITY_INVALID"
                and item.evidence.get("field") == "schema_version"
            )
        ]
    elif version == "1.0":
        findings.append(
            Finding(
                CHECK_ID,
                "WARN",
                "WORKER_REGISTRY_LEGACY_SCHEMA_COMPATIBILITY",
                "Registry schema 1.0 remains readable only as an explicit R6 compatibility format; canonical projection schema is 1.5.",
                {"actual": version, "canonical": CANONICAL_REGISTRY_SCHEMA_VERSION},
            )
        )
    elif not registry_schema_supported(version):
        if not any(item.code == "WORKER_REGISTRY_SCHEMA_UNSUPPORTED_FAIL_CLOSED" for item in findings):
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_REGISTRY_SCHEMA_UNSUPPORTED_FAIL_CLOSED",
                    "Unknown GPT worker registry schema versions are never normalized into executable authority.",
                    {"actual": version, "supported": ["1.0", CANONICAL_REGISTRY_SCHEMA_VERSION]},
                )
            )
    return findings


def _slot_required_field_findings(slot: WorkerSlot) -> list[Finding]:
    # Preserve all R5 binding/type checks, but replace the frozen three-state enum gate
    # with the canonical R6 lifecycle resolver.
    findings = [
        item
        for item in _R5_SLOT_REQUIRED_FIELD_FINDINGS(slot)
        if item.code not in {
            "WORKER_SLOT_ACTIVATION_STATE_INVALID",
            "WORKER_SLOT_CLOSURE_STATE_INVALID",
        }
    ]
    resolution = worker_slot_lifecycle_resolution(slot)
    if resolution.lifecycle_state == LIFECYCLE_UNKNOWN:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "WORKER_SLOT_LIFECYCLE_UNKNOWN_FAIL_CLOSED",
                "Unknown worker lifecycle projections are non-executable and slot-occupying until a governed migration resolves them.",
                {
                    "worker_slot_id": slot.worker_slot_id,
                    "activation_state": slot.activation_state,
                    "closure_state": slot.closure_state,
                    "status": slot.status,
                    "resolution": resolution.lifecycle_state,
                },
            )
        )
    else:
        for code in resolution.findings:
            findings.append(
                Finding(
                    CHECK_ID,
                    "WARN",
                    "WORKER_SLOT_LIFECYCLE_NORMALIZATION",
                    "R6 normalized a legacy/stale lifecycle projection without granting execution authority.",
                    {
                        "worker_slot_id": slot.worker_slot_id,
                        "lifecycle_state": resolution.lifecycle_state,
                        "normalization": code,
                    },
                )
            )
    return findings


def worker_slot_is_executable(slot: WorkerSlot) -> bool:
    resolution = worker_slot_lifecycle_resolution(slot)
    if not resolution.executable or resolution.lifecycle_state != LIFECYCLE_ACTIVE:
        return False
    # ACTIVE still has to pass every strict R5 executable prerequisite. R6 only
    # broadens lifecycle vocabulary; it never weakens identity/surface/provenance gates.
    return _R5_WORKER_SLOT_IS_EXECUTABLE(slot)


def _raw_slot_resolutions(repo_root: Path) -> list[tuple[dict[str, Any], WorkerLifecycleResolution]]:
    doc, error = _r5._load_registry_doc(repo_root.resolve())
    if error or doc is None:
        return []
    raw_slots = doc.get("worker_slots")
    if not isinstance(raw_slots, list):
        return []
    result: list[tuple[dict[str, Any], WorkerLifecycleResolution]] = []
    for raw in raw_slots:
        if not isinstance(raw, dict):
            continue
        result.append((raw, resolve_worker_lifecycle(raw)))
    return result


def _r6_authority_findings(repo_root: Path) -> list[Finding]:
    path = repo_root.resolve() / R6_MAINTENANCE_ADOPTION_FILE
    if not path.exists():
        return []
    try:
        doc = load_yaml(path)
    except (OSError, ValueError, TypeError):
        return [
            Finding(
                CHECK_ID,
                "ERROR",
                "R6_MAINTENANCE_AUTHORITY_NOT_MAPPING",
                "R6 corrective-maintenance authority must remain machine-readable.",
                {"path": R6_MAINTENANCE_ADOPTION_FILE},
            )
        ]
    findings: list[Finding] = []
    expected = {
        "schema_version": "1.0",
        "authority_id": R6_EXPECTED_AUTHORITY_ID,
        "authority_type": EXPECTED_MAINTENANCE_AUTHORITY_TYPE,
        "issuer": "USER",
        "actor": "GPT_ARCHITECTURE_OWNER",
        "task_id": R6_EXPECTED_TASK_ID,
        "maintenance_generation": 6,
        "issue": R6_EXPECTED_ISSUE,
        "branch": R6_EXPECTED_BRANCH,
        "user_authorization_comment": R6_USER_AUTH_COMMENT,
        "prewrite_snapshot_comment": R6_PREWRITE_SNAPSHOT_COMMENT,
        "scope_refinement_comment": R6_SCOPE_REFINEMENT_COMMENT,
        "activation_parent_head": R6_EXPECTED_PARENT,
        "canonical_main_at_authorization": R6_EXPECTED_PARENT,
    }
    for field, required in expected.items():
        if doc.get(field) != required:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "R6_MAINTENANCE_AUTHORITY_BINDING_INVALID",
                    "R6 maintenance identity must remain bound to the fresh user authorization and pre-write snapshot.",
                    {"field": field, "actual": doc.get(field), "required": required},
                )
            )

    predecessor = doc.get("predecessor_authority")
    expected_predecessor = {
        "path": MAINTENANCE_ADOPTION_FILE,
        "authority_id": EXPECTED_MAINTENANCE_AUTHORITY_ID,
        "required_state": "RELEASED",
        "required_terminal_scope_status": EXPECTED_RELEASED_SCOPE_STATUS,
    }
    if predecessor != expected_predecessor:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "R6_MAINTENANCE_PREDECESSOR_INVALID",
                "R6 must be a new authority identity chained to terminal R5; R5 cannot be reactivated.",
                {"actual": predecessor, "required": expected_predecessor},
            )
        )
    predecessor_doc, predecessor_error = _r5._load_yaml_mapping(
        repo_root,
        MAINTENANCE_ADOPTION_FILE,
        "R6_MAINTENANCE_PREDECESSOR_NOT_MAPPING",
    )
    if predecessor_error or predecessor_doc is None:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                predecessor_error or "R6_MAINTENANCE_PREDECESSOR_MISSING",
                "R6 requires retained terminal R5 authority evidence.",
                {"path": MAINTENANCE_ADOPTION_FILE},
            )
        )
    elif (
        predecessor_doc.get("state") != "RELEASED"
        or predecessor_doc.get("released_scope_status") != EXPECTED_RELEASED_SCOPE_STATUS
    ):
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "R6_MAINTENANCE_PREDECESSOR_NOT_TERMINAL",
                "R5 must remain RELEASED before R6 can exist.",
                {
                    "state": predecessor_doc.get("state"),
                    "released_scope_status": predecessor_doc.get("released_scope_status"),
                },
            )
        )

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
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "R6_MAINTENANCE_UNSAFE_AUTHORITY",
                    "R6 is maintenance-only and may never mint runtime, trade, review or merge authority.",
                    {"field": field, "actual": doc.get(field)},
                )
            )
    for field in ("independent_review_required", "same_pr_required", "fresh_exact_head_ci_required"):
        if doc.get(field) is not True:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "R6_MAINTENANCE_REVIEW_GUARD_MISSING",
                    "R6 requires same-PR continuity, fresh exact-head CI and separate independent review.",
                    {"field": field, "actual": doc.get(field)},
                )
            )

    allowed = doc.get("allowed_write_paths")
    required_paths = {
        "coordination/CONTROL-TOWER/worker_lifecycle.py",
        "coordination/CONTROL-TOWER/worker_slots.py",
        R6_COMPAT_PATH,
        "coordination/CONTROL-TOWER/tests/test_worker_lifecycle.py",
        "coordination/CONTROL-TOWER/tests/test_worker_slots.py",
        R6_MAINTENANCE_ADOPTION_FILE,
    }
    if not isinstance(allowed, list) or not required_paths.issubset(set(allowed)):
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "R6_MAINTENANCE_WRITE_SCOPE_INVALID",
                "R6 must retain the frozen Control-Tower-only implementation surface.",
                {"actual": allowed, "required_subset": sorted(required_paths)},
            )
        )
    forbidden = set(doc.get("explicitly_forbidden_write_paths") or [])
    expected_forbidden = {
        "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml",
        "coordination/ACTIVE-PROGRAM-LANES.yaml",
    }
    if forbidden != expected_forbidden:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "R6_MAINTENANCE_LIVE_PROJECTION_GUARD_INVALID",
                "First-slice R6 maintenance must not write live worker or Program Lane projections.",
                {"actual": sorted(forbidden), "required": sorted(expected_forbidden)},
            )
        )

    invariants = doc.get("required_invariants") if isinstance(doc.get("required_invariants"), dict) else {}
    if invariants.get("r5_compatibility_blob_immutable") != R6_COMPAT_BLOB:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "R6_COMPATIBILITY_BLOB_BINDING_INVALID",
                "R6 must bind the immutable pre-R6 worker-slot validator blob.",
                {"actual": invariants.get("r5_compatibility_blob_immutable"), "required": R6_COMPAT_BLOB},
            )
        )

    state = doc.get("state")
    if state not in {"ACTIVE", "RELEASED"}:
        findings.append(
            Finding(
                CHECK_ID,
                "ERROR",
                "R6_MAINTENANCE_STATE_INVALID",
                "R6 authority state must be ACTIVE or terminal RELEASED.",
                {"actual": state},
            )
        )
    if state == "RELEASED":
        expected_transition = {
            "from_state": "ACTIVE",
            "to_state": "RELEASED",
            "terminal_for_authority_id": True,
            "next_activation_requires_new_user_issued_authority_id": True,
        }
        if not doc.get("release_reason"):
            findings.append(
                Finding(CHECK_ID, "ERROR", "R6_MAINTENANCE_RELEASE_REASON_MISSING", "Released R6 authority requires a durable release reason.", {})
            )
        if doc.get("released_scope_status") != R6_RELEASED_SCOPE:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "R6_MAINTENANCE_RELEASE_SCOPE_INVALID",
                    "Released R6 authority grants no further modifier writes.",
                    {"actual": doc.get("released_scope_status"), "required": R6_RELEASED_SCOPE},
                )
            )
        if doc.get("release_transition") != expected_transition:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "R6_MAINTENANCE_RELEASE_TRANSITION_INVALID",
                    "Released R6 authority must be terminal and require a new user-issued ID for future maintenance.",
                    {"actual": doc.get("release_transition"), "required": expected_transition},
                )
            )
    return findings


def r6_maintenance_witness(repo_root: Path) -> dict[str, Any]:
    path = repo_root.resolve() / R6_MAINTENANCE_ADOPTION_FILE
    if not path.exists():
        return {"present": False}
    try:
        doc = load_yaml(path)
    except (OSError, ValueError, TypeError):
        return {"present": True, "load_error": "R6_MAINTENANCE_AUTHORITY_NOT_MAPPING", "raw": None}
    errors = [item for item in _r6_authority_findings(repo_root) if item.severity == "ERROR"]
    return {
        "present": True,
        "raw": doc,
        "structural_check": "PASS" if not errors else "FAIL",
    }


def worker_slot_findings(repo_root: Path) -> list[Finding]:
    # Run the complete R5 security suite through R6's schema/state/executable hooks.
    findings = list(_R5_WORKER_SLOT_FINDINGS(repo_root))
    findings.extend(_r6_authority_findings(repo_root))

    capacity_policy = _r5._program_capacity_policy(repo_root.resolve())
    capacity = capacity_policy.get("gpt_engineering_worker_active_slots_max")
    resolutions = _raw_slot_resolutions(repo_root)
    occupied = [
        str(raw.get("worker_slot_id") or "UNKNOWN")
        for raw, resolution in resolutions
        if resolution.occupies_capacity
    ]
    if not isinstance(capacity, bool) and isinstance(capacity, int) and capacity >= 1:
        if len(occupied) > capacity:
            findings.append(
                Finding(
                    CHECK_ID,
                    "ERROR",
                    "WORKER_SLOT_OCCUPIED_CAPACITY_EXCEEDED",
                    "GPT capacity counts reserved/review-wait/accepted/canonicalization-wait slots as occupied even when they are non-executable.",
                    {"occupied_slots": occupied, "occupied_count": len(occupied), "limit": capacity},
                )
            )
    return findings


def worker_registry_witness(repo_root: Path) -> dict[str, Any]:
    witness = dict(_R5_WORKER_REGISTRY_WITNESS(repo_root))
    doc = witness.get("raw_registry") if isinstance(witness, dict) else None
    version = doc.get("schema_version") if isinstance(doc, dict) else None
    witness["r6_schema_contract"] = {
        "canonical": CANONICAL_REGISTRY_SCHEMA_VERSION,
        "actual": version,
        "supported": registry_schema_supported(version),
        "legacy_compatibility": version == "1.0",
    }
    return witness


def validate_worker_slots(repo_root: Path) -> dict[str, Any]:
    report = dict(_R5_VALIDATE_WORKER_SLOTS(repo_root))
    # Legacy validate() calls the R6-patched worker_slot_findings/executable hooks below.
    resolutions = _raw_slot_resolutions(repo_root)
    report["worker_registry"] = worker_registry_witness(repo_root)
    report["worker_lifecycle_schema"] = "WorkerLifecycleResolution/v1"
    report["worker_lifecycle_resolutions"] = [
        {
            "worker_slot_id": raw.get("worker_slot_id"),
            **resolution.to_dict(),
        }
        for raw, resolution in resolutions
    ]
    report["occupied_capacity_slots"] = [
        raw.get("worker_slot_id")
        for raw, resolution in resolutions
        if resolution.occupies_capacity
    ]
    report["occupied_capacity_count"] = len(report["occupied_capacity_slots"])
    report["r6_maintenance_adoption"] = r6_maintenance_witness(repo_root)
    r6_raw = report["r6_maintenance_adoption"].get("raw") if isinstance(report["r6_maintenance_adoption"], dict) else None
    r6_state = r6_raw.get("state") if isinstance(r6_raw, dict) else None
    report["r6_maintenance_authority_state"] = r6_state
    report["r6_maintenance_write_allowed"] = (
        r6_state == "ACTIVE" and report["r6_maintenance_adoption"].get("structural_check") == "PASS"
    )
    # Recompute error/warning projections because R6 adds findings after R5 validate().
    findings = worker_slot_findings(repo_root)
    report["errors"] = [asdict(item) for item in findings if item.severity == "ERROR"]
    report["warnings"] = [asdict(item) for item in findings if item.severity == "WARN"]
    report["worker_slot_structural_check"] = "PASS" if not report["errors"] else "FAIL"
    report["active_executable_slots"] = [
        slot.worker_slot_id for slot in load_worker_slots(repo_root) if worker_slot_is_executable(slot)
    ]
    return report


# Patch only the lifecycle/schema hooks used by the immutable R5 validation functions.
# This preserves R5 tombstone, claim, collision, provenance and self-review checks while
# ensuring every caller importing worker_slots sees one R6 lifecycle interpretation.
_r5._registry_findings = _registry_findings
_r5._slot_required_field_findings = _slot_required_field_findings
_r5.worker_slot_is_executable = worker_slot_is_executable
_r5.worker_slot_findings = worker_slot_findings
_r5.worker_registry_witness = worker_registry_witness
_r5.validate_worker_slots = validate_worker_slots
