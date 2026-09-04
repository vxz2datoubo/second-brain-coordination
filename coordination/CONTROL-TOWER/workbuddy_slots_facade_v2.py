from __future__ import annotations

"""Second-layer fail-closed facade for WorkBuddy multi-slot governance.

The previously reviewed admission facade is preserved byte-for-byte in
``workbuddy_slots_facade_v1.py``.  This successor layer closes the next exact-
head T3 findings without replacing the existing collision/lifecycle engine:
repository-root containment for every bound authorization reference, complete
legacy compatibility projection binding for authority-bearing fields, and
closed scalar typing for executable identity.
"""

import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import workbuddy_slots_facade_v1 as _v1
from workbuddy_slots_facade_v1 import *  # noqa: F401,F403

_WINDOWS_DRIVE_REF = re.compile(r"^[A-Za-z]:")
_CORE = _v1._core
_V1_WORKBUDDY_SLOT_FINDINGS = _v1.workbuddy_slot_findings
_CORE_SLOT_IDENTITY = _CORE._slot_identity
_CORE_LEGACY_IDENTITY = _CORE._legacy_identity

_BOUND_REF_FIELDS = (
    "canonical_route",
    "work_claim",
    "task_lease",
    "executor_reservation",
    "prewrite_snapshot",
    "executable_batch",
)


def _resolve_repo_bound_ref(repo_root: Path, relpath: str) -> Path:
    """Resolve one governed ref only when it is contained by repository truth."""

    if not isinstance(relpath, str) or not relpath.strip() or relpath != relpath.strip():
        raise ValueError("BOUND_REF_MUST_BE_NONEMPTY_CANONICAL_STRING")
    if "\\" in relpath or relpath.startswith(("/", "~")) or _WINDOWS_DRIVE_REF.match(relpath):
        raise ValueError("BOUND_REF_ABSOLUTE_OR_PLATFORM_ALIAS_FORBIDDEN")
    if "\x00" in relpath:
        raise ValueError("BOUND_REF_NUL_FORBIDDEN")
    segments = relpath.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError("BOUND_REF_DOT_OR_EMPTY_SEGMENT_FORBIDDEN")

    root = repo_root.resolve()
    candidate = root.joinpath(*segments)
    try:
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        raise ValueError("BOUND_REF_RESOLUTION_FAILED") from exc
    if resolved == root or root not in resolved.parents:
        raise ValueError("BOUND_REF_ESCAPES_REPOSITORY_TRUST_ROOT")
    return candidate


