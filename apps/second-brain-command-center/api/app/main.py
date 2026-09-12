"""Second Brain Command Center — thin READ-ONLY BFF (FastAPI).

Boundary contract:
  - READ / NORMALIZE / PROJECT only.
  - Never writes system truth, never starts processes, never merges, never trades.
  - Holds credentials (gh CLI) server-side; browser never sees them.
  - Phase 1: no dispatch/start endpoints. Extension points are declared but
    return 501 with a governance message.

All important responses are {data, meta} envelopes carrying provenance.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .repo_paths import get_paths
from .schemas import (
    Envelope, Meta, Freshness, SourceRef, TrustBadge,
    RepoState, SystemHealth, HealthComponent,
)
from .adapters import git_local, github
from .adapters import coordination as coord_adapter
from .adapters import control_tower as ct_adapter

app = FastAPI(
    title="Second Brain Command Center API",
    version=__version__,
    description="READ-ONLY projection BFF. UI state is not system truth.",
)

# Local-first: allow the Vite dev server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

COORD_REPO = "vxz2datoubo/second-brain-coordination"
DOMAIN_REPOS = {"AI_DIRECTOR": "vxz2datoubo/eustia-ai-film"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _svc_meta(authority: str, sources: list[SourceRef],
              warnings: list[str] | None = None,
              status: str = "COMPLETE") -> Meta:
    return Meta(
        observed_at=_now(), freshness=Freshness.FRESH,
        authority=authority, trust=TrustBadge.DERIVED,
        projection_status=status, sources=sources,
        warnings=warnings or [],
    )


# --------------------------------------------------------------------------
# /api/health
# --------------------------------------------------------------------------

@app.get("/api/health")
def health():
    paths = get_paths()
    comps: list[HealthComponent] = []
    coord_ok = paths.available
    comps.append(HealthComponent(
        component="LOCAL_REPO",
        status="OK" if coord_ok else "UNAVAILABLE",
        detail=str(paths.coordination) if coord_ok else "coordination repo not found",
        freshness=Freshness.FRESH if coord_ok else Freshness.UNKNOWN,
    ))
    gh_ok = github.gh_available()
    comps.append(HealthComponent(
        component="GITHUB_CLI",
        status="OK" if gh_ok else "UNAVAILABLE",
        detail="gh CLI authenticated" if gh_ok else "gh CLI missing",
        freshness=Freshness.FRESH if gh_ok else Freshness.UNKNOWN,
    ))
    # W3 is not wired in Phase 1 — declared UNAVAILABLE honestly.
    comps.append(HealthComponent(
        component="W3_RUNTIME", status="UNAVAILABLE",
        detail="W3 interface not connected in Phase 1 (read-only MVP)",
        freshness=Freshness.UNKNOWN,
    ))
    comps.append(HealthComponent(
        component="CONTROL_TOWER",
        status="OK" if coord_ok else "UNAVAILABLE",
        detail="reads canonical ACTIVE-* + lanes",
    ))
    comps.append(HealthComponent(
        component="HOST_BROKER", status="UNAVAILABLE",
        detail="auto-dispatch is Phase 3, not enabled",
        freshness=Freshness.UNKNOWN,
    ))
    overall = "OK" if all(c.status == "OK" for c in comps if c.component in
                          ("LOCAL_REPO", "GITHUB_CLI", "CONTROL_TOWER")) else "DEGRADED"
    sh = SystemHealth(
        components=comps, overall=overall,
        frontend_version="0.1.0-phase1", backend_version=__version__,
        coordination_main_sha=_coord_sha(),
        meta=_svc_meta("BFF_SELF", [SourceRef(kind="runtime", detail="self health")]),
    )
    return Envelope(data=sh, meta=sh.meta)


def _coord_sha() -> str | None:
    paths = get_paths()
    if not paths.coordination:
        return None
    st = git_local.read_local_state(paths.coordination, COORD_REPO)
    return st.local_sha


# --------------------------------------------------------------------------
# /api/system  (top bar aggregate)
# --------------------------------------------------------------------------

@app.get("/api/system")
def system_top():
    paths = get_paths()
    gh_sha, gh_err = github.get_default_branch_sha(COORD_REPO) if github.gh_available() else (None, "gh unavailable")

    repos: list[RepoState] = []
    if paths.coordination:
        st = git_local.read_local_state(paths.coordination, COORD_REPO)
        st.remote_main_sha = gh_sha or st.remote_main_sha
        # reclassify now that we have fresh remote
        repos.append(st)
    if paths.domain.get("AI_DIRECTOR"):
        d = paths.domain["AI_DIRECTOR"]
        repos.append(git_local.read_local_state(d, DOMAIN_REPOS["AI_DIRECTOR"]))

    lanes_doc, _ = coord_adapter.read_lanes(paths.coordination) if paths.available else ({}, None)
    tasks, _ = coord_adapter.read_active_tasks(paths.coordination) if paths.available else ([], None)

    data = {
        "repos": [r.model_dump() for r in repos],
        "github_sha": gh_sha,
        "github_error": gh_err,
        "active_task_count": len(tasks),
        "lane_count": len(lanes_doc.get("program_lanes") or []),
        "last_refresh": _now().isoformat(),
    }
    meta = _svc_meta(
        "BFF_SYSTEM",
        [SourceRef(kind="github_ref", repo=COORD_REPO, ref=gh_sha, detail="remote main")] +
        [SourceRef(kind="local_file", path=str(paths.coordination))] if paths.coordination else [],
        warnings=[f"github: {gh_err}"] if gh_err else [],
    )
    return Envelope(data=data, meta=meta)


# --------------------------------------------------------------------------
# /api/projects
# --------------------------------------------------------------------------

@app.get("/api/projects")
def projects():
    paths = get_paths()
    if not paths.available:
        return Envelope(
            data=[],
            meta=_svc_meta("PROJECT_REGISTRY", [],
                           ["coordination repo not available"], status="UNAVAILABLE"),
        )
    summaries, meta = coord_adapter.build_project_summaries(paths.coordination)
    return Envelope(data=[s.model_dump() for s in summaries], meta=meta)


@app.get("/api/projects/{project_id}")
def project_detail(project_id: str):
    paths = get_paths()
    if not paths.available:
        raise HTTPException(503, "coordination repo not available")
    detail = coord_adapter.build_project_detail(paths.coordination, project_id)
    if detail is None:
        raise HTTPException(404, f"project {project_id} not in registry")
    return Envelope(data=detail.model_dump(), meta=detail.meta)


# --------------------------------------------------------------------------
# /api/tasks
# --------------------------------------------------------------------------

@app.get("/api/tasks")
def tasks():
    paths = get_paths()
    if not paths.available:
        return Envelope(data=[], meta=_svc_meta("ACTIVE_TASKS", [], ["no repo"], "UNAVAILABLE"))
    views, meta = coord_adapter.read_active_tasks(paths.coordination)
    return Envelope(data=[t.model_dump() for t in views], meta=meta)


# --------------------------------------------------------------------------
# /api/control-tower
# --------------------------------------------------------------------------

@app.get("/api/control-tower")
def control_tower():
    paths = get_paths()
    if not paths.available:
        return Envelope(data=None, meta=_svc_meta("CONTROL_TOWER", [], ["no repo"], "UNAVAILABLE"))
    summary = ct_adapter.read_summary(paths.coordination)
    d = summary.model_dump()
    d["projection_as_of"] = ct_adapter.main_projection_head(paths.coordination)
    return Envelope(data=d, meta=summary.meta)


# --------------------------------------------------------------------------
# /api/agents  (who is actually working — never from PID alone)
# --------------------------------------------------------------------------

@app.get("/api/agents")
def agents():
    paths = get_paths()
    if not paths.available:
        return Envelope(data=[], meta=_svc_meta("AGENTS", [], ["no repo"], "UNAVAILABLE"))
    views, meta = coord_adapter.read_active_tasks(paths.coordination)

    from .schemas import AgentView, AgentLiveness, TaskState
    out: list[AgentView] = []
    for t in views:
        # Liveness is derived ONLY from task-level evidence (state), never PID.
        if t.state == TaskState.RUNNING or t.state == TaskState.DISPATCHED:
            live = AgentLiveness.AGENT_ACTIVE
            reason = "active route with execution_allowed"
        elif t.state == TaskState.READY:
            live = AgentLiveness.IDLE
            reason = "route READY, not yet executing (no session evidence)"
        elif t.state == TaskState.BLOCKED:
            live = AgentLiveness.BLOCKED
            reason = "route blocked_by set"
        elif t.state == TaskState.DONE:
            live = AgentLiveness.TERMINATED
            reason = "terminal state"
        elif t.state == TaskState.PAUSED:
            live = AgentLiveness.IDLE
            reason = "paused"
        else:
            live = AgentLiveness.OUTCOME_UNKNOWN
            reason = "insufficient evidence"
        out.append(AgentView(
            agent_id=t.executor or "UNKNOWN",
            role="executor",
            task_id=t.task_id, model=t.model, carrier=t.carrier,
            branch=t.branch,
            liveness=live, liveness_reason=reason,
            meta=t.meta,
        ))
    return Envelope(data=[a.model_dump() for a in out], meta=meta)


# --------------------------------------------------------------------------
# Phase 2+ extension points — declared, NOT implemented (fail closed)
# --------------------------------------------------------------------------

@app.post("/api/commands/dispatch-intent")
def dispatch_intent():
    raise HTTPException(
        status_code=501,
        detail=("DISPATCH_NOT_ENABLED: Phase 1 is READ-ONLY. "
                "Dispatch requires Control Tower authority check (route/claim/lease/"
                "collision) and is Phase 2. This endpoint exists only as a declared "
                "extension point and fails closed."),
    )


@app.post("/api/commands/start")
def start_task():
    raise HTTPException(
        status_code=501,
        detail=("START_NOT_ENABLED: Host Broker auto-dispatch is Phase 3 and requires "
                "R194 physical canary proof. Fails closed."),
    )
