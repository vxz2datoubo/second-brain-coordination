"""Synthetic Git fixtures used to prove S0D mechanisms without external access."""
from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Mapping

from .adapter import ExactSourceBinding


FIXTURE_REPOSITORY = "fixture/ai-film"
FIXTURE_PATHS = ("PROJECT_INDEX.yaml", "pending_canonical_writes.yaml", "UNKNOWN_REGISTRY.yaml", "continuity.md")


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr)
    return completed.stdout.strip()


def _commit(root: Path, message: str) -> str:
    git(root, "add", ".")
    git(root, "commit", "-m", message)
    return git(root, "rev-parse", "HEAD")


def make_source_fixture(root: Path, *, pending_status: str = "pending", include_unknown: bool = True) -> tuple[str, ExactSourceBinding]:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", str(root)], capture_output=True, check=True)
    git(root, "config", "user.email", "s0d-fixture@example.invalid")
    git(root, "config", "user.name", "S0D Fixture")
    (root / "PROJECT_INDEX.yaml").write_text(
        "project_id: EUSTIA_AI_FILM\nsource_authority: this_file\nschema_version: fixture-v1\n",
        encoding="utf-8",
    )
    (root / "pending_canonical_writes.yaml").write_text(
        "registry_id: fixture-pending\nstatus: active\nitems:\n  - id: ITEM-001\n    status: " + pending_status + "\n",
        encoding="utf-8",
    )
    (root / "UNKNOWN_REGISTRY.yaml").write_text(
        "registry_id: fixture-unknown\nunknowns:\n  - id: U-001\n    status: open\n" if include_unknown else "registry_id: fixture-unknown\nunknowns: []\n",
        encoding="utf-8",
    )
    (root / "continuity.md").write_text("synthetic fixture domain body", encoding="utf-8")
    commit = _commit(root, "fixture source")
    binding = ExactSourceBinding.fixture_from_git_snapshot(root, repository=FIXTURE_REPOSITORY, commit=commit, allowed_paths=FIXTURE_PATHS)
    return commit, binding


def commit_source_status(root: Path, status: str) -> tuple[str, ExactSourceBinding]:
    path = root / "pending_canonical_writes.yaml"
    path.write_text(
        "registry_id: fixture-pending\nstatus: active\nitems:\n  - id: ITEM-001\n    status: " + status + "\n",
        encoding="utf-8",
    )
    commit = _commit(root, "fixture status transition")
    binding = ExactSourceBinding.fixture_from_git_snapshot(root, repository=FIXTURE_REPOSITORY, commit=commit, allowed_paths=FIXTURE_PATHS)
    return commit, binding


def make_control_fixture(root: Path, *, task_id: str = "TASK-A") -> str:
    subprocess.run(["git", "init", str(root)], capture_output=True, check=True)
    git(root, "config", "user.email", "s0d-fixture@example.invalid")
    git(root, "config", "user.name", "S0D Fixture")
    files: Mapping[str, str] = {
        "coordination/ACTIVE-CODEX-TASK.yaml": "task_id: " + task_id + "\nroute_epoch: 135\ncanonical_route: coordination/ROUTES/route.yaml\n",
        "coordination/ROUTES/route.yaml": "task_id: " + task_id + "\nroute_epoch: 135\n",
        "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml": "claims: []\n",
        "coordination/ACTIVE-PROGRAM-LANES.yaml": "program_lanes: []\n",
    }
    for relative, payload in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
    return _commit(root, "fixture control plane")


def commit_control_task(root: Path, task_id: str) -> str:
    (root / "coordination/ACTIVE-CODEX-TASK.yaml").write_text(
        "task_id: " + task_id + "\nroute_epoch: 135\ncanonical_route: coordination/ROUTES/route.yaml\n",
        encoding="utf-8",
    )
    (root / "coordination/ROUTES/route.yaml").write_text("task_id: " + task_id + "\nroute_epoch: 135\n", encoding="utf-8")
    return _commit(root, "fixture control drift")
