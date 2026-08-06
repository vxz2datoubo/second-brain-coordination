"""Genuine isolated E57 source mutations.

Every mutation rewrites an actual source byte sequence inside a disposable copy
of this task, executes its named invariant test, restores the original bytes in
``finally``, and records both changed and restored digests. Production source is
never mutated in place by this runner.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Iterable

from .core import AuthorityError, stable_digest


@dataclass(frozen=True, slots=True)
class MutationDefinition:
    mutation_id: str
    relative_path: str
    old: bytes
    new: bytes
    invariant_test: str


@dataclass(frozen=True, slots=True)
class MutationResult:
    mutation_id: str
    changed: bool
    named_invariant_failed: bool
    restored_exactly: bool
    before_sha256: str
    mutated_sha256: str
    restored_sha256: str
    exit_code: int
    stdout_sha256: str
    stderr_sha256: str

    def canonical(self) -> dict[str, object]:
        return {
            "mutation_id": self.mutation_id,
            "changed": self.changed,
            "named_invariant_failed": self.named_invariant_failed,
            "restored_exactly": self.restored_exactly,
            "before_sha256": self.before_sha256,
            "mutated_sha256": self.mutated_sha256,
            "restored_sha256": self.restored_sha256,
            "exit_code": self.exit_code,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
        }


CATALOG: tuple[MutationDefinition, ...] = (
    MutationDefinition(
        "MUT-PERMIT-CLONE-BYPASS",
        "src/e57_authority/core.py",
        b"if permit != stable_digest(record.wire()):\n                return False",
        b"if False:\n                return False",
        "tests.test_issuer_authority.IssuerAuthorityTests.test_copy_is_not_an_issued_presentation",
    ),
    MutationDefinition(
        "MUT-REMOTE-LEDGER-BYPASS",
        "src/e57_authority/core.py",
        b"valid = hmac.compare_digest(canonical_bytes(expected), canonical_bytes(candidate))",
        b"valid = True",
        "tests.test_issuer_authority.IssuerAuthorityTests.test_local_presentation_permit_tampering_does_not_bypass_remote_ledger",
    ),
    MutationDefinition(
        "MUT-VERIFIER-ISSUE-CHANNEL",
        "src/e57_authority/core.py",
        b"if action == \"issue\" and connection is issuer_connection:",
        b"if action == \"issue\":",
        "tests.test_issuer_authority.IssuerAuthorityTests.test_verifier_channel_refuses_issue_command",
    ),
    MutationDefinition(
        "MUT-CONFLICT-SAME-SOURCE",
        "src/e57_authority/semantic.py",
        b"if left_payload[\"source_record_id\"] == right_payload[\"source_record_id\"]:",
        b"if False:",
        "tests.test_semantic_records.SemanticRecordTests.test_conflict_rejects_distinct_evidence_from_the_same_source",
    ),
    MutationDefinition(
        "MUT-VALIDATION-INPUT-BINDING",
        "src/e57_authority/semantic.py",
        b"if receipt.input_digest != evidence.payload_digest:",
        b"if receipt.input_digest == evidence.payload_digest:",
        "tests.test_semantic_records.SemanticRecordTests.test_validation_requires_bound_execution_receipt",
    ),
    MutationDefinition(
        "MUT-REDACTION-RANGE",
        "src/e57_authority/semantic.py",
        b"if not reason_policy_id or raw.end > int(source.payload()[\"byte_length\"]):",
        b"if not reason_policy_id or raw.end < int(source.payload()[\"byte_length\"]):",
        "tests.test_semantic_records.SemanticRecordTests.test_redaction_requires_exact_in_source_range_and_policy",
    ),
    MutationDefinition(
        "MUT-RELATION-ENDPOINT-BINDING",
        "src/e57_authority/semantic.py",
        b"if tuple(sorted((left.record_id, right.record_id))) != endpoint_ids:",
        b"if tuple(sorted((left.record_id, right.record_id))) == endpoint_ids:",
        "tests.test_semantic_records.SemanticRecordTests.test_relation_requires_endpoint_bound_evidence",
    ),
    MutationDefinition(
        "MUT-JSON-BOOLEAN-TYPING",
        "src/e57_authority/semantic.py",
        b"TypedValue(ValueKind.BOOLEAN, ByteRange(offsets[start], offsets[index]), literal)",
        b"TypedValue(ValueKind.STRUCTURAL, ByteRange(offsets[start], offsets[index]), literal)",
        "tests.test_semantic_records.SemanticRecordTests.test_json_number_boolean_and_null_are_typed",
    ),
    MutationDefinition(
        "MUT-MARKDOWN-UNKNOWN",
        "src/e57_authority/semantic.py",
        b"kind = ValueKind.UNKNOWN if unknown else ValueKind.TEXT",
        b"kind = ValueKind.TEXT if unknown else ValueKind.TEXT",
        "tests.test_semantic_records.SemanticRecordTests.test_markdown_complex_constructs_are_typed_unknown",
    ),
    MutationDefinition(
        "MUT-RAW-PARTITION-GAP",
        "src/e57_authority/semantic.py",
        b"if item.start != cursor:\n                raise AuthorityError(\"raw ownership has a gap or overlap\")",
        b"if False:\n                raise AuthorityError(\"raw ownership has a gap or overlap\")",
        "tests.test_semantic_records.SemanticRecordTests.test_partition_gap_is_rejected",
    ),
)


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _apply_once(original: bytes, definition: MutationDefinition) -> bytes:
    if original.count(definition.old) != 1:
        raise AuthorityError(f"mutation target is not unique: {definition.mutation_id}")
    changed = original.replace(definition.old, definition.new, 1)
    if changed == original:
        raise AuthorityError(f"mutation did not change source bytes: {definition.mutation_id}")
    return changed


def run_mutation(task_root: Path, definition: MutationDefinition) -> MutationResult:
    """Execute one real mutation in a disposable source tree and restore bytes."""

    with tempfile.TemporaryDirectory(prefix="e57-mutation-") as temporary:
        sandbox = Path(temporary) / "CODEX-E57"
        shutil.copytree(task_root / "src", sandbox / "src")
        shutil.copytree(task_root / "tests", sandbox / "tests")
        target = sandbox / definition.relative_path
        original = target.read_bytes()
        before = _digest(original)
        mutated = _apply_once(original, definition)
        mutated_digest = _digest(mutated)
        target.write_bytes(mutated)
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(sandbox / "src")
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "unittest", definition.invariant_test],
                cwd=sandbox,
                env=environment,
                capture_output=True,
                check=False,
            )
            failed = completed.returncode != 0
            stdout, stderr = completed.stdout, completed.stderr
            exit_code = completed.returncode
        finally:
            target.write_bytes(original)
        restored = target.read_bytes()
        return MutationResult(
            mutation_id=definition.mutation_id,
            changed=before != mutated_digest,
            named_invariant_failed=failed,
            restored_exactly=restored == original,
            before_sha256=before,
            mutated_sha256=mutated_digest,
            restored_sha256=_digest(restored),
            exit_code=exit_code,
            stdout_sha256=_digest(stdout),
            stderr_sha256=_digest(stderr),
        )


def run_catalog(task_root: Path, definitions: Iterable[MutationDefinition] = CATALOG) -> tuple[MutationResult, ...]:
    results = tuple(run_mutation(task_root, definition) for definition in definitions)
    invalid = [result.mutation_id for result in results if not (result.changed and result.named_invariant_failed and result.restored_exactly)]
    if invalid:
        raise AuthorityError(f"genuine mutation invariant failed: {','.join(invalid)}")
    return results


def catalog_digest() -> str:
    return stable_digest(
        [
            {"id": item.mutation_id, "path": item.relative_path, "old": item.old.decode("ascii"), "new": item.new.decode("ascii"), "test": item.invariant_test}
            for item in CATALOG
        ]
    )
