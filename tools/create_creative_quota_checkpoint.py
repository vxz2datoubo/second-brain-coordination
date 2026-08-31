"""Create a hashed quota checkpoint after proving local and remote Git identity."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
AGENT_PREFIX = {"CODEX": "codex/", "WORKBUDDY": "workbuddy/"}
RESULTS = {"PASS", "FAIL", "SKIP", "NOT_RUN"}


class CheckpointError(RuntimeError):
    """Raised when a safe quota checkpoint cannot be proven."""


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", os.fspath(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise CheckpointError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout.strip()


def _parse_test(value: str) -> dict[str, str]:
    if "=" not in value:
        raise CheckpointError("test must use NAME=PASS|FAIL|SKIP|NOT_RUN")
    name, result = value.split("=", 1)
    name = name.strip()
    result = result.strip().upper()
    if not name or result not in RESULTS:
        raise CheckpointError("test must use NAME=PASS|FAIL|SKIP|NOT_RUN")
    return {"name": name, "result": result}


def _assert_sha(value: str, label: str) -> None:
    if not SHA_RE.fullmatch(value):
        raise CheckpointError(f"{label} must be a lowercase 40-character SHA")


def _safe_output(repo: Path, output: Path) -> Path:
    root = repo.resolve(strict=True)
    candidate = output if output.is_absolute() else root / output
    candidate = candidate.resolve(strict=False)
    evidence_root = (root / ".creative-evidence").resolve(strict=False)
    try:
        candidate.relative_to(evidence_root)
    except ValueError as exc:
        raise CheckpointError("receipt output must stay under .creative-evidence") from exc
    cursor = candidate.parent
    while cursor != root and cursor != cursor.parent:
        if cursor.exists() and cursor.is_symlink():
            raise CheckpointError("receipt output ancestry cannot contain a symlink")
        cursor = cursor.parent
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def build_checkpoint(
    *,
    repo: Path,
    source_agent: str,
    target_agent: str,
    baseline: str,
    checkpoint_remote_ref: str,
    remaining_next_action: str,
    tests: Iterable[str],
    completed_scope: Iterable[str],
) -> dict[str, Any]:
    repo = repo.resolve(strict=True)
    if source_agent not in AGENT_PREFIX or target_agent not in AGENT_PREFIX:
        raise CheckpointError("source and target must be CODEX or WORKBUDDY")
    if source_agent == target_agent:
        raise CheckpointError("source and target agents must differ")
    _assert_sha(baseline, "baseline")
    if not remaining_next_action.strip():
        raise CheckpointError("remaining_next_action must be non-empty")

    top = Path(_git(repo, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top != repo:
        raise CheckpointError("repo must be the Git toplevel")
    dirty = _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    if dirty:
        raise CheckpointError("worktree must be clean before checkpoint generation")
    branch = _git(repo, "symbolic-ref", "--quiet", "--short", "HEAD")
    if not branch.startswith(AGENT_PREFIX[source_agent]):
        raise CheckpointError("current branch does not identify source_agent")
    head = _git(repo, "rev-parse", "HEAD")
    remote_head = _git(repo, "rev-parse", checkpoint_remote_ref)
    _assert_sha(head, "HEAD")
    _assert_sha(remote_head, "checkpoint remote HEAD")
    if remote_head != head:
        raise CheckpointError(
            f"checkpoint remote mismatch: local={head} remote={remote_head}"
        )
    expected_prefix = f"refs/remotes/origin/{AGENT_PREFIX[source_agent]}checkpoint-"
    if not checkpoint_remote_ref.startswith(expected_prefix):
        raise CheckpointError("checkpoint_remote_ref must be a dedicated executor checkpoint ref")

    parsed_tests = [_parse_test(item) for item in tests]
    if not parsed_tests:
        raise CheckpointError("at least one test result is required")
    buildable = all(item["result"] in {"PASS", "SKIP"} for item in parsed_tests)
    return {
        "schema": "CreativeQuotaCheckpoint/v1",
        "checkpoint_id": f"{source_agent}-{head[:12]}",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_agent": source_agent,
        "target_agent": target_agent,
        "reason": "COMPUTE_LIMIT_OR_SAFE_NATURAL_BOUNDARY",
        "repository": "vxz2datoubo/second-brain-coordination",
        "branch": branch,
        "baseline": baseline,
        "exact_head": head,
        "checkpoint_remote_ref": checkpoint_remote_ref,
        "remote_head": remote_head,
        "pushed": True,
        "worktree_clean": True,
        "buildable": buildable,
        "completed_scope": list(completed_scope),
        "remaining_single_next_action": remaining_next_action,
        "tests": parsed_tests,
        "raw_logs_embedded": False,
        "final_acceptance": False,
        "rollback": "Create a normal revert commit; never rewrite shared history.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--source-agent", choices=sorted(AGENT_PREFIX), required=True)
    parser.add_argument("--target-agent", choices=sorted(AGENT_PREFIX), required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--checkpoint-remote-ref", required=True)
    parser.add_argument("--remaining-next-action", required=True)
    parser.add_argument("--test", action="append", default=[])
    parser.add_argument("--completed", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = build_checkpoint(
            repo=args.repo,
            source_agent=args.source_agent,
            target_agent=args.target_agent,
            baseline=args.baseline,
            checkpoint_remote_ref=args.checkpoint_remote_ref,
            remaining_next_action=args.remaining_next_action,
            tests=args.test,
            completed_scope=args.completed,
        )
        output = _safe_output(args.repo, args.output)
        encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        output.write_bytes(encoded)
        if _git(args.repo.resolve(), "status", "--porcelain=v1", "--untracked-files=all"):
            output.unlink(missing_ok=True)
            raise CheckpointError("checkpoint output made the tracked worktree dirty")
    except (OSError, UnicodeError, CheckpointError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "output": output.relative_to(args.repo.resolve()).as_posix(),
                "receipt_sha256": hashlib.sha256(encoded).hexdigest(),
                "exact_head": payload["exact_head"],
                "checkpoint_remote_ref": payload["checkpoint_remote_ref"],
                "buildable": payload["buildable"],
                "final_acceptance": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
