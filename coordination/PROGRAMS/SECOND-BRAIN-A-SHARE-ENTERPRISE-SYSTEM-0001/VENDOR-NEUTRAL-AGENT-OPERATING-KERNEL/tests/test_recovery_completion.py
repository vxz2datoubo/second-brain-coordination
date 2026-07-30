from __future__ import annotations

from dataclasses import replace
import unittest

from _support import meta
from vendor_neutral_agent_kernel.completion import audit_completion
from vendor_neutral_agent_kernel.contracts import (
    CompletionStatus,
    RequirementEvidence,
    SideEffectClass,
    SideEffectRecord,
)
from vendor_neutral_agent_kernel.recovery import (
    build_checkpoint,
    record_side_effect,
    resume_checkpoint,
)


def evidence(requirement_id: str, disposition: str = "PROVES") -> RequirementEvidence:
    return RequirementEvidence(
        requirement_id=requirement_id,
        evidence_refs=("test:" + requirement_id,),
        disposition=disposition,
        scope="exact requirement",
    )


class RecoveryCompletionTests(unittest.TestCase):
    def checkpoint(self):
        return build_checkpoint(
            meta("checkpoint"),
            intent_hash="intent",
            context_hash="context",
            authority_hash="authority",
            completed_steps=("inspect",),
            remaining_steps=("edit", "test"),
            artifact_refs=("artifact:1",),
            test_state=("syntax:pass",),
            resume_instructions=("re-read authority", "continue edit"),
            external_anchors=("anchor:remote",),
        )

    def test_checkpoint_is_sealed(self):
        self.assertEqual(len(self.checkpoint().meta.content_hash), 64)

    def test_record_side_effect_adds_idempotency_guard(self):
        effect = SideEffectRecord(
            effect_id="comment",
            side_effect_class=SideEffectClass.EXTERNAL_REVERSIBLE,
            idempotency_key="issue-comment-1",
            external_anchor="comment:1",
            status="DONE",
        )
        updated = record_side_effect(
            self.checkpoint(),
            meta=meta("checkpoint-2"),
            effect=effect,
        )
        self.assertEqual(updated.side_effect_ledger, (effect,))
        self.assertNotEqual(updated.meta.content_hash, self.checkpoint().meta.content_hash)

    def test_record_side_effect_rejects_duplicate_key(self):
        effect = SideEffectRecord(
            effect_id="comment",
            side_effect_class=SideEffectClass.EXTERNAL_REVERSIBLE,
            idempotency_key="same",
            external_anchor="comment:1",
            status="DONE",
        )
        first = record_side_effect(self.checkpoint(), meta=meta("checkpoint-2"), effect=effect)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_SIDE_EFFECT_IDEMPOTENCY_KEY"):
            record_side_effect(
                first,
                meta=meta("checkpoint-3"),
                effect=replace(effect, effect_id="comment-2"),
            )

    def test_resume_ready_preserves_completed_steps(self):
        result = resume_checkpoint(
            self.checkpoint(),
            current_authority_hash="authority",
            observed_external_anchors=("anchor:remote",),
        )
        self.assertEqual(result.status, "READY")
        self.assertEqual(result.already_completed, ("inspect",))
        self.assertEqual(result.next_steps, ("edit", "test"))

    def test_resume_detects_authority_change(self):
        result = resume_checkpoint(
            self.checkpoint(),
            current_authority_hash="different",
            observed_external_anchors=("anchor:remote",),
        )
        self.assertEqual(result.status, "REVALIDATE_AUTHORITY")
        self.assertIn("AUTHORITY_CHANGED", result.findings)

    def test_resume_detects_external_anchor_drift(self):
        result = resume_checkpoint(
            self.checkpoint(),
            current_authority_hash="authority",
            observed_external_anchors=(),
        )
        self.assertEqual(result.status, "EXTERNAL_DRIFT")
        self.assertTrue(any(item.startswith("MISSING_EXTERNAL_ANCHORS") for item in result.findings))

    def test_resume_preserves_authority_and_external_drift(self):
        result = resume_checkpoint(
            self.checkpoint(),
            current_authority_hash="different",
            observed_external_anchors=(),
        )
        self.assertEqual(result.status, "REVALIDATE_AUTHORITY_AND_EXTERNAL_DRIFT")
        self.assertEqual(
            result.findings,
            ("AUTHORITY_CHANGED", "MISSING_EXTERNAL_ANCHORS:anchor:remote"),
        )

    def test_complete_exact_evidence_is_success_clean(self):
        result = audit_completion(
            meta("receipt"),
            requirements=("R1", "R2"),
            evidence=(evidence("R1"), evidence("R2")),
            tests=("test:all",),
            rollback=("revert candidate commit",),
        )
        self.assertEqual(result.completion_status, CompletionStatus.SUCCESS_CLEAN)

    def test_complete_with_findings_is_not_clean(self):
        result = audit_completion(
            meta("receipt"),
            requirements=("R1",),
            evidence=(evidence("R1"),),
            findings=("model profile remains candidate",),
        )
        self.assertEqual(result.completion_status, CompletionStatus.SUCCESS_WITH_FINDINGS)

    def test_missing_requirement_is_partial(self):
        result = audit_completion(
            meta("receipt"),
            requirements=("R1", "R2"),
            evidence=(evidence("R1"),),
        )
        self.assertEqual(result.completion_status, CompletionStatus.PARTIAL)
        self.assertTrue(any(item.startswith("MISSING_REQUIREMENT_EVIDENCE") for item in result.findings))

    def test_narrow_evidence_cannot_prove_broad_requirement(self):
        result = audit_completion(
            meta("receipt"),
            requirements=("SYSTEM_COMPLETE",),
            evidence=(evidence("SYSTEM_COMPLETE", disposition="INSUFFICIENT_SCOPE"),),
        )
        self.assertEqual(result.completion_status, CompletionStatus.PARTIAL)
        self.assertTrue(any(item.startswith("UNPROVEN_REQUIREMENTS") for item in result.findings))

    def test_unknowns_make_success_with_findings(self):
        result = audit_completion(
            meta("receipt"),
            requirements=("R1",),
            evidence=(evidence("R1"),),
            unknowns=("cross-model production behavior",),
        )
        self.assertEqual(result.completion_status, CompletionStatus.SUCCESS_WITH_FINDINGS)

    def test_duplicate_requirement_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "COMPLETION_REQUIREMENTS_DUPLICATE"):
            audit_completion(
                meta("receipt"),
                requirements=("R1", "R1"),
                evidence=(evidence("R1"),),
            )


if __name__ == "__main__":
    unittest.main()
