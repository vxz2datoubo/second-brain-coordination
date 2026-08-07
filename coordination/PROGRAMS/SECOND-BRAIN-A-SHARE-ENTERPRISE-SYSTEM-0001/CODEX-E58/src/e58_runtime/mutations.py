"""Sequential genuine E58 semantic mutations run only against temporary copies."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Sequence

from .process_lifecycle import HeavyStageMutex, OwnedProcessRegistry


@dataclass(frozen=True, slots=True)
class MutationSpec:
    mutation_id: str
    audit_blocker: str
    source_relative_path: str
    original: str
    replacement: str
    test_selector: str
    invariant: str


@dataclass(frozen=True, slots=True)
class MutationResult:
    mutation_id: str
    audit_blocker: str
    source_relative_path: str
    before_sha256: str
    mutated_sha256: str
    restored_sha256: str
    replacement_count: int
    test_selector: str
    exit_code: int
    killed: bool
    restored_exactly: bool
    spawned_pid: int

    def public(self) -> dict[str, object]:
        return asdict(self)


_SEMANTIC = "src/e58_runtime/semantic_execution.py"

MUTATION_SPECS: tuple[MutationSpec, ...] = (
    MutationSpec(
        "E58-M-B1-CALLER-RECEIPT",
        "E57-B1-CALLER-AUTHORED-EVALUATOR-RECEIPT",
        _SEMANTIC,
        "return bool(expected and hmac.compare_digest(_canonical_bytes(expected), _canonical_bytes(dict(receipt.claim()))) and hmac.compare_digest(self._sign(receipt.claim()), receipt.attestation))",
        "return isinstance(receipt, ExecutionReceipt) and receipt.outcome in {\"PASS\", \"FAIL\"}",
        "tests.test_semantic_execution.SemanticExecutionTests.test_caller_constructed_receipt_is_rejected",
        "caller constructed execution receipt is rejected",
    ),
    MutationSpec(
        "E58-M-B2-NONOPPOSING-CONFLICT",
        "E57-B2-NON-OPPOSING-CONFLICT",
        _SEMANTIC,
        "if not left.evidence.proposition.opposes(right.evidence.proposition):",
        "if False:",
        "tests.test_semantic_execution.SemanticExecutionTests.test_unrelated_sources_are_not_a_conflict",
        "conflict requires semantic opposition rather than distinct sources",
    ),
    MutationSpec(
        "E58-M-B3-CIRCULAR-RELATION",
        "E57-B3-CIRCULAR-RELATION-EVIDENCE",
        _SEMANTIC,
        "if left.evidence.proposition.subject != right.evidence.proposition.subject:",
        "if False:",
        "tests.test_semantic_execution.SemanticExecutionTests.test_relation_rejects_unrelated_validated_subjects",
        "relation relevance is derived from validated subject identity",
    ),
    MutationSpec(
        "E58-M-B4-ARBITRARY-POLICY",
        "E57-B4-UNVERIFIED-REDACTION-POLICY",
        _SEMANTIC,
        "if policy != self._EMAIL:",
        "if False:",
        "tests.test_semantic_execution.SemanticExecutionTests.test_redaction_rejects_unknown_policy",
        "redaction policy id and version are registered",
    ),
    MutationSpec(
        "E58-M-B5-ISSUER-ON-VERIFIER",
        "E57-B5-NO-PUBLIC-VERIFIER-ONLY-CAPABILITY",
        _SEMANTIC,
        "    def verify_execution(self, receipt: object) -> bool:\n",
        "    def issue(self, receipt: object) -> bool:\n",
        "tests.test_semantic_execution.SemanticExecutionTests.test_verifier_capability_has_no_issue_method",
        "verifier capability exposes no issue method",
    ),
    MutationSpec(
        "E58-M-B6-DROP-TERMINATOR-OWNERSHIP",
        "E57-B6-JSONL-WHOLE-SOURCE-OWNERSHIP-INCOMPLETE",
        _SEMANTIC,
        "        segments.append(OwnedByteSegment(SegmentKind.LINE_TERMINATOR, ByteRange(content_end, terminator_end), line_index))\n",
        "        # mutation: line terminator ownership intentionally omitted\n",
        "tests.test_semantic_execution.JsonlWholeSourceOwnershipTests.test_blank_lines_and_crlf_are_owned",
        "JSONL partition owns CR/LF terminators and global offsets",
    ),
    MutationSpec(
        "E58-M-B7-ALLOW-ISOLATED-HIGH-SURROGATE",
        "E57-B7-SURROGATE-EDGE-NOT-CLOSED",
        _SEMANTIC,
        "            raise JsonlOwnershipError(\"ISOLATED_HIGH_SURROGATE\", byte_offset)\n",
        "            return\n",
        "tests.test_semantic_execution.JsonlWholeSourceOwnershipTests.test_isolated_high_surrogate_is_stable_error",
        "isolated high surrogate fails with a deterministic typed error",
    ),
)


REQUIRED_AUDIT_BLOCKERS = frozenset(spec.audit_blocker for spec in MUTATION_SPECS)


def catalog_digest() -> str:
    return sha256(json.dumps([asdict(item) for item in MUTATION_SPECS], sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _copy_task_surface(task_root: Path, temp_root: Path) -> Path:
    copied = temp_root / "task"
    shutil.copytree(task_root / "src", copied / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(task_root / "tests", copied / "tests", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return copied


def run_catalog(task_root: Path, specs: Sequence[MutationSpec] = MUTATION_SPECS) -> tuple[MutationResult, ...]:
    """Mutate temporary copied bytes one at a time and require each selected test to fail."""

    results: list[MutationResult] = []
    with HeavyStageMutex(), OwnedProcessRegistry("E58-GENUINE-MUTATION-CATALOG") as registry:
        for spec in specs:
            with tempfile.TemporaryDirectory(prefix="e58-mutation-") as temporary:
                copied_root = _copy_task_surface(task_root, Path(temporary))
                target = copied_root / spec.source_relative_path
                before = target.read_bytes()
                source_text = before.decode("utf-8")
                count = source_text.count(spec.original)
                if count != 1:
                    raise RuntimeError(f"{spec.mutation_id} expected one replacement site, found {count}")
                mutated = source_text.replace(spec.original, spec.replacement, 1).encode("utf-8")
                target.write_bytes(mutated)
                pid = registry.spawn(
                    [sys.executable, "-m", "unittest", spec.test_selector],
                    purpose=spec.mutation_id,
                    expected_exit=None,
                    cwd=copied_root,
                )
                exit_code = registry.wait(pid, timeout_seconds=30)
                target.write_bytes(before)
                restored = target.read_bytes()
                results.append(
                    MutationResult(
                        mutation_id=spec.mutation_id,
                        audit_blocker=spec.audit_blocker,
                        source_relative_path=spec.source_relative_path,
                        before_sha256=sha256(before).hexdigest(),
                        mutated_sha256=sha256(mutated).hexdigest(),
                        restored_sha256=sha256(restored).hexdigest(),
                        replacement_count=count,
                        test_selector=spec.test_selector,
                        exit_code=exit_code,
                        killed=exit_code != 0,
                        restored_exactly=restored == before,
                        spawned_pid=pid,
                    )
                )
    if any(not (result.killed and result.restored_exactly and result.before_sha256 != result.mutated_sha256) for result in results):
        raise RuntimeError("a semantic mutation survived or was not restored exactly")
    return tuple(results)
