"""Actual E57 evaluator output split into canonical and environment evidence."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Mapping

from .core import AuthorityError, canonical_bytes, stable_digest
from .mutations import MutationResult, catalog_digest, run_catalog


@dataclass(frozen=True, slots=True)
class ProductRun:
    command: tuple[str, ...]
    exit_code: int
    test_count: int
    stdout: bytes
    stderr: bytes

    @property
    def stdout_sha256(self) -> str:
        return sha256(self.stdout).hexdigest()

    @property
    def stderr_sha256(self) -> str:
        return sha256(self.stderr).hexdigest()


def _source_hashes(task_root: Path) -> tuple[tuple[str, str], ...]:
    source_root = task_root / "src" / "e57_authority"
    return tuple((path.relative_to(task_root).as_posix(), sha256(path.read_bytes()).hexdigest()) for path in sorted(source_root.glob("*.py")))


def load_evaluation_contract(task_root: Path) -> Mapping[str, object]:
    path = task_root / "PROVIDER-CONTRACT.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        evaluation = payload["evaluation"]
        matrix = payload["matrix"]
        if (
            payload["schema"] != "e57-provider-route-contract-v1"
            or payload["workflow"] != ".github/workflows/codex-e57-capability-authority-closure.yml"
            or not isinstance(evaluation["exact_test_count"], int)
            or not isinstance(evaluation["mutation_ids"], list)
            or matrix["job_count"] != 7
            or matrix["artifact_count"] != 13
        ):
            raise AuthorityError("Provider route contract is incompatible")
        return payload
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, AuthorityError):
            raise
        raise AuthorityError("Provider route contract is malformed") from exc


def run_product_suite(task_root: Path) -> ProductRun:
    command = (sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v")
    environment = {**__import__("os").environ, "PYTHONPATH": str(task_root / "src")}
    completed = subprocess.run(command, cwd=task_root, env=environment, capture_output=True, check=False)
    output = completed.stdout + b"\n" + completed.stderr
    match = re.search(rb"Ran ([0-9]+) tests", output)
    count = int(match.group(1)) if match else 0
    return ProductRun(command, completed.returncode, count, completed.stdout, completed.stderr)


def _stable_mutation_result(result: MutationResult) -> Mapping[str, object]:
    return {
        "mutation_id": result.mutation_id,
        "changed": result.changed,
        "named_invariant_failed": result.named_invariant_failed,
        "restored_exactly": result.restored_exactly,
        "before_sha256": result.before_sha256,
        "mutated_sha256": result.mutated_sha256,
        "restored_sha256": result.restored_sha256,
        "exit_code": result.exit_code,
    }


def build_canonical_payload(task_root: Path, product: ProductRun, mutations: tuple[MutationResult, ...]) -> Mapping[str, object]:
    contract = load_evaluation_contract(task_root)
    expected_count = contract["evaluation"]["exact_test_count"]
    expected_mutations = tuple(contract["evaluation"]["mutation_ids"])
    if product.exit_code != 0 or product.test_count != expected_count:
        raise AuthorityError("canonical evaluation refuses a failed or contract-mismatched product suite")
    if any(not (item.changed and item.named_invariant_failed and item.restored_exactly) for item in mutations):
        raise AuthorityError("canonical evaluation refuses incomplete genuine mutation evidence")
    if tuple(item.mutation_id for item in mutations) != expected_mutations:
        raise AuthorityError("canonical evaluation mutation identities differ from the route contract")
    payload: dict[str, object] = {
        "schema": "e57-canonical-evaluation-v1",
        "product_command": ["python", "-m", "unittest", "discover", "-s", "tests", "-v"],
        "product_exit_code": product.exit_code,
        "product_test_count": product.test_count,
        "route_contract_sha256": sha256((task_root / "PROVIDER-CONTRACT.json").read_bytes()).hexdigest(),
        "source_hashes": [{"path": path, "sha256": digest} for path, digest in _source_hashes(task_root)],
        "mutation_catalog_digest": catalog_digest(),
        "mutations": [_stable_mutation_result(item) for item in mutations],
    }
    payload["evaluation_digest"] = stable_digest(payload)
    return payload


def build_environment_payload(product: ProductRun, mutations: tuple[MutationResult, ...]) -> Mapping[str, object]:
    return {
        "schema": "e57-environment-evidence-v1",
        "python_version": sys.version,
        "product_command": list(product.command),
        "product_exit_code": product.exit_code,
        "product_test_count": product.test_count,
        "stdout_sha256": product.stdout_sha256,
        "stderr_sha256": product.stderr_sha256,
        "mutations": [item.canonical() for item in mutations],
    }


def execute_evaluation(task_root: Path) -> tuple[bytes, bytes]:
    product = run_product_suite(task_root)
    if product.exit_code != 0:
        raise AuthorityError("product suite failed before canonical evidence could be emitted")
    mutations = run_catalog(task_root)
    canonical = canonical_bytes(build_canonical_payload(task_root, product, mutations))
    environment = canonical_bytes(build_environment_payload(product, mutations))
    return canonical, environment
