"""Validate a WorkBuddy-to-Codex return package without granting acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
RESULTS = {"PASS", "FAIL", "PARTIAL", "BLOCKED"}


class ReturnValidationError(ValueError):
    """Raised when a WorkBuddy return package is unsafe or contradictory."""


def _require(mapping: dict[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise ReturnValidationError(f"{where}.{key} is required")
    return mapping[key]


def _safe_relative(value: str, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReturnValidationError(f"{where} must be a non-empty string")
    normalized = value.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ReturnValidationError(f"{where} escapes repository: {value}")
    return path.as_posix()


def _within(path: str, roots: list[str]) -> bool:
    folded = path.casefold()
    return any(
        folded == root.casefold() or folded.startswith(root.casefold().rstrip("/") + "/")
        for root in roots
    )


def validate_return(payload: dict[str, Any]) -> list[str]:
    if payload.get("schema") != "WorkBuddyRelayResult/v1":
        raise ReturnValidationError("unsupported schema")
    if payload.get("agent_id") != "WORKBUDDY" or payload.get("return_target") != "CODEX":
        raise ReturnValidationError("return identity must be WORKBUDDY to CODEX")

    source = _require(payload, "source_checkpoint", "package")
    if not isinstance(source, dict):
        raise ReturnValidationError("source_checkpoint must be an object")
    for field in ("exact_head", "baseline"):
        value = _require(source, field, "source_checkpoint")
        if not isinstance(value, str) or not SHA_RE.fullmatch(value):
            raise ReturnValidationError(f"source_checkpoint.{field} must be a 40-character SHA")
    remote_ref = _require(source, "checkpoint_remote_ref", "source_checkpoint")
    if not isinstance(remote_ref, str) or not remote_ref.startswith(
        "refs/remotes/origin/codex/checkpoint-"
    ):
        raise ReturnValidationError("source checkpoint must use an immutable Codex checkpoint ref")

    route = _require(payload, "route_authority", "package")
    if route.get("execution_allowed") is not True:
        raise ReturnValidationError("WorkBuddy result requires the executable route used for the work")
    for field in ("route_ref", "claim_ref", "lease_ref", "snapshot_ref"):
        if not route.get(field):
            raise ReturnValidationError(f"route_authority.{field} is required")

    result = _require(payload, "result", "package")
    if result not in RESULTS:
        raise ReturnValidationError(f"unsupported result: {result}")
    work = _require(payload, "workbuddy_work", "package")
    if not isinstance(work, dict):
        raise ReturnValidationError("workbuddy_work must be an object")
    branch = _require(work, "branch", "workbuddy_work")
    if not isinstance(branch, str) or not branch.startswith("workbuddy/"):
        raise ReturnValidationError("WorkBuddy implementation must use a workbuddy branch")
    head = _require(work, "exact_head", "workbuddy_work")
    if not isinstance(head, str) or not SHA_RE.fullmatch(head):
        raise ReturnValidationError("workbuddy_work.exact_head must be a 40-character SHA")
    if work.get("pushed") is not True or work.get("worktree_clean") is not True:
        raise ReturnValidationError("WorkBuddy return must be pushed and recorded clean")

    allowed_roots = [
        _safe_relative(item.replace("/**", ""), "allowed_write_paths")
        for item in _require(work, "allowed_write_paths", "workbuddy_work")
    ]
    changed_paths = [
        _safe_relative(item, "changed_paths")
        for item in _require(work, "changed_paths", "workbuddy_work")
    ]
    outside = [path for path in changed_paths if not _within(path, allowed_roots)]
    if outside:
        raise ReturnValidationError("changed paths outside WorkBuddy allowlist: " + ", ".join(outside))

    receipts = _require(payload, "receipts", "package")
    if not isinstance(receipts, list) or not receipts:
        raise ReturnValidationError("at least one receipt is required")
    receipt_results: list[str] = []
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, dict):
            raise ReturnValidationError(f"receipts[{index}] must be an object")
        command = _require(receipt, "command", f"receipts[{index}]")
        if not isinstance(command, str) or not command:
            raise ReturnValidationError(f"receipts[{index}].command must be non-empty")
        receipt_result = _require(receipt, "result", f"receipts[{index}]")
        if receipt_result not in {"PASS", "FAIL", "SKIP"}:
            raise ReturnValidationError(f"invalid receipt result: {receipt_result}")
        receipt_results.append(receipt_result)
        for field in ("stdout_sha256", "stderr_sha256"):
            digest = _require(receipt, field, f"receipts[{index}]")
            if not isinstance(digest, str) or not HASH_RE.fullmatch(digest):
                raise ReturnValidationError(f"receipts[{index}].{field} must be SHA-256")

    findings = _require(payload, "findings", "package")
    if not isinstance(findings, list):
        raise ReturnValidationError("findings must be a list")
    blocking_findings = [item for item in findings if isinstance(item, dict) and item.get("blocks_milestone")]
    if result == "PASS" and ("FAIL" in receipt_results or blocking_findings):
        raise ReturnValidationError("PASS contradicts failed receipts or blocking findings")
    if result == "FAIL" and "FAIL" not in receipt_results and not blocking_findings:
        raise ReturnValidationError("FAIL requires failed evidence or a blocking finding")

    integrity = _require(payload, "integrity", "package")
    required_false = (
        "acceptance_oracle_changed",
        "codex_branch_patched",
        "independent_acceptance",
        "ready_or_merge_authorized",
        "credentials_or_real_user_data_used",
        "external_paid_generation_used",
    )
    invalid = [field for field in required_false if integrity.get(field) is not False]
    if invalid:
        raise ReturnValidationError("unsafe integrity flags: " + ", ".join(invalid))

    next_action = _require(payload, "single_next_action", "package")
    if not isinstance(next_action, str) or not next_action.strip():
        raise ReturnValidationError("single_next_action must be non-empty")
    return [
        "identity_valid",
        "source_checkpoint_bound",
        "route_authority_complete",
        "workbuddy_branch_pushed_and_clean",
        "changed_paths_within_allowlist",
        "receipts_consistent_with_result",
        "integrity_flags_safe",
        "codex_return_action_present",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    try:
        raw = args.package.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        checks = validate_return(payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ReturnValidationError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "package_sha256": hashlib.sha256(raw).hexdigest(),
                "checks": checks,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
