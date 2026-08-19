"""Fail-closed Git range hygiene for E55 public delivery paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from .authority import AuthorityError


FORBIDDEN_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".jsonl",
    ".env",
    ".generated",
    ".generated.json",
    ".tmp",
    ".coverage",
)
FORBIDDEN_PARTS = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "provider-artifacts",
        "local-artifacts",
        "artifact",
        "artifacts",
        "generated",
        "tmp",
        "cache",
        "node_modules",
    }
)


@dataclass(frozen=True, slots=True)
class HistoryPath:
    commit_sha: str
    parent_sha: str | None
    change_kind: str
    path: str
    forbidden: bool


@dataclass(frozen=True, slots=True)
class HygieneReport:
    base_sha: str
    head_sha: str
    commits: tuple[str, ...]
    history_paths: tuple[HistoryPath, ...]
    forbidden_history_paths: tuple[HistoryPath, ...]
    inherited_forbidden_final_paths: tuple[str, ...]
    forbidden_final_paths: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not self.forbidden_history_paths and not self.forbidden_final_paths


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="strict", check=False
    )
    if result.returncode != 0:
        raise AuthorityError(result.stderr.strip() or f"git command failed: {' '.join(args)}")
    return result.stdout


def is_forbidden_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lower().strip("/")
    parts = tuple(part for part in normalized.split("/") if part)
    return normalized.endswith(FORBIDDEN_SUFFIXES) or any(part in FORBIDDEN_PARTS for part in parts)


def _changed_paths(repo: Path, commit: str) -> tuple[HistoryPath, ...]:
    parents = tuple(item for item in _git(repo, "show", "-s", "--format=%P", commit).split() if item)
    # -m makes every merge-parent comparison visible.  --root preserves the
    # initial commit.  Both copy and rename sources/destinations are history.
    raw = _git(repo, "diff-tree", "--root", "-m", "--no-commit-id", "--name-status", "-r", "-M", "-C", commit)
    parent_cycle = parents or (None,)
    parent_index = 0
    records: list[HistoryPath] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < 2:
            raise AuthorityError("unparseable Git history record")
        status = fields[0]
        paths = fields[1:]
        if status.startswith(("R", "C")):
            if len(paths) != 2:
                raise AuthorityError("rename/copy history record must expose old and new paths")
        elif len(paths) != 1:
            raise AuthorityError("ordinary Git history record must expose one path")
        parent = parent_cycle[min(parent_index, len(parent_cycle) - 1)]
        for path in paths:
            normalized = path.replace("\\", "/")
            records.append(HistoryPath(commit, parent, status, normalized, is_forbidden_path(normalized)))
        # diff-tree emits merge-parent groups separately; status lines are the
        # only portable public signal in this compact report, so parent is
        # retained as best-effort provenance rather than silently discarded.
        if len(parents) > 1:
            parent_index = min(parent_index + 1, len(parents) - 1)
    return tuple(records)


def scan_commit_range(repo: Path, base_sha: str, head: str = "HEAD") -> HygieneReport:
    resolved_head = _git(repo, "rev-parse", head).strip()
    if not _git(repo, "merge-base", "--is-ancestor", base_sha, resolved_head) == "":
        # git emits no output for a successful ancestry check; nonzero is
        # handled by _git before this point.
        raise AuthorityError("base must be an ancestor of head")
    commits = tuple(item for item in _git(repo, "rev-list", "--reverse", f"{base_sha}..{resolved_head}").splitlines() if item)
    history = tuple(record for commit in commits for record in _changed_paths(repo, commit))
    base_tree = tuple(item for item in _git(repo, "ls-tree", "-r", "--name-only", base_sha).splitlines() if item)
    final_tree = tuple(item for item in _git(repo, "ls-tree", "-r", "--name-only", resolved_head).splitlines() if item)
    forbidden_history = tuple(item for item in history if item.forbidden)
    inherited = tuple(path for path in final_tree if path in base_tree and is_forbidden_path(path))
    forbidden_final = tuple(path for path in final_tree if path not in base_tree and is_forbidden_path(path))
    return HygieneReport(base_sha, resolved_head, commits, history, forbidden_history, inherited, forbidden_final)
