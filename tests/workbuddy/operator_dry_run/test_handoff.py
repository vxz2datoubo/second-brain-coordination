"""Handoff-receipt and runtime-boundary tests (WB-S3).

Consumer-side regressions only: they exercise the checkpoint's governance,
provenance, generation and knowledge contracts exactly as an operator would,
asserting their fail-closed behavior without modifying them.
"""

from __future__ import annotations

import unittest

import sys
from pathlib import Path

# Resolve imports without relying on discover's top-level directory.
_REPO_ROOT = Path(__file__).resolve().parents[3]
for _candidate in (str(_REPO_ROOT), str(_REPO_ROOT / "tools" / "workbuddy")):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from creative_runtime.generation import ExternalGenerationGuard, GenerationViolation, adapter_for  # noqa: E402
from creative_runtime.governance import GovernanceViolation, TaskGovernance  # noqa: E402
from creative_runtime.knowledge import KnowledgeBridgeViolation, KnowledgeReviewBridge  # noqa: E402
from creative_runtime.provenance import ProvenanceViolation, SourceProvenance, require_reusable_source  # noqa: E402
from operator_dry_run import operator  # noqa: E402


class HandoffReceiptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.op = operator.OperatorDryRun()
        self.op.intake("listen")

    def test_receipt_is_deterministic(self) -> None:
        self.assertEqual(self.op.handoff_receipt(), self.op.handoff_receipt())

    def test_receipt_carries_return_fields(self) -> None:
        receipt = self.op.handoff_receipt()
        self.assertEqual(receipt["agent_id"], "WORKBUDDY")
        self.assertEqual(receipt["source_agent"], "WORKBUDDY")
        self.assertEqual(receipt["target_agent"], "CODEX")
        self.assertEqual(receipt["reviewer"], "pending_independent_reviewer")
        self.assertIn("head_event_hash", receipt)
        self.assertIn("receipt_sha256", receipt)

    def test_receipt_hash_covers_body(self) -> None:
        receipt = self.op.handoff_receipt()
        body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        self.assertEqual(receipt["receipt_sha256"], operator.sha256_of(body))


class GenerationBoundaryTest(unittest.TestCase):
    def test_offline_generation_is_simulated_and_never_a_file(self) -> None:
        result = operator.OperatorDryRun().generate_offline()
        self.assertEqual(result["provider"], "offline")
        self.assertEqual(result["status"], "simulated")
        self.assertTrue(result["simulated"])
        self.assertTrue(result["output_ref"].startswith("offline://"))

    def test_external_provider_is_guarded(self) -> None:
        guard = adapter_for("dreamina")
        self.assertIsInstance(guard, ExternalGenerationGuard)

    def test_unknown_provider_is_rejected(self) -> None:
        with self.assertRaises(GenerationViolation):
            adapter_for("paid_external_model")


class GovernanceBoundaryTest(unittest.TestCase):
    def _governance(self) -> TaskGovernance:
        return TaskGovernance(
            task_id="WB-S3",
            route_epoch=175,
            allowed_write_patterns=("tests/workbuddy/**", "tools/workbuddy/**", "coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/WORKBUDDY-R175/**"),
            authority_invariants={"agent": "WORKBUDDY"},
        )

    def test_allowed_path_passes(self) -> None:
        self.assertTrue(self._governance().is_write_path_allowed("tools/workbuddy/operator_dry_run/operator.py"))

    def test_core_runtime_path_is_rejected(self) -> None:
        self.assertFalse(self._governance().is_write_path_allowed("creative_runtime/director.py"))

    def test_require_allowed_paths_fails_closed(self) -> None:
        with self.assertRaises(GovernanceViolation):
            self._governance().require_allowed_write_paths(["creative_runtime/director.py"])

    def test_authority_declaration_mismatch_rejected(self) -> None:
        with self.assertRaises(GovernanceViolation):
            self._governance().require_authority_declaration({"agent": "CODEX"})


class ProvenanceBoundaryTest(unittest.TestCase):
    def test_local_unverified_source_rejected(self) -> None:
        source = SourceProvenance(source_id="R-LOCAL", classification="LOCAL_UNVERIFIED", approved_for_reuse=True, gpt_import_record="gpt-1")
        with self.assertRaises(ProvenanceViolation):
            require_reusable_source(source)

    def test_missing_import_record_rejected(self) -> None:
        source = SourceProvenance(source_id="R-OK", classification="PRIMARY", approved_for_reuse=True, gpt_import_record=None)
        with self.assertRaises(ProvenanceViolation):
            require_reusable_source(source)

    def test_reusable_source_passes(self) -> None:
        source = SourceProvenance(source_id="R-OK", classification="PRIMARY", approved_for_reuse=True, gpt_import_record="gpt-import-1")
        require_reusable_source(source)


class KnowledgeBoundaryTest(unittest.TestCase):
    def test_correction_requires_source_reference(self) -> None:
        bridge = KnowledgeReviewBridge()
        with self.assertRaises(KnowledgeBridgeViolation):
            bridge.correct("a fact with no source")

    def test_review_requires_named_human_reviewer(self) -> None:
        bridge = KnowledgeReviewBridge()
        candidate = bridge.correct("a sourced fact", source_event_ids=["evt_1"])
        with self.assertRaises(KnowledgeBridgeViolation):
            bridge.review(candidate.candidate_id, "executor", True, "note")

    def test_canonical_write_is_disabled(self) -> None:
        self.assertFalse(KnowledgeReviewBridge.canonical_write_enabled)


if __name__ == "__main__":
    unittest.main()
