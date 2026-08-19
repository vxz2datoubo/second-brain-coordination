"""Exact base-plan-tested-receipt topology and external-anchor validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Mapping, Sequence

from .authority import AuthorityError
from .provider import SHA40


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="strict", check=False)
    if result.returncode != 0:
        raise AuthorityError(result.stderr.strip() or f"git command failed: {' '.join(args)}")
    return result.stdout.strip()


def _ancestor(repo: Path, older: str, newer: str) -> bool:
    result = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", older, newer], capture_output=True, check=False)
    return result.returncode == 0


@dataclass(frozen=True, slots=True)
class RouteExpectation:
    task_id: str
    route_epoch: int
    issue: int
    pull_request: int
    branch: str
    base_sha: str
    plan_sha: str
    workflow: str
    completion_signal: str
    receipt_allowlist: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReceiptTopologyReport:
    receipt_sha: str
    parent_sha: str
    tree_sha: str
    changed_paths: tuple[str, ...]
    externally_bound: bool


def _require_exact_receipt(receipt: Mapping[str, object], expected: RouteExpectation) -> None:
    required = {
        "task_id", "route_epoch", "issue", "pull_request", "branch", "base_sha", "plan_sha", "tested_sha", "workflow", "completion_signal", "receipt_paths",
    }
    missing = required - set(receipt)
    if missing:
        raise AuthorityError(f"receipt is missing fields: {sorted(missing)}")
    for field, value in (
        ("task_id", expected.task_id), ("route_epoch", expected.route_epoch), ("issue", expected.issue), ("pull_request", expected.pull_request),
        ("branch", expected.branch), ("base_sha", expected.base_sha), ("plan_sha", expected.plan_sha), ("workflow", expected.workflow),
        ("completion_signal", expected.completion_signal),
    ):
        if receipt.get(field) != value:
            raise AuthorityError(f"receipt {field} differs from the route expectation")
    if not isinstance(receipt["tested_sha"], str) or not SHA40.fullmatch(receipt["tested_sha"]):
        raise AuthorityError("receipt tested_sha must be a lowercase SHA-40")
    paths = receipt["receipt_paths"]
    if not isinstance(paths, list) or tuple(sorted(paths)) != tuple(sorted(expected.receipt_allowlist)):
        raise AuthorityError("receipt must declare the exact receipt-only allowlist")


def _require_external_anchor(anchor: Mapping[str, object], *, receipt_sha: str, parent: str, tree: str, expected: RouteExpectation) -> None:
    required = {"task_id", "route_epoch", "issue", "pull_request", "branch", "workflow", "completion_signal", "receipt_head_sha", "receipt_parent_sha", "receipt_tree_sha", "provider_compare_sha256"}
    missing = required - set(anchor)
    if missing:
        raise AuthorityError(f"external anchor missing fields: {sorted(missing)}")
    for field, value in (
        ("task_id", expected.task_id), ("route_epoch", expected.route_epoch), ("issue", expected.issue), ("pull_request", expected.pull_request),
        ("branch", expected.branch), ("workflow", expected.workflow), ("completion_signal", expected.completion_signal),
        ("receipt_head_sha", receipt_sha), ("receipt_parent_sha", parent), ("receipt_tree_sha", tree),
    ):
        if anchor.get(field) != value:
            raise AuthorityError(f"external anchor {field} differs from observed topology or route")
    value = anchor["provider_compare_sha256"]
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise AuthorityError("external anchor provider compare digest is invalid")


def verify_final_receipt(
    repo: Path,
    receipt_sha: str,
    expected: RouteExpectation,
    receipt: Mapping[str, object],
    external_anchor: Mapping[str, object],
) -> ReceiptTopologyReport:
    if not SHA40.fullmatch(receipt_sha):
        raise AuthorityError("receipt SHA must be a lowercase SHA-40")
    _require_exact_receipt(receipt, expected)
    parent = _git(repo, "rev-parse", f"{receipt_sha}^")
    if parent != receipt["tested_sha"]:
        raise AuthorityError("observed receipt parent is not the tested head")
    for commit in (expected.base_sha, expected.plan_sha, receipt["tested_sha"]):
        if not SHA40.fullmatch(str(commit)):
            raise AuthorityError("route topology includes an invalid SHA")
    if not _ancestor(repo, expected.base_sha, expected.plan_sha) or not _ancestor(repo, expected.plan_sha, receipt["tested_sha"]):
        raise AuthorityError("base-plan-tested ancestry is incomplete")
    head = _git(repo, "rev-parse", "HEAD")
    if head != receipt_sha:
        raise AuthorityError("receipt must be the final observed head")
    changed = tuple(sorted(item for item in _git(repo, "diff", "--name-only", f"{parent}..{receipt_sha}").splitlines() if item))
    if changed != tuple(sorted(expected.receipt_allowlist)):
        raise AuthorityError("receipt changed paths do not exactly equal the allowlist")
    tree = _git(repo, "rev-parse", f"{receipt_sha}^{{tree}}")
    _require_external_anchor(external_anchor, receipt_sha=receipt_sha, parent=parent, tree=tree, expected=expected)
    return ReceiptTopologyReport(receipt_sha, parent, tree, changed, True)
