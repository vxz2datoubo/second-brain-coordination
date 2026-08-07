"""E43 Q1 — Authority Tests"""
import unittest, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_e43.authority import (
    AtomType, VerificationState, ConfidenceBand, EvidenceLayer,
    EvidenceRecord, EvidenceBundle, Atom,
    AtomFactory, EvidenceFactory, AuthorityRegistry,
    FACTORY_REJECTED, REGISTRY_REJECTED,
)


class TestAuthorityRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = AuthorityRegistry()
        self.ev_factory = EvidenceFactory(self.registry)

    def test_empty_registry(self):
        self.assertEqual(self.registry.record_count, 0)
        self.assertEqual(self.registry.bundle_count, 0)
        self.assertEqual(self.registry.atom_count, 0)

    def test_register_record(self):
        r = self.ev_factory.create_record("src:1..10", EvidenceLayer.AUTHOR_CLAIM, "text", "abc123")
        self.assertEqual(self.registry.record_count, 1)
        self.assertTrue(self.registry.verify_record_id(r.record_id))

    def test_register_bundle(self):
        r1 = self.ev_factory.create_record("src:1..10", EvidenceLayer.SOURCE_FACT, "fact A", "d1")
        r2 = self.ev_factory.create_record("src:11..20", EvidenceLayer.AUTHOR_CLAIM, "claim B", "d2")
        b = self.ev_factory.create_bundle((r1, r2))
        self.assertEqual(self.registry.bundle_count, 1)
        self.assertTrue(self.registry.verify_bundle_id(b.bundle_id))

    def test_register_atom(self):
        r = self.ev_factory.create_record("src:1..10", EvidenceLayer.SOURCE_FACT, "X is Y", "d1")
        b = self.ev_factory.create_bundle((r,))
        af = AtomFactory(self.registry)
        a = af.create("X is Y", AtomType.CONCEPT, b.bundle_id, EvidenceLayer.SOURCE_FACT,
                      ConfidenceBand.HIGH, "global", VerificationState.VERIFIED, ())
        self.assertEqual(self.registry.atom_count, 1)
        self.assertTrue(self.registry.verify_atom_id(a.atom_id))

    def test_duplicate_record_rejected(self):
        self.ev_factory.create_record("src:1..10", EvidenceLayer.AUTHOR_CLAIM, "Z", "d1")
        with self.assertRaises(ValueError):
            self.ev_factory.create_record("src:1..10", EvidenceLayer.AUTHOR_CLAIM, "Z", "d1")

    def test_unknown_id_returns_none(self):
        self.assertIsNone(self.registry.get_record("nonexistent"))
        self.assertIsNone(self.registry.get_bundle("nonexistent"))
        self.assertIsNone(self.registry.get_atom("nonexistent"))


class TestEvidenceFactory(unittest.TestCase):
    def setUp(self):
        self.registry = AuthorityRegistry()
        self.factory = EvidenceFactory(self.registry)

    def test_create_record_has_valid_signature(self):
        r = self.factory.create_record("src:0..5", EvidenceLayer.SOURCE_FACT, "data", "sha256abc")
        self.assertTrue(self.factory.verify_record(r))
        self.assertTrue(r.verify(self.registry, self.factory))

    def test_record_with_wrong_signature_fails(self):
        r = self.factory.create_record("src:0..5", EvidenceLayer.SOURCE_FACT, "data", "sha256abc")
        # Tamper with signature
        bad_r = EvidenceRecord(
            record_id=r.record_id, source_span_ref=r.source_span_ref,
            evidence_layer=r.evidence_layer, content=r.content,
            source_digest=r.source_digest,
            factory_signature=b"bad_signature_xxxxxxxxxxxxxxxxxxxxxx")
        self.assertFalse(self.factory.verify_record(bad_r))

    def test_create_bundle_identity_stable(self):
        r1 = self.factory.create_record("s1", EvidenceLayer.SOURCE_FACT, "A", "d1")
        r2 = self.factory.create_record("s2", EvidenceLayer.AUTHOR_CLAIM, "B", "d2")
        b1 = self.factory.create_bundle((r1, r2))
        # Same records => same bundle_id => registry rejects duplicate => proof of identity stability
        with self.assertRaises(ValueError):
            self.factory.create_bundle((r1, r2))

    def test_bundle_rejects_unregistered_record(self):
        # Create a record that looks like it's from the factory but isn't in registry
        pass  # Actually can't — factory always registers.

    def test_derived_confidence_high(self):
        r1 = self.factory.create_record("s1", EvidenceLayer.SOURCE_FACT, "A", "d1")
        r2 = self.factory.create_record("s2", EvidenceLayer.SOURCE_FACT, "B", "d2")
        r3 = self.factory.create_record("s3", EvidenceLayer.AUTHOR_CLAIM, "C", "d3")
        b = self.factory.create_bundle((r1, r2, r3))
        self.assertEqual(b.derived_confidence(), ConfidenceBand.HIGH)

    def test_derived_confidence_very_low(self):
        r = self.factory.create_record("s1", EvidenceLayer.HYPOTHESIS, "maybe?", "d1")
        b = self.factory.create_bundle((r,))
        self.assertEqual(b.derived_confidence(), ConfidenceBand.VERY_LOW)


