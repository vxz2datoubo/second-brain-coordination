"""Local git adapter — reads real local repo state.

Uses subprocess git (no library dependency). All git operations are read-only:
  rev-parse, status, worktree list, rev-list, branch.

Authority: LOCAL_RUNTIME_OBSERVED. This is local machine truth, not canonical.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ..schemas import RepoState, RepoSyncState, Freshness, Meta, SourceRef, TrustBadge


def _git(repo: Path, *args: str, timeout: int = 15) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def read_local_state(repo: Path, repo_slug: str, remote_ref: str = "origin/main") -> RepoState:
    state = RepoState(repo=repo_slug, local_path=str(repo))
    if not repo.exists():
        state.sync_state = RepoSyncState.UNKNOWN
        state.note = "local path not found"
        return state

    state.branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD") or None
    state.local_sha = _git(repo, "rev-parse", "HEAD") or None
    state.remote_main_sha = _git(repo, "rev-parse", remote_ref) or None

    # ahead / behind against remote main
    ab = _git(repo, "rev-list", "--left-right", "--count", f"{remote_ref}...HEAD")
    if ab:
        parts = ab.split()
        if len(parts) == 2:
            state.behind, state.ahead = int(parts[0]), int(parts[1])

    # dirty / untracked
    porcelain = _git(repo, "status", "--porcelain")
    if porcelain:
        lines = [l for l in porcelain.splitlines() if l.strip()]
        state.dirty = True
        state.untracked = sum(1 for l in lines if l.startswith("??"))

    # worktrees
    wt = _git(repo, "worktree", "list", "--porcelain")
    state.worktree_count = wt.count("worktree ") if wt else 0

    # classify sync state
    if state.local_sha and state.remote_main_sha:
        if state.ahead == 0 and state.behind == 0:
            state.sync_state = RepoSyncState.DIRTY if state.dirty else RepoSyncState.SYNCED
        elif state.ahead > 0 and state.behind == 0:
            state.sync_state = RepoSyncState.LOCAL_AHEAD
        elif state.behind > 0 and state.ahead == 0:
            state.sync_state = RepoSyncState.REMOTE_AHEAD
        else:
            state.sync_state = RepoSyncState.DIVERGED
    else:
        state.sync_state = RepoSyncState.UNKNOWN

    state.fetched_at = datetime.now(timezone.utc)
    return state


def local_state_meta(state: RepoState) -> Meta:
    src = SourceRef(
        kind="git_ref", repo=state.repo, ref=state.local_sha,
        path=state.local_path, detail="local working tree",
    )
    return Meta(
        freshness=Freshness.FRESH if state.local_sha else Freshness.UNKNOWN,
        authority="LOCAL_GIT_RUNTIME",
        trust=TrustBadge.RUNTIME_OBSERVED,
        sources=[src],
        warnings=[] if state.sync_state != RepoSyncState.UNKNOWN else ["local repo state unavailable"],
    )


def read_worktrees(repo: Path) -> list[dict]:
    """List worktrees with their branch + head (real local state)."""
    raw = _git(repo, "worktree", "list", "--porcelain")
    if not raw:
        return []
    entries: list[dict] = []
    cur: dict = {}
    for line in raw.splitlines():
        if line.startswith("worktree "):
            if cur:
                entries.append(cur)
            cur = {"path": line[len("worktree "):]}
        elif line.startswith("HEAD "):
            cur["head"] = line[len("HEAD "):]
        elif line.startswith("branch "):
            cur["branch"] = line[len("branch "):].replace("refs/heads/", "")
        elif line.strip() == "detached":
            cur["branch"] = "(detached)"
    if cur:
        entries.append(cur)
    return entries
