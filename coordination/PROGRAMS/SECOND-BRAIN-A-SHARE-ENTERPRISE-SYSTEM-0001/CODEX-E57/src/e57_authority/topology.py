"""Actual Git route and history-hygiene checks for E57."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Iterable

from .core import AuthorityError
from .provider import DualProviderEvidence, ProviderContract, verify_dual_provider_evidence


SHA40 = re.compile(r"^[0-9a-f]{40}$")
GENERATED_OR_RUNTIME = re.compile(r"(?:^|/)(?:__pycache__/|.*\.py[co]$|.*\.sqlite(?:3)?$|.*\.jsonl$|.*\.log$)")


@dataclass(frozen=True, slots=True)
class RouteTopology:
    base_sha: str
    plan_sha: str
    plan_path: str
    tested_sha: str
    receipt_sha: str
    receipt_allowlist: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HistoryHygieneReport:
    all_history_paths: tuple[str, ...]
    generated_or_runtime_paths: tuple[str, ...]
    outside_allowlist_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TopologyReport:
    plan_parent: str
    plan_paths: tuple[str, ...]
    chain: tuple[str, ...]
    receipt_parent: str
    receipt_paths: tuple[str, ...]
    receipt_tree: str
    hygiene: HistoryHygieneReport


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="strict", check=False)
    if completed.returncode:
        raise AuthorityError(completed.stderr.strip() or f"git command failed: {' '.join(args)}")
    return completed.stdout.strip()


def _sha(value: str, label: str) -> None:
    if not SHA40.fullmatch(value):
        raise AuthorityError(f"{label} must be a lowercase full SHA-40")


def _one_parent(repo: Path, commit: str) -> str:
    parents = tuple(item for item in _git(repo, "show", "-s", "--format=%P", commit).split() if item)
    if len(parents) != 1:
        raise AuthorityError("E57 route must be linear")
    return parents[0]


def verify_plan_commit(repo: Path, *, base_sha: str, plan_sha: str, plan_path: str) -> tuple[str, tuple[str, ...]]:
    _sha(base_sha, "base")
    _sha(plan_sha, "plan")
    parent = _one_parent(repo, plan_sha)
    if parent != base_sha:
        raise AuthorityError("plan parent differs from the claimed base")
    paths = tuple(sorted(item for item in _git(repo, "diff", "--name-only", f"{base_sha}..{plan_sha}").splitlines() if item))
    if paths != (plan_path,):
        raise AuthorityError("plan commit must change exactly the declared plan path")
    return parent, paths


def inspect_history_hygiene(repo: Path, *, base_sha: str, end_sha: str, allowed_prefixes: Iterable[str]) -> HistoryHygieneReport:
    _sha(base_sha, "hygiene base")
    _sha(end_sha, "hygiene end")
    prefixes = tuple(allowed_prefixes)
    output = _git(repo, "log", "--format=", "--name-status", f"{base_sha}..{end_sha}")
    paths: set[str] = set()
    for line in output.splitlines():
        parts = line.split("\t")
        if not parts or not parts[0] or parts[0].startswith(" "):
            continue
        if parts[0][0] not in {"A", "M", "D", "R", "C", "T"}:
            continue
        for path in parts[1:]:
            if path:
                paths.add(path)
    ordered = tuple(sorted(paths))
    generated = tuple(path for path in ordered if GENERATED_OR_RUNTIME.search(path))
    outside = tuple(path for path in ordered if not any(path.startswith(prefix) for prefix in prefixes))
    return HistoryHygieneReport(ordered, generated, outside)


def verify_final_route(
    repo: Path,
    route: RouteTopology,
    provider_evidence: DualProviderEvidence,
    provider_contract: ProviderContract,
    *,
    allowed_history_prefixes: tuple[str, ...],
) -> TopologyReport:
    for label, value in (("base", route.base_sha), ("plan", route.plan_sha), ("tested", route.tested_sha), ("receipt", route.receipt_sha)):
        _sha(value, label)
    plan_parent, plan_paths = verify_plan_commit(repo, base_sha=route.base_sha, plan_sha=route.plan_sha, plan_path=route.plan_path)
    chain = tuple(item for item in _git(repo, "rev-list", "--reverse", f"{route.base_sha}..{route.receipt_sha}").splitlines() if item)
    if not chain or chain[0] != route.plan_sha or route.tested_sha not in chain or chain[-1] != route.receipt_sha:
        raise AuthorityError("route chain omits its declared plan, tested, or receipt commit")
    previous = route.plan_sha
    for commit in chain[1:]:
        if _one_parent(repo, commit) != previous:
            raise AuthorityError("route chain is not direct and linear")
        previous = commit
    receipt_parent = _one_parent(repo, route.receipt_sha)
    if receipt_parent != route.tested_sha:
        raise AuthorityError("receipt must be the direct child of tested head")
    if _git(repo, "rev-parse", "HEAD") != route.receipt_sha:
        raise AuthorityError("current head must equal receipt head")
    receipt_paths = tuple(sorted(item for item in _git(repo, "diff", "--name-only", f"{receipt_parent}..{route.receipt_sha}").splitlines() if item))
    if receipt_paths != tuple(sorted(route.receipt_allowlist)):
        raise AuthorityError("receipt path set differs from its exact allowlist")
    for path in receipt_paths:
        if not _git(repo, "show", f"{route.receipt_sha}:{path}"):
            raise AuthorityError("receipt paths must be nonempty")
    verify_dual_provider_evidence(provider_evidence, provider_contract, tested_head=route.tested_sha, receipt_head=route.receipt_sha)
    hygiene = inspect_history_hygiene(repo, base_sha=route.base_sha, end_sha=route.receipt_sha, allowed_prefixes=allowed_history_prefixes)
    if hygiene.outside_allowlist_paths:
        raise AuthorityError("actual route history changed paths outside its allowlist")
    if hygiene.generated_or_runtime_paths:
        raise AuthorityError("actual route history contains generated or runtime artifacts")
    return TopologyReport(plan_parent, plan_paths, chain, receipt_parent, receipt_paths, _git(repo, "rev-parse", f"{route.receipt_sha}^{{tree}}"), hygiene)
