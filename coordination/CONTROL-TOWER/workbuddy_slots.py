from __future__ import annotations

"""Fail-closed admission facade for WorkBuddy multi-slot governance.

The heavily tested collision/authorization engine remains byte-identical in
``workbuddy_slots_core.py``.  This facade owns only input-boundary safety:
registry lifecycle/identity, parser containment, scalar slot identity and
executor-role admission.  It deliberately does not create a second collision
or authorization state machine.
"""

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

import workbuddy_slots_core as _core
from workbuddy_slots_core import *  # noqa: F401,F403

EXPECTED_EXECUTOR_ROLE = "WORKBUDDY_LOCAL_EXECUTOR"
EXPECTED_REGISTRY_STATUS = "ACTIVE"
EXPECTED_REPOSITORY_FULL_NAME = "vxz2datoubo/second-brain-coordination"

# The pre-R579 loader correctly rejects non-mapping YAML but allowed parser
# exceptions to escape.  Normalize parser failures to ValueError so all of the
# core's existing fail-closed catches remain effective without modifying its
# validated semantics.
_CORE_LOAD_YAML = _core.load_yaml


def _parser_contained_load_yaml(path: Path) -> dict[str, Any]:
    try:
        return _CORE_LOAD_YAML(path)
    except yaml.YAMLError as exc:
        raise ValueError(f"malformed YAML at {path}") from exc


_core.load_yaml = _parser_contained_load_yaml


def _error(code: str, message: str, evidence: dict[str, Any]) -> Finding:
    return Finding(CHECK_ID, "ERROR", code, message, evidence)


