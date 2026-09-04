from __future__ import annotations

"""Third-layer fail-closed facade for WorkBuddy multi-slot governance.

The predecessor R579 admission layers remain byte-identical in
``workbuddy_slots_facade_v1.py`` and ``workbuddy_slots_facade_v2.py``.
This successor closes only the snapshot-003 findings:

* preserve ``/*`` versus ``/**`` semantics in governed write-surface identity;
* fence validation with a before/after fingerprint of the complete authority
  input closure, not the registry alone;
* require executable-slot completion signals to be unique.

The collision/lifecycle engine remains the existing R579 core. This module
constrains and witnesses its inputs; it does not create a second scheduler.
"""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import workbuddy_slots_facade_v2 as _v2
from workbuddy_slots_facade_v2 import *  # noqa: F401,F403

_CORE = _v2._CORE
_V2_WORKBUDDY_SLOT_FINDINGS = _v2.workbuddy_slot_findings
_BOUND_REF_FIELDS = _v2._BOUND_REF_FIELDS


def _glob_preserving_paths(values: Any) -> list[str] | None:
    """Canonicalize ordering while preserving terminal glob semantics."""

    if not isinstance(values, list) or not all(isinstance(item, str) and item.strip() for item in values):
        return None
    if any(_CORE._path_scope_error(item) is not None for item in values):
        return None
    return sorted(values)


def _v3_slot_identity(slot: WorkBuddySlot) -> dict[str, Any]:
    """Preserve strict v2 identity while keeping exact authorized glob scopes."""

    identity = dict(_v2._CORE_SLOT_IDENTITY(slot))
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
            "authorized_paths": _glob_preserving_paths(list(slot.write_paths)),
        }
    )
    return identity


def _v3_legacy_identity(raw: dict[str, Any]) -> dict[str, Any]:
    """Project the singular compatibility file without collapsing glob depth."""

    identity = dict(_v2._CORE_LEGACY_IDENTITY(raw))
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
            "authorized_paths": _glob_preserving_paths(raw.get("authorized_paths")),
        }
    )
    return identity


def _v3_bound_surface_findings(
    slot: WorkBuddySlot,
    ref_name: str,
    relpath: str,
    raw: dict[str, Any],
) -> list[Finding]:
    """Require exact governed write-scope identity without changing collision geometry."""

    findings: list[Finding] = []
    expected_write = _glob_preserving_paths(list(slot.write_paths))
    write_locations = {
        "canonical_route": _CORE._nested(raw, "write_ownership", "workbuddy_exclusive"),
        "work_claim": raw.get("authorized_paths"),
        "task_lease": raw.get("exclusive_write_surface"),
        "executor_reservation": raw.get("reservation_scope"),
    }
    if ref_name in write_locations:
        actual_write = _glob_preserving_paths(write_locations[ref_name])
        if actual_write != expected_write:
            findings.append(
                _CORE._error(
                    "WORKBUDDY_BOUND_WRITE_SURFACE_DRIFT",
                    "Registry write_paths must exactly match the governed authorization document write surface.",
                    {
                        "slot": slot.worker_slot_id,
                        "ref": ref_name,
                        "path": relpath,
                        "expected": expected_write,
                        "actual": actual_write,
                    },
                )
            )

    if slot.primary_compatibility_projection:
        dangerous = {
            field: list(getattr(slot, field))
            for field in _CORE.LEGACY_PRIMARY_UNBOUND_RISK_FIELDS
            if getattr(slot, field)
        }
        if dangerous:
            findings.append(
                _CORE._error(
                    "WORKBUDDY_LEGACY_PRIMARY_UNBOUND_RESOURCE_CLAIM",
                    "Legacy primary slot cannot introduce unbound local-resource, credential, or real-data collision claims.",
                    {"slot": slot.worker_slot_id, "claims": dangerous},
                )
            )
        return findings

    actual_slot_id = _CORE._doc_slot_id(ref_name, raw)
    if actual_slot_id != slot.worker_slot_id:
        findings.append(
            _CORE._error(
                "WORKBUDDY_BOUND_REF_SLOT_ID_MISMATCH",
                "Every non-primary authorization document must bind the selected worker_slot_id.",
                {
                    "slot": slot.worker_slot_id,
                    "ref": ref_name,
                    "path": relpath,
                    "actual": actual_slot_id,
                },
            )
        )
    expected_surface = _CORE._canonical_surface_value(_CORE._slot_collision_surface(slot))
    actual_surface = _CORE._doc_collision_surface(ref_name, raw)
    if not isinstance(actual_surface, dict) or _CORE._canonical_surface_value(actual_surface) != expected_surface:
        findings.append(
            _CORE._error(
                "WORKBUDDY_BOUND_COLLISION_SURFACE_DRIFT",
                "Every non-primary authorization document must bind the complete collision surface used for admission.",
                {"slot": slot.worker_slot_id, "ref": ref_name, "path": relpath},
            )
        )
    return findings


