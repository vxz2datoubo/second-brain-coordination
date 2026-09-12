"""Projection schemas — the UI ViewModel contract.

These are NOT new canonical schemas. They are read-model projections of
existing authorities. Every payload carries a `Meta` block with provenance
and freshness so the UI can always answer "where did this come from?".

Authority semantics used everywhere (never collapse these):
  CANDIDATE      -> proposed, not yet independently reviewed
  CI_PASSED      -> machine check passed, still not accepted
  INDEPENDENT_REVIEW / ACCEPT
  CANONICAL      -> merged to authority main
  DEPLOYED       -> actually running somewhere
  ACTIVE         -> currently being executed

Freshness semantics:
  FRESH / AGING / STALE / UNKNOWN
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Meta / provenance
# --------------------------------------------------------------------------

class Freshness(str, Enum):
    FRESH = "FRESH"
    AGING = "AGING"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class TrustBadge(str, Enum):
    CANONICAL = "CANONICAL"
    CANDIDATE = "CANDIDATE"
    RUNTIME_OBSERVED = "RUNTIME_OBSERVED"
    DERIVED = "DERIVED"
    HISTORICAL = "HISTORICAL"
    UNKNOWN = "UNKNOWN"


class SourceRef(BaseModel):
    """A concrete, resolvable source for a projected fact."""
    kind: Literal[
        "github_file", "github_issue", "github_pr", "github_ref",
        "local_file", "git_ref", "control_tower", "runtime", "registry",
    ]
    repo: str | None = None
    ref: str | None = None          # commit sha / branch
    path: str | None = None
    url: str | None = None
    detail: str | None = None


class Meta(BaseModel):
    """Attached to every important response."""
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    freshness: Freshness = Freshness.UNKNOWN
    authority: str = "UNKNOWN"
    trust: TrustBadge = TrustBadge.UNKNOWN
    projection_status: Literal["COMPLETE", "PARTIAL", "UNAVAILABLE"] = "COMPLETE"
    sources: list[SourceRef] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Envelope(BaseModel):
    """Standard response envelope: {data, meta}."""
    data: Any
    meta: Meta


# --------------------------------------------------------------------------
# Git / repo state
# --------------------------------------------------------------------------

class RepoSyncState(str, Enum):
    SYNCED = "SYNCED"
    REMOTE_AHEAD = "REMOTE_AHEAD"
    LOCAL_AHEAD = "LOCAL_AHEAD"
    DIVERGED = "DIVERGED"
    DIRTY = "DIRTY"
    NO_REMOTE = "NO_REMOTE"
    UNKNOWN = "UNKNOWN"


class RepoState(BaseModel):
    repo: str
    local_path: str | None = None
    branch: str | None = None
    local_sha: str | None = None
    remote_sha: str | None = None
    remote_main_sha: str | None = None
    ahead: int = 0
    behind: int = 0
    dirty: bool = False
    untracked: int = 0
    worktree_count: int = 0
    sync_state: RepoSyncState = RepoSyncState.UNKNOWN
    main_protected: bool | None = None
    note: str | None = None
    fetched_at: datetime | None = None


# --------------------------------------------------------------------------
# Project registry + adapters
# --------------------------------------------------------------------------

class ProjectStateKind(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"
    BLOCKED = "BLOCKED"
    CANONICAL_HISTORY = "CANONICAL_HISTORY"
    UNKNOWN = "UNKNOWN"


class ProjectSummary(BaseModel):
    project_id: str
    display_name: str
    mission: str | None = None
    phase: str | None = None
    state: ProjectStateKind = ProjectStateKind.UNKNOWN
    desired_state: str | None = None
    observed_state: str | None = None
    active_executor: str | None = None
    carrier: str | None = None
    model: str | None = None
    current_task: str | None = None
    current_task_why: str | None = None
    latest_progress: str | None = None
    blocker: str | None = None
    next_gate: str | None = None
    lifecycle: str | None = None          # candidate / CI / review / canonical
    authority_repo: str | None = None
    domain_repo: str | None = None
    lane_id: str | None = None
    issue: int | str | None = None
    pr: int | str | None = None
    trading_authorized: bool | None = None
    owner_action_required: bool = False
    meta: Meta = Field(default_factory=Meta)


class ProjectDetail(ProjectSummary):
    adapter_status: str | None = None
    collision_domains: list[str] = Field(default_factory=list)
    canonical_entrypoints: list[str] = Field(default_factory=list)
    hard_boundaries: list[str] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Tasks / agents
# --------------------------------------------------------------------------

class TaskState(str, Enum):
    IDEA = "IDEA"
    PLANNED = "PLANNED"
    READY = "READY"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    REVIEW = "REVIEW"
    CANONICALIZATION = "CANONICALIZATION"
    DONE = "DONE"
    BLOCKED = "BLOCKED"
    STALLED = "STALLED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    OWNER_GATE = "OWNER_GATE"
    PAUSED = "PAUSED"


class TaskView(BaseModel):
    task_id: str
    project_id: str | None = None
    title: str | None = None
    goal: str | None = None
    why: str | None = None
    state: TaskState = TaskState.PLANNED
    raw_status: str | None = None
    executor: str | None = None
    carrier: str | None = None
    model: str | None = None
    route_epoch: int | str | None = None
    issue: int | str | None = None
    pr: int | str | None = None
    branch: str | None = None
    exact_head: str | None = None
    next_gate: str | None = None
    blocker: str | None = None
    execution_allowed: bool | None = None
    meta: Meta = Field(default_factory=Meta)


class AgentLiveness(str, Enum):
    """Never claim 'working' from PID/heartbeat alone."""
    INFRA_LIVE = "INFRA_LIVE"
    SESSION_LIVE = "SESSION_LIVE"
    AGENT_ACTIVE = "AGENT_ACTIVE"
    MEANINGFUL_PROGRESS = "MEANINGFUL_PROGRESS"
    STALLED = "STALLED"
    BLOCKED = "BLOCKED"
    TERMINATED = "TERMINATED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    IDLE = "IDLE"


class AgentView(BaseModel):
    agent_id: str
    role: str | None = None
    project_id: str | None = None
    task_id: str | None = None
    model: str | None = None
    carrier: str | None = None
    branch: str | None = None
    worktree: str | None = None
    liveness: AgentLiveness = AgentLiveness.OUTCOME_UNKNOWN
    liveness_reason: str | None = None
    started_at: datetime | None = None
    meta: Meta = Field(default_factory=Meta)


# --------------------------------------------------------------------------
# Control Tower summary
# --------------------------------------------------------------------------

class ControlTowerSummary(BaseModel):
    counts: dict[str, int] = Field(default_factory=dict)
    lanes: list[dict[str, Any]] = Field(default_factory=list)
    routes: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)
    collisions: list[dict[str, Any]] = Field(default_factory=list)
    meta: Meta = Field(default_factory=Meta)


# --------------------------------------------------------------------------
# System health
# --------------------------------------------------------------------------

class HealthComponent(BaseModel):
    component: str
    status: Literal["OK", "DEGRADED", "UNAVAILABLE", "UNKNOWN"]
    detail: str | None = None
    freshness: Freshness = Freshness.UNKNOWN
    latency_ms: int | None = None


class SystemHealth(BaseModel):
    components: list[HealthComponent] = Field(default_factory=list)
    overall: Literal["OK", "DEGRADED", "UNAVAILABLE", "UNKNOWN"] = "UNKNOWN"
    frontend_version: str | None = None
    backend_version: str | None = None
    coordination_main_sha: str | None = None
    meta: Meta = Field(default_factory=Meta)
