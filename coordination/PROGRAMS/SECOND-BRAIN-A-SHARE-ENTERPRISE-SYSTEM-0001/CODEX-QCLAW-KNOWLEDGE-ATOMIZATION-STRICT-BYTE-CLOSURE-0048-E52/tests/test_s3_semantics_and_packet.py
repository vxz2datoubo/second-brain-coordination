"""S3 schema, typed relation, and finalized canonical-packet tests."""
from __future__ import annotations

import hashlib
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
    RelationType,
    extract_claim,
    extract_explicit_link_relation,
    unknown_field_values,
    validate_relation,
)


SOURCE = b"alpha beta"
DIGEST = hashlib.sha256(SOURCE).hexdigest()


def _packet(atoms):
    return CanonicalPacket(
        source_identity={"sha256": DIGEST, "byte_length": len(SOURCE), "format": "synthetic"},
        atoms=atoms,
        relations=(),
        unknowns=("unit-not-specified",),
        conflicts=("none-verified",),
        redaction_lineage={"applied": False, "policy": "none"},
        coverage_manifest={"total_bytes": len(SOURCE), "finalized": True},
        config={"schema_version": "1"},
        validator_results={"schema": True},
    )


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
    def _relation_fixture(self):
        source = b"left [[left-id->right-id]] right"
        digest = hashlib.sha256(source).hexdigest()
        fields = unknown_field_values()
        left = Atom("left-id", "left", (0, 4), digest, AtomClassification.CLAIM, fields, ("byte-span:0:4",), True)
        right = Atom("right-id", "right", (27, 32), digest, AtomClassification.CLAIM, fields, ("byte-span:27:32",), True)
        return source, {left.atom_id: left, right.atom_id: right}

    def test_explicit_link_requires_existing_endpoints_and_real_source_span(self):
        source, atoms = self._relation_fixture()
        relation = extract_explicit_link_relation(source, (5, 26), atoms)
        validate_relation(relation, atoms, source)
        with self.assertRaises(ValueError):
            extract_explicit_link_relation(source, (5, 26), {next(iter(atoms)): next(iter(atoms.values()))})

    def test_relation_evidence_digest_mismatch_and_arbitrary_types_fail(self):
        source, atoms = self._relation_fixture()
        relation = extract_explicit_link_relation(source, (5, 26), atoms)
        with self.assertRaises(ValueError):
            validate_relation(relation, atoms, source.replace(b"->", b"=>"))
        with self.assertRaises(ValueError):
            Relation("left-id", "right-id", "ARBITRARY", relation.evidence)
        with self.assertRaises(ValueError):
            RelationEvidence(RelationEvidenceType.EXPLICIT_LINK, "0" * 64, (0, 1), "not-a-hash")

    def test_packet_contains_full_semantics_and_identity_changes_with_content(self):
        left = extract_claim(OwnershipSpan(0, 5, Owner.ATOM_CANDIDATE, "left"), SOURCE)
        right = extract_claim(OwnershipSpan(6, 10, Owner.ATOM_CANDIDATE, "right"), SOURCE)
        packet = _packet((left, right))
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
