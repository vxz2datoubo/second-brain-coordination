"""Typed candidate contracts for host-local execution arbitration.

R1 is synthetic-only. These objects do not grant canonical execution authority and
never launch, kill, or attach to a real process. They are the host-runtime projection
that a future canonical Control Tower admission gate may consume.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Any, Iterable

from coordination.EXECUTION import canonical_write_paths as write_paths


class DecisionOutcome(str, Enum):
    ADMIT = "ADMIT"
    WAIT = "WAIT"
    JOIN_EXISTING = "JOIN_EXISTING"
    BLOCK_CONFLICT = "BLOCK_CONFLICT"
    REROUTE = "REROUTE"


class ResourceMode(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


class ResourceType(str, Enum):
    HOST = "HOST"
    RDC_PROCESS_MUTATION_CHANNEL = "RDC_PROCESS_MUTATION_CHANNEL"
    WORKBUDDY_DAEMON = "WORKBUDDY_DAEMON"
    WORKBUDDY_AGENT_SESSION = "WORKBUDDY_AGENT_SESSION"
    WORKBUDDY_ONE_TIME_RUNNER = "WORKBUDDY_ONE_TIME_RUNNER"
    CODEX_SESSION = "CODEX_SESSION"
    LOCAL_PORT = "LOCAL_PORT"
    WORKTREE = "WORKTREE"
    BRANCH = "BRANCH"
    COLLISION_DOMAIN = "COLLISION_DOMAIN"
    WRITE_SURFACE = "WRITE_SURFACE"
    CPU_LIGHT = "CPU_LIGHT"
    CPU_HEAVY = "CPU_HEAVY"
    GPU_LOCAL = "GPU_LOCAL"
    MARKET_DATA_PROVIDER = "MARKET_DATA_PROVIDER"
    EXCLUSIVE_LOCAL_RUNTIME = "EXCLUSIVE_LOCAL_RUNTIME"


class AuthorityState(str, Enum):
    CURRENT = "CURRENT"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    REVOKED = "REVOKED"


class ProgressState(str, Enum):
    AUTHORIZED_NOT_STARTED = "AUTHORIZED_NOT_STARTED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    IDLE_EXPECTED = "IDLE_EXPECTED"
    STALLED = "STALLED"
    WAITING_REVIEW = "WAITING_REVIEW"
    WAITING_CANONICALIZATION = "WAITING_CANONICALIZATION"
    CHECKPOINTING = "CHECKPOINTING"
    RESUMING = "RESUMING"
    WORKER_FAILURE = "WORKER_FAILURE"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    UNKNOWN_REQUIRES_RECONCILE = "OUTCOME_UNKNOWN"
    COMPLETE = "COMPLETE"


class TransportState(str, Enum):
    OK = "OK"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    TRANSPORT_TIMEOUT_RECONCILE_REQUIRED = "OUTCOME_UNKNOWN"
    WORKER_FAILURE = "WORKER_FAILURE"


@dataclass(frozen=True)
class ResourceClaim:
    resource_type: ResourceType
    resource_id: str
    mode: ResourceMode = ResourceMode.WRITE
    units: int = 1
    exclusive: bool = False

    def __post_init__(self) -> None:
        if not self.resource_id.strip():
            raise ValueError("resource_id must be non-empty")
        if self.units < 1:
            raise ValueError("units must be >= 1")
        if self.resource_type == ResourceType.WRITE_SURFACE:
            write_paths.canonicalize_write_path_pattern(self.resource_id)

    @property
    def key(self) -> str:
        return f"{self.resource_type.value}:{self.resource_id}"


@dataclass(frozen=True)
class ExecutionRequest:
    project_id: str
    task_id: str
    route_epoch: int
    mission_id: str
    milestone_id: str
    episode_id: str
    attempt: int
    role: str
    branch: str
    worktree: str
    collision_domain: str
    carrier: str
    model: str
    canonical_main_sha: str
    authority_receipt_digest: str
    authority_state: AuthorityState
    resource_claims: tuple[ResourceClaim, ...] = field(default_factory=tuple)
    write_surfaces: tuple[str, ...] = field(default_factory=tuple)
    repo_write: bool = True
    owner_window: str | None = None

    def __post_init__(self) -> None:
        required = (
            self.project_id, self.task_id, self.mission_id, self.milestone_id,
            self.episode_id, self.role, self.branch, self.worktree, self.collision_domain,
            self.carrier, self.model, self.canonical_main_sha, self.authority_receipt_digest,
        )
        if any(not value.strip() for value in required):
            raise ValueError("execution request identity/authority fields must be non-empty")
        if self.route_epoch < 1 or self.attempt < 1:
            raise ValueError("route_epoch and attempt must be positive")
        if not re.fullmatch(r"[0-9a-f]{40}", self.canonical_main_sha):
            raise ValueError("canonical_main_sha must be a full lowercase commit SHA")
        try:
            canonical_surfaces = write_paths.canonicalize_authorized_paths(self.write_surfaces)
        except write_paths.CanonicalWritePathError as exc:
            raise ValueError(f"non-canonical write surface: {exc}") from exc
        object.__setattr__(self, "write_surfaces", canonical_surfaces)

    @property
    def idempotency_key(self) -> str:
        raw = f"{self.task_id}\0{self.route_epoch}\0{self.episode_id}\0{self.attempt}"
        return sha256(raw.encode("utf-8")).hexdigest()

    @property
    def execution_identity(self) -> str:
        material = {
            "project_id": self.project_id,
            "task_id": self.task_id,
            "route_epoch": self.route_epoch,
            "mission_id": self.mission_id,
            "milestone_id": self.milestone_id,
            "episode_id": self.episode_id,
            "attempt": self.attempt,
            "role": self.role,
        }
        payload = json.dumps(material, sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode("utf-8")).hexdigest()

    @property
    def broker_key(self) -> str:
        return "HX" + self.execution_identity[:16].upper()

    def all_claims(self) -> tuple[ResourceClaim, ...]:
        mode = ResourceMode.WRITE if self.repo_write else ResourceMode.READ
        implicit = [
            ResourceClaim(ResourceType.BRANCH, self.branch, mode),
            ResourceClaim(ResourceType.WORKTREE, self.worktree, mode),
            ResourceClaim(ResourceType.COLLISION_DOMAIN, self.collision_domain, mode),
        ]
        if self.repo_write:
            implicit.extend(
                ResourceClaim(ResourceType.WRITE_SURFACE, surface, ResourceMode.WRITE)
                for surface in self.write_surfaces
            )
        by_key: dict[tuple[str, str], ResourceClaim] = {}
        for claim in (*implicit, *self.resource_claims):
            key = (claim.resource_type.value, claim.resource_id)
            previous = by_key.get(key)
            if previous is None:
                by_key[key] = claim
                continue
            strongest_mode = (
                ResourceMode.WRITE
                if ResourceMode.WRITE in {previous.mode, claim.mode}
                else ResourceMode.READ
            )
            by_key[key] = ResourceClaim(
                claim.resource_type,
                claim.resource_id,
                strongest_mode,
                max(previous.units, claim.units),
                previous.exclusive or claim.exclusive,
            )
        return tuple(sorted(by_key.values(), key=lambda c: (c.resource_type.value, c.resource_id)))


@dataclass(frozen=True)
class LeaseBinding:
    lease_id: str
    execution_id: str
    holder: str
    resource_type: ResourceType
    resource_id: str
    mode: ResourceMode
    generation: int
    fencing_token: str
    issued_at_ms: int
    expires_at_ms: int
    state: str = "ACTIVE"


@dataclass(frozen=True)
class AdmissionDecision:
    outcome: DecisionOutcome
    execution_id: str | None
    broker_key: str | None
    reason: str
    leases: tuple[LeaseBinding, ...] = field(default_factory=tuple)
    joined_execution_id: str | None = None


@dataclass(frozen=True)
class WorkerIdentity:
    pid: int
    process_creation_identity: str
    session_id: str
    executor_id: str
    task_id: str
    route_epoch: int
    execution_lease_id: str
    generation: int
    fencing_token: str
    cli_path: str
    cli_version: str
    endpoint: str | None = None

    def __post_init__(self) -> None:
        if self.pid <= 0 or self.route_epoch < 1 or self.generation < 1:
            raise ValueError("invalid process/route/generation identity")
        required = (
            self.process_creation_identity, self.session_id, self.executor_id,
            self.task_id, self.execution_lease_id, self.fencing_token,
            self.cli_path, self.cli_version,
        )
        if any(not value.strip() for value in required):
            raise ValueError("worker identity fields must be non-empty")


@dataclass(frozen=True)
class ProcessStartReceipt:
    schema: str
    execution_id: str
    broker_key: str
    task_id: str
    route_epoch: int
    role: str
    branch: str
    worktree: str
    collision_domain: str
    carrier: str
    model: str
    canonical_main_sha: str
    worker: WorkerIdentity
    issued_at_ms: int


@dataclass(frozen=True)
class ProgressObservation:
    now_ms: int
    process_alive: bool
    process_started: bool = True
    process_started_at_ms: int | None = None
    heartbeat_at_ms: int | None = None
    model_response_at_ms: int | None = None
    meaningful_progress_at_ms: int | None = None
    expected_idle: bool = False
    terminal: bool = False

    def classify(self, *, stall_after_ms: int) -> ProgressState:
        if stall_after_ms < 1:
            raise ValueError("stall_after_ms must be positive")
        if self.terminal:
            return ProgressState.COMPLETE
        if not self.process_started:
            return ProgressState.AUTHORIZED_NOT_STARTED
        if not self.process_alive:
            return ProgressState.WORKER_FAILURE
        if self.expected_idle:
            return ProgressState.IDLE_EXPECTED
        if self.meaningful_progress_at_ms is None:
            if (
                self.process_started_at_ms is not None
                and self.now_ms - self.process_started_at_ms <= stall_after_ms
            ):
                return ProgressState.STARTING
            return ProgressState.STALLED
        if self.now_ms - self.meaningful_progress_at_ms > stall_after_ms:
            return ProgressState.STALLED
        return ProgressState.RUNNING


class EpisodeBudgetOutcome(str, Enum):
    CONTINUE_EPISODE = "CONTINUE_EPISODE"
    CHECKPOINT_AND_SUCCESSOR = "CHECKPOINT_AND_SUCCESSOR"
    MISSION_COMPLETE = "MISSION_COMPLETE"


@dataclass(frozen=True)
class EpisodeBudgetDecision:
    outcome: EpisodeBudgetOutcome
    checkpoint_required: bool
    successor_episode_required: bool
    checkpoint_ref: str | None


def canonical_digest(items: Iterable[Any]) -> str:
    payload = json.dumps(list(items), sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + sha256(payload.encode("utf-8")).hexdigest()
