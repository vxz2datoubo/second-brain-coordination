"""E45 Q1 — VerifiedEvidenceCapabilityView tests"""
import unittest, hashlib, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from qclaw_e45.capability import (
    VerifiedEvidenceCapabilityView, make_test_capability,
    CapabilityIssuerIdentity, EvidenceOrigin, VerificationState,
    UNTRUSTED_TEST_DOUBLE
)

SAMPLE = b"The market opened at 9:30 AM with strong momentum."


class TestCapabilityProtocol(unittest.TestCase):
    def test_immutable_fields(self):
        cap = make_test_capability("doc1", (4, 10), "market", EvidenceOrigin.SOURCE_DOCUMENT, SAMPLE, verified=True)
        with self.assertRaises(Exception):
            cap.origin = EvidenceOrigin.USER_EXPLICIT_MESSAGE  # frozen

    def test_verified_state(self):
        cap = make_test_capability("doc1", (4, 10), "market", EvidenceOrigin.SOURCE_DOCUMENT, SAMPLE, verified=True)
        self.assertTrue(cap.is_verified())
        self.assertFalse(cap.is_rejected())

    def test_unverified_state(self):
        cap = make_test_capability("doc1", (4, 10), "market", EvidenceOrigin.HYPOTHESIS, SAMPLE)
        self.assertFalse(cap.is_verified())
        self.assertEqual(cap.verification_result, VerificationState.UNVERIFIED)

    def test_user_explicit_origin(self):
        cap = make_test_capability("msg42", (0, 15), "I know about RSI", EvidenceOrigin.USER_EXPLICIT_MESSAGE, b"I know about RSI", verified=True)
        self.assertTrue(cap.origin_is_user_explicit())

    def test_source_document_not_user(self):
        cap = make_test_capability("doc1", (0, 5), "hello", EvidenceOrigin.SOURCE_DOCUMENT, SAMPLE)
        self.assertFalse(cap.origin_is_user_explicit())

    def test_digest_matches(self):
        cap = make_test_capability("doc1", (4, 10), "market", EvidenceOrigin.SOURCE_DOCUMENT, SAMPLE)
        self.assertTrue(cap.digest_matches(SAMPLE))

    def test_digest_mismatch(self):
        cap = make_test_capability("doc1", (4, 10), "market", EvidenceOrigin.SOURCE_DOCUMENT, SAMPLE)
        tampered = b"The TRADING closed at 4:00 PM"
        self.assertFalse(cap.digest_matches(tampered))

    def test_different_issuer_different_id(self):
        cap1 = make_test_capability("doc1", (0, 3), "The", EvidenceOrigin.SOURCE_DOCUMENT, SAMPLE, verified=True)
        cap2 = make_test_capability("doc2", (0, 3), "The", EvidenceOrigin.SOURCE_DOCUMENT, SAMPLE, verified=True)
        self.assertNotEqual(cap1.source_identity, cap2.source_identity)

    def test_origin_types_distinct(self):
        origins = set()
        for o in EvidenceOrigin:
            cap = make_test_capability("d", (0, 3), "abc", o, b"abc", verified=(o == EvidenceOrigin.USER_EXPLICIT_MESSAGE))
            origins.add(cap.origin)
        self.assertIn(EvidenceOrigin.USER_EXPLICIT_MESSAGE, origins)
        self.assertIn(EvidenceOrigin.HYPOTHESIS, origins)
        self.assertIn(EvidenceOrigin.AUTHOR_CLAIM, origins)

    def test_test_double_marked(self):
        cap = make_test_capability("d", (0, 1), "a", EvidenceOrigin.SOURCE_DOCUMENT, b"a")
        self.assertEqual(cap.issuer.issuer_id, UNTRUSTED_TEST_DOUBLE)

    def test_capability_does_not_expose_signing_key(self):
        cap = make_test_capability("d", (0, 5), "hello", EvidenceOrigin.SOURCE_DOCUMENT, b"hello world", verified=True)
        self.assertFalse(hasattr(cap, "signing_key"))
        self.assertFalse(hasattr(cap, "hmac_key"))
        self.assertFalse(hasattr(cap, "private_key"))

    def test_no_issuer_constructor_in_consumer(self):
        """Consumer cannot create a capability with arbitrary verified=True from a source it owns."""
        source = "I fabricated this evidence"
        digest = hashlib.sha256(source.encode()).hexdigest()
        with self.assertRaises(TypeError):
            VerifiedEvidenceCapabilityView(
                issuer=CapabilityIssuerIdentity("my-fake-issuer", "1.0"),
                source_identity="fake",
                raw_span=(0, len(source)),
                decoded_text=source,
                evidence_digest=digest,
                origin=EvidenceOrigin.USER_EXPLICIT_MESSAGE,
                verification_result=VerificationState.VERIFIED,
                _bypass_frozen=True  # should not exist
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
