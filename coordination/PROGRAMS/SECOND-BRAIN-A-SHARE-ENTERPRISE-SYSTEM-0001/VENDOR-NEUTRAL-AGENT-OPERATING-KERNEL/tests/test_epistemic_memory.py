from __future__ import annotations

from dataclasses import replace
import unittest

from _support import claim, meta
from vendor_neutral_agent_kernel.contracts import EpistemicLane, QualityStatus
from vendor_neutral_agent_kernel.epistemic import (
    propose_memory_write,
    reject_authority_promotion,
    revise_claim,
)


class EpistemicMemoryTests(unittest.TestCase):
    def test_revision_preserves_original_and_links_supersedes(self):
        original = claim()
        revised = revise_claim(
            original,
            meta=meta("claim-2", lane=EpistemicLane.USER_ASSERTED),
            canonical_statement="The user selected the revised approach.",
            provenance_lane=EpistemicLane.USER_ASSERTED,
            supporting_evidence=(),
            opposing_evidence=("user:correction",),
            alternative_explanations=(),
            confidence=1.0,
            confidence_basis="explicit correction",
            freshness="CURRENT",
            invalidation_conditions=("future correction",),
        )
        self.assertEqual(revised.meta.supersedes, original.meta.object_id)
        self.assertNotEqual(revised.meta.content_hash, original.meta.content_hash)
        self.assertEqual(original.canonical_statement, "The user selected the candidate approach.")

    def test_revision_requires_new_object_id(self):
        original = claim()
        with self.assertRaisesRegex(ValueError, "CLAIM_REVISION_REQUIRES_NEW_OBJECT_ID"):
            revise_claim(
                original,
                meta=replace(original.meta, content_hash=""),
                canonical_statement="Changed.",
                provenance_lane=EpistemicLane.USER_ASSERTED,
                supporting_evidence=(),
                opposing_evidence=(),
                alternative_explanations=(),
                confidence=1.0,
                confidence_basis="explicit",
                freshness="CURRENT",
                invalidation_conditions=(),
            )

    def test_user_adopted_is_not_rewritten_as_model_inference(self):
        adopted = claim(lane=EpistemicLane.USER_ADOPTED)
        self.assertEqual(adopted.provenance_lane, EpistemicLane.USER_ADOPTED)
        self.assertEqual(adopted.meta.epistemic_status, EpistemicLane.USER_ADOPTED)

    def test_inferred_claim_keeps_supporting_evidence(self):
        inferred = claim(lane=EpistemicLane.INFERRED, statement="A supported inference.")
        self.assertEqual(inferred.supporting_evidence, ("evidence:1",))
        self.assertEqual(inferred.provenance_lane, EpistemicLane.INFERRED)

    def test_opposing_evidence_can_mark_revision_disputed(self):
        original = claim()
        revised = revise_claim(
            original,
            meta=meta("claim-disputed", lane=EpistemicLane.HYPOTHESIS),
            canonical_statement="A disputed hypothesis.",
            provenance_lane=EpistemicLane.HYPOTHESIS,
            supporting_evidence=("evidence:support",),
            opposing_evidence=("evidence:oppose",),
            alternative_explanations=("alternative:a",),
            confidence=0.4,
            confidence_basis="conflicting evidence",
            freshness="CURRENT",
            invalidation_conditions=("strong counterevidence",),
            quality_status=QualityStatus.DISPUTED,
        )
        self.assertEqual(revised.meta.quality_status, QualityStatus.DISPUTED)
        self.assertEqual(revised.opposing_evidence, ("evidence:oppose",))

    def test_memory_proposal_is_candidate_only(self):
        proposal = propose_memory_write(
            meta("memory-proposal"),
            candidate_claims=(claim(),),
            destination_scope="project:kernel",
            source_provenance=("user:explicit",),
        )
        self.assertFalse(proposal.authority_write)
        self.assertEqual(proposal.validation_status, "CANDIDATE")
        self.assertEqual(len(proposal.meta.content_hash), 64)

    def test_same_memory_input_has_same_idempotency_key(self):
        first = propose_memory_write(
            meta("memory-1"),
            candidate_claims=(claim(),),
            destination_scope="project:kernel",
            source_provenance=("user:explicit",),
        )
        second = propose_memory_write(
            meta("memory-2"),
            candidate_claims=(claim(),),
            destination_scope="project:kernel",
            source_provenance=("user:explicit",),
        )
        self.assertEqual(first.idempotency_key, second.idempotency_key)

    def test_changed_memory_input_changes_idempotency_key(self):
        first = propose_memory_write(
            meta("memory-1"),
            candidate_claims=(claim(),),
            destination_scope="project:kernel",
            source_provenance=("user:explicit",),
        )
        second = propose_memory_write(
            meta("memory-2"),
            candidate_claims=(claim(statement="Different durable claim."),),
            destination_scope="project:kernel",
            source_provenance=("user:explicit",),
        )
        self.assertNotEqual(first.idempotency_key, second.idempotency_key)

    def test_kernel_rejects_canonical_memory_promotion(self):
        proposal = propose_memory_write(
            meta("memory-proposal"),
            candidate_claims=(claim(),),
            destination_scope="project:kernel",
            source_provenance=("user:explicit",),
        )
        with self.assertRaisesRegex(PermissionError, "CANNOT_PROMOTE_CANONICAL_AUTHORITY"):
            reject_authority_promotion(proposal)


if __name__ == "__main__":
    unittest.main()
