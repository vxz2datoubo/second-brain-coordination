"""E42 Q1 — Authority Tests

- Factory-controlled Atom creation
- Direct construction rejection
- Deep immutability
- Derived (not caller-labeled) confidence/verification/evidence_layer
- Evidence bundle validation
"""
import unittest
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_e42.authority import (
    Atom, AtomFactory, AtomAccessError, EvidenceRecord, EvidenceBundle,
    AtomType, EvidenceLayer, VerificationState, ConfidenceBand,
    _compute_atom_id, DOMAIN_SEPARATOR,
)

def _make_verified_record(rec_id="R001", src_id="SRC001",
                          etype=EvidenceLayer.AUTHOR_CLAIM,
                          vstate=VerificationState.UNVERIFIED):
    return EvidenceRecord(
        record_id=rec_id,
        source_document_id=src_id,
        source_span_start=0,
        source_span_end=100,
        evidence_type=etype,
        verification_status=vstate,
    )


class TestEvidenceBundle(unittest.TestCase):
    def test_dominant_layer_single(self):
        r = _make_verified_record(etype=EvidenceLayer.AUTHOR_CLAIM)
        b = EvidenceBundle(records=(r,), bundle_id="B1")
        self.assertEqual(b.dominant_layer(), EvidenceLayer.AUTHOR_CLAIM)

    def test_dominant_layer_precedence_evidence_wins(self):
        r1 = _make_verified_record("R1", etype=EvidenceLayer.AUTHOR_CLAIM)
        r2 = _make_verified_record("R2", etype=EvidenceLayer.EVIDENCE)
        b = EvidenceBundle(records=(r1, r2), bundle_id="B2")
        self.assertEqual(b.dominant_layer(), EvidenceLayer.EVIDENCE)

    def test_derived_confidence_low_on_empty(self):
        b = EvidenceBundle(records=(), bundle_id="B0")
        self.assertEqual(b.derived_confidence(), ConfidenceBand.LOW)

    def test_derived_confidence_high(self):
        records = tuple(
            _make_verified_record(f"R{i}", vstate=VerificationState.VERIFIED)
            for i in range(4)
        )
        b = EvidenceBundle(records=records, bundle_id="BH")
        self.assertEqual(b.derived_confidence(), ConfidenceBand.HIGH)

    def test_derived_confidence_medium(self):
        records = (
            _make_verified_record("R1", vstate=VerificationState.VERIFIED),
            _make_verified_record("R2", vstate=VerificationState.VERIFIED),
            _make_verified_record("R3", vstate=VerificationState.UNVERIFIED),
        )
        b = EvidenceBundle(records=records, bundle_id="BM")
        self.assertEqual(b.derived_confidence(), ConfidenceBand.MEDIUM)

    def test_derived_verification_falsified(self):
        records = (
            _make_verified_record("R1", vstate=VerificationState.VERIFIED),
            _make_verified_record("R2", vstate=VerificationState.FALSIFIED),
        )
        b = EvidenceBundle(records=records, bundle_id="BF")
        self.assertEqual(b.derived_verification(), VerificationState.FALSIFIED)

    def test_source_fact_requires_verified(self):
        with self.assertRaises(ValueError):
            EvidenceRecord(record_id="R1", source_document_id="S1",
                          source_span_start=0, source_span_end=10,
                          evidence_type=EvidenceLayer.SOURCE_FACT,
                          verification_status=VerificationState.UNVERIFIED)

    def test_bundle_digest_deterministic(self):
        r1 = _make_verified_record("R1")
        r2 = _make_verified_record("R2")
        b1 = EvidenceBundle(records=(r1, r2), bundle_id="BD")
        b2 = EvidenceBundle(records=(r1, r2), bundle_id="BD")
        self.assertEqual(b1.digest, b2.digest)

    def test_bundle_digest_differs(self):
        r1 = _make_verified_record("R1")
        r2 = _make_verified_record("R2", etype=EvidenceLayer.EVIDENCE)
        b1 = EvidenceBundle(records=(r1,), bundle_id="BD")
        b2 = EvidenceBundle(records=(r2,), bundle_id="BD")
        self.assertNotEqual(b1.digest, b2.digest)


