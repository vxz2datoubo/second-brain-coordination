"""Validate a Codex/WorkBuddy relay package without granting authority."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
AGENT_PREFIX = {"CODEX": "codex/", "WORKBUDDY": "workbuddy/"}
ALLOWED_STATES = {
    "CODEX_CHECKPOINT_READY",
    "BLOCKED_PENDING_TARGET_ROUTE",
    "WORKBUDDY_ROUTE_READY",
    "WORKBUDDY_RUNNING",
    "WORKBUDDY_RESULT_READY",
    "CODEX_RESUME_READY",
    "STAGE_CLOSEOUT_READY",
}


class RelayValidationError(ValueError):
    """Raised when a relay package is unsafe or internally inconsistent."""


def _require(mapping: dict[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise RelayValidationError(f"{where}.{key} is required")
    return mapping[key]


def _normalized_surface(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RelayValidationError("write surfaces must be non-empty strings")
    raw = value.replace("\\", "/").strip().removesuffix("/**").rstrip("/")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts:
        raise RelayValidationError(f"unsafe write surface: {value}")
    return path.as_posix().casefold()


def _overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def validate_package(payload: dict[str, Any]) -> list[str]:
    if payload.get("schema") != "CreativeExecutorRelayPackage/v1":
        raise RelayValidationError("unsupported schema")
    state = _require(payload, "relay_state", "package")
    if state not in ALLOWED_STATES:
        raise RelayValidationError(f"unsupported relay_state: {state}")

    source = _require(payload, "source", "package")
    target = _require(payload, "target", "package")
    if not isinstance(source, dict) or not isinstance(target, dict):
        raise RelayValidationError("source and target must be objects")
    source_agent = _require(source, "agent", "source")
    target_agent = _require(target, "agent", "target")
    if source_agent == target_agent:
        raise RelayValidationError("source and target agents must differ")
    if source_agent not in AGENT_PREFIX or target_agent not in AGENT_PREFIX:
        raise RelayValidationError("only CODEX and WORKBUDDY executor relay is supported")

    source_branch = _require(source, "branch", "source")
    if not isinstance(source_branch, str) or not source_branch.startswith(AGENT_PREFIX[source_agent]):
        raise RelayValidationError("source branch does not identify its executor")
    target_branch = _require(target, "proposed_branch", "target")
    if not isinstance(target_branch, str) or not target_branch.startswith(AGENT_PREFIX[target_agent]):
        raise RelayValidationError("target branch does not identify its executor")
    for field in ("baseline", "exact_head"):
        value = _require(source, field, "source")
        if not isinstance(value, str) or not SHA_RE.fullmatch(value):
            raise RelayValidationError(f"source.{field} must be a lowercase 40-character SHA")
    if source.get("pushed") is not True or source.get("worktree_clean_at_checkpoint") is not True:
        raise RelayValidationError("relay source must be pushed and recorded clean")

    source_surfaces = [_normalized_surface(item) for item in _require(source, "write_surfaces", "source")]
    target_surfaces = [
        _normalized_surface(item)
        for item in _require(target, "write_surfaces_after_future_route", "target")
    ]
    for left in source_surfaces:
        for right in target_surfaces:
            if _overlap(left, right):
                raise RelayValidationError(f"single-writer overlap: {left} <> {right}")

    route = _require(target, "route_authority", "target")
    if not isinstance(route, dict):
        raise RelayValidationError("target.route_authority must be an object")
    executable = route.get("execution_allowed") is True
    authority_refs = ("route_ref", "claim_ref", "lease_ref", "snapshot_ref")
    if executable:
        missing = [name for name in authority_refs if not route.get(name)]
        if missing:
            raise RelayValidationError("executable target route lacks: " + ", ".join(missing))
        if state not in {"WORKBUDDY_ROUTE_READY", "WORKBUDDY_RUNNING", "WORKBUDDY_RESULT_READY"}:
            raise RelayValidationError("executable target route conflicts with relay_state")
    elif state != "BLOCKED_PENDING_TARGET_ROUTE":
        raise RelayValidationError("non-executable target must fail closed in BLOCKED_PENDING_TARGET_ROUTE")

    plan = _require(payload, "verification_plan", "package")
    commands = _require(plan, "commands", "verification_plan")
    if not isinstance(commands, list) or not commands or not all(isinstance(item, str) and item for item in commands):
        raise RelayValidationError("verification_plan.commands must be a non-empty string list")
    forbidden_command_fragments = ("--token", "--password", "--secret", "api_key=", "cookie=")
    for command in commands:
        if any(fragment in command.casefold() for fragment in forbidden_command_fragments):
            raise RelayValidationError("verification command appears to contain secret material")
    semantics = _require(plan, "receipt_semantics", "verification_plan")
    if semantics.get("independent_acceptance") is not False or semantics.get("may_ready_or_merge") is not False:
        raise RelayValidationError("executor receipt cannot grant acceptance or merge authority")

    return [
        "schema_valid",
        "agent_identity_valid",
        "exact_sha_valid",
        "checkpoint_pushed_and_clean",
        "single_writer_surfaces_disjoint",
        "target_authority_fail_closed" if not executable else "target_authority_complete",
        "receipt_semantics_safe",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.package.read_text(encoding="utf-8"))
        checks = validate_package(payload)
    except (OSError, json.JSONDecodeError, RelayValidationError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "PASS", "checks": checks}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
