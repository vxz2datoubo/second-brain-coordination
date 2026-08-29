"""Small, dependency-free enforcement helpers for the creative task boundary."""

from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import json
from pathlib import PurePosixPath
from typing import Any, Iterable


class GovernanceViolation(ValueError):
    """Raised when a task artifact attempts to exceed its published boundary."""


@dataclass(frozen=True)
class TaskGovernance:
    task_id: str
    route_epoch: int
    allowed_write_patterns: tuple[str, ...]
    authority_invariants: dict[str, str]

    def is_write_path_allowed(self, path: str) -> bool:
        normalized = PurePosixPath(path.replace("\\", "/")).as_posix()
        return any(fnmatch.fnmatchcase(normalized, pattern) for pattern in self.allowed_write_patterns)

    def require_allowed_write_paths(self, paths: Iterable[str]) -> None:
        rejected = [path for path in paths if not self.is_write_path_allowed(path)]
        if rejected:
            raise GovernanceViolation(
                "Task write scope rejects: " + ", ".join(sorted(rejected))
            )

    def require_authority_declaration(self, declaration: dict[str, Any]) -> None:
        unexpected = {
            key: value
            for key, value in declaration.items()
            if key not in self.authority_invariants
            or str(value) != self.authority_invariants[key]
        }
        missing = sorted(set(self.authority_invariants) - set(declaration))
        if missing or unexpected:
            details: list[str] = []
            if missing:
                details.append("missing=" + ",".join(missing))
            if unexpected:
                details.append("unexpected=" + ",".join(sorted(unexpected)))
            raise GovernanceViolation("Authority declaration rejected: " + "; ".join(details))


def load_task_governance(path: str) -> TaskGovernance:
    """Load the task-local JSON policy without relying on an optional YAML parser."""

    with open(path, "r", encoding="utf-8") as stream:
        data = json.load(stream)
    return TaskGovernance(
        task_id=data["task_id"],
        route_epoch=data["route_epoch"],
        allowed_write_patterns=tuple(data["allowed_write_patterns"]),
        authority_invariants=dict(data["authority_invariants"]),
    )