class TestAtomFactory(unittest.TestCase):
    def setUp(self):
        self.factory = AtomFactory("TEST_FACTORY")
        self.evidence = EvidenceBundle(records=(
            _make_verified_record("R1", vstate=VerificationState.VERIFIED),
            _make_verified_record("R2", vstate=VerificationState.VERIFIED),
            _make_verified_record("R3", vstate=VerificationState.VERIFIED),
            _make_verified_record("R4", vstate=VerificationState.VERIFIED),
        ), bundle_id="E001")

    def test_factory_build_ok(self):
        atom = self.factory.build(AtomType.CONCEPT, "market makers provide liquidity",
                                   self.evidence)
        self.assertEqual(atom.atom_type, AtomType.CONCEPT)
        self.assertEqual(atom.confidence, ConfidenceBand.HIGH)
        self.assertEqual(atom.verification_state, VerificationState.VERIFIED)
        self.assertEqual(atom.evidence_layer, EvidenceLayer.AUTHOR_CLAIM)

    def test_factory_rejects_direct_construction(self):
        """Direct Atom() must fail — AtomAccessError raised during construction."""
        with self.assertRaises(AtomAccessError):
            Atom(atom_id="fake", atom_type=AtomType.CONCEPT,
                 content="test", evidence_layer=EvidenceLayer.AUTHOR_CLAIM,
                 confidence=ConfidenceBand.HIGH,
                 verification_state=VerificationState.VERIFIED,
                 source_bundle_id="X", factory_signature="fakesig",
                 canonical_payload=b"xx")

    def test_factory_confidence_derived_not_caller(self):
        """Evidence with 0 verified records → LOW confidence regardless of what caller wants."""
        evidence = EvidenceBundle(records=(
            _make_verified_record("R1", vstate=VerificationState.UNVERIFIED),
        ), bundle_id="LOW")
        atom = self.factory.build(AtomType.CONCEPT, "test", evidence)
        self.assertEqual(atom.confidence, ConfidenceBand.LOW)

    def test_factory_high_confidence_requires_min_3(self):
        evidence = EvidenceBundle(records=(
            _make_verified_record("R1", vstate=VerificationState.VERIFIED),
            _make_verified_record("R2", vstate=VerificationState.VERIFIED),
        ), bundle_id="E2")
        # With >=3 verified, HIGH. With 2 verified + 1 unverified, still MEDIUM
        atom = self.factory.build(AtomType.CONCEPT, "test", evidence)
        self.assertNotEqual(atom.confidence, ConfidenceBand.HIGH)

    def test_atom_id_deterministic(self):
        a1 = self.factory.build(AtomType.CONCEPT, "test content", self.evidence)
        self.factory = AtomFactory("TEST_FACTORY2")
        a2 = self.factory.build(AtomType.CONCEPT, "test content", self.evidence)
        self.assertEqual(a1.atom_id, a2.atom_id)

    def test_atom_id_differs_by_content(self):
        a1 = self.factory.build(AtomType.CONCEPT, "content A", self.evidence)
        a2 = self.factory.build(AtomType.CONCEPT, "content B", self.evidence)
        self.assertNotEqual(a1.atom_id, a2.atom_id)

    def test_cannot_build_empty_content(self):
        with self.assertRaises(ValueError):
            self.factory.build(AtomType.CONCEPT, "   ", self.evidence)

    def test_cannot_build_without_evidence(self):
        with self.assertRaises(TypeError):
            self.factory.build(AtomType.CONCEPT, "test", "not_evidence")

    def test_cannot_duplicate_atom(self):
        self.factory.build(AtomType.CONCEPT, "dup test", self.evidence)
        with self.assertRaises(ValueError):
            self.factory.build(AtomType.CONCEPT, "dup test", self.evidence)

    def test_immutable_collections(self):
        atom = self.factory.build(AtomType.CONCEPT, "immutable test", self.evidence)
        self.assertIsInstance(atom.invalidation_conditions, tuple)
        self.assertIsInstance(atom.provenance_chain, tuple)
        self.assertIsInstance(atom.scope_notes, tuple)

    def test_falsified_overrides_verified(self):
        records = (
            _make_verified_record("R1", vstate=VerificationState.VERIFIED),
            _make_verified_record("R2", vstate=VerificationState.VERIFIED),
            _make_verified_record("R3", vstate=VerificationState.VERIFIED),
            _make_verified_record("R4", vstate=VerificationState.FALSIFIED),
        )
        evidence = EvidenceBundle(records=records, bundle_id="FAL")
        atom = self.factory.build(AtomType.CONCEPT, "falsified test", evidence)
        self.assertEqual(atom.verification_state, VerificationState.FALSIFIED)

    def test_factory_signature_present(self):
        atom = self.factory.build(AtomType.CONCEPT, "sig test", self.evidence)
        self.assertTrue(len(atom.factory_signature) == 64)

    def test_issued_count(self):
        self.factory.build(AtomType.CONCEPT, "a", self.evidence)
        self.factory.build(AtomType.MECHANISM, "b", self.evidence)
        self.assertEqual(self.factory.issued_count, 2)

    def test_domain_separation(self):
        self.assertIn(b"QCLAW:E42:ATOM:V1", DOMAIN_SEPARATOR)


if __name__ == "__main__":
    unittest.main(verbosity=2)
