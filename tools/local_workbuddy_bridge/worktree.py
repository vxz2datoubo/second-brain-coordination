"""Isolated worktree preparation abstraction.

Rule (TASK-BRIEF.yaml):
  - "Create one isolated worktree or clone per write task from
     execution_repository only."
  - "Windows-first path/process implementation with portable abstractions;
     no shell-string concatenation authority boundary."

This module PLANS the isolation. It does not create a worktree in Phase 2B —
creating a real worktree mutates the host filesystem and therefore requires the
same independent review + canonicalization gate as process activation.

The abstraction exists now so that:
  1. the launch plan can prove isolation was *required and declared*; and
  2. the eventual real implementation has a reviewed, single choke point.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .contracts import BridgeBoundaryError

# A worktree path is derived from validated fields, never from free text.
_SAFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]{0,63}$")


def _normalize(path: str) -> str:
    """Case/separator/Unicode-normalized identity for a filesystem path."""
    text = unicodedata.normalize("NFC", str(path or ""))
    text = text.replace("\\", "/").strip()
    while text.endswith("/") and len(text) > 1:
        text = text[:-1]
    return text.lower()


@dataclass(frozen=True)
class WorktreePlan:
    """A PLAN to prepare isolation. Creates nothing."""

    task_id: str
    branch: str
    base_sha: str
    worktree_path: str
    execution_repository: str
    creates_real_worktree: bool = False
    reason: str = ""

    def __post_init__(self) -> None:
        if self.creates_real_worktree:
            raise BridgeBoundaryError(
                "Phase 2B worktree plans must never claim a real worktree creation"
            )


def plan_isolated_worktree(
    *,
    task_id: str,
    branch: str,
    base_sha: str,
    execution_repository: str,
    worktree_root: str | Path,
) -> WorktreePlan:
    """Compose a validated, collision-safe worktree plan.

    Every path segment is validated against a strict allowlist pattern so that
    a malicious task_id or branch cannot escape the worktree root via `..`,
    absolute paths, drive letters or separator tricks.
    """
    if not _is_safe_segment(task_id):
        raise BridgeBoundaryError(f"task_id {task_id!r} is not a safe path segment")
    if not _is_safe_branch(branch):
        raise BridgeBoundaryError(f"branch {branch!r} is not a safe branch name")
    if len(base_sha) < 7 or len(base_sha) > 64:
        raise BridgeBoundaryError(f"base_sha {base_sha!r} is not a plausible git sha")

    root = Path(worktree_root)
    candidate = root / task_id

    # Defence in depth: the resolved path must remain inside the root.
    if not _is_contained(root, candidate):
        raise BridgeBoundaryError(
            f"worktree path {candidate} escapes the worktree root {root}"
        )

    return WorktreePlan(
        task_id=task_id,
        branch=branch,
        base_sha=base_sha,
        worktree_path=str(candidate),
        execution_repository=execution_repository,
        creates_real_worktree=False,
        reason="isolation planned; creation deferred to post-canonicalization phase",
    )


def worktrees_collide(a: WorktreePlan, b: WorktreePlan) -> bool:
    """Two write tasks must never share a worktree."""
    return _normalize(a.worktree_path) == _normalize(b.worktree_path)


def _is_safe_segment(segment: str) -> bool:
    if not segment or segment in {".", ".."}:
        return False
    if any(ch in segment for ch in ("/", "\\", ":", "\0")):
        return False
    return bool(_SAFE_SEGMENT_RE.match(segment))


def _is_safe_branch(branch: str) -> bool:
    text = str(branch or "").strip()
    if not text or text.startswith("-") or text.endswith("/") or ".." in text:
        return False
    # git ref-name rules: no control chars, no backslash, no space, no "~^:?*["
    if any(ch in text for ch in ("\\", " ", "~", "^", ":", "?", "*", "[", "\0")):
        return False
    return all(_is_safe_segment(part) for part in PurePosixPath(text).parts)


def _is_contained(root: Path, candidate: Path) -> bool:
    try:
        root_res = root.resolve()
        cand_res = candidate.resolve()
    except OSError:
        # Cannot resolve (e.g. path does not exist yet) — fall back to lexical.
        root_res = Path(_normalize(str(root)))
        cand_res = Path(_normalize(str(candidate)))
    return cand_res == root_res or root_res in cand_res.parents
