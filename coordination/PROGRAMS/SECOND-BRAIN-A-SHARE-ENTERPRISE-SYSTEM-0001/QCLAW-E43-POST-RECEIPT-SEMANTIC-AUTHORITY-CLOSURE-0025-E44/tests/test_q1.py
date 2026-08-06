"""E44 Q1 Tests — VerifiedEvidenceCapability boundary contract"""
import unittest
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)

from qclaw_e44.capability import (
    CapabilityVerifier, VerifiedEvidenceCapability, CapabilityError,
    CapabilityStatus, EvidenceOrigin, SYNTHETIC_BYTES, SYNTHETIC_SOURCE_IDS,
)


class TestCapabilityVerifier(unittest.TestCase):
    def setUp(self):
        self.verifier = CapabilityVerifier("E44-test-issuer", "1.0")

    def test_verify_produces_capability(self):
        cap = self.verifier.verify(b"Market data", "src:0:11", EvidenceOrigin.SOURCE_FACT)
        self.assertIsInstance(cap, VerifiedEvidenceCapability)
        self.assertEqual(cap.issuer, "E44-test-issuer")
        self.assertEqual(cap.source_id, "src:0:11")
        self.assertEqual(len(cap.capability_id), 64)
        self.assertEqual(len(cap.raw_span_hash), 64)
        self.assertTrue(cap.verify_integrity(self.verifier))

    def test_duplicate_capability_rejected(self):
        self.verifier.verify(b"test", "src:0:4", EvidenceOrigin.SOURCE_FACT)
        with self.assertRaises(CapabilityError) as ctx:
            self.verifier.verify(b"test", "src:0:4", EvidenceOrigin.SOURCE_FACT)
        self.assertEqual(ctx.exception.status, CapabilityStatus.SELF_ISSUED)

    def test_different_source_produces_different_id(self):
        cap1 = self.verifier.verify(b"alpha", "src:0:5", EvidenceOrigin.SOURCE_FACT)
        cap2 = self.verifier.verify(b"beta", "src:0:4", EvidenceOrigin.SOURCE_FACT)
        self.assertNotEqual(cap1.capability_id, cap2.capability_id)

    def test_different_issuer_produces_different_id(self):
        v1 = CapabilityVerifier("issuer-A", "1.0")
        v2 = CapabilityVerifier("issuer-B", "1.0")
        cap1 = v1.verify(b"data", "src:0:4", EvidenceOrigin.SOURCE_FACT)
        cap2 = v2.verify(b"data", "src:0:4", EvidenceOrigin.SOURCE_FACT)
        self.assertNotEqual(cap1.capability_id, cap2.capability_id)

    def test_immutable_fields(self):
        cap = self.verifier.verify(b"data", "src:0:4", EvidenceOrigin.SOURCE_FACT)
        with self.assertRaises((AttributeError, dataclasses.FrozenInstanceError)):
            cap.issuer = "fake"

    def test_verify_integrity_false_with_wrong_issuer(self):
        cap = self.verifier.verify(b"data", "src:0:4", EvidenceOrigin.SOURCE_FACT)
        v2 = CapabilityVerifier("other-issuer", "1.0")
        self.assertFalse(cap.verify_integrity(v2))

    def test_verify_integrity_false_with_new_policy(self):
        cap = self.verifier.verify(b"data", "src:0:4", EvidenceOrigin.SOURCE_FACT)
        v2 = CapabilityVerifier("E44-test-issuer", "2.0")
        self.assertFalse(cap.verify_integrity(v2))

    def test_derive_user_explicit(self):
        cap = self.verifier.verify(b"I know that this works", "src:0:20",
                                   EvidenceOrigin.SOURCE_FACT)
        self.assertEqual(cap.origin_class, EvidenceOrigin.USER_EXPLICIT)

    def test_derive_hypothesis(self):
        cap = self.verifier.verify(b"It could be that patterns repeat", "src:0:30",
                                   EvidenceOrigin.SOURCE_FACT)
        self.assertEqual(cap.origin_class, EvidenceOrigin.HYPOTHESIS)

    def test_derive_inference(self):
        cap = self.verifier.verify(b"Therefore, the result is valid", "src:0:28",
                                   EvidenceOrigin.SOURCE_FACT)
        self.assertEqual(cap.origin_class, EvidenceOrigin.INFERENCE)

    def test_derive_value_judgment(self):
        cap = self.verifier.verify(b"This is the best strategy", "src:0:24",
                                   EvidenceOrigin.SOURCE_FACT)
        self.assertEqual(cap.origin_class, EvidenceOrigin.VALUE_JUDGMENT)

    def test_derive_author_claim(self):
        cap = self.verifier.verify(b"According to the analyst, profits rose", "src:0:37",
                                   EvidenceOrigin.SOURCE_FACT)
        self.assertEqual(cap.origin_class, EvidenceOrigin.AUTHOR_CLAIM)

    def test_derive_source_fact(self):
        cap = self.verifier.verify(b"Market volatility increases during earnings season",
                                   "src:0:45", EvidenceOrigin.SOURCE_FACT)
        self.assertEqual(cap.origin_class, EvidenceOrigin.SOURCE_FACT)

    def test_synthetic_fixtures_available(self):
        self.assertIn("fact_short", SYNTHETIC_BYTES)
        self.assertIn("user_explicit", SYNTHETIC_BYTES)
        self.assertIn("hypothesis", SYNTHETIC_BYTES)
        self.assertGreater(len(SYNTHETIC_BYTES), 5)

    def test_evidence_digest_different_per_origin(self):
        cap1 = self.verifier.verify(b"Market data here", "src:0:16", EvidenceOrigin.SOURCE_FACT)
        cap2 = self.verifier.verify(b"I know that Market data here", "src:0:26",
                                    EvidenceOrigin.SOURCE_FACT)
        self.assertNotEqual(cap1.evidence_digest, cap2.evidence_digest)

    def test_capability_error_contains_status(self):
        try:
            self.verifier.verify(b"test", "src:0:4", EvidenceOrigin.SOURCE_FACT)
            self.verifier.verify(b"test", "src:0:4", EvidenceOrigin.SOURCE_FACT)
        except CapabilityError as e:
            self.assertEqual(e.status, CapabilityStatus.SELF_ISSUED)
            self.assertIn("duplicate", str(e))


import dataclasses

if __name__ == "__main__":
    unittest.main(verbosity=2)
