"""Versioned, parent-exact Git hygiene scanning for E56 delivery history."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
import subprocess
from typing import Sequence

from .authority import AuthorityError, stable_digest


_BUILTIN_GLOBS = (
    "**/__pycache__/**", "**/*.pyc", "**/*.pyo", "**/*.sqlite", "**/*.sqlite3", "**/*.db",
    "**/*.jsonl", "**/.env", "**/*.tmp", "**/node_modules/**", "**/provider-artifacts/**",
    "**/local-artifacts/**", "**/.pytest_cache/**", "**/.mypy_cache/**", "**/.ruff_cache/**",
)


@dataclass(frozen=True, slots=True)
class HygienePolicy:
    version: str
    forbidden_globs: tuple[str, ...]

    @property
    def identity(self) -> str:
        return stable_digest({"version": self.version, "forbidden_globs": self.forbidden_globs})

    @classmethod
    def default(cls) -> "HygienePolicy":
        return cls("e56-hygiene-v1", _BUILTIN_GLOBS)


@dataclass(frozen=True, slots=True)
class HistoryPath:
    commit_sha: str
    parent_sha: str | None
    change_kind: str
    path_role: str
    path: str
    forbidden: bool


@dataclass(frozen=True, slots=True)
class HygieneReport:
    policy_identity: str
    base_sha: str
    head_sha: str
    commits: tuple[str, ...]
    history_paths: tuple[HistoryPath, ...]
    introduced_forbidden: tuple[HistoryPath, ...]
    inherited_final_forbidden: tuple[str, ...]
    introduced_final_forbidden: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not self.introduced_forbidden and not self.introduced_final_forbidden


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="strict", check=False)
    if result.returncode:
        raise AuthorityError(result.stderr.strip() or f"git failed: {' '.join(args)}")
    return result.stdout


def is_forbidden(path: str, policy: HygienePolicy) -> bool:
    normalized = path.replace("\\", "/").strip("/")
    return any(fnmatchcase(normalized, pattern) or fnmatchcase("/" + normalized, pattern) for pattern in policy.forbidden_globs)


def _records_for_diff(repo: Path, commit: str, parent: str | None, policy: HygienePolicy) -> tuple[HistoryPath, ...]:
    args = ("diff-tree", "--no-commit-id", "--name-status", "-r", "-M", "-C", parent, commit) if parent else ("diff-tree", "--root", "--no-commit-id", "--name-status", "-r", "-M", "-C", commit)
    records: list[HistoryPath] = []
    for line in _git(repo, *args).splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            raise AuthorityError("unparseable Git name-status record")
        kind, paths = fields[0], fields[1:]
        if kind.startswith(("R", "C")):
            if len(paths) != 2:
                raise AuthorityError("rename/copy record must contain old and new paths")
            roles = ("old", "new")
        elif len(paths) == 1:
            roles = ("path",)
        else:
            raise AuthorityError("ordinary diff record must contain exactly one path")
        for role, path in zip(roles, paths):
            normalized = path.replace("\\", "/")
            records.append(HistoryPath(commit, parent, kind, role, normalized, is_forbidden(normalized, policy)))
    return tuple(records)


def scan_commit_range(repo: Path, base_sha: str, *, head: str = "HEAD", policy: HygienePolicy | None = None) -> HygieneReport:
    selected = policy or HygienePolicy.default()
    resolved = _git(repo, "rev-parse", head).strip()
    _git(repo, "merge-base", "--is-ancestor", base_sha, resolved)
    commits = tuple(item for item in _git(repo, "rev-list", "--reverse", f"{base_sha}..{resolved}").splitlines() if item)
    all_paths: list[HistoryPath] = []
    for commit in commits:
        parents = tuple(item for item in _git(repo, "show", "-s", "--format=%P", commit).split() if item)
        for parent in parents or (None,):
            all_paths.extend(_records_for_diff(repo, commit, parent, selected))
    base_tree = set(item for item in _git(repo, "ls-tree", "-r", "--name-only", base_sha).splitlines() if item)
    final_tree = set(item for item in _git(repo, "ls-tree", "-r", "--name-only", resolved).splitlines() if item)
    return HygieneReport(
        selected.identity,
        base_sha,
        resolved,
        commits,
        tuple(all_paths),
        tuple(item for item in all_paths if item.forbidden),
        tuple(sorted(path for path in final_tree & base_tree if is_forbidden(path, selected))),
        tuple(sorted(path for path in final_tree - base_tree if is_forbidden(path, selected))),
    )
