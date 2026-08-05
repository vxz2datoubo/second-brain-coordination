"""Commit-history hygiene that cannot be bypassed by add-then-delete paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from .authority import AuthorityError


FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".sqlite", ".db", ".jsonl", ".env")
FORBIDDEN_PARTS = ("__pycache__", "provider-artifacts", "local-artifacts", "private", "generated")


@dataclass(frozen=True, slots=True)
class HistoryPath:
    commit_sha: str
    change_kind: str
    path: str
    forbidden: bool


@dataclass(frozen=True, slots=True)
class HygieneReport:
    base_sha: str
    head_sha: str
    commits: tuple[str, ...]
    history_paths: tuple[HistoryPath, ...]
    base_tree_paths: tuple[str, ...]
    final_tree_paths: tuple[str, ...]
    forbidden_history_paths: tuple[HistoryPath, ...]
    inherited_forbidden_final_paths: tuple[str, ...]
    forbidden_final_paths: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not self.forbidden_history_paths and not self.forbidden_final_paths


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="strict", check=False)
    if result.returncode != 0:
        raise AuthorityError(result.stderr.strip() or f"git command failed: {' '.join(args)}")
    return result.stdout


def is_forbidden_path(path: str) -> bool:
    normal = path.replace("\\", "/").lower()
    return normal.endswith(FORBIDDEN_SUFFIXES) or any(part in normal.split("/") for part in FORBIDDEN_PARTS)


def scan_commit_range(repo: Path, base_sha: str, head: str = "HEAD") -> HygieneReport:
    resolved_head = _git(repo, "rev-parse", head).strip()
    commits = tuple(item for item in _git(repo, "rev-list", "--reverse", f"{base_sha}..{resolved_head}").splitlines() if item)
    entries: list[HistoryPath] = []
    for commit in commits:
        for line in _git(repo, "diff-tree", "--root", "--no-commit-id", "--name-status", "-r", commit).splitlines():
            if not line.strip():
                continue
            columns = line.split("\t")
            kind = columns[0]
            # Rename and copy records include source plus destination; both are historical evidence.
            for path in columns[1:]:
                normalized = path.replace("\\", "/")
                entries.append(HistoryPath(commit, kind, normalized, is_forbidden_path(normalized)))
    base_tree = tuple(sorted(item for item in _git(repo, "ls-tree", "-r", "--name-only", base_sha).splitlines() if item))
    final_tree = tuple(sorted(item for item in _git(repo, "ls-tree", "-r", "--name-only", resolved_head).splitlines() if item))
    bad_history = tuple(item for item in entries if item.forbidden)
    inherited = tuple(item for item in final_tree if item in base_tree and is_forbidden_path(item))
    bad_final = tuple(item for item in final_tree if item not in base_tree and is_forbidden_path(item))
    return HygieneReport(base_sha, resolved_head, commits, tuple(entries), base_tree, final_tree, bad_history, inherited, bad_final)
