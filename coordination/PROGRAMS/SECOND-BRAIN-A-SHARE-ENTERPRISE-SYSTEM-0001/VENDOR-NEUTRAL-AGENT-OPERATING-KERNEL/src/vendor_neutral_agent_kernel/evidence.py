"""Fail-closed validation for E30 public evidence artifacts."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import yaml


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("E30_JSON_OBJECT_REQUIRED:" + path.name)
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("E30_YAML_OBJECT_REQUIRED:" + path.name)
    return value


def _require(mapping: dict[str, Any], *keys: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise ValueError("E30_REQUIRED_FIELD_MISSING:" + ",".join(missing))


def _require_sha(value: Any, kind: str) -> None:
    pattern = SHA40_RE if kind == "commit" else SHA256_RE
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"E30_INVALID_{kind.upper()}_SHA")


def validate_archive_manifest(path: Path) -> dict[str, Any]:
    manifest = _load_yaml(path)
    _require(manifest, "schema_version", "task_id", "status", "required_root_count", "roots")
    if manifest["status"] != "E30_ARCHIVE_PROVENANCE_REQUIRED":
        raise ValueError("E30_ARCHIVE_STATUS_INVALID")
    roots = manifest["roots"]
    if not isinstance(roots, list) or len(roots) != manifest["required_root_count"] or len(roots) != 3:
        raise ValueError("E30_ARCHIVE_ROOT_COUNT_INVALID")

    root_ids: list[str] = []
    artifact_sets: list[tuple[tuple[str, int, str], ...]] = []
    set_hashes: list[str] = []
    for root in roots:
        if not isinstance(root, dict):
            raise ValueError("E30_ARCHIVE_ROOT_OBJECT_REQUIRED")
        _require(root, "root_id", "root_locator", "hash_seed", "command", "exit_code", "stdout_sha256", "stderr_sha256", "artifacts", "artifact_set_sha256")
        root_id = root["root_id"]
        if not isinstance(root_id, str) or not root_id or root_id in root_ids:
            raise ValueError("E30_ARCHIVE_ROOT_ID_DUPLICATE_OR_EMPTY")
        root_ids.append(root_id)
        if not isinstance(root["root_locator"], str) or not root["root_locator"].startswith("archive://"):
            raise ValueError("E30_ARCHIVE_EXTERNAL_PATH_OR_UNSCOPED_ROOT")
        if not isinstance(root["command"], str) or "ci_verify.py" not in root["command"] or "--commit" not in root["command"] or "--tree" not in root["command"]:
            raise ValueError("E30_ARCHIVE_COMMAND_NOT_ROOT_CONTAINED")
        if root["exit_code"] != 0:
            raise ValueError("E30_ARCHIVE_NONZERO_EXIT")
        for key in ("stdout_sha256", "stderr_sha256", "artifact_set_sha256"):
            _require_sha(root[key], "sha256")
        artifacts = root["artifacts"]
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError("E30_ARCHIVE_ARTIFACTS_REQUIRED")
        entries: list[tuple[str, int, str]] = []
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                raise ValueError("E30_ARCHIVE_ARTIFACT_OBJECT_REQUIRED")
            _require(artifact, "path", "size", "sha256")
            if not isinstance(artifact["path"], str) or artifact["path"].startswith(("/", "\\")) or ":\\" in artifact["path"]:
                raise ValueError("E30_ARCHIVE_ARTIFACT_EXTERNAL_PATH")
            if not isinstance(artifact["size"], int) or artifact["size"] < 0:
                raise ValueError("E30_ARCHIVE_ARTIFACT_SIZE_INVALID")
            _require_sha(artifact["sha256"], "sha256")
            entries.append((artifact["path"], artifact["size"], artifact["sha256"]))
        canonical_entries = tuple(sorted(entries))
        if len(canonical_entries) != len(set(canonical_entries)):
            raise ValueError("E30_ARCHIVE_ARTIFACT_DUPLICATE")
        artifact_sets.append(canonical_entries)
        set_hashes.append(root["artifact_set_sha256"])

    if any(items != artifact_sets[0] for items in artifact_sets[1:]):
        raise ValueError("E30_ARCHIVE_ARTIFACT_SET_DRIFT")
    if len(set(set_hashes)) != 1:
        raise ValueError("E30_ARCHIVE_ARTIFACT_SET_HASH_DRIFT")
    return {"root_count": len(roots), "root_ids": tuple(root_ids), "artifact_count": len(artifact_sets[0])}


def validate_e30_evidence(
    root: Path,
    *,
    current_commit: str | None = None,
    current_tree: str | None = None,
    tested_commit: str | None = None,
    tested_tree: str | None = None,
) -> dict[str, Any]:
    evidence_path = root / "E30-COMPLETION-EVIDENCE.json"
    archive_path = root / "E30-ARCHIVE-PROVENANCE-MATRIX.yaml"
    wpdcr_path = root / "E30-WORK-PROCESS-AND-COORDINATION-REPORT.yaml"
    evidence = _load_json(evidence_path)
    _require(evidence, "schema", "task_id", "route_epoch", "status", "primary_tested_identity", "boundary", "completion_signal", "authority", "activation")
    if evidence["schema"] != "VNAK_E30_COMPLETION_EVIDENCE_v1":
        raise ValueError("E30_EVIDENCE_SCHEMA_INVALID")
    expected_task = "CODEX-PEOS-0010-E29-WPDCR-ARCHIVE-MANIFEST-CURRENT-REVIEW-PACKET-AND-RECEIPT-TRUTH-CLOSURE-0022-E30"
    if evidence["task_id"] != expected_task or evidence["route_epoch"] != 31:
        raise ValueError("E30_ROUTE_IDENTITY_INVALID")
    if evidence["boundary"] != "PUBLIC_SAFE / CANDIDATE_ONLY / DISABLED / research_only / NO_TRADE":
        raise ValueError("E30_BOUNDARY_INVALID")
    if evidence["authority"] != "CANDIDATE_ONLY" or evidence["activation"] != "DISABLED":
        raise ValueError("E30_PROMOTION_OR_ACTIVATION_FORBIDDEN")
    expected_signal = "CODEX_E30_PEOS_0010_E29_WPDCR_ARCHIVE_MANIFEST_PACKET_AND_RECEIPT_TRUTH_READY_FOR_GPT_REVIEW"
    if evidence["completion_signal"] != expected_signal:
        raise ValueError("E30_COMPLETION_SIGNAL_INVALID")

    identity = evidence["primary_tested_identity"]
    _require(identity, "tested_commit", "tested_tree", "authority")
    if identity["authority"] != "E30_PRIMARY_TESTED_HEAD":
        raise ValueError("E30_PRIMARY_AUTHORITY_INVALID")
    if evidence["status"] == "FINAL":
        _require_sha(identity["tested_commit"], "commit")
        _require_sha(identity["tested_tree"], "sha256")
        expected_commit = tested_commit or current_commit
        expected_tree = tested_tree or current_tree
        if expected_commit and identity["tested_commit"] != expected_commit:
            raise ValueError("E30_PRIMARY_TESTED_COMMIT_MISMATCH")
        if expected_tree and identity["tested_tree"] != expected_tree:
            raise ValueError("E30_PRIMARY_TESTED_TREE_MISMATCH")
    elif evidence["status"] != "IN_PROGRESS":
        raise ValueError("E30_STATUS_INVALID")

    archive_summary = validate_archive_manifest(archive_path)
    wpdcr = _load_yaml(wpdcr_path)
    _require(wpdcr, "task_id", "status", "base_sections", "autonomous_remediation_ledger", "model_reasoning_and_execution_profile", "unknowns", "rollback", "coordination")
    if wpdcr["task_id"] != evidence["task_id"] or wpdcr["status"] not in {"IN_PROGRESS", "READY_FOR_GPT_REVIEW"}:
        raise ValueError("E30_WPDCR_ID_OR_STATUS_INVALID")
    if not isinstance(wpdcr["base_sections"], list) or not wpdcr["base_sections"]:
        raise ValueError("E30_WPDCR_BASE_SECTIONS_MISSING")
    for key in ("autonomous_remediation_ledger", "model_reasoning_and_execution_profile", "unknowns", "rollback", "coordination"):
        if not wpdcr[key]:
            raise ValueError("E30_WPDCR_OVERLAY_EMPTY:" + key)

    return {"status": evidence["status"], "archive": archive_summary, "tested_commit": identity["tested_commit"]}