def _strict_load_bound_mapping(repo_root: Path, relpath: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        path = _resolve_repo_bound_ref(repo_root, relpath)
    except (TypeError, ValueError):
        return None, "OUTSIDE_TRUST_ROOT"
    if not path.exists():
        return None, "NOT_FOUND"
    try:
        return _v1._parser_contained_load_yaml(path), None
    except (OSError, ValueError, TypeError, UnicodeError):
        return None, "UNREADABLE"


def _strict_slot_identity(slot: WorkBuddySlot) -> dict[str, Any]:
    identity = dict(_CORE_SLOT_IDENTITY(slot))
    identity.update(
        {
            "repository": EXPECTED_REPOSITORY_FULL_NAME,
            "target_agent": AGENT_TYPE,
            "canonical_route": slot.canonical_route,
            "work_claim": slot.work_claim,
            "task_lease": slot.task_lease,
            "executor_reservation": slot.executor_reservation,
            "prewrite_snapshot": slot.prewrite_snapshot,
            "executable_batch": slot.executable_batch,
            "authorized_paths": _CORE._normalized_paths(list(slot.write_paths)),
        }
    )
    return identity


def _strict_legacy_identity(raw: dict[str, Any]) -> dict[str, Any]:
    identity = dict(_CORE_LEGACY_IDENTITY(raw))
    identity.update(
        {
            "repository": raw.get("repository"),
            "target_agent": raw.get("target_agent"),
            "canonical_route": raw.get("canonical_route"),
            "work_claim": raw.get("work_claim"),
            "task_lease": raw.get("task_lease"),
            "executor_reservation": raw.get("executor_reservation"),
            "prewrite_snapshot": raw.get("prewrite_snapshot"),
            "executable_batch": raw.get("executable_batch"),
            "authorized_paths": _CORE._normalized_paths(raw.get("authorized_paths")),
        }
    )
    return identity


# Install successor hardening into the same underlying engine.  There remains
# one collision/lifecycle authority; this layer only constrains its inputs.
_CORE._load_bound_mapping = _strict_load_bound_mapping
_CORE._slot_identity = _strict_slot_identity
_CORE._legacy_identity = _strict_legacy_identity


def _identity_type_error(index: int, slot_id: Any, field: str, value: Any, expected: str) -> Finding:
    return _v1._error(
        "WORKBUDDY_SLOT_IDENTITY_TYPE_INVALID",
        "Executable WorkBuddy identity fields must use the closed scalar types required by schema v1.",
        {
            "index": index,
            "slot": slot_id,
            "field": field,
            "expected": expected,
            "actual_type": type(value).__name__,
        },
    )


def _successor_guard_findings(repo_root: Path) -> tuple[list[Finding], bool]:
    root = repo_root.resolve()
    try:
        registry = _v1.load_workbuddy_registry(root)
    except (OSError, ValueError, TypeError, UnicodeError):
        return [], False
    raw_slots = registry.get("worker_slots")
    if not isinstance(raw_slots, list):
        return [], False

    findings: list[Finding] = []
    fatal = False
    for index, raw in enumerate(raw_slots):
        if not isinstance(raw, dict) or not _v1._raw_slot_is_candidate_executable(raw):
            continue
        slot_id = _v1._first_raw(raw, "worker_slot_id", "slot_id")

        route_epoch = _v1._first_raw(raw, "route_epoch", "epoch")
        if not isinstance(route_epoch, int) or isinstance(route_epoch, bool) or route_epoch < 1:
            findings.append(_identity_type_error(index, slot_id, "route_epoch", route_epoch, "positive integer"))
            fatal = True

        issue = _v1._first_raw(raw, "active_issue", "issue")
        if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
            findings.append(_identity_type_error(index, slot_id, "issue", issue, "positive integer"))
            fatal = True

        source_issue = raw.get("source_issue")
        if source_issue is not None and (
            not isinstance(source_issue, int) or isinstance(source_issue, bool) or source_issue < 1
        ):
            findings.append(_identity_type_error(index, slot_id, "source_issue", source_issue, "positive integer or null"))
            fatal = True

        pull_request = _v1._first_raw(raw, "pull_request", "pr", "implementation_pr")
        if pull_request is not None and (
            not isinstance(pull_request, int) or isinstance(pull_request, bool) or pull_request < 1
        ):
            findings.append(_identity_type_error(index, slot_id, "pull_request", pull_request, "positive integer or null"))
            fatal = True

        branch = _v1._first_raw(raw, "branch", "implementation_branch")
        if not isinstance(branch, str) or not branch.strip() or branch != branch.strip():
            findings.append(_identity_type_error(index, slot_id, "branch", branch, "non-empty canonical string"))
            fatal = True

        completion_signal = raw.get("completion_signal")
        if not isinstance(completion_signal, str) or not completion_signal.strip():
            findings.append(
                _identity_type_error(index, slot_id, "completion_signal", completion_signal, "non-empty string")
            )
            fatal = True

        for field in _BOUND_REF_FIELDS:
            relpath = raw.get(field)
            if not isinstance(relpath, str) or not relpath.strip():
                findings.append(_identity_type_error(index, slot_id, field, relpath, "repository-relative file string"))
                fatal = True
                continue
            try:
                _resolve_repo_bound_ref(root, relpath)
            except (TypeError, ValueError) as exc:
                findings.append(
                    _v1._error(
                        "WORKBUDDY_BOUND_REF_OUTSIDE_TRUST_ROOT",
                        "Executable WorkBuddy bound references must remain inside the resolved repository trust root.",
                        {"index": index, "slot": slot_id, "field": field, "path": relpath, "reason": str(exc)},
                    )
                )
                fatal = True

    return findings, fatal


def workbuddy_slot_findings(repo_root: Path) -> list[Finding]:
    successor_findings, fatal = _successor_guard_findings(repo_root)
    if fatal:
        return successor_findings
    return successor_findings + _V1_WORKBUDDY_SLOT_FINDINGS(repo_root)


def validate_workbuddy_slots(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    before_fingerprint = _v1._registry_sha256(root)
    findings = workbuddy_slot_findings(root)
    structural_pass = not any(item.severity == "ERROR" for item in findings)

    slots: list[WorkBuddySlot] = []
    if structural_pass:
        try:
            slots = _v1.load_workbuddy_slots(root)
        except (OSError, ValueError, TypeError, UnicodeError):
            slots = []
            findings.append(
                _v1._error(
                    "WORKBUDDY_VALIDATED_SLOT_SNAPSHOT_UNREADABLE",
                    "Validated WorkBuddy slot snapshot could not be materialized.",
                    {},
                )
            )
            structural_pass = False

    after_fingerprint = _v1._registry_sha256(root)
    if before_fingerprint != after_fingerprint:
        findings.append(
            _v1._error(
                "WORKBUDDY_REGISTRY_CHANGED_DURING_VALIDATION",
                "Canonical WorkBuddy registry changed while the validation snapshot was being built.",
                {"before_sha256": before_fingerprint, "after_sha256": after_fingerprint},
            )
        )
        slots = []
        structural_pass = False

    structural_pass = structural_pass and not any(item.severity == "ERROR" for item in findings)
    return {
        "schema_version": "1.0",
        "registry": WORKBUDDY_REGISTRY,
        "validated_registry_sha256": before_fingerprint if before_fingerprint == after_fingerprint else None,
        "active_slots_max": _v1.workbuddy_active_slots_max(root) if structural_pass else 0,
        "slots": [asdict(slot) for slot in slots] if structural_pass else [],
        "errors": [asdict(item) for item in findings if item.severity == "ERROR"],
        "warnings": [asdict(item) for item in findings if item.severity == "WARN"],
        "structural_check": "PASS" if structural_pass else "FAIL",
    }
