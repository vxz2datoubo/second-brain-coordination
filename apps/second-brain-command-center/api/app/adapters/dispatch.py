"""Dispatch Intent composer — Phase 2A. READ-ONLY.

Boundary (non-negotiable):
  - NEVER starts, attaches to, or kills any process.
  - NEVER calls the Host Execution Broker's admit().
  - NEVER invokes RDC.
  - NEVER writes system truth.

It only READS canonical Control Tower state, evaluates which authorization
inputs are present, composes an explicit DispatchIntent, and routes it to a
human gate. Authority belongs to canonical repository state; a button press
or chat text is intent, never authority.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from ..adapters.coordination import read_active_tasks
from ..schemas import (
    AuthorityInputCheck,
    AuthorityState,
    CriticPreScreen,
    DispatchIntent,
    DispatchNextGate,
    DispatchVerdict,
    Freshness,
    Meta,
    SourceRef,
    TrustBadge,
)

# Canonical authorization inputs required before any process may start.
# Mirrors LOCAL-WORKBUDDY-BRIDGE-CONTRACT-v1.0 + issue310 broker review doc.
_REQUIRED_INPUTS: tuple[tuple[str, str, str], ...] = (
    ("route", "执行路线（ACTIVE route）", "coordination/ACTIVE-*-TASK.yaml"),
    ("claim", "工作认领（Work Claim）", "coordination/EXECUTION/**/WORK-CLAIM.yaml"),
    ("lease", "任务租约（Task Lease）", "coordination/EXECUTION/**/TASK-LEASE.yaml"),
    ("reservation", "执行者预留（Executor Reservation）", "coordination/EXECUTION/**/EXECUTOR-RESERVATION.yaml"),
    ("prewrite_snapshot", "预写快照（Prewrite Snapshot）", "coordination/EXECUTION/**/PREWRITE-RECONCILIATION-SNAPSHOT.yaml"),
    ("executable_batch", "可执行批次（Executable Batch）", "coordination/EXECUTION/**/EXECUTABLE-BATCH.json"),
    ("adapter", "项目适配器（Project Adapter）", "coordination/EXECUTION/PROJECT-ADAPTERS/*.yaml"),
    ("model", "模型可用性（Model Availability）", "coordination/EXECUTION/MODEL-CATALOG-SNAPSHOT-*.yaml"),
    ("collision", "碰撞域独占（Collision Domain）", "coordination/EXECUTION/PROJECT-ADAPTERS/*.yaml"),
)


def _intent_id(project_id: str, task_id: str, route_epoch: object, requested_by: str) -> str:
    raw = f"{project_id}\0{task_id}\0{route_epoch}\0{requested_by}"
    return "DI-" + sha256(raw.encode("utf-8")).hexdigest()[:24]


def _find_task(tasks: list, task_id: str):
    for t in tasks:
        if t.task_id == task_id:
            return t
    return None


def compose_intent(
    coord: Path | None,
    *,
    project_id: str,
    task_id: str,
    route_epoch: object = None,
    requested_by: str = "operator",
) -> DispatchIntent:
    """Compose a Phase 2A DispatchIntent. This function performs no side effects."""
    now = datetime.now(timezone.utc)
    intent_id = _intent_id(project_id, task_id, route_epoch, requested_by)

    tasks: list = []
    warnings: list[str] = []
    sources: list[SourceRef] = []
    if coord is not None:
        tasks, task_meta = read_active_tasks(coord)
        sources = list(task_meta.sources)
    else:
        warnings.append("coordination repo not available; authority cannot be verified")

    task = _find_task(tasks, task_id)

    checks: list[AuthorityInputCheck] = []
    missing: list[str] = []

    def _task_scoped_artifacts(basename: str) -> list[Path]:
        """Find authorization artifacts belonging to THIS task only.

        A file must match by task id (either in the directory name or the
        declared task_id inside the file). Matching any file would falsely
        report authorized state for an unrelated or unknown task.
        """
        assert coord is not None
        out: list[Path] = []
        for p in coord.glob("coordination/EXECUTION/**/" + basename):
            rel = str(p.relative_to(coord))
            if task_id and task_id in rel:
                out.append(p)
        return sorted(out)

    for input_id, label_zh, path_glob in _REQUIRED_INPUTS:
        present = False
        detail: str | None = None
        source_path: str | None = None

        if input_id == "route":
            if task is not None:
                present = bool(task.execution_allowed) and (task.raw_status or "").upper() == "READY"
                detail = f"status={task.raw_status} execution_allowed={task.execution_allowed}"
                source_path = "coordination/ACTIVE-*-TASK.yaml"
            else:
                detail = "no matching active task found in canonical state"
        elif input_id in ("claim", "lease", "reservation", "prewrite_snapshot", "executable_batch"):
            if coord is None or task is None:
                detail = ("coordination repo unavailable" if coord is None
                          else "unknown task; no task-scoped artifact can be attributed")
            else:
                basename = {
                    "claim": "WORK-CLAIM.yaml",
                    "lease": "TASK-LEASE.yaml",
                    "reservation": "EXECUTOR-RESERVATION.yaml",
                    "prewrite_snapshot": "PREWRITE-RECONCILIATION-SNAPSHOT.yaml",
                    "executable_batch": "EXECUTABLE-BATCH.json",
                }[input_id]
                matches = _task_scoped_artifacts(basename)
                present = len(matches) > 0
                detail = (f"task-scoped: {matches[0].name}") if present else "not found for this task"
                source_path = str(matches[0].relative_to(coord)) if matches else None
        elif input_id == "adapter":
            if coord is not None and task is not None:
                matches = sorted(coord.glob("coordination/EXECUTION/PROJECT-ADAPTERS/*.yaml"))
                present = len(matches) > 0
                detail = f"{len(matches)} adapter(s) registered"
            else:
                detail = "coordination repo unavailable or task unknown"
        elif input_id == "model":
            if task is not None and task.model:
                present = True
                detail = f"declared model={task.model}"
            else:
                detail = "no model declared on the active task"
        elif input_id == "collision":
            if task is not None and task.executor:
                present = True
                detail = f"executor={task.executor} (single-writer per collision domain)"
            else:
                detail = "executor identity unknown; collision exclusivity unverifiable"

        if not present:
            missing.append(input_id)
        checks.append(AuthorityInputCheck(
            input_id=input_id, label_zh=label_zh, present=present,
            detail=detail, source_path=source_path,
        ))

    # --- authority state -------------------------------------------------
    if coord is None:
        authority_state = AuthorityState.UNKNOWN
    elif task is None:
        authority_state = AuthorityState.UNKNOWN
    elif (task.raw_status or "").upper() in ("CANDIDATE", "CANDIDATE_PENDING_INDEPENDENT_REVIEW"):
        authority_state = AuthorityState.STALE
    elif task.execution_allowed is False:
        authority_state = AuthorityState.REVOKED
    else:
        authority_state = AuthorityState.CURRENT

    # --- verdict (fail closed) ------------------------------------------
    if task is None:
        # No canonical task at all: nothing is authorized. This is a MISSING
        # AUTHORITY case, not a stale-base case.
        verdict = DispatchVerdict.BLOCKED_MISSING_AUTHORITY
        next_gate = DispatchNextGate.KEEP_READ_ONLY
    elif authority_state == AuthorityState.UNKNOWN:
        verdict = DispatchVerdict.BLOCKED_MISSING_AUTHORITY
        next_gate = DispatchNextGate.KEEP_READ_ONLY
    elif authority_state == AuthorityState.STALE:
        verdict = DispatchVerdict.BLOCKED_STALE_BASE
        next_gate = DispatchNextGate.KEEP_READ_ONLY
    elif authority_state == AuthorityState.REVOKED:
        verdict = DispatchVerdict.BLOCKED_STATE_CONFLICT
        next_gate = DispatchNextGate.KEEP_READ_ONLY
    elif missing:
        verdict = DispatchVerdict.BLOCKED_MISSING_AUTHORITY
        next_gate = DispatchNextGate.KEEP_READ_ONLY
    else:
        verdict = DispatchVerdict.ADMISSIBLE
        next_gate = DispatchNextGate.HUMAN_DISPATCH_APPROVAL

    # --- critic pre-screen ------------------------------------------------
    # Phase 2A: the critic is DECLARED but not wired to a live model yet.
    # It must never auto-approve; unwired means escalate to human.
    critic = CriticPreScreen(
        enabled=False,
        confidence=None,
        governance_conflicts=[],
        requires_tier_upgrade=False,
        irreversible_or_externally_visible=False,
        rationale=None,
        escalated_to_human=True,
        note=("Critic pre-screen declared by DISPATCH-INTENT-CONTRACT-v1.0 but not wired in "
              "Phase 2A; defaulting to human review. A critic can rank and route, never approve."),
    )

    # --- plain-language answer -------------------------------------------
    total = len(checks)
    ok = total - len(missing)
    if task is None:
        plain = (f"控制塔里找不到任务 {task_id}。这不是「快好了」，是这条任务在本地第二大脑"
                 f"项目里根本不存在或还没被登记，所以 0/{total} 项授权可核对，暂不能开工。")
    elif verdict == DispatchVerdict.ADMISSIBLE:
        plain = f"{task_id} 想开工。授权齐了 {ok}/{total} 项。授权已齐，等人确认即可进入下一阶段。"
    elif verdict == DispatchVerdict.BLOCKED_MISSING_AUTHORITY:
        plain = f"{task_id} 想开工。授权齐了 {ok}/{total} 项。还缺 {len(missing)} 项授权，暂不能开工。"
    elif verdict == DispatchVerdict.BLOCKED_STALE_BASE:
        plain = f"{task_id} 想开工。授权齐了 {ok}/{total} 项。授权状态已过期或基准已移动，暂不能开工。"
    elif verdict == DispatchVerdict.BLOCKED_STATE_CONFLICT:
        plain = f"{task_id} 想开工。授权齐了 {ok}/{total} 项。授权已被撤销或状态冲突，暂不能开工。"
    else:
        plain = f"{task_id} 想开工。授权齐了 {ok}/{total} 项。需要老板决策。"

    return DispatchIntent(
        dispatch_intent_id=intent_id,
        created_at=now,
        requested_by=requested_by,
        source="CONSOLE_BUTTON",
        project_id=project_id,
        task_id=task_id,
        route_epoch=route_epoch if route_epoch is not None else (task.route_epoch if task else None),
        executor=(task.executor if task else None),
        carrier=(task.carrier if task else None),
        model=(task.model if task else None),
        branch=(task.branch if task else None),
        canonical_main_sha=None,
        authority_state=authority_state,
        readonly_authority_check=checks,
        missing_authorization_inputs=missing,
        critic_pre_screen=critic,
        verdict=verdict,
        next_gate=next_gate,
        plain_answer=plain,
        starts_any_process=False,
        meta=Meta(
            observed_at=now,
            freshness=Freshness.FRESH if coord is not None else Freshness.UNKNOWN,
            authority="CONTROL_TOWER_READONLY",
            trust=TrustBadge.DERIVED,
            projection_status="COMPLETE" if coord is not None else "PARTIAL",
            sources=sources,
            warnings=warnings,
        ),
    )
