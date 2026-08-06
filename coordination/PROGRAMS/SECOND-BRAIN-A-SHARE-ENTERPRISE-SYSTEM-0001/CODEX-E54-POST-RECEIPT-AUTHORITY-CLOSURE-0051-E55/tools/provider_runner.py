"""Run the ordinary E55 suite and write one provider-matrix evidence bundle."""

from __future__ import annotations

import argparse
from dataclasses import asdict
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

from e55_authority.mutations import MUTATION_SPECS, run_production_source_mutations  # noqa: E402


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def git_head() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError("cannot resolve tested Git head")
    return result.stdout.decode("ascii", "strict").strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--seed", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    command = (sys.executable, "-m", "unittest", "test_authority", "test_hygiene_topology_provider", "-v")
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join((str(ROOT / "src"), str(ROOT / "tests"))),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": args.seed,
    }
    started = time.perf_counter_ns()
    run = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, check=False)
    duration = time.perf_counter_ns() - started
    stdout, stderr = run.stdout, run.stderr
    (output / "stdout.txt").write_bytes(stdout)
    (output / "stderr.txt").write_bytes(stderr)
    merged = (stdout + b"\n" + stderr).decode("utf-8", "replace")
    match = re.search(r"Ran (\d+) tests", merged)
    if run.returncode or match is None:
        return run.returncode or 1
    mutation_results = run_production_source_mutations(ROOT / "src" / "e55_authority", ROOT / "tests")
    mutation_payload = json.dumps(
        {"schema": "e55-provider-mutation-results-v1", "results": [asdict(item) for item in mutation_results]},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    (output / "mutation-results.json").write_bytes(mutation_payload)
    canonical = {
        "schema": "e55-provider-canonical-v1",
        "task_root": ROOT.name,
        "ordinary_test_modules": ["test_authority", "test_hygiene_topology_provider"],
        "mutation_ids": [item.mutation_id for item in MUTATION_SPECS],
        "mutation_result_sha256": digest(mutation_payload),
        "mutation_count": len(mutation_results),
    }
    (output / "canonical.json").write_bytes(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    evidence = {
        "schema": "e55-provider-environment-v1",
        "head_sha": git_head(),
        "branch": args.branch,
        "workflow": args.workflow,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "hash_seed": args.seed,
        "command": list(command),
        "command_sha256": digest("\0".join(command).encode("utf-8")),
        "test_count": int(match.group(1)),
        "mutation_ids": [item.mutation_id for item in MUTATION_SPECS],
        "stdout_sha256": digest(stdout),
        "stderr_sha256": digest(stderr),
        "duration_ns": duration,
    }
    (output / "environment.json").write_bytes(json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
