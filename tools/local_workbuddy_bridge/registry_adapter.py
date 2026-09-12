"""Canonical task registry discovery adapter.

Rule (TASK-BRIEF.yaml):
  - "Discover executable work only from registered task indexes; arbitrary
     issue/comment/branch prose is never execution authority."
  - "Rebuild selected authority through unified_active_task_registry +
     unified_execution_trust_gate before process start."

This adapter READS the canonical index. It does not own, mutate or re-derive it.
The index documents are the single source of truth; this module merely projects
them into a small, string-only lookup structure the bridge can consume.

NO_SECOND_CONTROL_TOWER_OR_SECOND_TRUST_GATE: this module never decides whether
authority exists. It answers only "is this task_id registered, and what is its
declared canonical shape?" — the trust gate decides the rest.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contracts import BridgeBoundaryError


@dataclass(frozen=True)
class RegisteredTask:
    """A read-only projection of one registered task."""

    task_id: str
    route_epoch: int | None
    branch: str
    base_sha: str
    collision_domain: str
    status: str
    execution_allowed: bool
    is_canonical: bool
    authority_state: str


@dataclass
class RegistryAdapter:
    """Reads registered-task indexes. Never writes them."""

    index_paths: tuple[Path, ...] = ()
    _tasks: dict[str, RegisteredTask] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._tasks = {}

    # -- loading ---------------------------------------------------------
    def load(self) -> "RegistryAdapter":
        """(Re)read all configured indexes from disk. Idempotent."""
        tasks: dict[str, RegisteredTask] = {}
        for path in self.index_paths:
            p = Path(path)
            if not p.exists():
                continue
            try:
                raw = p.read_text(encoding="utf-8")
            except OSError as exc:
                raise BridgeBoundaryError(f"cannot read registry index {p}: {exc}")
            if not raw.strip():
                continue
            data = json.loads(raw)
            for entry in _iter_task_entries(data):
                project = _project(entry)
                if project.task_id:
                    # First registration wins; later duplicates do not overwrite
                    # canonical truth (fail closed, no silent shadowing).
                    tasks.setdefault(project.task_id, project)
        self._tasks = tasks
        return self

    # -- queries ---------------------------------------------------------
    def get(self, task_id: str) -> RegisteredTask | None:
        return self._tasks.get(str(task_id))

    def is_registered(self, task_id: str) -> bool:
        """A task is registrable only if it is actively registered AND allowed.

        Ancestor tasks that are byte-frozen/retired (status not READY) remain
        discoverable but are NOT executable — this is what keeps R175
        unchanged and conflict-isolated while still visible.
        """
        found = self.get(task_id)
        if found is None:
            return False
        return bool(found.execution_allowed)

    def is_discoverable(self, task_id: str) -> bool:
        """Discoverable != executable. Frozen ancestors stay discoverable."""
        return self.get(task_id) is not None

    def registered_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._tasks))

    def count(self) -> int:
        return len(self._tasks)


_ENTRY_LIST_KEYS = (
    "active", "active_tasks", "tasks", "registered", "registered_tasks",
    "entries", "index",
)


def _iter_task_entries(data: Any):
    """Yield candidate task dicts from the various index shapes in use."""
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item
        return
    if not isinstance(data, dict):
        return
    for key in _ENTRY_LIST_KEYS:
        value = data.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    yield item
    # A single flattened task document.
    if data.get("task_id"):
        yield data


def _first(entry: dict, *keys: str) -> Any:
    for key in keys:
        if key in entry and entry[key] not in (None, ""):
            return entry[key]
    return None


def _project(entry: dict) -> RegisteredTask:
    task_id = str(_first(entry, "task_id", "id", "taskId") or "").strip()
    epoch_raw = _first(entry, "route_epoch", "epoch", "routeEpoch")
    try:
        route_epoch = int(epoch_raw) if epoch_raw is not None else None
    except (TypeError, ValueError):
        route_epoch = None

    status = str(_first(entry, "status", "state") or "").strip().upper()
    execution_allowed = bool(
        _first(entry, "execution_allowed", "executionAllowed") is True
    )

    # A task is canonical unless it is explicitly flagged as a candidate.
    is_canonical = True
    if str(_first(entry, "candidate", "is_candidate") or "").lower() in {
        "1", "true", "yes"
    }:
        is_canonical = False

    return RegisteredTask(
        task_id=task_id,
        route_epoch=route_epoch,
        branch=str(_first(entry, "branch", "implementation_branch") or ""),
        base_sha=str(
            _first(
                entry, "canonical_main_sha", "base_sha", "base", "head_sha",
                "branch_parent_required",
            )
            or ""
        ),
        collision_domain=str(
            _first(entry, "collision_domain", "collisionDomain", "surface") or ""
        ),
        status=status,
        execution_allowed=execution_allowed,
        is_canonical=is_canonical,
        authority_state=str(_first(entry, "authority_state", "authority") or ""),
    )