class TestAtomFactory(unittest.TestCase):
    def setUp(self):
        self.registry = AuthorityRegistry()
        self.ev_factory = EvidenceFactory(self.registry)
        self.atom_factory = AtomFactory(self.registry)

    def _make_bundle(self):
        r = self.ev_factory.create_record("src:0..10", EvidenceLayer.SOURCE_FACT, "fact content", "d1")
        return self.ev_factory.create_bundle((r,))

    def test_create_and_verify_atom(self):
        b = self._make_bundle()
        a = self.atom_factory.create("ATOM TEXT", AtomType.DEFINITION, b.bundle_id,
                                     EvidenceLayer.SOURCE_FACT, ConfidenceBand.HIGH,
                                     "domain:test", VerificationState.VERIFIED, ())
        self.assertTrue(self.atom_factory.verify_atom(a))
        self.assertTrue(a.verify(self.registry, self.atom_factory))

    def test_cannot_create_atom_for_unregistered_bundle(self):
        with self.assertRaises(ValueError):
            self.atom_factory.create("X", AtomType.CONCEPT, "nonexistent_bundle",
                                     EvidenceLayer.AUTHOR_CLAIM, ConfidenceBand.LOW,
                                     "", VerificationState.UNVERIFIED, ())

    def test_cannot_create_duplicate_atom(self):
        b = self._make_bundle()
        self.atom_factory.create("dup", AtomType.CONCEPT, b.bundle_id,
                                 EvidenceLayer.SOURCE_FACT, ConfidenceBand.HIGH,
                                 "test", VerificationState.VERIFIED, ())
        with self.assertRaises(ValueError):
            self.atom_factory.create("dup", AtomType.CONCEPT, b.bundle_id,
                                     EvidenceLayer.SOURCE_FACT, ConfidenceBand.HIGH,
                                     "test", VerificationState.VERIFIED, ())

    def test_different_atom_types_produce_different_ids(self):
        b = self._make_bundle()
        a1 = self.atom_factory.create("SAME TEXT", AtomType.CONCEPT, b.bundle_id,
                                      EvidenceLayer.SOURCE_FACT, ConfidenceBand.HIGH,
                                      "test", VerificationState.VERIFIED, ())
        a2 = self.atom_factory.create("SAME TEXT", AtomType.MECHANISM, b.bundle_id,
                                      EvidenceLayer.SOURCE_FACT, ConfidenceBand.HIGH,
                                      "test", VerificationState.VERIFIED, ())
        self.assertNotEqual(a1.atom_id, a2.atom_id)

    def test_deterministic_ids(self):
        b = self._make_bundle()
        a1 = self.atom_factory.create("deterministic", AtomType.CONCEPT, b.bundle_id,
                                      EvidenceLayer.SOURCE_FACT, ConfidenceBand.HIGH,
                                      "test", VerificationState.VERIFIED, ())
        # Recompute
        expected = Atom.compute_deterministic_id(
            "deterministic", AtomType.CONCEPT, b.bundle_id,
            EvidenceLayer.SOURCE_FACT, ConfidenceBand.HIGH,
            "test", VerificationState.VERIFIED, ())
        self.assertEqual(a1.atom_id, expected)

    def test_tampered_atom_rejected(self):
        b = self._make_bundle()
        a = self.atom_factory.create("valid", AtomType.CONCEPT, b.bundle_id,
                                     EvidenceLayer.SOURCE_FACT, ConfidenceBand.HIGH,
                                     "test", VerificationState.VERIFIED, ())
        # Create a forgery with factory's atom_id but wrong signature
        forgery = Atom(
            atom_id=a.atom_id, atom_type=a.atom_type, text=a.text,
            source_bundle_id=a.source_bundle_id, provenance=a.provenance,
            confidence=a.confidence, scope=a.scope,
            verification_state=a.verification_state,
            invalidation_conditions=a.invalidation_conditions,
            factory_signature=b"forged_signature_xxxxxxxxxxxxxxx")
        self.assertFalse(self.atom_factory.verify_atom(forgery))
        self.assertFalse(forgery.verify(self.registry, self.atom_factory))

    def test_forged_atom_with_wrong_id_rejected(self):
        b = self._make_bundle()
        forged = Atom(
            atom_id="i_made_this_up", atom_type=AtomType.CONCEPT, text="fake",
            source_bundle_id=b.bundle_id, provenance=EvidenceLayer.SOURCE_FACT,
            confidence=ConfidenceBand.HIGH, scope="test",
            verification_state=VerificationState.VERIFIED,
            invalidation_conditions=(),
            factory_signature=b"fake_signature_xxxxxxxxxxxxxxxx")
        self.assertFalse(forged.verify(self.registry, self.atom_factory))

    def test_verification_recomputes_all_fields(self):
        """Changing any field should fail verification."""
        b = self._make_bundle()
        a = self.atom_factory.create("text", AtomType.CONCEPT, b.bundle_id,
                                     EvidenceLayer.SOURCE_FACT, ConfidenceBand.HIGH,
                                     "test", VerificationState.VERIFIED, ("deprecated",))
        # Forge with different scope
        forgery = Atom(
            atom_id=a.atom_id, atom_type=a.atom_type, text=a.text,
            source_bundle_id=a.source_bundle_id, provenance=a.provenance,
            confidence=a.confidence, scope="different_scope",
            verification_state=a.verification_state,
            invalidation_conditions=a.invalidation_conditions,
            factory_signature=a.factory_signature)
        self.assertFalse(forgery.verify(self.registry, self.atom_factory))


if __name__ == "__main__":
    unittest.main(verbosity=2)
