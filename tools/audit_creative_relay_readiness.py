"""Audit whether canonical WorkBuddy authority can consume a relay package."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    from tools.validate_creative_executor_relay import RelayValidationError, validate_package
except ModuleNotFoundError:  # Direct execution from the tools directory.
    from validate_creative_executor_relay import RelayValidationError, validate_package


TOP_LEVEL = re.compile(r"^([A-Za-z0-9_]+):(?:\s*(.*))?$")


class ReadinessAuditError(RuntimeError):
    """Raised when authoritative readiness evidence cannot be read."""


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
        raise ReadinessAuditError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout.strip()


def parse_top_level_scalars(text: str) -> dict[str, Any]:
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


def audit_readiness(*, repo: Path, main_ref: str, package_path: Path) -> dict[str, Any]:
    repo = repo.resolve(strict=True)
    package_abs = package_path if package_path.is_absolute() else repo / package_path
    try:
        package = json.loads(package_abs.read_text(encoding="utf-8"))
        package_checks = validate_package(package)
    except (OSError, UnicodeError, json.JSONDecodeError, RelayValidationError) as exc:
        raise ReadinessAuditError(f"relay package invalid: {exc}") from exc

    active_path = "coordination/ACTIVE-WORKBUDDY-TASK.yaml"
    active_text = _git(repo, "show", f"{main_ref}:{active_path}")
    active = parse_top_level_scalars(active_text)
    canonical_main = _git(repo, "rev-parse", main_ref)
    source = package["source"]
    target_route = package["target"]["route_authority"]
    checkpoint_remote_ref = source["checkpoint_remote_ref"]
    checkpoint_remote_head = _git(repo, "rev-parse", checkpoint_remote_ref)

    blockers: list[dict[str, str]] = []
    if checkpoint_remote_head != source["exact_head"]:
        blockers.append(
            {
                "code": "CHECKPOINT_REMOTE_HEAD_MISMATCH",
                "detail": f"declared={source['exact_head']} observed={checkpoint_remote_head}",
            }
        )
    if active.get("target_agent") != "WORKBUDDY":
        blockers.append({"code": "ACTIVE_TARGET_NOT_WORKBUDDY", "detail": str(active.get("target_agent"))})
    if active.get("status") != "READY":
        blockers.append({"code": "ACTIVE_WORKBUDDY_NOT_READY", "detail": str(active.get("status"))})
    if active.get("execution_allowed") is not True:
        blockers.append({"code": "ACTIVE_WORKBUDDY_EXECUTION_DISABLED", "detail": "execution_allowed is not true"})
    if target_route.get("execution_allowed") is not True:
        blockers.append({"code": "RELAY_PACKAGE_NOT_BOUND_TO_EXECUTABLE_ROUTE", "detail": package["relay_state"]})

    if active.get("execution_allowed") is True and target_route.get("execution_allowed") is True:
        identity_pairs = (
            ("task_id", "task_id"),
            ("active_issue", "active_issue"),
            ("route_epoch", "route_epoch"),
        )
        for active_key, route_key in identity_pairs:
            if active.get(active_key) != target_route.get(route_key):
                blockers.append(
                    {
                        "code": "ROUTE_IDENTITY_MISMATCH",
                        "detail": f"{active_key}: active={active.get(active_key)} package={target_route.get(route_key)}",
                    }
                )

    ready = not blockers
    unique_next_action = (
        "WORKBUDDY_MAY_CLAIM_AND_EXECUTE_THE_BOUND_RELAY_PACKAGE"
        if ready
        else "GITHUB_INTEGRATOR_MUST_PUBLISH_AND_BIND_A_FRESH_EXECUTABLE_WORKBUDDY_ROUTE"
    )
    return {
        "schema": "CreativeRelayReadinessAudit/v1",
        "status": "READY" if ready else "BLOCKED",
        "canonical_main_ref": main_ref,
        "canonical_main": canonical_main,
        "active_workbuddy": {
            key: active.get(key)
            for key in ("task_id", "active_issue", "route_epoch", "status", "execution_allowed")
        },
        "source_checkpoint": {
            "declared_head": source["exact_head"],
            "remote_ref": checkpoint_remote_ref,
            "observed_head": checkpoint_remote_head,
        },
        "relay_state": package["relay_state"],
        "package_checks": package_checks,
        "blockers": blockers,
        "unique_next_action": unique_next_action,
        "authority_note": "This audit observes authority; it never grants execution, review or merge power.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--main-ref", default="origin/main")
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit_readiness(repo=args.repo, main_ref=args.main_ref, package_path=args.package)
    except ReadinessAuditError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
