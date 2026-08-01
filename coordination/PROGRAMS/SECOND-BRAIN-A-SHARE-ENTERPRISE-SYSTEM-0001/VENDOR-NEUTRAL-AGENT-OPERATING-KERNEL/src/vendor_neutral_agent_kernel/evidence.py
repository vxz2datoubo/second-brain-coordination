"""Fail-closed validation for the public E30/E31 evidence contracts."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

import yaml


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
E31_TASK = "CODEX-PEOS-0010-E30-COMMITTED-WPDCR-ARCHIVE-ROOT-AND-RECEIPT-ANCHOR-TRUTH-CLOSURE-0023-E31"
E31_SIGNAL = "CODEX_E31_PEOS_0010_COMMITTED_WPDCR_ARCHIVE_ROOT_AND_RECEIPT_ANCHOR_TRUTH_READY_FOR_GPT_REVIEW"
E31_BOUNDARY = "PUBLIC_SAFE / CANDIDATE_ONLY / DISABLED / research_only / NO_TRADE"
E31_SECTION_NAMES = (
    "task_result_and_current_scope",
    "verified_remote_and_local_facts",
    "work_process_and_difficulty",
    "plan_vs_actual_and_failures",
    "changed_files_and_tests",
    "discoveries_and_opportunities",
    "unknowns_and_negative_results",
    "coordination_and_system_feedback",
    "rollback_and_next_gate",
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("EVIDENCE_JSON_OBJECT_REQUIRED:" + path.name)
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("EVIDENCE_YAML_OBJECT_REQUIRED:" + path.name)
    return value


def _require(mapping: dict[str, Any], *keys: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise ValueError("EVIDENCE_REQUIRED_FIELD_MISSING:" + ",".join(missing))


def _require_sha(value: Any, kind: str) -> None:
    pattern = SHA40_RE if kind in {"commit", "tree"} else SHA256_RE
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"EVIDENCE_INVALID_{kind.upper()}_SHA")


def _reject_unresolved_marker(value: Any, label: str) -> None:
    text = json.dumps(value, ensure_ascii=True, sort_keys=True) if not isinstance(value, str) else value
    if re.search(r"\bPENDING(?:_[A-Z0-9_]+)?\b|UNRESOLVED|<root>|PLACEHOLDER", text, re.IGNORECASE):
        raise ValueError("E31_UNRESOLVED_MARKER:" + label)


def _safe_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")) or ":" in value:
        raise ValueError("E31_EXTERNAL_OR_EMPTY_PATH:" + label)
    parts = value.replace("\\", "/").split("/")
    if ".." in parts or any(not part for part in parts):
        raise ValueError("E31_UNSAFE_RELATIVE_PATH:" + label)
    return "/".join(parts)


def _artifact_set_hash(entries: list[tuple[str, int, str]]) -> str:
    canonical = "".join(f"{path}\t{size}\t{digest}\n" for path, size, digest in sorted(entries))
    return sha256(canonical.encode("utf-8")).hexdigest()


def _content_tree_hash(entries: list[tuple[str, int, str]]) -> str:
    canonical = "".join(f"{path}\0{size}\0{digest}\n" for path, size, digest in sorted(entries))
    return sha256(canonical.encode("utf-8")).hexdigest()


def _validate_artifacts(artifacts: Any, expected_paths: tuple[str, ...], root_id: str) -> tuple[tuple[str, int, str], ...]:
    if not isinstance(artifacts, list) or len(artifacts) < 2:
        raise ValueError("E31_FULL_ARTIFACT_SURFACE_REQUIRED:" + root_id)
    entries: list[tuple[str, int, str]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("E31_ARTIFACT_OBJECT_REQUIRED:" + root_id)
        _require(artifact, "path", "size", "sha256")
        path = _safe_relative_path(artifact["path"], root_id)
        if not isinstance(artifact["size"], int) or artifact["size"] < 0:
            raise ValueError("E31_ARTIFACT_SIZE_INVALID:" + root_id)
        _require_sha(artifact["sha256"], "sha256")
        entries.append((path, artifact["size"], artifact["sha256"]))
    canonical = tuple(sorted(entries))
    if len(canonical) != len(set(canonical)):
        raise ValueError("E31_ARTIFACT_DUPLICATE:" + root_id)
    paths = tuple(path for path, _, _ in canonical)
    if paths != expected_paths:
        raise ValueError("E31_DECLARED_ARTIFACT_SURFACE_MISMATCH:" + root_id)
    return canonical


def validate_archive_manifest(path: Path) -> dict[str, Any]:
    """Validate the E31 archive contract; retain the E30 name for callers."""
    manifest = _load_yaml(path)
    if manifest.get("schema_version") == "VNAK_E31_ARCHIVE_PROVENANCE_v1":
        return validate_e31_archive_manifest(path)

    # Historical E30 validation remains available for old fixtures only.
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


def validate_e31_archive_manifest(path: Path) -> dict[str, Any]:
    manifest = _load_yaml(path)
    _require(manifest, "schema_version", "task_id", "status", "required_root_count", "tested_identity", "declared_artifact_surface", "roots")
    if manifest["schema_version"] != "VNAK_E31_ARCHIVE_PROVENANCE_v1" or manifest["task_id"] != E31_TASK:
        raise ValueError("E31_ARCHIVE_IDENTITY_INVALID")
    if manifest["status"] != "FINAL":
        raise ValueError("E31_ARCHIVE_STATUS_NOT_FINAL")
    if manifest["required_root_count"] != 3 or not isinstance(manifest["roots"], list) or len(manifest["roots"]) != 3:
        raise ValueError("E31_ARCHIVE_ROOT_COUNT_INVALID")
    tested = manifest["tested_identity"]
    if not isinstance(tested, dict):
        raise ValueError("E31_TESTED_IDENTITY_OBJECT_REQUIRED")
    _require(tested, "authority", "tested_commit", "tested_tree", "source_run")
    if tested["authority"] != "E31_TESTED_SUBSTANTIVE_COMMIT":
        raise ValueError("E31_TESTED_AUTHORITY_INVALID")
    _require_sha(tested["tested_commit"], "commit")
    _require_sha(tested["tested_tree"], "tree")
    if not isinstance(tested["source_run"], (str, int)):
        raise ValueError("E31_TESTED_SOURCE_RUN_REQUIRED")

    surface = manifest["declared_artifact_surface"]
    if not isinstance(surface, dict):
        raise ValueError("E31_DECLARED_SURFACE_OBJECT_REQUIRED")
    _require(surface, "name", "path_count", "paths")
    if not isinstance(surface["name"], str) or not surface["name"]:
        raise ValueError("E31_DECLARED_SURFACE_NAME_REQUIRED")
    if not isinstance(surface["paths"], list) or surface["path_count"] != len(surface["paths"]):
        raise ValueError("E31_DECLARED_SURFACE_COUNT_INVALID")
    expected_paths = tuple(sorted({_safe_relative_path(item, "declared_surface") for item in surface["paths"]}))
    if len(expected_paths) < 2 or len(expected_paths) != len(surface["paths"]):
        raise ValueError("E31_DECLARED_SURFACE_TOO_SMALL_OR_DUPLICATE")

    root_ids: list[str] = []
    artifact_sets: list[tuple[tuple[str, int, str], ...]] = []
    archive_hashes: list[str] = []
    content_hashes: list[str] = []
    tree_hashes: list[str] = []
    path_hashes: list[str] = []
    for root in manifest["roots"]:
        if not isinstance(root, dict):
            raise ValueError("E31_ROOT_OBJECT_REQUIRED")
        _require(root, "root_id", "run_id", "job_id", "root_locator", "root_path_sha256", "archive_content_sha256", "archive_size_bytes", "archive_git_tree_sha", "archive_content_tree_sha256", "cwd", "command", "exit_code", "stdout_sha256", "stderr_sha256", "artifact_set_sha256", "artifacts")
        root_id = root["root_id"]
        if not isinstance(root_id, str) or not root_id or root_id in root_ids:
            raise ValueError("E31_ROOT_ID_DUPLICATE_OR_EMPTY")
        root_ids.append(root_id)
        for key in ("root_path_sha256", "archive_content_sha256", "archive_content_tree_sha256", "stdout_sha256", "stderr_sha256", "artifact_set_sha256"):
            _require_sha(root[key], "sha256")
        _require_sha(root["archive_git_tree_sha"], "tree")
        if not isinstance(root["run_id"], (str, int)) or not str(root["run_id"]):
            raise ValueError("E31_RUN_ID_REQUIRED")
        if not isinstance(root["job_id"], str) or not root["job_id"]:
            raise ValueError("E31_JOB_ID_REQUIRED")
        if not isinstance(root["root_locator"], str) or not root["root_locator"].startswith("github-actions://"):
            raise ValueError("E31_ROOT_LOCATOR_INVALID")
        if root["cwd"] != "." or not isinstance(root["command"], str):
            raise ValueError("E31_ROOT_COMMAND_CONTEXT_INVALID")
        command = root["command"]
        for token in ("./coordination/", "./.e31-changed-files.txt", "ci_verify.py", "--commit", "--tree", "--tested-commit", "--tested-tree"):
            if token not in command:
                raise ValueError("E31_ROOT_COMMAND_INCOMPLETE:" + token)
        _reject_unresolved_marker(command, root_id + ":command")
        if root["exit_code"] != 0:
            raise ValueError("E31_ROOT_NONZERO_EXIT")
        if not isinstance(root["archive_size_bytes"], int) or root["archive_size_bytes"] <= 0:
            raise ValueError("E31_ARCHIVE_SIZE_INVALID")
        entries = _validate_artifacts(root["artifacts"], expected_paths, root_id)
        if root["artifact_set_sha256"] != _artifact_set_hash(list(entries)):
            raise ValueError("E31_ARTIFACT_SET_HASH_INVALID")
        if root["archive_content_tree_sha256"] != _content_tree_hash(list(entries)):
            raise ValueError("E31_CONTENT_TREE_HASH_INVALID")
        artifact_sets.append(entries)
        archive_hashes.append(root["archive_content_sha256"])
        content_hashes.append(root["archive_content_tree_sha256"])
        tree_hashes.append(root["archive_git_tree_sha"])
        path_hashes.append(root["root_path_sha256"])
    if any(items != artifact_sets[0] for items in artifact_sets[1:]):
        raise ValueError("E31_ARTIFACT_SET_DRIFT")
    if len(set(archive_hashes)) != 1 or len(set(content_hashes)) != 1 or len(set(tree_hashes)) != 1:
        raise ValueError("E31_ARCHIVE_CONTENT_DRIFT")
    if len(set(path_hashes)) != 3:
        raise ValueError("E31_ROOT_PATH_IDENTITY_NOT_DISTINCT")
    return {"root_count": 3, "root_ids": tuple(root_ids), "artifact_count": len(artifact_sets[0]), "tested_commit": tested["tested_commit"]}


def _validate_semantic_wpdcr(path: Path) -> dict[str, Any]:
    wpdcr = _load_yaml(path)
    _require(wpdcr, "schema_version", "task_id", "route_epoch", "agent_id", "actual_executor", "reviewer", "status", "mode", "boundary", "base_sections", "autonomous_remediation_ledger", "model_reasoning_and_execution_profile", "unknowns", "negative_results", "coordination", "rollback")
    if wpdcr["task_id"] != E31_TASK or wpdcr["route_epoch"] != 32 or wpdcr["agent_id"] != "CODEX" or wpdcr["actual_executor"] != "CODEX" or wpdcr["reviewer"] != "GPT":
        raise ValueError("E31_WPDCR_IDENTITY_INVALID")
    if wpdcr["status"] not in {"IN_PROGRESS", "READY_FOR_GPT_REVIEW"} or wpdcr["mode"] != "target" or wpdcr["boundary"] != E31_BOUNDARY:
        raise ValueError("E31_WPDCR_STATUS_OR_BOUNDARY_INVALID")
    sections = wpdcr["base_sections"]
    if not isinstance(sections, dict):
        raise ValueError("E31_WPDCR_SECTIONS_MUST_BE_PAYLOADS")
    for name in E31_SECTION_NAMES:
        if name not in sections or not isinstance(sections[name], dict) or not sections[name]:
            raise ValueError("E31_WPDCR_SECTION_PAYLOAD_MISSING:" + name)
        if not any(value not in (None, "", [], {}, ()) for value in sections[name].values()):
            raise ValueError("E31_WPDCR_SECTION_SEMANTICALLY_EMPTY:" + name)
    for key in ("autonomous_remediation_ledger", "model_reasoning_and_execution_profile", "unknowns", "negative_results", "coordination", "rollback"):
        if not wpdcr[key]:
            raise ValueError("E31_WPDCR_OVERLAY_EMPTY:" + key)
    return {"section_count": len(E31_SECTION_NAMES), "status": wpdcr["status"]}


def validate_e31_evidence(
    root: Path,
    *,
    current_commit: str | None = None,
    current_tree: str | None = None,
    tested_commit: str | None = None,
    tested_tree: str | None = None,
) -> dict[str, Any]:
    evidence = _load_json(root / "E31-COMPLETION-EVIDENCE.json")
    _require(evidence, "schema", "task_id", "route_epoch", "status", "boundary", "completion_signal", "authority", "activation", "tested_parent_identity", "receipt_head_identity", "external_anchor")
    if evidence["schema"] != "VNAK_E31_COMPLETION_EVIDENCE_v1" or evidence["task_id"] != E31_TASK or evidence["route_epoch"] != 32:
        raise ValueError("E31_EVIDENCE_IDENTITY_INVALID")
    if evidence["boundary"] != E31_BOUNDARY or evidence["authority"] != "CANDIDATE_ONLY" or evidence["activation"] != "DISABLED" or evidence["completion_signal"] != E31_SIGNAL:
        raise ValueError("E31_BOUNDARY_AUTHORITY_OR_SIGNAL_INVALID")
    if evidence["status"] not in {"IN_PROGRESS", "FINAL"}:
        raise ValueError("E31_EVIDENCE_STATUS_INVALID")
    _reject_unresolved_marker(evidence, "completion_evidence")
    tested = evidence["tested_parent_identity"]
    receipt = evidence["receipt_head_identity"]
    if not isinstance(tested, dict) or not isinstance(receipt, dict):
        raise ValueError("E31_IDENTITY_OBJECTS_REQUIRED")
    _require(tested, "authority", "tested_commit", "tested_tree", "source_run")
    if tested["authority"] != "E31_TESTED_SUBSTANTIVE_COMMIT":
        raise ValueError("E31_TESTED_PARENT_AUTHORITY_INVALID")
    _require_sha(tested["tested_commit"], "commit")
    _require_sha(tested["tested_tree"], "tree")
    if evidence["status"] == "FINAL":
        _require(receipt, "authority", "binding", "parent_commit", "tested_parent_commit", "correction_chain")
        if receipt["authority"] != "E31_RECEIPT_HEAD" or receipt["binding"] != "CURRENT_PR_HEAD":
            raise ValueError("E31_RECEIPT_BINDING_INVALID")
        _require_sha(receipt["parent_commit"], "commit")
        _require_sha(receipt["tested_parent_commit"], "commit")
        if receipt["tested_parent_commit"] != tested["tested_commit"]:
            raise ValueError("E31_RECEIPT_TESTED_PARENT_MISMATCH")
        chain = receipt["correction_chain"]
        if not isinstance(chain, list) or not chain:
            raise ValueError("E31_RECEIPT_CORRECTION_CHAIN_INVALID")
        if any(not isinstance(item, str) or not SHA40_RE.fullmatch(item) for item in chain):
            raise ValueError("E31_RECEIPT_CORRECTION_CHAIN_SHA_INVALID")
        if chain[0] != tested["tested_commit"] or chain[-1] != receipt["parent_commit"]:
            raise ValueError("E31_RECEIPT_CORRECTION_CHAIN_ENDPOINT_MISMATCH")
        if not isinstance(evidence["external_anchor"], dict):
            raise ValueError("E31_EXTERNAL_ANCHOR_REQUIRED")
        _require(evidence["external_anchor"], "kind", "url", "binding")
        if evidence["external_anchor"]["kind"] != "GITHUB_PR_HEAD" or evidence["external_anchor"]["binding"] != "CURRENT_PR_HEAD":
            raise ValueError("E31_EXTERNAL_ANCHOR_INVALID")
        if not isinstance(evidence["external_anchor"]["url"], str) or not evidence["external_anchor"]["url"].startswith("https://github.com/"):
            raise ValueError("E31_EXTERNAL_ANCHOR_URL_INVALID")
        observed_commit = evidence["external_anchor"].get("observed_commit")
        observed_tree = evidence["external_anchor"].get("observed_tree")
        if observed_commit not in {None, "EXTERNAL_PR_HEAD"} and current_commit and current_commit != observed_commit:
            raise ValueError("E31_RECEIPT_EXTERNAL_COMMIT_MISMATCH")
        if observed_tree not in {None, "EXTERNAL_PR_HEAD"} and current_tree and current_tree != observed_tree:
            raise ValueError("E31_RECEIPT_EXTERNAL_TREE_MISMATCH")
        if tested_commit and tested["tested_commit"] != tested_commit:
            raise ValueError("E31_TESTED_COMMIT_MISMATCH")
        if tested_tree and tested["tested_tree"] != tested_tree:
            raise ValueError("E31_TESTED_TREE_MISMATCH")
    elif receipt.get("binding") not in {"CURRENT_PR_HEAD", "NOT_YET_BOUND"}:
        raise ValueError("E31_IN_PROGRESS_RECEIPT_BINDING_INVALID")

    archive_summary = validate_e31_archive_manifest(root / "E31-ARCHIVE-PROVENANCE-MATRIX.yaml")
    if archive_summary["tested_commit"] != tested["tested_commit"]:
        raise ValueError("E31_ARCHIVE_TESTED_COMMIT_MISMATCH")
    wpdcr_summary = _validate_semantic_wpdcr(root / "E31-WORK-PROCESS-AND-COORDINATION-REPORT.yaml")
    _reject_unresolved_marker(root.joinpath("E31-ARCHIVE-PROVENANCE-MATRIX.yaml").read_text(encoding="utf-8"), "archive_manifest")
    _reject_unresolved_marker(root.joinpath("E31-WORK-PROCESS-AND-COORDINATION-REPORT.yaml").read_text(encoding="utf-8"), "wpdcr")
    return {"status": evidence["status"], "archive": archive_summary, "wpdcr": wpdcr_summary, "tested_commit": tested["tested_commit"]}


def validate_e30_evidence(
    root: Path,
    *,
    current_commit: str | None = None,
    current_tree: str | None = None,
    tested_commit: str | None = None,
    tested_tree: str | None = None,
) -> dict[str, Any]:
    """Historical E30 contract retained for regression fixtures."""
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
    if evidence["boundary"] != E31_BOUNDARY:
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
        _require_sha(identity["tested_tree"], "tree")
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
    if not isinstance(wpdcr["base_sections"], (list, dict)) or not wpdcr["base_sections"]:
        raise ValueError("E30_WPDCR_BASE_SECTIONS_MISSING")
    for key in ("autonomous_remediation_ledger", "model_reasoning_and_execution_profile", "unknowns", "rollback", "coordination"):
        if not wpdcr[key]:
            raise ValueError("E30_WPDCR_OVERLAY_EMPTY:" + key)
    return {"status": evidence["status"], "archive": archive_summary, "tested_commit": identity["tested_commit"]}
