"""Focused fail-closed tests for the E47 receipt gate."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from brainops_control_plane.pre_receipt_validator import (  # noqa: E402
    ExactHeadCiEvidence,
    PreReceiptCode,
    PreReceiptValidationInput,
    ReceiptTopology,
    validate_pre_receipt,
)
from brainops_control_plane.recoverable_lifecycle import LifecycleStage  # noqa: E402


SHA_A = "a" * 40
SHA_B = "b" * 40


def _ci(sha: str, *, versions=frozenset({"3.11", "3.13"}), conclusion="success") -> ExactHeadCiEvidence:
    return ExactHeadCiEvidence("brainops-e47", sha, versions, conclusion, "run.e47.one")


def _ready_input(**changes) -> PreReceiptValidationInput:
    values = {
        "tested_head_sha1": SHA_A,
        "tested_head_ci": _ci(SHA_A),
        "completed_stages": frozenset(LifecycleStage),
        "text_evidence": ("all concrete evidence",),
    }
    values.update(changes)
    return PreReceiptValidationInput(**values)


class E47PreReceiptValidatorTests(unittest.TestCase):
    def test_ready_after_exact_tested_head_ci_and_stage_coverage(self):
        self.assertEqual(validate_pre_receipt(_ready_input()), PreReceiptCode.READY)

    def test_missing_tested_ci_fails_closed(self):
        self.assertEqual(validate_pre_receipt(_ready_input(tested_head_ci=None)), PreReceiptCode.TESTED_HEAD_CI_MISSING)

    def test_wrong_tested_head_ci_fails_closed(self):
        self.assertEqual(validate_pre_receipt(_ready_input(tested_head_ci=_ci(SHA_B))), PreReceiptCode.TESTED_HEAD_CI_MISMATCH)

    def test_python_matrix_must_contain_311_and_313(self):
        self.assertEqual(validate_pre_receipt(_ready_input(tested_head_ci=_ci(SHA_A, versions=frozenset({"3.13"})))), PreReceiptCode.PYTHON_MATRIX_INCOMPLETE)

    def test_every_lifecycle_stage_is_required(self):
        self.assertEqual(validate_pre_receipt(_ready_input(completed_stages=frozenset({LifecycleStage.EFFECT_AUTHORIZED}))), PreReceiptCode.STAGE_COVERAGE_INCOMPLETE)

    def test_placeholder_text_fails_closed(self):
        self.assertEqual(validate_pre_receipt(_ready_input(text_evidence=("TODO add CI run",))), PreReceiptCode.PLACEHOLDER_PRESENT)

    def test_receipt_parent_must_be_the_tested_head(self):
        topology = ReceiptTopology(SHA_A, SHA_B, "c" * 40, ("coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/E47/RUN-RECEIPT.md",))
        self.assertEqual(validate_pre_receipt(_ready_input(receipt_topology=topology)), PreReceiptCode.RECEIPT_TOPOLOGY_INVALID)

    def test_receipt_cannot_change_runtime_or_tests(self):
        topology = ReceiptTopology(SHA_A, SHA_A, "c" * 40, ("coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/src/brainops_control_plane/recoverable_lifecycle.py",))
        self.assertEqual(validate_pre_receipt(_ready_input(receipt_topology=topology)), PreReceiptCode.RECEIPT_SCOPE_INVALID)

    def test_receipt_head_requires_its_own_exact_ci(self):
        topology = ReceiptTopology(SHA_A, SHA_A, "c" * 40, ("coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/E47/RUN-RECEIPT.md",))
        self.assertEqual(validate_pre_receipt(_ready_input(receipt_topology=topology), require_receipt_head=True), PreReceiptCode.RECEIPT_HEAD_CI_MISSING)
        self.assertEqual(validate_pre_receipt(_ready_input(receipt_topology=topology, receipt_head_ci=_ci(SHA_B)), require_receipt_head=True), PreReceiptCode.RECEIPT_HEAD_CI_MISMATCH)
        self.assertEqual(validate_pre_receipt(_ready_input(receipt_topology=topology, receipt_head_ci=_ci("c" * 40)), require_receipt_head=True), PreReceiptCode.READY)
