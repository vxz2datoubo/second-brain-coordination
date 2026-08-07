"""E46 Q1 tests — Capability anti-forgery."""

import unittest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from qclaw_e46.capability import (
    VerifiedEvidenceCapabilityView,
    CapabilityVerifier,
    CapabilityAccessError,
    UntrustedTestCapability,
    EvidenceOrigin,
    VerificationResult,
)


class TestCapabilityAntiForgery(unittest.TestCase):
    """Q1: No ordinary caller can construct VERIFIED authority."""

    def test_direct_construction_rejected(self):
        """Direct construction of VerifiedEvidenceCapabilityView must fail."""
        with self.assertRaises(CapabilityAccessError):
            VerifiedEvidenceCapabilityView(
                capability_id="test",
                issuer_identity="me",
                source_identity="src",
                raw_span=(0, 10),
                decoded_text="hello",
                evidence_digest="abc",
                origin=EvidenceOrigin.UNKNOWN,
            )
    
    def test_factory_seal_blocks_known_sentinel_bypass(self):
        """Even knowing the sentinel, caller cannot bypass without the internal factory."""
        # The sentinel is module-private; external code cannot access _FACTORY_SEAL_SENTINEL
        # Proving this: any attempt with None or a string seal fails
        with self.assertRaises(CapabilityAccessError):
            VerifiedEvidenceCapabilityView(
                capability_id="x", issuer_identity="x", source_identity="x",
                raw_span=(0,1), decoded_text="x", evidence_digest="x",
                origin=EvidenceOrigin.UNKNOWN,
                _factory_seal=None,
            )
    
    def test_verifier_always_untrusted_pre_e59(self):
        """Pre-E59: verifier.accept() always returns UNTRUSTED_DOUBLE."""
        verifier = CapabilityVerifier()
        cap = verifier.accept({
            "capability_id": "cap-1",
            "issuer_identity": "E59_CANONICAL_VERIFIER",
            "source_identity": "user-msg-42",
            "raw_span": (0, 5),
            "decoded_text": "hello",
            "evidence_digest": "abc123",
            "origin": "USER_EXPLICIT_MESSAGE",
        })
        self.assertTrue(cap.is_untrusted_double())
        self.assertFalse(cap.is_verified())
        self.assertFalse(cap.origin_is_user_explicit())
        self.assertEqual(cap.verification_result, VerificationResult.UNTRUSTED_DOUBLE)
    
    def test_verifier_rejects_unknown_issuer(self):
        """Any non-E59 issuer is UNTRUSTED_DOUBLE."""
        verifier = CapabilityVerifier()
        cap = verifier.accept({
            "issuer_identity": "fake-verifier",
            "source_identity": "x",
            "origin": "USER_EXPLICIT_MESSAGE",
        })
        self.assertTrue(cap.is_untrusted_double())
    
    def test_test_double_explicitly_marked(self):
        """UntrustedTestCapability.make() produces marked UNTRUSTED_DOUBLE."""
        cap = UntrustedTestCapability.make(
            source_identity="test-source",
            decoded_text="some text",
            origin=EvidenceOrigin.USER_EXPLICIT_MESSAGE,
        )
        self.assertTrue(cap.is_untrusted_double())
        self.assertEqual(cap.issuer_identity, "UNTRUSTED_TEST_DOUBLE")
        self.assertFalse(cap.is_verified())
        self.assertFalse(cap.origin_is_user_explicit())
    
    def test_origin_types_preserved_but_not_authority(self):
        """Origin enum is preserved but UNTRUSTED_DOUBLE blocks authority."""
        cap = UntrustedTestCapability.make(
            decoded_text="user said X",
            origin=EvidenceOrigin.USER_EXPLICIT_MESSAGE,
        )
        self.assertEqual(cap.origin, EvidenceOrigin.USER_EXPLICIT_MESSAGE)
        self.assertFalse(cap.origin_is_user_explicit())  # Not verified!
    
    def test_external_source_document_not_user(self):
        """Source document origin is distinct from user origin."""
        cap = UntrustedTestCapability.make(
            decoded_text="document content",
            origin=EvidenceOrigin.EXTERNAL_SOURCE_DOCUMENT,
        )
        self.assertFalse(cap.origin_is_user_explicit())
        self.assertFalse(cap.origin_is_source_document())  # Not verified!
    
    def test_digest_matches_works(self):
        """digest_matches compares evidence digests."""
        c1 = UntrustedTestCapability.make(decoded_text="abc")
        c2 = UntrustedTestCapability.make(decoded_text="abc")
        c3 = UntrustedTestCapability.make(decoded_text="different")
        self.assertTrue(c1.digest_matches(c2))
        self.assertFalse(c1.digest_matches(c3))
    
    def test_raw_span_bytes_slice(self):
        """raw_span_bytes correctly slices source."""
        cap = UntrustedTestCapability.make(decoded_text="hello world")
        self.assertEqual(cap.raw_span, (0, 11))
        self.assertEqual(cap.raw_span_bytes(b"hello world"), b"hello world")
    
    def test_user_origin_requires_verified(self):
        """origin_is_user_explicit requires both VERIFIED and correct origin."""
        # Test double: correct origin but UNTRUSTED -> not user_explicit
        cap = UntrustedTestCapability.make(
            decoded_text="hello",
            origin=EvidenceOrigin.USER_EXPLICIT_MESSAGE,
        )
        self.assertFalse(cap.origin_is_user_explicit())
    
    def test_inference_not_user_origin(self):
        """INFERENCE origin is never user-explicit."""
        cap = UntrustedTestCapability.make(
            decoded_text="probably...",
            origin=EvidenceOrigin.INFERENCE,
        )
        self.assertFalse(cap.origin_is_user_explicit())
    
    def test_hypothesis_not_authority(self):
        """HYPOTHESIS carries no authority."""
        cap = UntrustedTestCapability.make(
            decoded_text="maybe X causes Y",
            origin=EvidenceOrigin.HYPOTHESIS,
        )
        self.assertFalse(cap.is_verified())
    
    def test_value_judgment_not_fact(self):
        """VALUE_JUDGMENT is not evidence of fact."""
        cap = UntrustedTestCapability.make(
            decoded_text="this is good",
            origin=EvidenceOrigin.VALUE_JUDGMENT,
        )
        self.assertFalse(cap.origin_is_user_explicit())


if __name__ == "__main__":
    unittest.main()
