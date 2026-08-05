"""Strict final-receipt shape validation for public-safe delivery evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Mapping, Sequence

from .authority import AuthorityError


SHA40 = re.compile(r"^[0-9a-f]{40}$")
REQUIRED = ("task_id", "route_epoch", "base_sha", "plan_sha", "tested_sha", "workflow", "tested_run_id", "completion_signal", "external_receipt_binding")
EXTERNAL_BINDING_SCHEMA = "external-receipt-head-v1"
EXTERNAL_BINDING_FIELDS = (
    "schema",
    "issue",
    "pull_request",
    "receipt_parent_sha",
    "required_anchor_fields",
)
EXTERNAL_ANCHOR_FIELDS = (
    "schema",
    "task_id",
    "route_epoch",
    "issue",
    "pull_request",
    "completion_signal",
    "receipt_head_sha",
    "receipt_tree_sha",
    "receipt_parent_sha",
    "receipt_run_id",
    "canonical_artifact_ids",
    "environment_artifact_ids",
    "compare_artifact_id",
    "compare_artifact_sha256",
)


def _require_sha(receipt: Mapping[str, object], field: str) -> None:
    value = receipt.get(field)
    if not isinstance(value, str) or not SHA40.fullmatch(value):
        raise AuthorityError(f"receipt {field} must be a lowercase SHA-40")


def _require_positive_int(value: object, name: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise AuthorityError(f"{name} must be a positive integer")
    return value


def _validate_artifact_ids(value: object, name: str, expected_artifact_count: int) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != expected_artifact_count:
        raise AuthorityError(f"{name} must contain the exact artifact id count")
    if any(not isinstance(item, int) or item <= 0 for item in value) or len(set(value)) != len(value):
        raise AuthorityError(f"{name} must contain unique positive artifact IDs")
    return tuple(value)


def validate_receipt_fields(
    receipt: Mapping[str, object],
    *,
    task_id: str,
    completion_signal: str,
    workflow: str,
    issue: int | None = None,
    pull_request: int | None = None,
) -> None:
    missing = [field for field in REQUIRED if field not in receipt]
    if missing:
        raise AuthorityError(f"receipt is missing required fields: {missing}")
    if receipt.get("task_id") != task_id or receipt.get("completion_signal") != completion_signal or receipt.get("workflow") != workflow:
        raise AuthorityError("receipt task, completion signal, or workflow identity differs from route")
    if not isinstance(receipt.get("route_epoch"), int) or int(receipt["route_epoch"]) < 1:
        raise AuthorityError("receipt route epoch must be a positive integer")
    for field in ("base_sha", "plan_sha", "tested_sha"):
        _require_sha(receipt, field)
    _require_positive_int(receipt.get("tested_run_id"), "receipt tested_run_id")
    if any(field in receipt for field in ("receipt_sha", "receipt_run_id")):
        raise AuthorityError("receipt body must not self-reference a receipt commit or Provider run")
    binding = receipt["external_receipt_binding"]
    if not isinstance(binding, Mapping):
        raise AuthorityError("receipt external binding must be an object")
    missing_binding = [field for field in EXTERNAL_BINDING_FIELDS if field not in binding]
    if missing_binding:
        raise AuthorityError(f"receipt external binding is missing fields: {missing_binding}")
    if binding.get("schema") != EXTERNAL_BINDING_SCHEMA:
        raise AuthorityError("receipt external binding schema differs from the approved external schema")
    binding_issue = _require_positive_int(binding.get("issue"), "receipt binding issue")
    binding_pr = _require_positive_int(binding.get("pull_request"), "receipt binding pull_request")
    if issue is not None and binding_issue != issue:
        raise AuthorityError("receipt binding issue differs from route")
    if pull_request is not None and binding_pr != pull_request:
        raise AuthorityError("receipt binding pull request differs from route")
    if binding.get("receipt_parent_sha") != receipt["tested_sha"]:
        raise AuthorityError("receipt binding parent must equal the tested head")
    _require_sha(binding, "receipt_parent_sha")
    required_anchor_fields = binding.get("required_anchor_fields")
    if not isinstance(required_anchor_fields, list) or tuple(required_anchor_fields) != EXTERNAL_ANCHOR_FIELDS:
        raise AuthorityError("receipt binding must publish the exact external anchor field contract")


def validate_external_receipt_anchor(
    receipt: Mapping[str, object],
    anchor: Mapping[str, object],
    *,
    receipt_sha: str | None = None,
    receipt_tree_sha: str | None = None,
    expected_artifact_count: int = 6,
) -> None:
    """Validate the post-push anchor that cannot safely live inside its own receipt commit."""
    binding = receipt.get("external_receipt_binding")
    if not isinstance(binding, Mapping):
        raise AuthorityError("receipt external binding must be an object before anchor validation")
    missing = [field for field in EXTERNAL_ANCHOR_FIELDS if field not in anchor]
    if missing:
        raise AuthorityError(f"external receipt anchor is missing fields: {missing}")
    if anchor.get("schema") != EXTERNAL_BINDING_SCHEMA:
        raise AuthorityError("external receipt anchor schema differs from receipt binding")
    if anchor.get("task_id") != receipt.get("task_id") or anchor.get("route_epoch") != receipt.get("route_epoch") or anchor.get("completion_signal") != receipt.get("completion_signal"):
        raise AuthorityError("external receipt anchor identity differs from receipt")
    if anchor.get("issue") != binding.get("issue") or anchor.get("pull_request") != binding.get("pull_request"):
        raise AuthorityError("external receipt anchor route differs from receipt binding")
    if anchor.get("receipt_parent_sha") != receipt.get("tested_sha"):
        raise AuthorityError("external receipt anchor parent differs from tested head")
    for field in ("receipt_head_sha", "receipt_tree_sha", "receipt_parent_sha"):
        _require_sha(anchor, field)
    if receipt_sha is not None and anchor.get("receipt_head_sha") != receipt_sha:
        raise AuthorityError("external receipt anchor head differs from the observed receipt commit")
    if receipt_tree_sha is not None and anchor.get("receipt_tree_sha") != receipt_tree_sha:
        raise AuthorityError("external receipt anchor tree differs from the observed receipt tree")
    _require_positive_int(anchor.get("receipt_run_id"), "external receipt anchor receipt_run_id")
    canonical_ids = _validate_artifact_ids(anchor.get("canonical_artifact_ids"), "external receipt anchor canonical_artifact_ids", expected_artifact_count)
    environment_ids = _validate_artifact_ids(anchor.get("environment_artifact_ids"), "external receipt anchor environment_artifact_ids", expected_artifact_count)
    if set(canonical_ids).intersection(environment_ids):
        raise AuthorityError("external receipt anchor must keep canonical and environment artifact IDs distinct")
    _require_positive_int(anchor.get("compare_artifact_id"), "external receipt anchor compare_artifact_id")
    digest_value = anchor.get("compare_artifact_sha256")
    if not isinstance(digest_value, str) or not re.fullmatch(r"[0-9a-f]{64}", digest_value):
        raise AuthorityError("external receipt anchor requires a SHA-256 compare artifact digest")


@dataclass(frozen=True, slots=True)
class ReceiptTopologyReport:
    receipt_sha: str
    head_sha: str
    parent_sha: str
    changed_paths: tuple[str, ...]
    receipt_only: bool
    final_head: bool
    tree_sha: str
    externally_anchored: bool


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="strict", check=False)
    if result.returncode != 0:
        raise AuthorityError(result.stderr.strip() or "git topology command failed")
    return result.stdout.strip()


def verify_final_receipt(
    repo: Path,
    receipt_sha: str,
    allowed_paths: Sequence[str],
    *,
    receipt: Mapping[str, object] | None = None,
    external_anchor: Mapping[str, object] | None = None,
) -> ReceiptTopologyReport:
    if not SHA40.fullmatch(receipt_sha):
        raise AuthorityError("receipt SHA must be a lowercase SHA-40")
    parent = _git(repo, "rev-parse", f"{receipt_sha}^")
    changed = tuple(sorted(item for item in _git(repo, "diff", "--name-only", f"{parent}..{receipt_sha}").splitlines() if item))
    allowed = set(allowed_paths)
    if not changed or not set(changed).issubset(allowed):
        raise AuthorityError("receipt commit contains a path outside its receipt-only allowlist")
    head = _git(repo, "rev-parse", "HEAD")
    if head != receipt_sha:
        raise AuthorityError("receipt commit is not the current final head")
    tree = _git(repo, "rev-parse", f"{receipt_sha}^{{tree}}")
    if (receipt is None) != (external_anchor is None):
        raise AuthorityError("receipt and external anchor must be supplied together")
    if receipt is not None and external_anchor is not None:
        validate_external_receipt_anchor(receipt, external_anchor, receipt_sha=receipt_sha, receipt_tree_sha=tree)
    return ReceiptTopologyReport(receipt_sha, head, parent, changed, True, receipt_sha == head, tree, external_anchor is not None)
