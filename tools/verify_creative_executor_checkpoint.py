"""One-command exact-head clean reproduction for Codex or WorkBuddy.

This runner orchestrates the existing creative tests and R175 gates without
claiming independent acceptance. It records hashes of captured command output
instead of embedding potentially sensitive logs in the durable receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Iterable, Sequence


SCHEMA = "CreativeExecutorCleanReproductionReceipt/v1"
_HEX40 = re.compile(r"\A[0-9a-f]{40}\Z")
_EXECUTOR_AGENTS = frozenset({"CODEX", "WORKBUDDY"})
_REMOTE_REF = re.compile(r"\Arefs/remotes/origin/[A-Za-z0-9][A-Za-z0-9._/-]*\Z")


class ReproductionViolation(ValueError):
    """The requested exact-head reproduction could not be proven."""


def _run(
    command: Sequence[str],
    *,
    repo: Path,
    timeout_seconds: int,
) -> tuple[int, bytes, bytes, int]:
    started = time.monotonic_ns()
    try:
        completed = subprocess.run(
            list(command),
            cwd=repo,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
        )
        return (
            completed.returncode,
            completed.stdout,
            completed.stderr,
            (time.monotonic_ns() - started) // 1_000_000,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout if isinstance(error.stdout, bytes) else (error.stdout or "").encode()
        stderr = error.stderr if isinstance(error.stderr, bytes) else (error.stderr or "").encode()
        return 124, stdout, stderr, (time.monotonic_ns() - started) // 1_000_000
    except OSError as error:
        return 127, b"", str(error).encode("utf-8", errors="replace"), (time.monotonic_ns() - started) // 1_000_000


def _git_text(repo: Path, *arguments: str) -> str:
    try:
        return subprocess.run(
            ["git", *arguments], cwd=repo, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ReproductionViolation(f"Git preflight failed: {' '.join(arguments)}") from error


def _command_plan(
    repo: Path,
    *,
    expected_head: str,
    baseline: str,
    policy_floor_ref: str,
) -> list[tuple[str, list[str]]]:
    python = sys.executable
    public_receipt = repo / ".creative-evidence" / f"public-safe-{expected_head}.json"
    return [
        (
            "creative_test_suite",
            [python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_creative_*.py"],
        ),
        (
            "public_safe_boundary",
            [
                python, "tools/verify_public_safe_boundary.py", "--repo", ".",
                "--policy-floor-ref", policy_floor_ref, "--expected-head", expected_head,
                "--receipt", str(public_receipt),
            ],
        ),
        (
            "r175_changed_path_scope",
            [python, "tools/verify_r175_scope.py", "--repo", ".", "--head", expected_head],
        ),
        ("git_diff_check", ["git", "diff", "--check", f"{baseline}...{expected_head}"]),
    ]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def run_clean_reproduction(
    repo: Path,
    *,
    expected_head: str,
    baseline: str,
    policy_floor_ref: str,
    agent_id: str,
    remote_ref: str | None = None,
    timeout_seconds: int = 300,
    command_plan: Sequence[tuple[str, Sequence[str]]] | None = None,
) -> dict[str, object]:
    repo = repo.resolve()
    for label, value in (
        ("expected_head", expected_head),
        ("baseline", baseline),
        ("policy_floor_ref", policy_floor_ref),
    ):
        if not _HEX40.fullmatch(value):
            raise ReproductionViolation(f"{label} must be an exact lowercase 40-hex commit")
    if agent_id not in _EXECUTOR_AGENTS:
        raise ReproductionViolation("agent_id must be CODEX or WORKBUDDY; this runner cannot claim GPT review")
    if remote_ref is not None and (
        not _REMOTE_REF.fullmatch(remote_ref)
        or ".." in remote_ref.split("/")
    ):
        raise ReproductionViolation("remote_ref must be a canonical refs/remotes/origin/... reference")
    if timeout_seconds < 1 or timeout_seconds > 3600:
        raise ReproductionViolation("timeout_seconds must be between 1 and 3600")
    if not repo.is_dir() or (repo / ".git").is_symlink():
        raise ReproductionViolation("repo must be a local non-link Git working directory")

    receipt: dict[str, object] = {
        "schema": SCHEMA,
        "status": "FAIL",
        "verification_class": "EXECUTOR_CLEAN_REPRODUCTION",
        "independent_acceptance": False,
        "agent_id": agent_id,
        "expected_head": expected_head,
        "baseline": baseline,
        "policy_floor_ref": policy_floor_ref,
        "remote_ref": remote_ref,
        "runner_sha256": _sha256(Path(__file__).read_bytes()),
        "commands": [],
    }
    actual_head = _git_text(repo, "rev-parse", "HEAD")
    receipt["actual_head_before"] = actual_head
    if actual_head != expected_head:
        receipt["failure_stage"] = "PRE_HEAD_IDENTITY"
        return receipt
    if remote_ref is not None:
        remote_head = _git_text(repo, "rev-parse", "--verify", remote_ref)
        receipt["remote_head"] = remote_head
        if remote_head != expected_head:
            receipt["failure_stage"] = "PRE_REMOTE_IDENTITY"
            return receipt
    dirty_before = _git_text(repo, "status", "--porcelain", "--untracked-files=all")
    if dirty_before:
        receipt["failure_stage"] = "PRE_WORKTREE_CLEANLINESS"
        receipt["dirty_path_count"] = len(dirty_before.splitlines())
        return receipt

    plan = list(command_plan) if command_plan is not None else _command_plan(
        repo,
        expected_head=expected_head,
        baseline=baseline,
        policy_floor_ref=policy_floor_ref,
    )
    results: list[dict[str, object]] = []
    for name, command in plan:
        code, stdout, stderr, duration_ms = _run(command, repo=repo, timeout_seconds=timeout_seconds)
        result = {
            "name": name,
            "command": list(command),
            "exit_code": code,
            "duration_ms": duration_ms,
            "stdout_sha256": _sha256(stdout),
            "stderr_sha256": _sha256(stderr),
            "stdout_bytes": len(stdout),
            "stderr_bytes": len(stderr),
        }
        results.append(result)
        if code != 0:
            receipt["failure_stage"] = name
            break
    receipt["commands"] = results
    receipt["actual_head_after"] = _git_text(repo, "rev-parse", "HEAD")
    dirty_after = _git_text(repo, "status", "--porcelain", "--untracked-files=all")
    receipt["dirty_path_count_after"] = len(dirty_after.splitlines()) if dirty_after else 0
    if (
        len(results) == len(plan)
        and all(result["exit_code"] == 0 for result in results)
        and receipt["actual_head_after"] == expected_head
        and not dirty_after
    ):
        receipt["status"] = "PASS"
        receipt.pop("failure_stage", None)
    elif "failure_stage" not in receipt:
        receipt["failure_stage"] = "POST_IDENTITY_OR_CLEANLINESS"
    return receipt


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--policy-floor-ref", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--remote-ref", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        receipt = run_clean_reproduction(
            args.repo,
            expected_head=args.expected_head,
            baseline=args.baseline,
            policy_floor_ref=args.policy_floor_ref,
            agent_id=args.agent_id,
            remote_ref=args.remote_ref,
            timeout_seconds=args.timeout_seconds,
        )
        rendered = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        destination = args.receipt or (
            args.repo / ".creative-evidence" / f"executor-clean-{args.expected_head}.json"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
        sys.stdout.write(rendered)
        return 0 if receipt["status"] == "PASS" else 2
    except Exception as error:
        sys.stderr.write(json.dumps({"schema": SCHEMA, "status": "FAIL", "error": str(error)}) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
