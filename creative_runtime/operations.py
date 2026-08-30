"""Read-only operational health reporting for synthetic creative workspaces.

The report deliberately sees only ledger envelopes and runtime coordination
markers.  It does not read customer content, credentials, provider state, or
any external service.  A later local service can use the same deterministic
signals before deciding whether an operator-approved mutation is safe.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .continuity import graph_for_ledger, replay_timeline, timeline_hash
from .ledger import CreativeLedger, LedgerViolation
from .session import (
    DEFAULT_SLOT,
    LEGACY_SCHEMA,
    LOCK_DIRECTORY,
    SLOT_DIRECTORY,
    SessionViolation,
    legacy_session_path,
    v2_session_path,
    validate_slot,
    verify_v2_source_binding,
)


def _relative(workspace: Path, path: Path) -> str:
    return path.relative_to(workspace).as_posix()


def _load_verified_ledger(path: Path) -> CreativeLedger:
    if path.is_symlink() or not path.is_file():
        raise SessionViolation("session must be a regular non-symlink file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SessionViolation("session is not valid UTF-8 JSON") from error
    if not isinstance(value, Mapping) or value.get("schema") != LEGACY_SCHEMA:
        raise SessionViolation("session schema must be CreativeSession/v1")
    try:
        return CreativeLedger.from_records(value.get("events", ()))
    except (LedgerViolation, KeyError, TypeError, ValueError) as error:
        raise SessionViolation("session ledger is invalid") from error


def _candidate_slots(workspace: Path) -> tuple[list[tuple[str, Path]], list[dict[str, str]]]:
    """Return only confinement-safe session candidates and path-shape findings."""

    candidates: list[tuple[str, Path]] = []
    findings: list[dict[str, str]] = []
    default_path = legacy_session_path(workspace)
    if default_path.exists() or default_path.is_symlink():
        candidates.append((DEFAULT_SLOT, default_path))
    slots_dir = workspace / SLOT_DIRECTORY
    if not slots_dir.exists() and not slots_dir.is_symlink():
        return candidates, findings
    if slots_dir.is_symlink() or not slots_dir.is_dir():
        findings.append({"path": _relative(workspace, slots_dir), "reason": "slots_directory_must_be_a_real_directory"})
        return candidates, findings
    for path in sorted(slots_dir.iterdir(), key=lambda item: item.name):
        if path.suffix != ".json":
            findings.append({"path": _relative(workspace, path), "reason": "unexpected_slots_member"})
            continue
        slot = path.stem
        try:
            validate_slot(slot)
        except SessionViolation:
            findings.append({"path": _relative(workspace, path), "reason": "invalid_slot_filename"})
            continue
        if slot == DEFAULT_SLOT:
            findings.append({"path": _relative(workspace, path), "reason": "default_slot_must_use_root_session_path"})
            continue
        candidates.append((slot, path))
    return candidates, findings


def _lock_findings(workspace: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    locks_dir = workspace / LOCK_DIRECTORY
    active: list[dict[str, str]] = []
    findings: list[dict[str, str]] = []
    if not locks_dir.exists() and not locks_dir.is_symlink():
        return active, findings
    if locks_dir.is_symlink() or not locks_dir.is_dir():
        return active, [{"path": _relative(workspace, locks_dir), "reason": "lock_directory_must_be_a_real_directory"}]
    for path in sorted(locks_dir.iterdir(), key=lambda item: item.name):
        if path.suffix != ".lock" or path.is_symlink() or not path.is_file():
            findings.append({"path": _relative(workspace, path), "reason": "invalid_lock_marker"})
            continue
        try:
            slot = validate_slot(path.stem)
            marker = path.read_text(encoding="ascii")
        except (OSError, UnicodeDecodeError, SessionViolation):
            findings.append({"path": _relative(workspace, path), "reason": "unreadable_lock_marker"})
            continue
        if marker != "slot=" + slot + "\n":
            findings.append({"path": _relative(workspace, path), "reason": "lock_marker_slot_mismatch"})
            continue
        active.append({"slot_id": slot, "path": _relative(workspace, path), "status": "mutation_lock_present"})
    return active, findings


def _stranded_atomic_temps(workspace: Path, slots: Iterable[str]) -> list[str]:
    paths = [legacy_session_path(workspace).with_name("session.json.replace-tmp")]
    paths.extend(legacy_session_path(workspace, slot).with_name(slot + ".json.replace-tmp") for slot in slots if slot != DEFAULT_SLOT)
    return [_relative(workspace, path) for path in paths if path.exists() or path.is_symlink()]


def build_operations_report(workspace: Path) -> dict[str, Any]:
    """Audit every confined slot without writing, retrying, or repairing anything."""

    workspace = workspace.resolve()
    candidates, path_findings = _candidate_slots(workspace)
    slots: list[dict[str, Any]] = []
    for slot, path in candidates:
        try:
            ledger = _load_verified_ledger(path)
            graph = graph_for_ledger(ledger)
            timeline = replay_timeline(ledger, graph)
            v2: dict[str, Any] = {"status": "not_migrated"}
            if v2_session_path(workspace, slot).is_file() and not v2_session_path(workspace, slot).is_symlink():
                v2 = verify_v2_source_binding(workspace, slot).to_dict()
            slots.append(
                {
                    "slot_id": slot,
                    "status": "slot_verified",
                    "session_path": _relative(workspace, path),
                    "event_count": len(ledger.events),
                    "timeline_hash": timeline_hash(timeline),
                    "graph_revision": graph.revision,
                    "v2_source_binding": v2["status"],
                }
            )
        except (LedgerViolation, SessionViolation, ValueError) as error:
            slots.append({"slot_id": slot, "status": "slot_invalid", "session_path": _relative(workspace, path), "reason": str(error)})
    active_locks, lock_findings = _lock_findings(workspace)
    temps = _stranded_atomic_temps(workspace, (slot for slot, _ in candidates))
    verified_count = sum(1 for slot in slots if slot["status"] == "slot_verified")
    invalid_count = len(slots) - verified_count
    findings = path_findings + lock_findings
    mutation_safe = invalid_count == 0 and not active_locks and not temps and not findings
    return {
        "schema": "CreativeRuntimeOperationsReport/v1",
        "status": "operations_report_verified" if mutation_safe else "operations_attention_required",
        "workspace_scope": "synthetic_runtime_only",
        "read_only": True,
        "mutation_safe": mutation_safe,
        "metrics": {
            "discovered_slot_count": len(slots),
            "verified_slot_count": verified_count,
            "invalid_slot_count": invalid_count,
            "active_lock_count": len(active_locks),
            "stranded_atomic_temp_count": len(temps),
            "path_finding_count": len(findings),
        },
        "slots": slots,
        "active_locks": active_locks,
        "stranded_atomic_temp_files": temps,
        "path_findings": findings,
        "authority_note": "Read-only synthetic workspace evidence. It does not repair locks or files and cannot authorize customer intake, deployment, or provider use.",
    }
