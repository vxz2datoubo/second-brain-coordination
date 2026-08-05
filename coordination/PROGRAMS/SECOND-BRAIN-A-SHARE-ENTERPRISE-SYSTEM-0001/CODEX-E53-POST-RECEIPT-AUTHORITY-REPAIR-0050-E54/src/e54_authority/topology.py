"""Strict final-receipt shape validation for public-safe delivery evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Mapping, Sequence

from .authority import AuthorityError


SHA40 = re.compile(r"^[0-9a-f]{40}$")
REQUIRED = ("task_id", "route_epoch", "base_sha", "plan_sha", "tested_sha", "receipt_sha", "workflow", "tested_run_id", "receipt_run_id", "completion_signal", "external_receipt_binding")


def _require_sha(receipt: Mapping[str, object], field: str) -> None:
    value = receipt.get(field)
    if not isinstance(value, str) or not SHA40.fullmatch(value):
        raise AuthorityError(f"receipt {field} must be a lowercase SHA-40")


def validate_receipt_fields(receipt: Mapping[str, object], *, task_id: str, completion_signal: str, workflow: str, expected_artifact_count: int = 6) -> None:
    missing = [field for field in REQUIRED if field not in receipt]
    if missing:
        raise AuthorityError(f"receipt is missing required fields: {missing}")
    if receipt.get("task_id") != task_id or receipt.get("completion_signal") != completion_signal or receipt.get("workflow") != workflow:
        raise AuthorityError("receipt task, completion signal, or workflow identity differs from route")
    if not isinstance(receipt.get("route_epoch"), int) or int(receipt["route_epoch"]) < 1:
        raise AuthorityError("receipt route epoch must be a positive integer")
    for field in ("base_sha", "plan_sha", "tested_sha", "receipt_sha"):
        _require_sha(receipt, field)
    for field in ("tested_run_id", "receipt_run_id"):
        if not isinstance(receipt.get(field), int) or int(receipt[field]) <= 0:
            raise AuthorityError(f"receipt {field} must be a positive numeric run id")
    binding = receipt["external_receipt_binding"]
    if not isinstance(binding, Mapping):
        raise AuthorityError("receipt external binding must be an object")
    if binding.get("head_sha") != receipt["receipt_sha"]:
        raise AuthorityError("external binding must refer to the exact receipt head")
    _require_sha(binding, "head_sha")
    artifact_ids = binding.get("canonical_artifact_ids")
    if not isinstance(artifact_ids, list) or len(artifact_ids) != expected_artifact_count or any(not isinstance(item, int) or item <= 0 for item in artifact_ids):
        raise AuthorityError("external binding must contain the exact canonical artifact id count")
    if len(set(artifact_ids)) != len(artifact_ids):
        raise AuthorityError("external binding artifact IDs must be unique")
    digest_value = binding.get("compare_artifact_sha256")
    if not isinstance(digest_value, str) or not re.fullmatch(r"[0-9a-f]{64}", digest_value):
        raise AuthorityError("external binding requires a SHA-256 compare artifact digest")


@dataclass(frozen=True, slots=True)
class ReceiptTopologyReport:
    receipt_sha: str
    head_sha: str
    parent_sha: str
    changed_paths: tuple[str, ...]
    receipt_only: bool
    final_head: bool


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="strict", check=False)
    if result.returncode != 0:
        raise AuthorityError(result.stderr.strip() or "git topology command failed")
    return result.stdout.strip()


def verify_final_receipt(repo: Path, receipt_sha: str, allowed_paths: Sequence[str]) -> ReceiptTopologyReport:
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
    return ReceiptTopologyReport(receipt_sha, head, parent, changed, True, receipt_sha == head)
