"""Execute the E56 product suite and create all matrix inner payloads."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from e56_authority.mutations import mutation_payload, run_mutation_matrix  # noqa: E402
from e56_authority.provider import CONTRACT_PATH, build_canonical_evaluation, canonical_artifact_bytes, digest  # noqa: E402


def git_head() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError("cannot resolve exact tested Git head")
    return result.stdout.decode("ascii", "strict").strip()


def run_suite(seed: str) -> tuple[subprocess.CompletedProcess[bytes], int, tuple[str, ...]]:
    command = (sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v")
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join((str(ROOT / "src"), str(ROOT / "tests"))), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": seed}
    started = time.perf_counter_ns()
    result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, check=False)
    return result, time.perf_counter_ns() - started, command


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--job-name", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-attempt", required=True, type=int)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    observed_head = git_head()
    if observed_head != args.expected_head:
        raise RuntimeError("checked-out head differs from the workflow event head")
    result, duration_ns, command = run_suite(args.seed)
    (output / "stdout.txt").write_bytes(result.stdout)
    (output / "stderr.txt").write_bytes(result.stderr)
    merged = (result.stdout + b"\n" + result.stderr).decode("utf-8", "replace")
    match = re.search(r"Ran (\d+) tests", merged)
    if result.returncode or match is None:
        return result.returncode or 1
    mutations = run_mutation_matrix(ROOT)
    mutation_bytes = mutation_payload(mutations)
    (output / "mutation-results.json").write_bytes(mutation_bytes)
    test_result = {"command": list(command), "exit_code": result.returncode, "test_count": int(match.group(1)), "suite_sha256": digest(("\0".join(command) + "\0" + str(int(match.group(1)))).encode("utf-8"))}
    canonical = build_canonical_evaluation(ROOT / "src" / "e56_authority", test_result=test_result, mutation_summary=[item.canonical_summary() for item in mutations])
    canonical_bytes = canonical_artifact_bytes(canonical)
    (output / "canonical.json").write_bytes(canonical_bytes)
    job_evidence = {
        "schema": "e56-provider-job-evidence-v1",
        "head_sha": observed_head,
        "job_name": args.job_name,
        "run_id": args.run_id,
        "run_attempt": args.run_attempt,
        "contract_sha256": digest(CONTRACT_PATH.read_bytes()),
    }
    job_evidence_bytes = json.dumps(job_evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
    (output / "job-evidence.json").write_bytes(job_evidence_bytes)
    environment = {
        "schema": "e56-provider-environment-v1",
        "head_sha": observed_head,
        "branch": args.branch,
        "workflow": args.workflow,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "hash_seed": args.seed,
        "command": list(command),
        "command_sha256": digest("\0".join(command).encode("utf-8")),
        "test_count": test_result["test_count"],
        "test_result_digest": digest(json.dumps(test_result, sort_keys=True, separators=(",", ":")).encode("utf-8")),
        "mutation_result_sha256": digest(mutation_bytes),
        "job_evidence_sha256": digest(job_evidence_bytes),
        "mutation_count": len(mutations),
        "canonical_sha256": digest(canonical_bytes),
        "stdout_sha256": digest(result.stdout),
        "stderr_sha256": digest(result.stderr),
        "duration_ns": duration_ns,
    }
    (output / "environment.json").write_bytes(json.dumps(environment, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
