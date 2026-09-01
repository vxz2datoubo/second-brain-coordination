"""Select safe Codex and WorkBuddy actions from canonical GitHub authority.

This coordinator is deliberately read-only.  It turns the collaboration baton,
the two canonical ACTIVE projections and an operator event into explicit next
actions, but it can never create a route, claim work, accept a review or merge.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
EVENTS = {"AUTO", "CODEX_QUOTA_LOW", "WORKBUDDY_BATCH_COMPLETE", "USER_SYNC", "USER_STOP"}
TOP_LEVEL = re.compile(r"^([A-Za-z0-9_]+):(?:\s*(.*))?$")


class CoordinationError(ValueError):
    """Raised when the baton or authority projections are unsafe."""


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise CoordinationError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout.strip()


def parse_top_level_scalars(text: str) -> dict[str, Any]:
    """Parse only unindented YAML scalars from canonical ACTIVE files."""

    result: dict[str, Any] = {}
    for line in text.splitlines():
        if not line or line[0].isspace() or line.lstrip().startswith("#"):
            continue
        match = TOP_LEVEL.match(line.rstrip())
        if not match:
            continue
        key, raw = match.groups()
        raw = (raw or "").strip()
        if not raw:
            result[key] = None
        elif raw.casefold() in {"true", "false"}:
            result[key] = raw.casefold() == "true"
        elif raw.casefold() in {"null", "none", "~"}:
            result[key] = None
        elif raw.startswith('"') and raw.endswith('"'):
            result[key] = json.loads(raw)
        elif raw.startswith("'") and raw.endswith("'"):
            result[key] = raw[1:-1].replace("''", "'")
        elif re.fullmatch(r"-?[0-9]+", raw):
            result[key] = int(raw)
        else:
            result[key] = raw
    return result


def parse_nested_scalars(text: str, section: str) -> dict[str, Any]:
    """Parse one two-space-indented scalar mapping from canonical YAML."""

    lines: list[str] = []
    in_section = False
    for line in text.splitlines():
        if not in_section:
            if line.rstrip() == f"{section}:":
                in_section = True
            continue
        if line and not line[0].isspace():
            break
        if line.startswith("  ") and not line.startswith("    "):
            lines.append(line[2:])
    return parse_top_level_scalars("\n".join(lines))


def _required(mapping: dict[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise CoordinationError(f"{where}.{key} is required")
    return mapping[key]


def _surface(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CoordinationError("write surfaces must be non-empty strings")
    raw = value.replace("\\", "/").strip().removesuffix("/**").rstrip("/")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts:
        raise CoordinationError(f"unsafe write surface: {value}")
    return path.as_posix().casefold()


def _overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def _route_ready(active: dict[str, Any], agent: str) -> bool:
    return (
        active.get("target_agent") == agent
        and active.get("status") == "READY"
        and active.get("execution_allowed") is True
        and bool(active.get("task_id"))
        and bool(active.get("active_issue"))
        and bool(active.get("route_epoch"))
    )


def _validate_baton(payload: dict[str, Any]) -> list[str]:
    if payload.get("schema") != "CreativeExecutorCoordinationBaton/v1":
        raise CoordinationError("unsupported baton schema")
    if payload.get("authority") != "NAVIGATION_ONLY_CANONICAL_ACTIVE_ROUTES_WIN":
        raise CoordinationError("baton must not claim execution authority")
    checkpoint = _required(payload, "source_checkpoint", "baton")
    exact_head = _required(checkpoint, "exact_head", "source_checkpoint")
    if not isinstance(exact_head, str) or not SHA_RE.fullmatch(exact_head):
        raise CoordinationError("source_checkpoint.exact_head must be a 40-character SHA")
    remote_ref = _required(checkpoint, "checkpoint_remote_ref", "source_checkpoint")
    if not isinstance(remote_ref, str) or not remote_ref.startswith(
        "refs/remotes/origin/codex/checkpoint-"
    ):
        raise CoordinationError("source checkpoint must use an immutable Codex checkpoint ref")

    lanes = _required(payload, "lanes", "baton")
    codex = _required(lanes, "CODEX_CORE", "lanes")
    verification = _required(lanes, "WORKBUDDY_VERIFICATION", "lanes")
    simple = _required(lanes, "WORKBUDDY_SIMPLE", "lanes")
    codex_paths = [_surface(item) for item in _required(codex, "write_surfaces", "CODEX_CORE")]
    if _required(verification, "write_surfaces", "WORKBUDDY_VERIFICATION"):
        raise CoordinationError("WorkBuddy verification lane must be read-only")
    simple_paths = [_surface(item) for item in _required(simple, "write_surfaces", "WORKBUDDY_SIMPLE")]
    for left in codex_paths:
        for right in simple_paths:
            if _overlap(left, right):
                raise CoordinationError(f"Codex/WorkBuddy single-writer overlap: {left} <> {right}")
    if simple.get("complexity_ceiling") not in {"D0", "D1"}:
        raise CoordinationError("WorkBuddy simple lane complexity ceiling must be D0 or D1")
    if payload.get("final_acceptance") != "USER_TRIGGERED_GPT_CROSS_MODULE_REVIEW":
        raise CoordinationError("executor baton cannot redefine final acceptance")
    return [
        "baton_is_navigation_only",
        "immutable_checkpoint_identity_present",
        "verification_lane_read_only",
        "implementation_lanes_do_not_overlap",
        "workbuddy_complexity_bounded",
        "final_acceptance_separate",
    ]


def coordinate(
    payload: dict[str, Any],
    *,
    codex_active: dict[str, Any],
    workbuddy_active: dict[str, Any],
    canonical_main: str,
    observed_checkpoint_head: str,
    event: str = "AUTO",
) -> dict[str, Any]:
    checks = _validate_baton(payload)
    if event not in EVENTS:
        raise CoordinationError(f"unsupported event: {event}")
    checkpoint = payload["source_checkpoint"]
    checkpoint_matches = observed_checkpoint_head == checkpoint["exact_head"]
    if not checkpoint_matches:
        raise CoordinationError(
            "immutable checkpoint drift: "
            f"declared={checkpoint['exact_head']} observed={observed_checkpoint_head}"
        )
    codex_ready = _route_ready(codex_active, "CODEX")
    workbuddy_ready = _route_ready(workbuddy_active, "WORKBUDDY")
    workbuddy_bound_head = workbuddy_active.get("bound_source_exact_head")
    workbuddy_checkpoint_matches = (
        workbuddy_ready
        and isinstance(workbuddy_bound_head, str)
        and workbuddy_bound_head == checkpoint["exact_head"]
    )

    if event == "USER_STOP":
        phase = "PAUSED_BY_USER"
        codex_action = "STOP_AFTER_SAFE_PUSHED_CHECKPOINT"
        workbuddy_action = "STOP_WITHOUT_CLAIMING_NEW_ITEM"
        next_action = "NO_NEW_WRITES_UNTIL_USER_RESUMES"
    elif event == "USER_SYNC":
        phase = "CLOSEOUT_READY"
        codex_action = "FREEZE_EXACT_HEAD_AND_BUILD_CONSOLIDATED_HANDOFF"
        workbuddy_action = "RETURN_ALL_RECEIPTS_AND_OPEN_FINDINGS"
        next_action = "USER_MAY_REQUEST_ONE_GPT_CROSS_MODULE_REVIEW"
    elif event == "WORKBUDDY_BATCH_COMPLETE":
        phase = "WORKBUDDY_RESULT_READY"
        codex_action = "VALIDATE_WORKBUDDY_RETURN_PACKAGE_THEN_RESUME_CORE_LANE"
        workbuddy_action = "PUSH_CLEAN_BRANCH_AND_RETURN_EXACT_HEAD_PACKAGE"
        next_action = "RUN_RETURN_VALIDATOR_AND_SELECT_CODEX_REPAIR_OR_NEXT_SLICE"
    elif event == "CODEX_QUOTA_LOW":
        phase = (
            "WORKBUDDY_ROUTE_READY"
            if workbuddy_checkpoint_matches
            else "WORKBUDDY_RUNNING_DIFFERENT_CHECKPOINT"
            if workbuddy_ready
            else "BLOCKED_PENDING_WORKBUDDY_ROUTE"
        )
        codex_action = "CREATE_PUSHED_IMMUTABLE_QUOTA_CHECKPOINT_THEN_STOP"
        workbuddy_action = (
            "CLAIM_ONLY_THE_FIRST_READY_ORDERED_BATCH_ITEM"
            if workbuddy_checkpoint_matches
            else "CONTINUE_ONLY_ITS_ALREADY_BOUND_DIFFERENT_CHECKPOINT_BATCH"
            if workbuddy_ready
            else "DO_NOT_EXECUTE_CANONICAL_ROUTE_IS_NOT_READY"
        )
        next_action = (
            "WORKBUDDY_RUNS_VERIFICATION_THEN_PREAUTHORIZED_D0_D1_QUEUE"
            if workbuddy_checkpoint_matches
            else "PUSH_CODEX_CHECKPOINT_AND_WAIT_FOR_CURRENT_WORKBUDDY_RETURN_BEFORE_NEW_ROUTE"
            if workbuddy_ready
            else "GITHUB_INTEGRATOR_PUBLISHES_ONE_FRESH_BOUND_WORKBUDDY_ROUTE"
        )
    else:
        if codex_ready and workbuddy_ready:
            phase = (
                "PARALLEL_NON_OVERLAPPING_EXECUTION"
                if workbuddy_checkpoint_matches
                else "PARALLEL_NON_OVERLAPPING_DIFFERENT_CHECKPOINT_EXECUTION"
            )
            codex_action = "CONTINUE_CORE_LANE_AND_PUBLISH_MILESTONE_CHECKPOINTS"
            workbuddy_action = (
                "VERIFY_FROZEN_HEAD_THEN_CONTINUE_ORDERED_D0_D1_ITEMS"
                if workbuddy_checkpoint_matches
                else "CONTINUE_ONLY_ITS_ALREADY_BOUND_DIFFERENT_CHECKPOINT_BATCH"
            )
            next_action = (
                "BOTH_EXECUTORS_CONTINUE_ONLY_WITHIN_DISJOINT_LANES"
                if workbuddy_checkpoint_matches
                else "DO_NOT_REDIRECT_ACTIVE_WORKBUDDY_TO_NEW_CODEX_CHECKPOINT"
            )
        elif codex_ready:
            phase = "CODEX_RUNNING_WORKBUDDY_BLOCKED"
            codex_action = "CONTINUE_CORE_LANE_AND_KEEP_SAFE_PUSHED_CHECKPOINTS"
            workbuddy_action = "DO_NOT_EXECUTE_CANONICAL_ROUTE_IS_NOT_READY"
            next_action = "PUBLISH_ONE_FRESH_WORKBUDDY_ROUTE_BEFORE_QUOTA_HANDOFF"
        elif workbuddy_ready:
            phase = "WORKBUDDY_RUNNING_CODEX_BLOCKED"
            codex_action = "DO_NOT_WRITE_WITHOUT_A_FRESH_CODEX_ROUTE"
            workbuddy_action = "CONTINUE_ORDERED_BATCH_UNTIL_RETURN_OR_STOP_CONDITION"
            next_action = "WORKBUDDY_COMPLETES_BOUND_QUEUE_AND_RETURNS_TO_CODEX"
        else:
            phase = "NO_EXECUTABLE_ROUTE"
            codex_action = "DO_NOT_WRITE"
            workbuddy_action = "DO_NOT_WRITE"
            next_action = "GITHUB_INTEGRATOR_RECONCILES_AND_RELEASES_THE_NEXT_EXECUTOR"

    return {
        "schema": "CreativeExecutorCoordinationDecision/v1",
        "status": "READY" if phase not in {"NO_EXECUTABLE_ROUTE", "BLOCKED_PENDING_WORKBUDDY_ROUTE"} else "BLOCKED",
        "event": event,
        "phase": phase,
        "canonical_main": canonical_main,
        "source_checkpoint": {
            "exact_head": checkpoint["exact_head"],
            "checkpoint_remote_ref": checkpoint["checkpoint_remote_ref"],
            "observed_head": observed_checkpoint_head,
        },
        "authority": {
            "codex_ready": codex_ready,
            "workbuddy_ready": workbuddy_ready,
            "codex_task_id": codex_active.get("task_id"),
            "workbuddy_task_id": workbuddy_active.get("task_id"),
            "workbuddy_bound_source_exact_head": workbuddy_bound_head,
            "workbuddy_checkpoint_matches_baton": workbuddy_checkpoint_matches,
        },
        "codex_action": codex_action,
        "workbuddy_action": workbuddy_action,
        "unique_next_action": next_action,
        "checks": checks + ["checkpoint_remote_identity_matches"],
        "authority_note": "This decision is read-only and cannot create execution, review or merge authority.",
    }


def coordinate_from_repository(*, repo: Path, main_ref: str, baton_path: Path, event: str) -> dict[str, Any]:
    repo = repo.resolve(strict=True)
    path = baton_path if baton_path.is_absolute() else repo / baton_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CoordinationError(f"cannot read baton: {exc}") from exc
    codex_active = parse_top_level_scalars(
        _git(repo, "show", f"{main_ref}:coordination/ACTIVE-CODEX-TASK.yaml")
    )
    workbuddy_text = _git(repo, "show", f"{main_ref}:coordination/ACTIVE-WORKBUDDY-TASK.yaml")
    workbuddy_active = parse_top_level_scalars(workbuddy_text)
    workbuddy_active["bound_source_exact_head"] = parse_nested_scalars(
        workbuddy_text, "source_checkpoint"
    ).get("exact_head")
    canonical_main = _git(repo, "rev-parse", main_ref)
    checkpoint_ref = payload.get("source_checkpoint", {}).get("checkpoint_remote_ref", "")
    observed_checkpoint_head = _git(repo, "rev-parse", checkpoint_ref)
    return coordinate(
        payload,
        codex_active=codex_active,
        workbuddy_active=workbuddy_active,
        canonical_main=canonical_main,
        observed_checkpoint_head=observed_checkpoint_head,
        event=event,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--main-ref", default="origin/main")
    parser.add_argument("--baton", type=Path, required=True)
    parser.add_argument("--event", choices=sorted(EVENTS), default="AUTO")
    args = parser.parse_args()
    try:
        result = coordinate_from_repository(
            repo=args.repo,
            main_ref=args.main_ref,
            baton_path=args.baton,
            event=args.event,
        )
    except CoordinationError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
