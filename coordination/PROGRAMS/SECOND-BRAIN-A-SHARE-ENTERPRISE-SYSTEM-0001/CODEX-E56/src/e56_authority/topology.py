"""Observed Git topology checks for E56 plan, tested and receipt authority."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Mapping, Sequence

from .authority import AuthorityError


SHA40 = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True, slots=True)
class RouteTopology:
    base_sha: str
    plan_sha: str
    plan_path: str
    tested_sha: str
    receipt_sha: str
    receipt_allowlist: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExternalProviderAnchor:
    tested_run_id: int
    receipt_run_id: int
    workflow: str
    branch: str
    tested_head: str
    receipt_head: str
    matrix_job_ids: tuple[int, ...]
    compare_job_id: int
    artifact_ids: tuple[int, ...]
    artifact_names: tuple[str, ...]
    archive_sha256: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TopologyReport:
    plan_parent: str
    plan_paths: tuple[str, ...]
    chain: tuple[str, ...]
    receipt_parent: str
    receipt_paths: tuple[str, ...]
    receipt_tree: str


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="strict", check=False)
    if result.returncode:
        raise AuthorityError(result.stderr.strip() or f"git failed: {' '.join(args)}")
    return result.stdout.strip()


def _one_parent(repo: Path, commit: str) -> str:
    parents = tuple(item for item in _git(repo, "show", "-s", "--format=%P", commit).split() if item)
    if len(parents) != 1:
        raise AuthorityError("topology must be strictly linear; merge and root commits are forbidden after base")
    return parents[0]


def _checked_sha(value: str, label: str) -> None:
    if not SHA40.fullmatch(value):
        raise AuthorityError(f"{label} must be a lowercase full SHA-40")


def verify_topology(repo: Path, route: RouteTopology, anchor: ExternalProviderAnchor) -> TopologyReport:
    for label, value in (("base", route.base_sha), ("plan", route.plan_sha), ("tested", route.tested_sha), ("receipt", route.receipt_sha)):
        _checked_sha(value, label)
    if _one_parent(repo, route.plan_sha) != route.base_sha:
        raise AuthorityError("plan parent is not the exact route base")
    plan_paths = tuple(sorted(item for item in _git(repo, "diff", "--name-only", f"{route.base_sha}..{route.plan_sha}").splitlines() if item))
    if plan_paths != (route.plan_path,):
        raise AuthorityError("first plan commit must change exactly the expected project-plan path")
    chain = tuple(item for item in _git(repo, "rev-list", "--reverse", f"{route.base_sha}..{route.receipt_sha}").splitlines() if item)
    if not chain or chain[0] != route.plan_sha or route.tested_sha not in chain or chain[-1] != route.receipt_sha:
        raise AuthorityError("base-to-receipt chain does not contain exact plan, tested and receipt commits")
    previous = route.plan_sha
    for commit in chain[1:]:
        if _one_parent(repo, commit) != previous:
            raise AuthorityError("base-to-receipt chain is not direct and linear")
        previous = commit
    receipt_parent = _one_parent(repo, route.receipt_sha)
    if receipt_parent != route.tested_sha:
        raise AuthorityError("receipt must be the direct child of tested head")
    if _git(repo, "rev-parse", "HEAD") != route.receipt_sha:
        raise AuthorityError("current head must equal the final receipt")
    receipt_paths = tuple(sorted(item for item in _git(repo, "diff", "--name-only", f"{receipt_parent}..{route.receipt_sha}").splitlines() if item))
    if receipt_paths != tuple(sorted(route.receipt_allowlist)):
        raise AuthorityError("receipt paths do not exactly equal receipt allowlist")
    if any(not _git(repo, "show", f"{route.receipt_sha}:{path}") for path in receipt_paths):
        raise AuthorityError("receipt-only files must be nonempty")
    if anchor.tested_head != route.tested_sha or anchor.receipt_head != route.receipt_sha:
        raise AuthorityError("provider anchor heads differ from observed route")
    if len(anchor.matrix_job_ids) != 6 or len(set(anchor.matrix_job_ids)) != 6 or not isinstance(anchor.compare_job_id, int):
        raise AuthorityError("anchor must bind exactly six matrix jobs and one distinct compare job")
    if len(anchor.artifact_ids) != 13 or len(set(anchor.artifact_ids)) != 13 or len(anchor.artifact_names) != 13 or len(anchor.archive_sha256) != 13:
        raise AuthorityError("anchor must bind exactly thirteen unique artifact identities and archive digests")
    if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in anchor.archive_sha256):
        raise AuthorityError("archive digest is invalid")
    return TopologyReport(_one_parent(repo, route.plan_sha), plan_paths, chain, receipt_parent, receipt_paths, _git(repo, "rev-parse", f"{route.receipt_sha}^{{tree}}"))
