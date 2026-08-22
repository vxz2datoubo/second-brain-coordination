"""E44 Q2 Tests — Derived evidence, bundle and atom authority"""
import unittest, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)

from qclaw_e44.capability import CapabilityVerifier, EvidenceOrigin
from qclaw_e44.authority import (
    EvidenceRegistry, EvidenceFactory, EvidenceRecord, EvidenceBundle, Atom,
    EvidenceLayer, ConfidenceBand, VerificationState, AtomType, EvidenceError,
)

class TestEvidenceFactory(unittest.TestCase):
    def setUp(self):
        self.registry = EvidenceRegistry()
        self.factory = EvidenceFactory(self.registry, b"e44_test_key_xxxxxxxxxxxxxxxx32")
        self.verifier = CapabilityVerifier("E44-test-issuer", "1.0")

    def test_create_record_produces_verified_record(self):
        cap = self.verifier.verify(b"Market data here", "src:0:16", EvidenceOrigin.SOURCE_FACT)
        rec = self.factory.create_record(cap)
        self.assertIsInstance(rec, EvidenceRecord)
        self.assertEqual(self.registry.record_count, 1)
        self.assertTrue(rec.verify(self.registry, self.factory))

    def test_duplicate_record_rejected(self):
        cap = self.verifier.verify(b"data", "src:0:4", EvidenceOrigin.SOURCE_FACT)
        self.factory.create_record(cap)
        with self.assertRaises(EvidenceError):
            self.factory.create_record(cap)

    def test_layer_derived_from_capability_not_caller(self):
        cap = self.verifier.verify(b"I know this is true", "src:0:18", EvidenceOrigin.SOURCE_FACT)
        rec = self.factory.create_record(cap)
        self.assertEqual(rec.origin_class, EvidenceOrigin.USER_EXPLICIT)
        # EvidenceLayer is derived, NOT raw SOURCE_FACT just because caller said so
        self.assertIsInstance(rec.evidence_layer, EvidenceLayer)

    def test_re_verify_fails_with_foreign_object(self):
        cap1 = self.verifier.verify(b"data1", "src:0:5", EvidenceOrigin.SOURCE_FACT)
        rec = self.factory.create_record(cap1)
        # Forged record with same ID
        forged = EvidenceRecord(rec.record_id, "fake_cap", EvidenceLayer.SOURCE_FACT,
            "fake_hash", EvidenceOrigin.SOURCE_FACT, "fake_digest",
            "44.0", "1.0", "fake_issuer", 0, b"bad_sig")
        self.assertFalse(forged.verify(self.registry, self.factory))

    def test_confidence_derived_high_for_source_fact(self):
        cap = self.verifier.verify(b"Market data", "src:0:11", EvidenceOrigin.SOURCE_FACT)
        rec = self.factory.create_record(cap)
        bundle = self.factory.create_bundle((rec,))
        self.assertEqual(bundle.confidence, ConfidenceBand.HIGH)

    def test_confidence_derived_low_for_hypothesis(self):
        cap = self.verifier.verify(b"It could be true", "src:0:16", EvidenceOrigin.HYPOTHESIS)
        rec = self.factory.create_record(cap)
        bundle = self.factory.create_bundle((rec,))
        self.assertEqual(bundle.confidence, ConfidenceBand.LOW)

    def test_verification_state_derived(self):
        cap = self.verifier.verify(b"Market fact data here", "src:0:20", EvidenceOrigin.SOURCE_FACT)
        rec = self.factory.create_record(cap)
        bundle = self.factory.create_bundle((rec,))
        self.assertEqual(bundle.verification_state, VerificationState.VERIFIED)

    def test_create_atom_from_bundle(self):
        cap = self.verifier.verify(b"Systematic risk affects all assets", "src:0:32",
                                   EvidenceOrigin.SOURCE_FACT)
        rec = self.factory.create_record(cap)
        bundle = self.factory.create_bundle((rec,))
        atom = self.factory.create_atom("Systematic risk", AtomType.CONCEPT, bundle)
        self.assertIsInstance(atom, Atom)
        self.assertEqual(atom.atom_type, AtomType.CONCEPT)
        self.assertEqual(self.registry.atom_count, 1)
        self.assertTrue(atom.verify(self.registry, self.factory))

    def test_empty_bundle_rejected(self):
        with self.assertRaises(EvidenceError):
            self.factory.create_bundle(())

    def test_bundle_identity_changes_with_records(self):
        cap1 = self.verifier.verify(b"data A", "src:0:6", EvidenceOrigin.SOURCE_FACT)
        cap2 = self.verifier.verify(b"data B", "src:0:6", EvidenceOrigin.SOURCE_FACT)
        r1 = self.factory.create_record(cap1)
        r2 = self.factory.create_record(cap2)
        b1 = self.factory.create_bundle((r1,))
        b2 = self.factory.create_bundle((r1, r2))
        self.assertNotEqual(b1.bundle_id, b2.bundle_id)

    def test_atom_text_field(self):
        cap = self.verifier.verify(b"text here", "src:0:9", EvidenceOrigin.SOURCE_FACT)
        rec = self.factory.create_record(cap)
        bundle = self.factory.create_bundle((rec,))
        atom = self.factory.create_atom("My atom text", AtomType.CONCEPT, bundle)
        self.assertEqual(atom.text, "My atom text")

    def test_immutable_fields(self):
        cap = self.verifier.verify(b"data", "src:0:4", EvidenceOrigin.SOURCE_FACT)
        rec = self.factory.create_record(cap)
        with self.assertRaises((AttributeError,)):
            rec.content_hash = "fake"

    def test_bundle_verify(self):
        cap = self.verifier.verify(b"Market signals", "src:0:14", EvidenceOrigin.SOURCE_FACT)
        rec = self.factory.create_record(cap)
        bundle = self.factory.create_bundle((rec,))
        self.assertTrue(bundle.verify(self.registry, self.factory))

if __name__ == "__main__":
    unittest.main(verbosity=2)
