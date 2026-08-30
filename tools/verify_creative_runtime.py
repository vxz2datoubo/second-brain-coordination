"""Offline, exact-head reproducibility verifier for the creative runtime.

This is intentionally a verifier rather than a release/merge tool. It runs no
network clients, reads no credentials, and changes only a temporary workspace.
It provides a compact JSON receipt that an independent reviewer can reproduce
from a frozen commit without relying on executor chat history.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)


def _git_head() -> str:
    result = _run(["git", "rev-parse", "HEAD"])
    if result.returncode != 0:
        raise RuntimeError("Cannot resolve git HEAD: " + result.stderr.strip())
    return result.stdout.strip()


def _load_cli() -> Any:
    path = ROOT / "apps" / "cli" / "creativectl.py"
    spec = importlib.util.spec_from_file_location("creative_runtime_verifier_cli", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load creativectl")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _demo(cli: Any) -> dict[str, Any]:
    """Run a deterministic route crossing all new runtime integration points."""

    with tempfile.TemporaryDirectory(prefix="creative-runtime-verify-") as directory:
        workspace = Path(directory)
        cli.run(["--workspace", str(workspace), "init", "--scenario", "three_scene"])
        cli.run(["--workspace", str(workspace), "choose", "listen"])
        cli.run(["--workspace", str(workspace), "choose", "approach"])
        cli.run(["--workspace", str(workspace), "choose", "listen"])
        timeline = cli.run(["--workspace", str(workspace), "timeline"])
        director = cli.run(["--workspace", str(workspace), "director"])
        understanding = cli.run(["--workspace", str(workspace), "understanding"])
        derived = cli.run(
            [
                "--workspace",
                str(workspace),
                "knowledge",
                "derive",
                "A documented handoff can preserve an earned witness lead.",
            ]
        )
        migration = cli.run(["--workspace", str(workspace), "migrate"])
        return {
            "scenario": "three_scene",
            "timeline_status": timeline["status"],
            "timeline_hash": timeline["timeline_hash"],
            "timeline_entry_count": len(timeline["entries"]),
            "final_state": timeline["entries"][-1]["state"],
            "director_status": director["status"],
            "director_can_generate": director["quality_report"]["can_generate"],
            "understanding_status": understanding["status"],
            "drift_statuses": [item["status"] for item in understanding["drift_assessments"]],
            "knowledge_status": derived["status"],
            "knowledge_candidate_status": derived["verified_timeline_candidate"]["candidate"]["status"],
            "migration_status": migration["status"],
        }


def verify(
    expected_head: str | None = None,
    *,
    run_test_suite: bool = True,
    require_clean_worktree: bool = True,
) -> dict[str, Any]:
    actual_head = _git_head()
    if expected_head is not None and actual_head != expected_head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {actual_head}")
    if require_clean_worktree:
        status = _run(["git", "status", "--porcelain"])
        if status.returncode != 0:
            raise RuntimeError("Cannot determine git worktree status: " + status.stderr.strip())
        if status.stdout.strip():
            raise RuntimeError("Verification requires a clean worktree; use a fresh clone or commit/checkpoint first")
    if run_test_suite:
        tests = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_creative*.py"])
        if tests.returncode != 0:
            raise RuntimeError("Creative test suite failed:\n" + tests.stdout + tests.stderr)
    diff = _run(["git", "diff", "--check"])
    if diff.returncode != 0:
        raise RuntimeError("git diff --check failed:\n" + diff.stdout + diff.stderr)
    demonstration = _demo(_load_cli())
    expected_demo = {
        "timeline_status": "timeline_verified",
        "timeline_entry_count": 4,
        "director_status": "director_verified",
        "director_can_generate": True,
        "understanding_status": "understanding_mapped",
        "drift_statuses": ["pass"],
        "knowledge_status": "pending_human_review",
        "knowledge_candidate_status": "pending_human_review",
        "migration_status": "migrated",
    }
    for key, expected in expected_demo.items():
        if demonstration[key] != expected:
            raise RuntimeError(f"Demonstration mismatch for {key}: {demonstration[key]!r} != {expected!r}")
    return {
        "schema": "CreativeRuntimeVerificationReceipt/v1",
        "head_sha": actual_head,
        "unit_test_command": f"{sys.executable} -m unittest discover -s tests -p test_creative*.py",
        "unit_test_status": "pass" if run_test_suite else "skipped_for_verifier_self_test",
        "worktree_status": "clean_required_and_clean" if require_clean_worktree else "not_checked_for_verifier_self_test",
        "diff_check_status": "pass",
        "demonstration": demonstration,
        "authority_note": "Executor reproducibility evidence only; independent acceptance requires a separate reviewer.",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Verify the offline creative runtime at an exact git head.")
    parser.add_argument("--expected-head", help="Require this exact commit SHA before running checks.")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify(args.expected_head), ensure_ascii=False, sort_keys=True, indent=2))
    except RuntimeError as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