# Install only authority-identity hardening into the same underlying engine.
# `_normalize_scope` remains untouched, so collision analysis keeps predecessor
# overlap behavior while Route/Claim/Lease/Reservation/legacy identity keeps
# `/*` and `/**` distinct.
_CORE._slot_identity = _v3_slot_identity
_CORE._legacy_identity = _v3_legacy_identity
_CORE._bound_surface_findings = _v3_bound_surface_findings


def _candidate_authority_paths(repo_root: Path) -> list[str]:
    """Return every repository file that can participate in slot authorization."""

    paths = {WORKBUDDY_REGISTRY, LEGACY_WORKBUDDY_PROJECTION}
    try:
        registry = _v2.load_workbuddy_registry(repo_root.resolve())
    except (OSError, ValueError, TypeError, UnicodeError):
        return sorted(paths)

    compatibility = registry.get("compatibility_projection")
    if isinstance(compatibility, dict):
        projection_path = compatibility.get("path")
        if isinstance(projection_path, str) and projection_path.strip():
            paths.add(projection_path)

    raw_slots = registry.get("worker_slots")
    if not isinstance(raw_slots, list):
        return sorted(paths)

    raw_is_executable = _v2._v1._raw_slot_is_candidate_executable
    for raw in raw_slots:
        if not isinstance(raw, dict) or not raw_is_executable(raw):
            continue
        for field in _BOUND_REF_FIELDS:
            relpath = raw.get(field)
            if isinstance(relpath, str) and relpath.strip():
                paths.add(relpath)
    return sorted(paths)


def _authority_input_fingerprint(repo_root: Path, relpath: str) -> dict[str, Any]:
    """Content-address one authority input without trusting caller path syntax."""

    root = repo_root.resolve()
    try:
        candidate = _v2._resolve_repo_bound_ref(root, relpath)
    except (TypeError, ValueError) as exc:
        return {"state": "INVALID_REF", "reason": str(exc)}

    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        return {"state": "MISSING"}
    except OSError as exc:
        return {"state": "UNRESOLVED", "error_class": type(exc).__name__}

    if resolved == root or root not in resolved.parents:
        return {"state": "OUTSIDE_TRUST_ROOT"}

    try:
        payload = candidate.read_bytes()
    except OSError as exc:
        return {"state": "UNREADABLE", "error_class": type(exc).__name__}

    return {
        "state": "PRESENT",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
        "resolved_repo_path": resolved.relative_to(root).as_posix(),
    }


def _authority_closure_snapshot(repo_root: Path) -> dict[str, Any]:
    inputs = {
        relpath: _authority_input_fingerprint(repo_root, relpath)
        for relpath in _candidate_authority_paths(repo_root)
    }
    canonical = json.dumps(inputs, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"sha256": hashlib.sha256(canonical).hexdigest(), "inputs": inputs}


