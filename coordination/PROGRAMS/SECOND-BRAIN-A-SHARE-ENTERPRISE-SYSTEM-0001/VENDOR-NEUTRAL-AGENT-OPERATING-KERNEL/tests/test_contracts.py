from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import unittest

from _support import capability, claim, meta
from vendor_neutral_agent_kernel.canonical import (
    canonical_json,
    canonical_sha256,
    canonical_value,
    seal_contract,
)
from vendor_neutral_agent_kernel.contracts import (
    ContractMeta,
    EpistemicClaim,
    EpistemicLane,
    MemoryWriteProposal,
    ModelBehaviorProfile,
    SideEffectClass,
    SideEffectRecord,
)
from vendor_neutral_agent_kernel.recovery import build_checkpoint


ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_canonical_mapping_order_is_stable(self):
        self.assertEqual(canonical_json({"b": 2, "a": 1}), canonical_json({"a": 1, "b": 2}))

    def test_canonical_hash_changes_with_semantic_content(self):
        self.assertNotEqual(canonical_sha256({"a": 1}), canonical_sha256({"a": 2}))

    def test_canonical_rejects_unsupported_object(self):
        with self.assertRaisesRegex(TypeError, "UNSUPPORTED_CANONICAL_VALUE"):
            canonical_value(object())

    def test_sealed_contract_hash_is_stable(self):
        first = claim()
        second = seal_contract(replace(first, meta=replace(first.meta, content_hash="")))
        self.assertEqual(first.meta.content_hash, second.meta.content_hash)

    def test_sealed_contract_hash_changes_after_content_change(self):
        first = claim()
        changed = seal_contract(
            replace(
                first,
                meta=replace(first.meta, content_hash=""),
                canonical_statement="Changed statement.",
            )
        )
        self.assertNotEqual(first.meta.content_hash, changed.meta.content_hash)

    def test_contract_meta_rejects_empty_identifier(self):
        with self.assertRaisesRegex(ValueError, "object_id_REQUIRED"):
            replace(meta("valid"), object_id="")

    def test_contract_meta_rejects_non_sha_content_hash(self):
        with self.assertRaisesRegex(ValueError, "CONTENT_HASH_INVALID"):
            replace(meta("valid"), content_hash="not-a-sha")

    def test_inference_requires_supporting_evidence(self):
        with self.assertRaisesRegex(ValueError, "INFERENCE_REQUIRES_SUPPORTING_EVIDENCE"):
            EpistemicClaim(
                meta=meta("inference", lane=EpistemicLane.INFERRED),
                canonical_statement="An inference.",
                provenance_lane=EpistemicLane.INFERRED,
                supporting_evidence=(),
                opposing_evidence=(),
                alternative_explanations=(),
                confidence=0.5,
                confidence_basis="none",
                freshness="CURRENT",
                invalidation_conditions=(),
            )

    def test_unknown_claim_requires_zero_confidence(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_CONFIDENCE_MUST_BE_ZERO"):
            replace(claim(lane=EpistemicLane.USER_ASSERTED), provenance_lane=EpistemicLane.UNKNOWN)

    def test_memory_proposal_cannot_write_authority(self):
        with self.assertRaisesRegex(ValueError, "MEMORY_PROPOSAL_CANNOT_WRITE_AUTHORITY"):
            MemoryWriteProposal(
                meta=meta("memory"),
                candidate_claims=(claim(),),
                destination_scope="project:test",
                source_provenance=("fixture:public",),
                validation_status="CANDIDATE",
                authority_write=True,
                idempotency_key="key",
            )

    def test_model_profile_cannot_override_authority(self):
        with self.assertRaisesRegex(ValueError, "MODEL_PROFILE_CANNOT_OVERRIDE_AUTHORITY"):
            ModelBehaviorProfile(
                meta=meta("profile"),
                model_family="example-family",
                model_version="1",
                evaluated_at="2026-07-30",
                evaluation_refs=("eval:1",),
                task_strengths=("coding",),
                known_failure_modes=("verbosity",),
                verbosity_profile="concise",
                tool_use_profile="bounded",
                verification_profile="risk-weighted",
                delegation_profile="bounded",
                structured_output_profile="strict",
                effective_from="2026-07-30",
                review_after="2026-08-30",
                authority_overrides=("write_main",),
            )

    def test_checkpoint_rejects_duplicate_side_effect_keys(self):
        effect = SideEffectRecord(
            effect_id="effect-1",
            side_effect_class=SideEffectClass.REVERSIBLE_LOCAL,
            idempotency_key="same-key",
            external_anchor=None,
            status="DONE",
        )
        with self.assertRaisesRegex(ValueError, "DUPLICATE_SIDE_EFFECT_IDEMPOTENCY_KEY"):
            build_checkpoint(
                meta("checkpoint"),
                intent_hash="intent",
                context_hash="context",
                authority_hash="authority",
                completed_steps=("one",),
                remaining_steps=("two",),
                side_effect_ledger=(effect, replace(effect, effect_id="effect-2")),
            )

    def test_capability_ratio_validation(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_QUALITY_OUT_OF_RANGE"):
            replace(capability("route-a"), source_quality=1.1)

    def test_aggregate_schema_has_all_ten_contracts(self):
        schema = json.loads((ROOT / "schemas" / "AgentKernelContracts.schema.json").read_text(encoding="utf-8"))
        expected = {
            "AuthorityResolution",
            "TaskIntent",
            "EpistemicClaim",
            "MemoryWriteProposal",
            "CapabilityDescriptor",
            "ToolRouteDecision",
            "ExecutionCheckpoint",
            "CompletionReceipt",
            "AgentHandoff",
            "ModelBehaviorProfile",
        }
        self.assertTrue(expected.issubset(schema["$defs"]))
        self.assertEqual(len(schema["oneOf"]), 10)


if __name__ == "__main__":
    unittest.main()
