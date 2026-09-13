"""Coordination repo reader — projects, lanes, active tasks, adapters.

Reads real YAML from the coordination repo (local working copy) and projects
it into ViewModels. Source of truth: the repo files themselves.

Mapping rules (important for truthfulness):
  - PROJECT-REGISTRY.yaml  -> the set of projects (NOT hardcoded 4)
  - ACTIVE-PROGRAM-LANES   -> per-lane mission/phase/next_gate/executor
  - ACTIVE-{AGENT}-TASK    -> current route per agent
  - PROJECT-ADAPTERS/*.yaml -> collision domains, entrypoints, boundaries
  - PROGRAM-CONTROL-TOWER.md autogen block -> lane release decision
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ..schemas import (
    Freshness, Meta, ProjectDetail, ProjectStateKind, ProjectSummary,
    SourceRef, TaskState, TaskView, TrustBadge,
)


def _load_yaml(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return None


def _mtime_freshness(path: Path) -> Freshness:
    """A file's freshness is about whether it could be read, not its age.
    Age-based staleness is applied at a higher level via timestamps inside."""
    return Freshness.FRESH if path.exists() else Freshness.UNKNOWN


# --------------------------------------------------------------------------
# Project registry
# --------------------------------------------------------------------------

def read_project_registry(coord: Path) -> tuple[list[dict], Meta]:
    path = coord / "coordination/EXECUTION/PROJECT-REGISTRY.yaml"
    data = _load_yaml(path)
    if not data:
        return [], Meta(
            freshness=Freshness.UNKNOWN, authority="PROJECT_REGISTRY",
            trust=TrustBadge.UNKNOWN, projection_status="UNAVAILABLE",
            sources=[SourceRef(kind="local_file", path=str(path))],
            warnings=["PROJECT-REGISTRY.yaml not readable"],
        )
    projects = data.get("projects") or []
    return projects, Meta(
        freshness=_mtime_freshness(path),
        authority="PROJECT_REGISTRY",
        trust=TrustBadge.CANONICAL,
        sources=[SourceRef(kind="local_file", path=str(path),
                           detail=f"registry_id={data.get('registry_id')}")],
    )


def read_adapter(coord: Path, rel: str) -> tuple[dict | None, Meta]:
    path = coord / rel
    data = _load_yaml(path)
    if data is None:
        return None, Meta(
            freshness=Freshness.UNKNOWN, authority="PROJECT_ADAPTER",
            trust=TrustBadge.UNKNOWN, projection_status="UNAVAILABLE",
            sources=[SourceRef(kind="local_file", path=str(path))],
            warnings=[f"adapter {rel} not readable"],
        )
    return data, Meta(
        freshness=Freshness.FRESH, authority="PROJECT_ADAPTER",
        trust=TrustBadge.CANONICAL,
        sources=[SourceRef(kind="local_file", path=str(path))],
    )


# --------------------------------------------------------------------------
# Program lanes
# --------------------------------------------------------------------------

def read_lanes(coord: Path) -> tuple[dict[str, Any], Meta]:
    path = coord / "coordination/ACTIVE-PROGRAM-LANES.yaml"
    data = _load_yaml(path)
    if not data:
        return {}, Meta(
            freshness=Freshness.UNKNOWN, authority="PROGRAM_LANES",
            trust=TrustBadge.UNKNOWN, projection_status="UNAVAILABLE",
            sources=[SourceRef(kind="local_file", path=str(path))],
            warnings=["ACTIVE-PROGRAM-LANES.yaml not readable"],
        )
    return data, Meta(
        freshness=Freshness.FRESH, authority="PROGRAM_LANES",
        trust=TrustBadge.CANONICAL,
        sources=[SourceRef(kind="local_file", path=str(path),
                           detail=f"registry_id={data.get('registry_id')}")],
    )


# --------------------------------------------------------------------------
# Active agent tasks
# --------------------------------------------------------------------------

_AGENT_FILES = {
    "WORKBUDDY": "coordination/ACTIVE-WORKBUDDY-TASK.yaml",
    "CODEX": "coordination/ACTIVE-CODEX-TASK.yaml",
    "QCLAW": "coordination/ACTIVE-QCLAW-TASK.yaml",
    "GPT_ENGINEERING_WORKER": "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml",
}

_TERMINAL_TOKENS = ("DONE", "CLOSED", "CANCELLED", "TERMINAL")

# Derive project attribution from task_id / route tokens (DERIVED, not authority).
def _infer_project_id(task_id: str, explicit: str | None) -> str | None:
    if explicit:
        return explicit
    blob = task_id.upper()
    if "DS10" in blob or "TRADING" in blob or "CSCV" in blob or "PBO" in blob or "SHARPE" in blob:
        return "TRADING_SYSTEM"
    if "R175" in blob or "FILM" in blob or "CREATIVE" in blob or "BATON" in blob:
        return "REALTIME_INTERACTIVE_FILM_GAME"
    if "DIRECTOR" in blob or "SCENE" in blob or "SHOT" in blob:
        return "AI_DIRECTOR"
    if "SECOND-BRAIN" in blob or "MEMORY" in blob or "COGNITIVE" in blob or "R181" in blob:
        return "SECOND_BRAIN"
    return None


def _classify_task_state(raw_status: str, execution_allowed: bool | None,
                         blocked_by: Any) -> TaskState:
    s = (raw_status or "").upper()
    if blocked_by:
        return TaskState.BLOCKED
    if any(t in s for t in _TERMINAL_TOKENS):
        return TaskState.DONE
    if "PAUSED" in s:
        return TaskState.PAUSED
    if "REVIEW" in s:
        return TaskState.REVIEW
    if "RUNNING" in s or "EXECUTING" in s:
        return TaskState.RUNNING
    if "READY" in s and execution_allowed:
        return TaskState.READY
    if execution_allowed:
        return TaskState.READY
    return TaskState.PLANNED


def read_active_tasks(coord: Path) -> tuple[list[TaskView], Meta]:
    tasks: list[TaskView] = []
    sources: list[SourceRef] = []
    for agent, rel in _AGENT_FILES.items():
        path = coord / rel
        if not path.exists():
            continue
        data = _load_yaml(path)
        if not data:
            continue
        sources.append(SourceRef(kind="local_file", path=str(path), detail=agent))
        raw_status = str(data.get("status", ""))
        exec_allowed = data.get("execution_allowed")
        tid = str(data.get("task_id") or data.get("active_task_id") or f"{agent}-UNKNOWN")
        task = TaskView(
            task_id=tid,
            project_id=_infer_project_id(tid, data.get("project_id")),
            title=data.get("mode_label") or data.get("task_id"),
            goal=data.get("mode"),
            why=data.get("mode_label"),
            state=_classify_task_state(raw_status, exec_allowed, data.get("blocked_by")),
            raw_status=raw_status,
            executor=agent,
            carrier=(data.get("execution_carrier") or data.get("carrier")),
            model=data.get("model_id") or data.get("model"),
            route_epoch=data.get("route_epoch"),
            issue=data.get("active_issue") or data.get("issue"),
            pr=data.get("pull_request") or data.get("pr"),
            branch=data.get("implementation_branch"),
            exact_head=(data.get("source_checkpoint") or {}).get("exact_head")
                       if isinstance(data.get("source_checkpoint"), dict) else None,
            next_gate=(data.get("return_target") and f"return_to_{data.get('return_target')}"),
            blocker=str(data.get("blocked_by")) if data.get("blocked_by") else None,
            execution_allowed=exec_allowed if isinstance(exec_allowed, bool) else None,
            meta=Meta(
                freshness=Freshness.FRESH, authority=f"ACTIVE_{agent}_TASK",
                trust=TrustBadge.CANONICAL,
                sources=[SourceRef(kind="local_file", path=str(path), detail=agent)],
            ),
        )
        tasks.append(task)
    return tasks, Meta(
        freshness=Freshness.FRESH if sources else Freshness.UNKNOWN,
        authority="ACTIVE_TASKS", trust=TrustBadge.CANONICAL,
        sources=sources,
        projection_status="COMPLETE" if sources else "UNAVAILABLE",
    )


# --------------------------------------------------------------------------
# Project cards (join registry + lanes + tasks)
# --------------------------------------------------------------------------

def _state_from_lane(observed: str, desired: str) -> ProjectStateKind:
    blob = f"{observed} {desired}".upper()
    if "BLOCK" in blob:
        return ProjectStateKind.BLOCKED
    if "PAUSE" in blob or "PARK" in blob:
        return ProjectStateKind.PAUSED
    if "ACTIVE" in blob:
        return ProjectStateKind.ACTIVE
    if "CLOSED" in blob or "DONE" in blob:
        return ProjectStateKind.CLOSED
    if "CANONICAL" in blob:
        return ProjectStateKind.CANONICAL_HISTORY
    return ProjectStateKind.UNKNOWN


def build_project_summaries(coord: Path) -> tuple[list[ProjectSummary], Meta]:
    registry, reg_meta = read_project_registry(coord)
    lanes_doc, _ = read_lanes(coord)
    tasks, _ = read_active_tasks(coord)
    lanes = {l.get("lane_id"): l for l in (lanes_doc.get("program_lanes") or [])}

    # Map lanes to projects heuristically by id keywords (registry is truth for
    # the project SET; lane attribution is derived and marked DERIVED).
    def lane_for(pid: str) -> dict | None:
        # Prefer a non-closed lane if several match.
        matched: list[dict] = []
        for lid, lane in lanes.items():
            blob = f"{lid} {lane.get('mission','')}".upper()
            if pid == "TRADING_SYSTEM" and "TRADING" in blob:
                matched.append(lane)
            elif pid == "REALTIME_INTERACTIVE_FILM_GAME" and ("FILM" in blob or "CREATIVE" in blob):
                matched.append(lane)
            elif pid == "SECOND_BRAIN" and "SECOND-BRAIN" in blob:
                matched.append(lane)
            elif pid == "AI_DIRECTOR" and "DIRECTOR" in blob:
                matched.append(lane)
        if not matched:
            return None
        active = [l for l in matched
                  if "CLOSED" not in str(l.get("observed_state", "")).upper()
                  and "DONE" not in str(l.get("observed_state", "")).upper()]
        return (active or matched)[0]

    out: list[ProjectSummary] = []
    for p in registry:
        pid = p.get("project_id", "UNKNOWN")
        lane = lane_for(pid) or {}
        adapter_doc, _ = read_adapter(coord, p.get("adapter", "")) if p.get("adapter") else (None, None)
        # Tasks belong to a project by inferred project_id (DERIVED attribution).
        proj_tasks = [t for t in tasks if t.project_id == pid]
        t = proj_tasks[0] if proj_tasks else None
        exec_name = (lane.get("implementation_owner") or "").upper() or (
            (t.executor) if t else None)
        state = _state_from_lane(str(lane.get("observed_state", "")),
                                 str(lane.get("desired_state", "")))
        # Mission fallback: adapter owns_statement / registry, never invented.
        mission = lane.get("mission")
        if not mission and adapter_doc:
            owns = adapter_doc.get("authority", {}).get("owns")
            if owns:
                mission = "权威域：" + " · ".join(str(x) for x in owns[:4])
        if not mission and adapter_doc:
            eps = adapter_doc.get("canonical_entrypoints") or []
            if eps:
                mission = "规范入口：" + " · ".join(str(x).split("/")[-1] for x in eps[:2])
        if not mission:
            mission = None
        summary = ProjectSummary(
            project_id=pid,
            display_name=p.get("display_name", pid),
            mission=mission,
            phase=lane.get("current_phase"),
            state=state,
            desired_state=lane.get("desired_state"),
            observed_state=lane.get("observed_state"),
            active_executor=exec_name,
            carrier=t.carrier if t else None,
            model=t.model if t else None,
            current_task=(t.task_id if t else lane.get("active_execution_route")),
            current_task_why=lane.get("mission") if t else None,
            latest_progress=None,
            blocker=(t.blocker if t else None),
            next_gate=lane.get("next_gate") or (adapter_doc.get("acceptance", {}).get("required", [None])[0]
                                                if adapter_doc else None),
            lifecycle=lane.get("maturity"),
            authority_repo=p.get("primary_coordination_repo"),
            domain_repo=p.get("domain_repo"),
            lane_id=lane.get("lane_id"),
            issue=t.issue if t else None,
            pr=t.pr if t else None,
            trading_authorized=lane.get("trading_authorized"),
            owner_action_required=state == ProjectStateKind.BLOCKED,
            meta=Meta(
                freshness=Freshness.FRESH,
                authority="PROJECT_REGISTRY+ACTIVE_LANES",
                trust=TrustBadge.DERIVED,
                sources=(
                    [SourceRef(kind="registry", path="coordination/EXECUTION/PROJECT-REGISTRY.yaml"),
                     SourceRef(kind="local_file", path="coordination/ACTIVE-PROGRAM-LANES.yaml",
                               detail=lane.get("lane_id") or "no-active-lane")]
                    + ([SourceRef(kind="local_file", path=str(p.get("adapter")))]
                       if adapter_doc else [])
                ),
                warnings=(
                    ["no active lane (state derived as UNKNOWN rather than invented)"]
                    if not lane else []
                ),
            ),
        )
        out.append(summary)
    return out, reg_meta


def build_project_detail(coord: Path, project_id: str) -> ProjectDetail | None:
    summaries, _ = build_project_summaries(coord)
    base = next((s for s in summaries if s.project_id == project_id), None)
    if base is None:
        return None
    registry, _ = read_project_registry(coord)
    reg = next((p for p in registry if p.get("project_id") == project_id), {})
    adapter_doc = None
    if reg.get("adapter"):
        adapter_doc, _ = read_adapter(coord, reg["adapter"])

    relationships: list[dict] = []
    if adapter_doc:
        for ti in adapter_doc.get("tool_interfaces", []) or []:
            relationships.append({"kind": "tool_interface", **ti})
        hn = adapter_doc.get("handoff")
        if hn:
            relationships.append({"kind": "handoff", **hn})

    detail = ProjectDetail(**base.model_dump())
    if adapter_doc:
        detail.adapter_status = adapter_doc.get("status")
        detail.collision_domains = list(adapter_doc.get("collision_domains") or [])
        detail.canonical_entrypoints = list(adapter_doc.get("canonical_entrypoints") or [])
        detail.hard_boundaries = list(adapter_doc.get("hard_boundaries") or [])
        detail.relationships = relationships
    return detail


# --------------------------------------------------------------------------
# Work claims & collision surfaces (control-tower projection fill)
# --------------------------------------------------------------------------

def read_claims(coord: Path) -> tuple[list[dict], Meta]:
    """Scan coordination/EXECUTION/**/WORK-CLAIM.yaml — READ-ONLY projection.

    A work claim is an artifact the executor itself declared. This projection
    only reports what the files say; it never grants or revokes authority.
    """
    sources = [SourceRef(kind="local_file",
                         path="coordination/EXECUTION/**/WORK-CLAIM.yaml")]
    if not coord.is_dir():
        return [], Meta(
            freshness=Freshness.UNKNOWN, authority="WORK_CLAIMS",
            trust=TrustBadge.UNKNOWN, projection_status="UNAVAILABLE",
            sources=sources, warnings=["coordination repo not available"],
        )

    claims: list[dict] = []
    warnings: list[str] = []
    for p in sorted(coord.glob("coordination/EXECUTION/**/WORK-CLAIM.yaml")):
        doc = _load_yaml(p)
        if not doc:
            warnings.append(f"unreadable claim skipped: {p.parent.name}")
            continue
        claims.append({
            "task_id": doc.get("task_id") or p.parent.name,
            "claim_id": doc.get("claim_id"),
            "agent": doc.get("agent"),
            "branch": doc.get("branch"),
            "route_epoch": doc.get("route_epoch"),
            "status_observed": doc.get("status_observed"),
            "execution_allowed_observed": doc.get("execution_allowed_observed"),
            "active_issue": doc.get("active_issue") or doc.get("source_issue"),
            "pull_request": doc.get("pull_request"),
            "authorized_paths": [str(s) for s in (doc.get("authorized_paths") or [])],
            "hard_boundaries": [str(s) for s in (doc.get("hard_boundaries") or [])],
            "source_path": str(p.relative_to(coord)).replace("\\", "/"),
        })

    return claims, Meta(
        freshness=Freshness.FRESH if claims else Freshness.UNKNOWN,
        authority="WORK_CLAIMS",
        trust=TrustBadge.CANONICAL,
        projection_status="COMPLETE" if claims else "PARTIAL",
        sources=sources, warnings=warnings,
    )


def build_collisions(coord: Path) -> tuple[list[dict], Meta]:
    """Derive per-surface holder sets from leases + claims. READ-ONLY.

    Grouping is EXACT STRING match on surface patterns; no glob semantics are
    expanded, so this never reports overlap beyond what the files themselves
    state. TASK-LEASE exclusive_write_surface is authoritative and wins;
    WORK-CLAIM authorized_paths dedup into the same holder entry.

    Severity (derived, never invented):
      CROSS_AGENT_OVERLAP      — 2+ DIFFERENT agents hold the same surface (red)
      SINGLE_AGENT_MULTI_TASK  — one agent holds it from 2+ tasks (amber)
      OK                       — single holder (green)
    """
    sources = [
        SourceRef(kind="local_file", path="coordination/EXECUTION/**/TASK-LEASE.yaml"),
        SourceRef(kind="local_file", path="coordination/EXECUTION/**/WORK-CLAIM.yaml"),
    ]
    if not coord.is_dir():
        return [], Meta(
            freshness=Freshness.UNKNOWN, authority="COLLISION_DOMAINS",
            trust=TrustBadge.UNKNOWN, projection_status="UNAVAILABLE",
            sources=sources, warnings=["coordination repo not available"],
        )

    holders_by_surface: dict[str, list[dict]] = {}

    for lp in sorted(coord.glob("coordination/EXECUTION/**/TASK-LEASE.yaml")):
        doc = _load_yaml(lp)
        if not doc:
            continue
        task_id = doc.get("task_id") or lp.parent.name
        agent = doc.get("agent_type") or doc.get("agent") or "UNKNOWN"
        for s in doc.get("exclusive_write_surface") or []:
            holders_by_surface.setdefault(str(s), []).append(
                {"agent": str(agent), "task_id": str(task_id), "source": "TASK-LEASE.yaml"})

    for cp in sorted(coord.glob("coordination/EXECUTION/**/WORK-CLAIM.yaml")):
        doc = _load_yaml(cp)
        if not doc:
            continue
        task_id = str(doc.get("task_id") or cp.parent.name)
        agent = str(doc.get("agent") or "UNKNOWN")
        for s in doc.get("authorized_paths") or []:
            lst = holders_by_surface.setdefault(str(s), [])
            if not any(h["task_id"] == task_id and h["agent"] == agent for h in lst):
                lst.append({"agent": agent, "task_id": task_id, "source": "WORK-CLAIM.yaml"})

    collisions: list[dict] = []
    cross_agent = 0
    for surface, holders in sorted(holders_by_surface.items()):
        agents = {h["agent"] for h in holders}
        if len(agents) > 1:
            severity = "CROSS_AGENT_OVERLAP"
            cross_agent += 1
        elif len(holders) > 1:
            severity = "SINGLE_AGENT_MULTI_TASK"
        else:
            severity = "OK"
        collisions.append({"surface": surface, "holders": holders, "severity": severity})

    warnings: list[str] = []
    if cross_agent:
        warnings.append(f"{cross_agent} surface(s) held by 2+ different agents — verify single-writer before dispatch")

    return collisions, Meta(
        freshness=Freshness.FRESH if collisions else Freshness.UNKNOWN,
        authority="COLLISION_DOMAINS",
        trust=TrustBadge.DERIVED,
        projection_status="COMPLETE" if collisions else "PARTIAL",
        sources=sources, warnings=warnings,
    )
