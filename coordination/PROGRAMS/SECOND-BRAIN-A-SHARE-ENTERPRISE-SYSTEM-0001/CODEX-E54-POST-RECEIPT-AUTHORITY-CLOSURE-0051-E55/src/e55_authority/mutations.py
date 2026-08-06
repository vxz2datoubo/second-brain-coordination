"""E55 production-source mutation runner with exact restoration evidence."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Sequence


@dataclass(frozen=True, slots=True)
class MutationSpec:
    mutation_id: str
    target_file: str
    old: str
    new: str
    counterexample_id: str
    purpose: str


@dataclass(frozen=True, slots=True)
class MutationResult:
    mutation_id: str
    target_file: str
    counterexample_id: str
    purpose: str
    anchor_offset: int
    replacement_count: int
    command: tuple[str, ...]
    command_sha256: str
    pristine_sha256: str
    mutated_sha256: str
    mutated_exit_code: int
    mutated_duration_ns: int
    mutated_stdout_sha256: str
    mutated_stderr_sha256: str
    restored_sha256: str
    restored_exit_code: int
    restored_duration_ns: int
    restored_stdout_sha256: str
    restored_stderr_sha256: str


MUTATION_SPECS: tuple[MutationSpec, ...] = (
    MutationSpec(
        "MUT-SOURCE-ISSUANCE-REGISTRY", "authority.py", "if not isinstance(evidence, SourceEvidence) or self._issued.get(id(evidence)) is not evidence:", "if False:", "CE-UNISSUED-SOURCE",
        "a source with copied data and a matching private seal can bypass the issuing registry",
    ),
    MutationSpec(
        "MUT-RAW-ADMISSION", "authority.py", "_reject_marker_variants(text, stage=\"raw\")", "pass", "CE-RAW-MARKER",
        "raw credential-shaped material is no longer rejected before graph construction",
    ),
    MutationSpec(
        "MUT-JSON-ESCAPE-OWNERSHIP", "authority.py", "return not token.is_key and not token.has_escape_syntax and token.quote_end - token.quote_start > 2", "return not token.is_key and token.quote_end - token.quote_start > 2", "CE-ESCAPE-SYNTAX",
        "JSON escape syntax is incorrectly promoted into a semantic atom candidate",
    ),
    MutationSpec(
        "MUT-JSON-DUPLICATE-KEY", "authority.py", "if key in result:", "if False:", "CE-DUPLICATE-KEY",
        "duplicate JSON keys are accepted with an overwritten earlier value",
    ),
    MutationSpec(
        "MUT-RELATION-SEMANTIC-RECORD", "authority.py", "if not self._evidence.verify(evidence):", "if False:", "CE-STRUCTURAL-RELATION",
        "relations accept arbitrary non-issued evidence rather than semantic record evidence",
    ),
    MutationSpec(
        "MUT-PACKET-SUBRECORD", "authority.py", "if any(not self._records.verify(record) for record in records):", "if False:", "CE-FOREIGN-SUBRECORD",
        "packet construction accepts a caller-minted unknown/conflict/validation record",
    ),
    MutationSpec(
        "MUT-HYGIENE-GENERATED", "hygiene.py", "return normalized.endswith(FORBIDDEN_SUFFIXES) or any(part in FORBIDDEN_PARTS for part in parts)", "return False", "CE-GENERATED-HISTORY",
        "generated and transient paths become invisible to history hygiene",
    ),
    MutationSpec(
        "MUT-TOPOLOGY-ACTUAL-PARENT", "topology.py", "if parent != receipt[\"tested_sha\"]:", "if False:", "CE-RECEIPT-PARENT",
        "receipt body can claim a tested head different from the observed Git parent",
    ),
    MutationSpec(
        "MUT-TOPOLOGY-ROUTE", "topology.py", "if receipt.get(field) != value:", "if False:", "CE-ROUTE-EPOCH",
        "receipt route fields can differ from the active route expectation",
    ),
    MutationSpec(
        "MUT-PROVIDER-RUN-METADATA", "provider.py", "if run.get(\"head_sha\") != expected_head or run.get(\"workflow\") != expected_workflow or run.get(\"branch\") != expected_branch:", "if False:", "CE-PROVIDER-HEAD",
        "unrelated provider run metadata can pass as the exact tested route",
    ),
    MutationSpec(
        "MUT-PROVIDER-BYTES", "provider.py", "if artifact.artifact_id in artifact_ids or not artifact.verify_bytes():", "if artifact.artifact_id in artifact_ids:", "CE-TAMPERED-ARTIFACT",
        "downloaded artifact bytes are no longer checked against their recorded digest",
    ),
)


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _run(command: tuple[str, ...], environment: dict[str, str], timeout_seconds: float) -> tuple[subprocess.CompletedProcess[bytes], int]:
    started = time.perf_counter_ns()
    completed = subprocess.run(command, capture_output=True, env=environment, timeout=timeout_seconds, check=False)
    return completed, time.perf_counter_ns() - started


def run_production_source_mutations(
    package_dir: Path,
    test_dir: Path,
    specs: Sequence[MutationSpec] = MUTATION_SPECS,
    *,
    timeout_seconds: float = 120.0,
) -> tuple[MutationResult, ...]:
    """Mutate task-local production bytes one at a time and restore exactly.

    This intentionally writes only the E55 candidate source in the isolated
    worktree.  Every write is protected by ``finally`` restoration and checked
    by SHA-256 plus a green restored test run.  No external runtime is touched.
    """
    package_dir = package_dir.resolve()
    test_dir = test_dir.resolve()
    source_root = package_dir.parent
    # Exclude ``test_mutations`` itself: otherwise a mutation verification
    # would recursively start another mutation matrix instead of testing the
    # same ordinary production suite that the matrix is intended to challenge.
    command = (sys.executable, "-m", "unittest", "test_authority", "test_hygiene_topology_provider", "test_tools", "-v")
    inherited_path = os.environ.get("PYTHONPATH", "")
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(item for item in (str(source_root), str(test_dir), inherited_path) if item),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    results: list[MutationResult] = []
    for spec in specs:
        target = package_dir / spec.target_file
        pristine = target.read_bytes()
        source = pristine.decode("utf-8", "strict")
        count = source.count(spec.old)
        if count != 1:
            raise RuntimeError(f"mutation anchor mismatch for {spec.mutation_id}: {count}")
        offset = source.index(spec.old)
        mutated = source.replace(spec.old, spec.new, 1).encode("utf-8")
        changed: subprocess.CompletedProcess[bytes] | None = None
        changed_duration = 0
        try:
            target.write_bytes(mutated)
            changed, changed_duration = _run(command, environment, timeout_seconds)
        finally:
            target.write_bytes(pristine)
        if target.read_bytes() != pristine:
            raise RuntimeError(f"restoration byte mismatch for {spec.mutation_id}")
        restored, restored_duration = _run(command, environment, timeout_seconds)
        if changed is None:
            raise RuntimeError(f"mutation did not execute for {spec.mutation_id}")
        if changed.returncode == 0:
            raise RuntimeError(f"surviving mutation: {spec.mutation_id}")
        if restored.returncode != 0:
            raise RuntimeError(f"restored suite is not green: {spec.mutation_id}")
        results.append(
            MutationResult(
                spec.mutation_id, spec.target_file, spec.counterexample_id, spec.purpose, offset, count,
                command, _sha("\0".join(command).encode("utf-8")), _sha(pristine), _sha(mutated),
                changed.returncode, changed_duration, _sha(changed.stdout), _sha(changed.stderr), _sha(target.read_bytes()),
                restored.returncode, restored_duration, _sha(restored.stdout), _sha(restored.stderr),
            )
        )
    return tuple(results)
