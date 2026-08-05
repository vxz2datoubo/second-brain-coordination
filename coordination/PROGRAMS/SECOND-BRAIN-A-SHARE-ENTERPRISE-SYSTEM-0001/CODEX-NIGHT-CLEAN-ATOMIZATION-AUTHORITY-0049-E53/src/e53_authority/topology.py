"""Fail-closed receipt topology validation used by E53 evidence tooling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Mapping, Sequence


class TopologyError(ValueError):
    pass


REQUIRED_RECEIPT_FIELDS = (
    "task_id",
    "route_epoch",
    "base_sha",
    "plan_sha",
    "tested_sha",
    "receipt_sha",
    "workflow",
    "tested_run_id",
    "receipt_run_id",
    "completion_signal",
)


def validate_receipt_fields(receipt: Mapping[str, object]) -> None:
    missing = [field for field in REQUIRED_RECEIPT_FIELDS if not isinstance(receipt.get(field), str) or not str(receipt[field]).strip()]
    placeholders = [field for field in REQUIRED_RECEIPT_FIELDS if str(receipt.get(field, "")).lower() in {"pending", "tbd", "unknown", "placeholder"}]
    if missing or placeholders:
        raise TopologyError(f"receipt is incomplete: missing={missing}, placeholders={placeholders}")


@dataclass(frozen=True, slots=True)
class ReceiptTopologyReport:
    receipt_sha: str
    head_sha: str
    changed_paths: tuple[str, ...]
    receipt_only: bool
    final_head: bool


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=False, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise TopologyError(result.stderr.strip() or "git topology command failed")
    return result.stdout.strip()


def verify_final_receipt(repo: Path, receipt_sha: str, allowed_paths: Sequence[str]) -> ReceiptTopologyReport:
    parent = _git(repo, "rev-parse", f"{receipt_sha}^")
    paths = tuple(sorted(path for path in _git(repo, "diff", "--name-only", f"{parent}..{receipt_sha}").splitlines() if path))
    allowed = set(allowed_paths)
    receipt_only = bool(paths) and set(paths).issubset(allowed)
    head = _git(repo, "rev-parse", "HEAD")
    return ReceiptTopologyReport(receipt_sha, head, paths, receipt_only, receipt_sha == head)