def _load_mapping_for_guard(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "NOT_FOUND"
    try:
        raw = _parser_contained_load_yaml(path)
    except (OSError, ValueError, TypeError, UnicodeError):
        return None, "UNREADABLE"
    return raw, None


def _first_raw(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _raw_slot_is_candidate_executable(raw: dict[str, Any]) -> bool:
    return (
        raw.get("execution_allowed") is True
        and str(raw.get("activation_state") or "").upper() == "ACTIVE"
        and raw.get("closure_state") in (None, "", "OPEN")
        and str(raw.get("status") or "").upper() == "READY"
    )


def _guard_registry_input(repo_root: Path) -> tuple[dict[str, Any] | None, list[Finding], bool]:
    """Return registry, guard findings and whether calling the core is unsafe.

    ``fatal_for_core`` is reserved for malformed parser/identity inputs that can
    otherwise raise before the core has a chance to emit structured evidence.
    Lifecycle/role violations are ordinary fail-closed findings and may still be
    passed through the core for additional diagnostics.
    """

    root = repo_root.resolve()
    registry_path = root / WORKBUDDY_REGISTRY
    registry, load_error = _load_mapping_for_guard(registry_path)
    if load_error == "NOT_FOUND":
        return None, [
            _error(
                "WORKBUDDY_REGISTRY_MISSING",
                "Canonical WorkBuddy multi-slot registry is missing.",
                {"path": WORKBUDDY_REGISTRY},
            )
        ], True
    if load_error:
        return None, [
            _error(
                "WORKBUDDY_REGISTRY_UNREADABLE",
                "Canonical WorkBuddy multi-slot registry is unreadable or malformed YAML.",
                {"path": WORKBUDDY_REGISTRY, "error": load_error},
            )
        ], True

    assert registry is not None
    findings: list[Finding] = []
    fatal_for_core = False

    if registry.get("status") != EXPECTED_REGISTRY_STATUS:
        findings.append(
            _error(
                "WORKBUDDY_REGISTRY_STATUS_INVALID",
                "The canonical WorkBuddy registry must be explicitly ACTIVE before any child slot can be admitted.",
                {"expected": EXPECTED_REGISTRY_STATUS, "actual": registry.get("status")},
            )
        )

    if registry.get("repository") != EXPECTED_REPOSITORY_FULL_NAME:
        findings.append(
            _error(
                "WORKBUDDY_REGISTRY_REPOSITORY_MISMATCH",
                "The WorkBuddy registry is bound to a different or missing repository identity.",
                {"expected": EXPECTED_REPOSITORY_FULL_NAME, "actual": registry.get("repository")},
            )
        )

    raw_slots = registry.get("worker_slots")
    if not isinstance(raw_slots, list):
        return registry, findings, fatal_for_core

    for index, raw in enumerate(raw_slots):
        if not isinstance(raw, dict):
            continue

        slot_id = _first_raw(raw, "worker_slot_id", "slot_id")
        if not isinstance(slot_id, str) or not slot_id.strip():
            findings.append(
                _error(
                    "WORKBUDDY_SLOT_ID_INVALID_OR_DUPLICATE",
                    "WorkBuddy slot IDs must be non-empty strings before uniqueness checks.",
                    {"index": index, "slot_id_type": type(slot_id).__name__},
                )
            )
            fatal_for_core = True

        task_id = _first_raw(raw, "task_id", "active_task_id")
        if task_id is not None and not isinstance(task_id, str):
            findings.append(
                _error(
                    "WORKBUDDY_SLOT_IDENTITY_TYPE_INVALID",
                    "WorkBuddy task identity must be a string when present.",
                    {"index": index, "field": "task_id", "value_type": type(task_id).__name__},
                )
            )
            fatal_for_core = True

        if raw.get("agent_type") != AGENT_TYPE:
            findings.append(
                _error(
                    "WORKBUDDY_SLOT_AGENT_TYPE_INVALID",
                    "Every WorkBuddy registry slot must carry the canonical WorkBuddy agent identity.",
                    {"index": index, "slot": slot_id, "actual": raw.get("agent_type")},
                )
            )

        if raw.get("executor_role") != EXPECTED_EXECUTOR_ROLE:
            findings.append(
                _error(
                    "WORKBUDDY_SLOT_EXECUTOR_ROLE_INVALID",
                    "Every WorkBuddy slot must bind the canonical local-executor role.",
                    {
                        "index": index,
                        "slot": slot_id,
                        "expected": EXPECTED_EXECUTOR_ROLE,
                        "actual": raw.get("executor_role"),
                    },
                )
            )

        if not _raw_slot_is_candidate_executable(raw):
            continue

        for field, ref_name in (
            ("canonical_route", "canonical_route"),
            ("work_claim", "work_claim"),
            ("task_lease", "task_lease"),
            ("executor_reservation", "executor_reservation"),
            ("prewrite_snapshot", "prewrite_snapshot"),
            ("executable_batch", "executable_batch"),
        ):
            relpath = raw.get(field)
            if not isinstance(relpath, str) or not relpath.strip():
                continue
            _, bound_error = _load_mapping_for_guard(root / relpath)
            if bound_error == "UNREADABLE":
                findings.append(
                    _error(
                        "WORKBUDDY_BOUND_REF_UNREADABLE",
                        "Executable WorkBuddy slot bound document is unreadable or malformed YAML.",
                        {"slot": slot_id, "ref": ref_name, "path": relpath},
                    )
                )
                fatal_for_core = True

    # The core's legacy compatibility read occurs after its ordinary guarded
    # loads.  Pre-parse that file here so malformed YAML is also observable as a
    # structured failure instead of escaping from the compatibility check.
    primary_declared = any(
        isinstance(raw, dict) and raw.get("primary_compatibility_projection") is True
        for raw in raw_slots
    )
    if primary_declared:
        legacy_path = root / LEGACY_WORKBUDDY_PROJECTION
        if legacy_path.exists():
            _, legacy_error = _load_mapping_for_guard(legacy_path)
            if legacy_error:
                findings.append(
                    _error(
                        "WORKBUDDY_LEGACY_PROJECTION_UNREADABLE",
                        "Legacy WorkBuddy compatibility projection is unreadable or malformed YAML.",
                        {"path": LEGACY_WORKBUDDY_PROJECTION},
                    )
                )
                fatal_for_core = True

    return registry, findings, fatal_for_core


def load_workbuddy_registry(repo_root: Path) -> dict[str, Any]:
    """Load canonical registry with YAML parser failures normalized."""

    return _parser_contained_load_yaml(repo_root.resolve() / WORKBUDDY_REGISTRY)


def load_workbuddy_slots(repo_root: Path) -> list[WorkBuddySlot]:
    """Return no candidate slots when the registry lifecycle is not ACTIVE."""

    registry = load_workbuddy_registry(repo_root)
    if registry.get("status") != EXPECTED_REGISTRY_STATUS:
        return []
    raw_slots = registry.get("worker_slots")
    if not isinstance(raw_slots, list):
        return []
    safe_slots: list[WorkBuddySlot] = []
    for raw in raw_slots:
        if not isinstance(raw, dict):
            continue
        slot_id = _first_raw(raw, "worker_slot_id", "slot_id")
        if not isinstance(slot_id, str) or not slot_id.strip():
            continue
        safe_slots.append(_core.normalize_workbuddy_slot(raw))
    return safe_slots


def workbuddy_active_slots_max(repo_root: Path) -> int:
    try:
        registry = load_workbuddy_registry(repo_root)
    except (OSError, ValueError, TypeError, UnicodeError):
        return 0
    if registry.get("status") != EXPECTED_REGISTRY_STATUS:
        return 0
    raw = registry.get("active_slots_max")
    return raw if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 1 else 0


def workbuddy_slot_findings(repo_root: Path) -> list[Finding]:
    registry, guard_findings, fatal_for_core = _guard_registry_input(repo_root)
    if registry is None or fatal_for_core:
        return guard_findings
    core_findings = _core.workbuddy_slot_findings(repo_root)
    return guard_findings + core_findings


def validate_workbuddy_slots(repo_root: Path) -> dict[str, Any]:
    findings = workbuddy_slot_findings(repo_root)
    try:
        slots = load_workbuddy_slots(repo_root)
    except (OSError, ValueError, TypeError, UnicodeError):
        slots = []
    return {
        "schema_version": "1.0",
        "registry": WORKBUDDY_REGISTRY,
        "active_slots_max": workbuddy_active_slots_max(repo_root),
        "slots": [asdict(slot) for slot in slots],
        "errors": [asdict(item) for item in findings if item.severity == "ERROR"],
        "warnings": [asdict(item) for item in findings if item.severity == "WARN"],
        "structural_check": "PASS" if not any(item.severity == "ERROR" for item in findings) else "FAIL",
    }