def _changed_authority_inputs(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    before_inputs = before.get("inputs") if isinstance(before.get("inputs"), dict) else {}
    after_inputs = after.get("inputs") if isinstance(after.get("inputs"), dict) else {}
    keys = set(before_inputs) | set(after_inputs)
    return sorted(key for key in keys if before_inputs.get(key) != after_inputs.get(key))


def _v3_guard_findings(repo_root: Path) -> list[Finding]:
    """Close executable lifecycle identity that must remain unambiguous."""

    try:
        slots = _v2.load_workbuddy_slots(repo_root.resolve())
    except (OSError, ValueError, TypeError, UnicodeError):
        return []

    seen: dict[str, str] = {}
    findings: list[Finding] = []
    for slot in slots:
        if not workbuddy_slot_is_executable(slot):
            continue
        signal = slot.completion_signal
        if not isinstance(signal, str) or not signal.strip():
            # Predecessor scalar typing owns malformed-value diagnostics.
            continue
        prior = seen.get(signal)
        if prior is not None:
            findings.append(
                _v2._v1._error(
                    "WORKBUDDY_DUPLICATE_COMPLETION_SIGNAL",
                    "Executable WorkBuddy slots must have unique completion signals.",
                    {
                        "completion_signal": signal,
                        "first_slot": prior,
                        "second_slot": slot.worker_slot_id,
                    },
                )
            )
        else:
            seen[signal] = str(slot.worker_slot_id)
    return findings


def workbuddy_slot_findings(repo_root: Path) -> list[Finding]:
    return _v3_guard_findings(repo_root) + _V2_WORKBUDDY_SLOT_FINDINGS(repo_root)


def validate_workbuddy_slots(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    before_registry_fingerprint = _v2._v1._registry_sha256(root)
    before_authority = _authority_closure_snapshot(root)

    findings = workbuddy_slot_findings(root)
    structural_pass = not any(item.severity == "ERROR" for item in findings)

    slots: list[WorkBuddySlot] = []
    active_slots_max = 0
    if structural_pass:
        try:
            slots = _v2.load_workbuddy_slots(root)
            active_slots_max = _v2.workbuddy_active_slots_max(root)
        except (OSError, ValueError, TypeError, UnicodeError):
            findings.append(
                _v2._v1._error(
                    "WORKBUDDY_VALIDATED_SLOT_SNAPSHOT_UNREADABLE",
                    "Validated WorkBuddy slot snapshot could not be materialized.",
                    {},
                )
            )
            structural_pass = False

    after_authority = _authority_closure_snapshot(root)
    after_registry_fingerprint = _v2._v1._registry_sha256(root)

    if before_registry_fingerprint != after_registry_fingerprint:
        findings.append(
            _v2._v1._error(
                "WORKBUDDY_REGISTRY_CHANGED_DURING_VALIDATION",
                "Canonical WorkBuddy registry changed while the validation snapshot was being built.",
                {
                    "before_sha256": before_registry_fingerprint,
                    "after_sha256": after_registry_fingerprint,
                },
            )
        )
        slots = []
        active_slots_max = 0
        structural_pass = False

    if before_authority["sha256"] != after_authority["sha256"]:
        findings.append(
            _v2._v1._error(
                "WORKBUDDY_AUTHORITY_INPUT_CHANGED_DURING_VALIDATION",
                "An authority-bearing WorkBuddy input changed while the validated snapshot was being built.",
                {
                    "before_sha256": before_authority["sha256"],
                    "after_sha256": after_authority["sha256"],
                    "changed_inputs": _changed_authority_inputs(before_authority, after_authority),
                },
            )
        )
        slots = []
        active_slots_max = 0
        structural_pass = False

    structural_pass = structural_pass and not any(item.severity == "ERROR" for item in findings)
    stable_authority = before_authority if before_authority["sha256"] == after_authority["sha256"] else None
    stable_registry = (
        before_registry_fingerprint
        if before_registry_fingerprint == after_registry_fingerprint
        else None
    )

    return {
        "schema_version": "1.0",
        "registry": WORKBUDDY_REGISTRY,
        "validated_registry_sha256": stable_registry,
        "validated_authority_closure_sha256": (
            stable_authority["sha256"] if stable_authority is not None else None
        ),
        "validated_authority_inputs": (
            stable_authority["inputs"] if stable_authority is not None else {}
        ),
        "active_slots_max": active_slots_max if structural_pass else 0,
        "slots": [asdict(slot) for slot in slots] if structural_pass else [],
        "errors": [asdict(item) for item in findings if item.severity == "ERROR"],
        "warnings": [asdict(item) for item in findings if item.severity == "WARN"],
        "structural_check": "PASS" if structural_pass else "FAIL",
    }
