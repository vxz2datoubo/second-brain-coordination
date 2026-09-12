"""Validate and select work from an ordered Codex/WorkBuddy batch.

The evaluator deliberately cannot create authority.  A valid batch remains
BLOCKED until its WorkBuddy route is executable and fully bound.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ITEM_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,63}$")
KINDS = {
    "CLEAN_REPRODUCTION",
    "ADVERSARIAL_MATRIX",
    "RECOVERY_MATRIX",
    "CONCURRENCY_MATRIX",
    "STORAGE_MATRIX",
    "SOAK_TEST",
    "ENVIRONMENT_PROBE",
    "SIMPLE_IMPLEMENTATION",
}
STATUSES = {"PLANNED", "RUNNING", "COMPLETE", "BLOCKED"}
READ_ONLY_KINDS = KINDS - {"SIMPLE_IMPLEMENTATION"}


class BatchValidationError(ValueError):
    """Raised when a batch could cause unsafe or ambiguous execution."""


def _require(mapping: dict[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise BatchValidationError(f"{where}.{key} is required")
    return mapping[key]


def _surface(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BatchValidationError("write paths must be non-empty strings")
    raw = value.replace("\\", "/").strip().removesuffix("/**").rstrip("/")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts:
        raise BatchValidationError(f"unsafe write path: {value}")
    return path.as_posix().casefold()


def _overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def _assert_acyclic(items: dict[str, dict[str, Any]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item_id: str) -> None:
        if item_id in visiting:
            raise BatchValidationError(f"dependency cycle contains {item_id}")
        if item_id in visited:
            return
        visiting.add(item_id)
        for dependency in items[item_id]["depends_on"]:
            if dependency not in items:
                raise BatchValidationError(f"unknown dependency: {dependency}")
            visit(dependency)
        visiting.remove(item_id)
        visited.add(item_id)

    for item_id in items:
        visit(item_id)


def evaluate_batch(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema") != "CreativeExecutorWorkBatch/v1":
        raise BatchValidationError("unsupported schema")
    checkpoint = _require(payload, "source_checkpoint", "batch")
    exact_head = _require(checkpoint, "exact_head", "source_checkpoint")
    if not isinstance(exact_head, str) or not SHA_RE.fullmatch(exact_head):
        raise BatchValidationError("source_checkpoint.exact_head must be a 40-character SHA")
    branch = _require(checkpoint, "branch", "source_checkpoint")
    if not isinstance(branch, str) or not branch.startswith("codex/"):
        raise BatchValidationError("source checkpoint branch must identify CODEX")
    checkpoint_ref = _require(checkpoint, "checkpoint_remote_ref", "source_checkpoint")
    if not isinstance(checkpoint_ref, str) or not checkpoint_ref.startswith(
        "refs/remotes/origin/codex/checkpoint-"
    ):
        raise BatchValidationError("source checkpoint must use a dedicated Codex checkpoint ref")

    retained = [_surface(item) for item in _require(payload, "codex_retained_write_surfaces", "batch")]
    raw_items = _require(payload, "items", "batch")
    if not isinstance(raw_items, list) or not raw_items:
        raise BatchValidationError("batch.items must be a non-empty list")
    items: dict[str, dict[str, Any]] = {}
    implementation_surfaces: list[tuple[str, str]] = []
    checkpoint_identity_bound = False
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            raise BatchValidationError(f"items[{index}] must be an object")
        item_id = _require(item, "item_id", f"items[{index}]")
        if not isinstance(item_id, str) or not ITEM_ID_RE.fullmatch(item_id):
            raise BatchValidationError(f"invalid item_id: {item_id}")
        if item_id in items:
            raise BatchValidationError(f"duplicate item_id: {item_id}")
        if item.get("owner") != "WORKBUDDY":
            raise BatchValidationError(f"{item_id} owner must be WORKBUDDY")
        kind = _require(item, "kind", item_id)
        if kind not in KINDS:
            raise BatchValidationError(f"unsupported kind for {item_id}: {kind}")
        status = _require(item, "status", item_id)
        if status not in STATUSES:
            raise BatchValidationError(f"unsupported status for {item_id}: {status}")
        complexity = _require(item, "complexity", item_id)
        if kind == "SIMPLE_IMPLEMENTATION" and complexity not in {"D0", "D1"}:
            raise BatchValidationError(f"{item_id} exceeds WorkBuddy implementation complexity ceiling")
        dependencies = _require(item, "depends_on", item_id)
        if not isinstance(dependencies, list) or not all(isinstance(dep, str) for dep in dependencies):
            raise BatchValidationError(f"{item_id}.depends_on must be a string list")
        commands = _require(item, "acceptance_commands", item_id)
        if not isinstance(commands, list) or not commands or not all(
            isinstance(command, str) and command.strip() for command in commands
        ):
            raise BatchValidationError(f"{item_id} requires acceptance commands")
        forbidden_fragments = ("--token", "--password", "--secret", "api_key=", "cookie=")
        if any(
            fragment in command.casefold()
            for command in commands
            for fragment in forbidden_fragments
        ):
            raise BatchValidationError(f"{item_id} acceptance command appears to contain secret material")
        if kind == "CLEAN_REPRODUCTION" and any(
            exact_head in command and checkpoint_ref in command for command in commands
        ):
            checkpoint_identity_bound = True
        if item.get("architecture_change") is not False or item.get("acceptance_oracle_change") is not False:
            raise BatchValidationError(f"{item_id} attempts a reserved Codex decision")
        write_paths = [_surface(path) for path in _require(item, "write_paths", item_id)]
        if kind in READ_ONLY_KINDS and write_paths:
            raise BatchValidationError(f"read-only verification item {item_id} cannot declare write paths")
        if kind == "SIMPLE_IMPLEMENTATION" and not write_paths:
            raise BatchValidationError(f"simple implementation {item_id} requires an isolated write path")
        for write_path in write_paths:
            for codex_path in retained:
                if _overlap(write_path, codex_path):
                    raise BatchValidationError(
                        f"single-writer overlap: {item_id}:{write_path} <> CODEX:{codex_path}"
                    )
            for prior_id, prior_path in implementation_surfaces:
                if _overlap(write_path, prior_path):
                    raise BatchValidationError(
                        f"WorkBuddy item overlap: {item_id}:{write_path} <> {prior_id}:{prior_path}"
                    )
            implementation_surfaces.append((item_id, write_path))
        if status == "COMPLETE" and not item.get("receipt_ref"):
            raise BatchValidationError(f"completed item {item_id} requires receipt_ref")
        items[item_id] = item
    _assert_acyclic(items)
    if not checkpoint_identity_bound:
        raise BatchValidationError(
            "CLEAN_REPRODUCTION must bind the declared exact head and checkpoint remote ref"
        )

    route = _require(payload, "route_authority", "batch")
    route_fields = ("task_id", "active_issue", "route_epoch", "route_ref", "claim_ref", "lease_ref", "snapshot_ref")
    route_ready = route.get("execution_allowed") is True and all(route.get(field) for field in route_fields)
    blockers: list[dict[str, str]] = []
    if not route_ready:
        blockers.append(
            {
                "code": "WORKBUDDY_ROUTE_NOT_EXECUTABLE",
                "detail": "A canonical route, claim, lease and pre-write snapshot must be bound before execution.",
            }
        )
    running = [item_id for item_id, item in items.items() if item["status"] == "RUNNING"]
    if len(running) > 1:
        raise BatchValidationError("only one ordered batch item may be RUNNING")
    blocked_items = [item_id for item_id, item in items.items() if item["status"] == "BLOCKED"]
    if blocked_items:
        blockers.append({"code": "BATCH_ITEM_BLOCKED", "detail": ",".join(blocked_items)})

    ready_items: list[str] = []
    if route_ready and not blockers and not running:
        for item_id, item in items.items():
            if item["status"] != "PLANNED":
                continue
            if all(items[dependency]["status"] == "COMPLETE" for dependency in item["depends_on"]):
                ready_items.append(item_id)
        ready_items = ready_items[:1]
    complete = all(item["status"] == "COMPLETE" for item in items.values())
    if complete:
        state = "RETURN_TO_CODEX"
        next_action = "PUBLISH_WORKBUDDY_RETURN_PACKAGE_AND_HAND_BATON_TO_CODEX"
    elif blockers:
        state = "BLOCKED"
        next_action = (
            "GITHUB_INTEGRATOR_MUST_PUBLISH_AND_BIND_EXECUTABLE_WORKBUDDY_ROUTE"
            if blockers[0]["code"] == "WORKBUDDY_ROUTE_NOT_EXECUTABLE"
            else "WORKBUDDY_MUST_RETURN_BLOCKING_FINDING_TO_CODEX"
        )
    elif running:
        state = "RUNNING"
        next_action = f"COMPLETE_CURRENT_ITEM:{running[0]}"
    elif ready_items:
        state = "READY"
        next_action = f"WORKBUDDY_MAY_CLAIM_ITEM:{ready_items[0]}"
    else:
        state = "BLOCKED"
        next_action = "RECONCILE_ITEM_DEPENDENCIES_AND_RECEIPTS"
    return {
        "schema": "CreativeExecutorWorkBatchEvaluation/v1",
        "status": state,
        "source_exact_head": exact_head,
        "route_ready": route_ready,
        "running_items": running,
        "ready_items": ready_items,
        "completed_items": [item_id for item_id, item in items.items() if item["status"] == "COMPLETE"],
        "blockers": blockers,
        "next_action": next_action,
        "authority_note": "This evaluator observes a governed batch; it never grants execution, review or merge authority.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.batch.read_text(encoding="utf-8"))
        result = evaluate_batch(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, BatchValidationError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"READY", "RUNNING", "RETURN_TO_CODEX"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
