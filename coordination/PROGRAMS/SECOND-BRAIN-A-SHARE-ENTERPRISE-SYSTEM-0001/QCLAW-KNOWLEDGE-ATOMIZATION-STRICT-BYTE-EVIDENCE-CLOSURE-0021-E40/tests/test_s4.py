"""E40 S4 — Atoms, Relations, Packet tests"""
import unittest, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"


class TestAtoms(unittest.TestCase):
    def test_atom_extraction(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        from qclaw_e40.atoms import extract_atoms
        src = b"hello world"
        ledger = ByteLedger(len(src))
        ledger.add(0, 5, Owner.ATOM_CANDIDATE, "hello")
        ledger.add(6, 11, Owner.ATOM_CANDIDATE, "world")
        atoms = extract_atoms(list(ledger.spans()), src)
        self.assertEqual(len(atoms), 2)

    def test_default_classification_is_claim(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        from qclaw_e40.atoms import extract_atoms
        src = b"factual statement"
        ledger = ByteLedger(len(src))
        ledger.add(0, len(src), Owner.ATOM_CANDIDATE)
        atoms = extract_atoms(list(ledger.spans()), src)
        for a in atoms:
            self.assertEqual(a.classification, "CLAIM")

    def test_never_auto_upgrade_to_fact(self):
        """No lexical pattern triggers automatic FACT classification."""
        from qclaw_e40.ledger import ByteLedger, Owner
        from qclaw_e40.atoms import extract_atoms
        src = b"it is absolutely true that the sky is blue"
        ledger = ByteLedger(len(src))
        ledger.add(0, len(src), Owner.ATOM_CANDIDATE)
        atoms = extract_atoms(list(ledger.spans()), src)
        for a in atoms:
            self.assertEqual(a.classification, "CLAIM")

    def test_skip_non_atom_owners(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        from qclaw_e40.atoms import extract_atoms
        src = b"atom structure unknown"
        ledger = ByteLedger(len(src))
        ledger.add(0, 4, Owner.ATOM_CANDIDATE, "atom")
        ledger.add(5, 13, Owner.STRUCTURE, "struct")
        ledger.add(14, len(src), Owner.UNKNOWN_ERROR, "err")
        atoms = extract_atoms(list(ledger.spans()), src)
        self.assertEqual(len(atoms), 1)

    def test_atom_id_deterministic(self):
        from qclaw_e40.ledger import OwnershipSpan, Owner
        from qclaw_e40.atoms import atom_id
        span = OwnershipSpan(0, 5, Owner.ATOM_CANDIDATE)
        id1 = atom_id(span, b"hello", "CLAIM")
        id2 = atom_id(span, b"hello", "CLAIM")
        self.assertEqual(id1, id2)

    def test_seven_fields_default_unspecified(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        from qclaw_e40.atoms import extract_atoms, AtomField
        src = b"test"
        ledger = ByteLedger(len(src))
        ledger.add(0, len(src), Owner.ATOM_CANDIDATE)
        atoms = extract_atoms(list(ledger.spans()), src)
        for a in atoms:
            for f in AtomField:
                self.assertEqual(a.fields[f.value], "UNSPECIFIED")


class TestRelations(unittest.TestCase):
    def test_six_types_accepted(self):
        from qclaw_e40.relations import Relation, RelationType
        for rt in RelationType:
            r = Relation(rt, "src", "tgt", "explicit_link_syntax")
            self.assertEqual(r.relation_type, rt)

    def test_illegal_type_rejected(self):
        from qclaw_e40.relations import Relation
        with self.assertRaises(ValueError):
            Relation("IS_SIMILAR_TO", "src", "tgt", "explicit_link_syntax")

    def test_valid_evidence_source(self):
        from qclaw_e40.relations import Relation, RelationType
        r = Relation(RelationType.SUPPORTS, "a", "b", "explicit_link_syntax")
        self.assertTrue(r.is_valid())

    def test_empty_evidence_invalid(self):
        from qclaw_e40.relations import Relation, RelationType
        r = Relation(RelationType.SUPPORTS, "a", "b", "")
        self.assertFalse(r.is_valid())

    def test_adjacency_always_returns_empty(self):
        from qclaw_e40.relations import adjacency_based_relations
        result = adjacency_based_relations([])
        self.assertEqual(result, [])


class TestPacket(unittest.TestCase):
    def test_packet_build(self):
        from qclaw_e40.packet import LearningPacket
        p = LearningPacket()
        p.atoms_count = 5
        p.relations_count = 3
        p.total_source_bytes = 100
        self.assertEqual(p.atoms_count, 5)

    def test_packet_hash_deterministic(self):
        from qclaw_e40.packet import LearningPacket
        p1 = LearningPacket(atoms_count=3, relations_count=1)
        p2 = LearningPacket(atoms_count=3, relations_count=1)
        h1 = p1.compute_hash()
        h2 = p2.compute_hash()
        self.assertEqual(h1, h2)

    def test_packet_hash_changes_with_content(self):
        from qclaw_e40.packet import LearningPacket
        p1 = LearningPacket(atoms_count=3)
        p2 = LearningPacket(atoms_count=4)
        self.assertNotEqual(p1.compute_hash(), p2.compute_hash())

    def test_packet_id_no_self_reference(self):
        from qclaw_e40.packet import LearningPacket
        p = LearningPacket(atoms_count=1)
        h = p.finalize()
        self.assertTrue(p.packet_id.startswith("pkt_"))
        # packet_id is NOT part of compute_hash (excluded in finalize)
        h2 = p.compute_hash()
        self.assertEqual(h, h2)

    def test_packet_to_json(self):
        from qclaw_e40.packet import LearningPacket
        p = LearningPacket(atoms_count=2)
        j = p.to_json()
        self.assertIn(b'"atoms_count"', j)
        self.assertIn(b"2", j)


if __name__ == "__main__":
    unittest.main(verbosity=2)
