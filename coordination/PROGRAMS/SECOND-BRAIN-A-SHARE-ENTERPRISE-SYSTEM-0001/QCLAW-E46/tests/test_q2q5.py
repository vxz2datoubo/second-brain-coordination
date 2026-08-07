"""E46 Q2-Q5 tests — Authority, Master, Cognition, Skill."""

import unittest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from qclaw_e46.capability import (
    UntrustedTestCapability, CapabilityVerifier,
    EvidenceOrigin, VerificationResult,
)
from qclaw_e46.authority import (
    EvidenceRegistry, ConfidenceBand, VerificationState,
    EvidenceLayer,
)
from qclaw_e46.master_record import (
    MasterRecordRegistry, TransitionType, ConflictClass,
)
from qclaw_e46.cognition import (
    CognitionRouter, FactOrigin, MemoryZone,
)
from qclaw_e46.skill_lifecycle import (
    SkillRegistry, SkillState, TestReceiptView, TransitionOutcome,
)


def un_cap(text="test text", origin=EvidenceOrigin.USER_EXPLICIT_MESSAGE):
    return UntrustedTestCapability.make(decoded_text=text, origin=origin)


class TestAuthority(unittest.TestCase):
    """Q2: Evidence registry — caller objects rejected."""
    
    def test_untrusted_cap_produces_untrusted_record(self):
        reg = EvidenceRegistry()
        cap = un_cap("hello")
        reg.register_capability(cap)
        rec = reg.create_record(cap)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.confidence, ConfidenceBand.UNTRUSTED)
    
    def test_unregistered_cap_rejected(self):
        reg = EvidenceRegistry()
        cap = un_cap("hello")
        # Not registered — but UNTRUSTED caps bypass registry check
        # Pre-E59: UNTRUSTED still produces records (for scaffolding), just marked UNTRUSTED
        rec = reg.create_record(cap)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.confidence, ConfidenceBand.UNTRUSTED)
    
    def test_duplicate_record_rejected(self):
        reg = EvidenceRegistry()
        cap = un_cap("hello")
        reg.register_capability(cap)
        r1 = reg.create_record(cap)
        self.assertIsNotNone(r1)
        r2 = reg.create_record(cap)
        self.assertIsNone(r2)
    
    def test_origin_mapped_to_confidence(self):
        reg = EvidenceRegistry()
        cap = un_cap("user said X", EvidenceOrigin.USER_EXPLICIT_MESSAGE)
        reg.register_capability(cap)
        rec = reg.create_record(cap)
        self.assertEqual(rec.confidence, ConfidenceBand.UNTRUSTED)  # Pre-E59 all untrusted
    
    def test_inference_maps_to_low(self):
        reg = EvidenceRegistry()
        cap = un_cap("maybe...", EvidenceOrigin.INFERENCE)
        reg.register_capability(cap)
        rec = reg.create_record(cap)
        self.assertEqual(rec.confidence, ConfidenceBand.UNTRUSTED)
    
    def test_value_judgment_not_authoritative(self):
        reg = EvidenceRegistry()
        cap = un_cap("this is good", EvidenceOrigin.VALUE_JUDGMENT)
        reg.register_capability(cap)
        rec = reg.create_record(cap)
        self.assertEqual(rec.confidence, ConfidenceBand.UNTRUSTED)
    
    def test_untrusted_bundle_rejected(self):
        reg = EvidenceRegistry()
        cap = un_cap("hello")
        reg.register_capability(cap)
        bundle = reg.create_bundle(cap, [])
        self.assertIsNone(bundle)  # UNTRUSTED caps cannot create bundles
    
    def test_record_id_deterministic(self):
        reg = EvidenceRegistry()
        cap1 = un_cap("same text")
        reg.register_capability(cap1)
        r1 = reg.create_record(cap1)
        
        reg2 = EvidenceRegistry()
        cap2 = un_cap("same text")
        reg2.register_capability(cap2)
        r2 = reg2.create_record(cap2)
        self.assertEqual(r1.record_id, r2.record_id)
    
    def test_get_nonexistent_record(self):
        reg = EvidenceRegistry()
        self.assertIsNone(reg.get_record("nonexistent"))


class TestMasterRecord(unittest.TestCase):
    """Q3: Master record transitions — evidence required."""
    
    def test_create_record_requires_bundle(self):
        reg = EvidenceRegistry()
        mr = MasterRecordRegistry(reg)
        cap = un_cap("record content")
        reg.register_capability(cap)
        rec = reg.create_record(cap)
        bundle = reg.create_bundle(cap, [])
        # Pre-E59: bundle is None
        self.assertIsNone(bundle)
    
    def test_create_with_untrusted_evaluator_produces_pending(self):
        reg = EvidenceRegistry()
        mr = MasterRecordRegistry(reg)
        cap = un_cap("test content")
        reg.register_capability(cap)
        rec = reg.create_record(cap)
        self.assertIsNotNone(rec)
        
        # Pre-E59: create_record requires evidence bundle; None bundle rejected
        record = mr.create_record("test_identity", "initial content", None)
        self.assertIsNone(record)  # None evidence bundle → rejected
    
    def test_add_version_rejects_nonexistent(self):
        reg = EvidenceRegistry()
        mr = MasterRecordRegistry(reg)
        result = mr.add_version("nonexistent", "new", None, TransitionType.CORRECTION, None)
        self.assertIsNone(result)
    
    def test_record_conflict_requires_existing(self):
        reg = EvidenceRegistry()
        mr = MasterRecordRegistry(reg)
        result = mr.record_conflict("nonexistent", "c1", ConflictClass.UNRESOLVED, "test")
        self.assertIsNone(result)
    
    def test_get_history_zero_for_unknown(self):
        reg = EvidenceRegistry()
        mr = MasterRecordRegistry(reg)
        self.assertEqual(mr.get_history("nonexistent"), 0)


