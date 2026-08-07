"""Produce deterministic E58 canonical evidence and separate environment evidence."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e58_runtime.mutations import catalog_digest, run_catalog  # noqa: E402


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def _source_hashes() -> list[dict[str, str]]:
    root = TASK_ROOT / "src" / "e58_runtime"
    return [
        {"path": path.relative_to(TASK_ROOT).as_posix(), "sha256": sha256(path.read_bytes()).hexdigest()}
        for path in sorted(root.glob("*.py"))
    ]


def _product_suite() -> tuple[int, int, bytes, bytes]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(TASK_ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "tools/run_local_suite.py"],
        cwd=TASK_ROOT,
        env=environment,
        capture_output=True,
        check=False,
    )
    combined = completed.stdout + b"\n" + completed.stderr
    match = re.search(rb"Ran ([0-9]+) tests", combined)
    return completed.returncode, int(match.group(1)) if match else 0, completed.stdout, completed.stderr


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--role", required=True, choices=("tested", "receipt"))
    arguments = parser.parse_args()
    exit_code, test_count, stdout, stderr = _product_suite()
    if exit_code != 0 or test_count != 46:
        raise SystemExit("E58 provider refuses to publish failed or unexpected product evidence")
    mutations = run_catalog(TASK_ROOT)
    if len(mutations) != 7 or any(not (result.killed and result.restored_exactly) for result in mutations):
        raise SystemExit("E58 provider refuses incomplete mutation evidence")
    canonical = {
        "schema": "e58-provider-canonical-v1",
        "product": {"command": ["python", "tools/run_local_suite.py"], "exit_code": exit_code, "test_count": test_count},
        "source_hashes": _source_hashes(),
        "mutation_catalog_digest": catalog_digest(),
        "mutations": [
            {
                "mutation_id": result.mutation_id,
                "audit_blocker": result.audit_blocker,
                "source_relative_path": result.source_relative_path,
                "before_sha256": result.before_sha256,
                "mutated_sha256": result.mutated_sha256,
                "restored_sha256": result.restored_sha256,
                "replacement_count": result.replacement_count,
                "test_selector": result.test_selector,
                "exit_code": result.exit_code,
                "killed": result.killed,
                "restored_exactly": result.restored_exactly,
            }
            for result in mutations
        ],
    }
    canonical_bytes = _canonical_bytes(canonical)
    environment = {
        "schema": "e58-provider-environment-v1",
        "role": arguments.role,
        "python_version": sys.version,
        "python_hash_seed": arguments.seed,
        "canonical_sha256": sha256(canonical_bytes).hexdigest(),
        "stdout_sha256": sha256(stdout).hexdigest(),
        "stderr_sha256": sha256(stderr).hexdigest(),
    }
    arguments.output.mkdir(parents=True, exist_ok=True)
    (arguments.output / "canonical.json").write_bytes(canonical_bytes + b"\n")
    (arguments.output / "environment.json").write_bytes(_canonical_bytes(environment) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
