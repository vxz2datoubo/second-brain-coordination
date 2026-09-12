"""Repository discovery — locates the coordination repo and domain repos
on the local machine, without hardcoding a single absolute path.

Resolution order:
  1. Environment variable SBC_COORD_ROOT / known workspace roots
  2. Walk up from the api package location
This keeps the Command Center portable across machines / AI hosts.
"""
from __future__ import annotations

import os
from pathlib import Path

# Candidate workspace roots (portable: checked in order, first hit wins).
_ENV_KEYS = ("SBC_WORKSPACE_ROOT", "SECOND_BRAIN_WORKSPACE")
_CANDIDATE_ROOTS = (
    Path("F:/SecondBrainWorkspace"),
    Path.home() / "SecondBrainWorkspace",
    Path("C:/SecondBrainWorkspace"),
)

# Known repo directory names inside the workspace.
COORD_DIR_NAMES = ("second-brain-coordination",)
COORD_IN_REPOS = ("repos/second-brain-coordination",)
DOMAIN_DIRS = {
    "AI_DIRECTOR": ("repos/eustia-ai-film", "eustia-ai-film"),
}


class RepoPaths:
    def __init__(self) -> None:
        self.workspace_root: Path | None = None
        self.coordination: Path | None = None
        self.domain: dict[str, Path] = {}

    @property
    def available(self) -> bool:
        return self.coordination is not None and self.coordination.exists()


def _first_existing(paths) -> Path | None:
    for p in paths:
        try:
            if p.exists():
                return p
        except OSError:
            continue
    return None


def discover() -> RepoPaths:
    rp = RepoPaths()

    roots: list[Path] = []
    for key in _ENV_KEYS:
        v = os.environ.get(key)
        if v:
            roots.append(Path(v))
    roots.extend(_CANDIDATE_ROOTS)

    for root in roots:
        if not root.exists():
            continue
        cand = _first_existing(
            [root / name for name in COORD_DIR_NAMES]
            + [root / name for name in COORD_IN_REPOS]
        )
        if cand:
            rp.workspace_root = root
            rp.coordination = cand
            for pid, rels in DOMAIN_DIRS.items():
                d = _first_existing([root / r for r in rels])
                if d:
                    rp.domain[pid] = d
            break

    return rp


_PATHS: RepoPaths | None = None


def get_paths() -> RepoPaths:
    global _PATHS
    if _PATHS is None:
        _PATHS = discover()
    return _PATHS