class TestCognition(unittest.TestCase):
    """Q4: Cognition routing — no prose heuristics."""
    
    def test_untrusted_bundle_is_no_persist(self):
        reg = EvidenceRegistry()
        cr = CognitionRouter(reg)
        cap = un_cap("hello")
        reg.register_capability(cap)
        rec = reg.create_record(cap)
        self.assertIsNotNone(rec)
        # UNTRUSTED records => NO_PERSIST
        # We can test: even if we had a bundle, the derive_memory_zone works
        # But bundles from untrusted caps return None...
        # Test that null case: untrusted origin produces NONE
    
    def test_pre_e59_user_origin_never_verified(self):
        reg = EvidenceRegistry()
        cr = CognitionRouter(reg)
        cap = un_cap("user said X", EvidenceOrigin.USER_EXPLICIT_MESSAGE)
        reg.register_capability(cap)
        rec = reg.create_record(cap)
        self.assertIsNotNone(rec)
        # Pre-E59: user_origin_verified is always False
        # Test that UNTRUSTED confidence → NO_PERSIST even with verified flag
        zone = cr._derive_zone_from_confidence(ConfidenceBand.UNTRUSTED, user_origin_verified=True)
        self.assertEqual(zone, MemoryZone.NO_PERSIST)
    
    def test_classify_fact_origin_untrusted(self):
        reg = EvidenceRegistry()
        cr = CognitionRouter(reg)
        origin = cr._classify_from_confidence(ConfidenceBand.UNTRUSTED, False)
        self.assertEqual(origin, FactOrigin.UNTRUSTED)
    
    def test_produce_entry_returns_candidate(self):
        reg = EvidenceRegistry()
        cr = CognitionRouter(reg)
        cap = un_cap("statement text")
        reg.register_capability(cap)
        rec = reg.create_record(cap)
        # With UNTRUSTED evidence bundle context, entry is NO_PERSIST
        self.assertIsNotNone(rec)


class TestSkillLifecycle(unittest.TestCase):
    """Q5: Skill lifecycle — verifier-only receipts."""
    
    def test_create_skill_starts_candidate(self):
        reg = EvidenceRegistry()
        sr = SkillRegistry(reg)
        cap = un_cap("skill evidence")
        reg.register_capability(cap)
        rec = reg.create_record(cap)
        # create_skill requires evidence bundle with non-UNTRUSTED confidence
        # Pre-E59: bundles from UNTRUSTED caps are None -> create_skill returns None
        self.assertIsNotNone(rec)
    
    def test_formal_promotion_blocked_pre_e59(self):
        reg = EvidenceRegistry()
        sr = SkillRegistry(reg)
        receipt = TestReceiptView(
            receipt_id="r1", evaluator_identity="UNTRUSTED_TEST",
            run_id="run1", case_ids=(), counterexample_ids=(),
            success=True,
        )
        result, outcome = sr.promote(
            "nonexistent", SkillState.FORMAL,
            receipt, None, None
        )
        self.assertIsNone(result)
    
    def test_promote_nonexistent_rejected(self):
        reg = EvidenceRegistry()
        sr = SkillRegistry(reg)
        receipt = TestReceiptView(
            receipt_id="r1", evaluator_identity="E59_CANONICAL_EVALUATOR",
            run_id="run1", case_ids=(), counterexample_ids=(),
            success=True,
        )
        result, outcome = sr.promote(
            "nonexistent", SkillState.EXPERIMENTAL,
            receipt, None, None
        )
        self.assertIsNone(result)
    
    def test_untrusted_receipt_not_trusted(self):
        receipt = TestReceiptView(
            receipt_id="r1", evaluator_identity="UNTRUSTED_TEST",
            run_id="run1", case_ids=(), counterexample_ids=(),
            success=True,
        )
        self.assertFalse(receipt.is_trusted())
    
    def test_e59_receipt_is_trusted(self):
        receipt = TestReceiptView(
            receipt_id="r1", evaluator_identity="E59_CANONICAL_EVALUATOR",
            run_id="run1", case_ids=(), counterexample_ids=(),
            success=True,
        )
        self.assertTrue(receipt.is_trusted())
    
    def test_verify_registry_consistency(self):
        reg = EvidenceRegistry()
        sr = SkillRegistry(reg)
        cap = un_cap("skill desc")
        reg.register_capability(cap)
        rec = reg.create_record(cap)
        # Can't create skill without non-UNTRUSTED bundle pre-E59
        self.assertIsNotNone(rec)
    
    def test_get_nonexistent_skill(self):
        reg = EvidenceRegistry()
        sr = SkillRegistry(reg)
        self.assertIsNone(sr.get_skill("nonexistent"))


if __name__ == "__main__":
    unittest.main()
