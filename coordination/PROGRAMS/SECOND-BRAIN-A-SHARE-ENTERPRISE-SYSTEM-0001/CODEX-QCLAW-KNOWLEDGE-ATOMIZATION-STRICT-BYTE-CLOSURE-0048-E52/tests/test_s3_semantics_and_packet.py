"""S3 semantic schema, executable relation, and complete packet tests."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from e52_strict_byte.ledger import Owner, OwnershipSpan
from e52_strict_byte.semantics import (
    Atom,
    AtomClassification,
    CanonicalPacket,
    FieldProvenance,
    Relation,
    RelationEvidence,
    RelationEvidenceType,
    SemanticFieldValue,
    extract_claim,
    extract_explicit_link_relation,
    validate_relation,
)


SOURCE = b"alpha [[PLACEHOLDER_A->PLACEHOLDER_B]] beta"
DIGEST = "synthetic-source-digest"


class TestAtomSchema(unittest.TestCase):
    def test_auto_extraction_is_claim_with_seven_explained_unknowns(self):
        atom = extract_claim(OwnershipSpan(0, 5, Owner.ATOM_CANDIDATE, "word"), SOURCE, DIGEST)
        self.assertEqual(atom.classification, AtomClassification.CLAIM)
        self.assertTrue(atom.auto_extracted)
        self.assertEqual(len(atom.fields), 7)
        self.assertTrue(all(field.provenance is FieldProvenance.UNKNOWN and field.unknown_reason for field in atom.fields.values()))

    def test_fact_cannot_be_auto_upgraded_without_verified_evidence(self):
        atom = extract_claim(OwnershipSpan(0, 5, Owner.ATOM_CANDIDATE, "word"), SOURCE, DIGEST)
        with self.assertRaises(ValueError):
            Atom(atom.atom_id, atom.text, atom.byte_span, atom.source_digest, AtomClassification.FACT, atom.fields, (), True)

    def test_missing_or_bare_fields_are_rejected(self):
        atom = extract_claim(OwnershipSpan(0, 5, Owner.ATOM_CANDIDATE, "word"), SOURCE, DIGEST)
        fields = dict(atom.fields)
        fields.pop("condition")
        with self.assertRaises(ValueError):
            Atom(atom.atom_id, atom.text, atom.byte_span, atom.source_digest, atom.classification, fields, atom.evidence_refs, True)


class TestRelationsAndPackets(unittest.TestCase):
    def _atoms(self):
        left = extract_claim(OwnershipSpan(0, 5, Owner.ATOM_CANDIDATE, "left"), SOURCE, DIGEST)
        right = extract_claim(OwnershipSpan(42, 46, Owner.ATOM_CANDIDATE, "right"), SOURCE, DIGEST)
        return left, right

    def test_explicit_link_requires_existing_endpoints_and_real_source_span(self):
        left, right = self._atoms()
        source = b"[[" + left.atom_id.encode("ascii") + b"->" + right.atom_id.encode("ascii") + b"]]"
        relation = extract_explicit_link_relation(source, DIGEST, (0, len(source)), {left.atom_id: left, right.atom_id: right})
        validate_relation(relation, {left.atom_id: left, right.atom_id: right}, DIGEST)
        with self.assertRaises(ValueError):
            validate_relation(relation, {left.atom_id: left}, DIGEST)

    def test_relation_evidence_digest_mismatch_and_arbitrary_strings_fail(self):
        left, right = self._atoms()
        relation = Relation(left.atom_id, right.atom_id, "EXPLICIT_LINK", RelationEvidence(RelationEvidenceType.EXPLICIT_LINK, "wrong", (0, 1)))
        with self.assertRaises(ValueError):
            validate_relation(relation, {left.atom_id: left, right.atom_id: right}, DIGEST)
        with self.assertRaises(ValueError):
            RelationEvidence("ARBITRARY", DIGEST, (0, 1))

    def test_packet_contains_full_semantics_and_identity_changes_with_content(self):
        left, right = self._atoms()
        packet = CanonicalPacket(
            source_identity={"digest": DIGEST, "format": "synthetic"},
            atoms=(left, right),
            relations=(),
            unknowns=("unit-not-specified",),
            conflicts=("none-verified",),
            redaction_lineage={"applied": False},
            coverage_manifest={"total_bytes": len(SOURCE), "finalized": True},
            config={"schema_version": "1"},
            validator_results={"schema": True},
        )
        payload = packet.payload()
        self.assertEqual(len(payload["atoms"]), 2)
        self.assertIn("unknowns", payload)
        self.assertNotIn("packet_id", payload)
        changed = CanonicalPacket(
            source_identity=packet.source_identity,
            atoms=(right, left),
            relations=packet.relations,
            unknowns=("different-unknown",),
            conflicts=packet.conflicts,
            redaction_lineage=packet.redaction_lineage,
            coverage_manifest=packet.coverage_manifest,
            config=packet.config,
            validator_results=packet.validator_results,
        )
        self.assertNotEqual(packet.packet_id(), changed.packet_id())


if __name__ == "__main__":
    unittest.main(verbosity=2)
