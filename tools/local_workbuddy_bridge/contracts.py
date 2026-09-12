"""Typed contracts for the local WorkBuddy bridge.

R184 is synthetic/dry-run only. These objects do NOT grant canonical execution
authority and never start, kill or attach to a real process.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable


class BridgeBoundaryError(RuntimeError):
    """Raised whenever a hard boundary would be crossed. Always fail closed."""


class BridgeDecision(str, Enum):
    PLANNED = "PLANNED"
    REFUSED_STALE_MAIN = "REFUSED_STALE_MAIN"
    REFUSED_UNREGISTERED_TASK = "REFUSED_UNREGISTERED_TASK"
    REFUSED_AUTHORITY_MISMATCH = "REFUSED_AUTHORITY_MISMATCH"
    REFUSED_BASE_MISMATCH = "REFUSED_BASE_MISMATCH"
    REFUSED_COLLISION_CONFLICT = "REFUSED_COLLISION_CONFLICT"
    REFUSED_CANDIDATE_ONLY = "REFUSED_CANDIDATE_ONLY"
    REFUSED_MODEL_UNAVAILABLE = "REFUSED_MODEL_UNAVAILABLE"
    REFUSED_DUPLICATE = "REFUSED_DUPLICATE"
    REFUSED_UNKNOWN_ADAPTER = "REFUSED_UNKNOWN_ADAPTER"


@dataclass(frozen=True)
class ModelPreflightResult:
    ok: bool
    model: str
    reason: str
    resolved_from: str | None = None


@dataclass(frozen=True)
class LaunchPlan:
    """A PLAN. It describes what WOULD be launched. It launches nothing."""
    decision: BridgeDecision
    reason: str
    task_id: str = ""
    route_epoch: int | None = None
    branch: str = ""
    worktree: str = ""
    collision_domain: str = ""
    carrier: str = ""
    model: str = ""
    canonical_main_sha: str = ""
    cli_path: str = ""
    argv: tuple[str, ...] = ()
    env_allowlist: tuple[tuple[str, str], ...] = ()
    dry_run: bool = True
    launches_real_process: bool = False

    def __post_init__(self) -> None:
        # A plan that claims a real launch is impossible in Phase 2B.
        if self.launches_real_process:
            raise BridgeBoundaryError(
                "Phase 2B plans must never claim a real process launch"
            )


@dataclass(frozen=True)
class LaunchReceipt:
    """Durable idempotency/launch receipt keyed to immutable authority identity."""
    receipt_id: str
    task_id: str
    route_epoch: int
    execution_identity: str
    idempotency_key: str
    decision: BridgeDecision
    created_at_ms: int
    dry_run: bool = True


@dataclass(frozen=True)
class ReturnPackage:
    """Standard WorkBuddy return package. Secrets are always redacted."""
    task_id: str
    route_epoch: int | None
    branch: str
    head_sha: str | None
    tests: tuple[str, ...] = ()
    findings: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    changed_files: tuple[str, ...] = ()
    telemetry: dict = field(default_factory=dict)
    redacted: bool = True

    def __post_init__(self) -> None:
        for text in (*self.tests, *self.findings, *self.unknowns):
            if _looks_like_secret(text):
                raise BridgeBoundaryError(
                    "return package would persist a credential-looking value"
                )


_SECRET_MARKERS = (
    "ghp_", "gho_", "ghs_", "github_pat_", "sk-", "xoxb-", "xoxp-",
    "-----begin", "password=", "token=", "apikey=", "api_key=", "secret=",
)


def _looks_like_secret(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _SECRET_MARKERS)


@runtime_checkable
class ProcessAdapter(Protocol):
    """The ONLY way the bridge may touch a process.

    The real adapter exists but is disabled until independent review +
    canonicalization. All automated tests use FakeProcessAdapter.
    """

    def identity(self) -> str: ...

    def plan(self, plan: LaunchPlan) -> LaunchPlan: ...

    def launch(self, plan: LaunchPlan) -> dict: ...
