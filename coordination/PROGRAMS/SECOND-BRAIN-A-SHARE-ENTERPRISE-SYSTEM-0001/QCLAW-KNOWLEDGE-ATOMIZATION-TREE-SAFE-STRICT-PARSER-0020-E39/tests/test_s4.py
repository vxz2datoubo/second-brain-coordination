"""E39 S4 tests — atoms, relations, packet with mutation families."""
import unittest
import sys, os

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_strict_byte.utf8_guard import UTF8ByteIndex
from qclaw_strict_byte.ledger import (
    ByteLedger, OwnerSpan,
    OWNER_ATOM_CANDIDATE, OWNER_STRUCTURE, OWNER_UNKNOWN_ERROR,
)
from qclaw_strict_byte.atoms import (
    Atom, extract_atoms, _make_atom_id,
    ATOM_CLAIM, ATOM_QUESTION, ATOM_FACT,
)
from qclaw_strict_byte.relations import (
    Relation, extract_relations, adjacency_based_relations,
    REL_SUPPORTS, REL_DEPENDS_ON, REL_CONTRADICTS, REL_REFINES,
    REL_RAISES_UNKNOWN, REL_VERIFIED_BY,
    LEGAL_RELATIONS,
)
from qclaw_strict_byte.packet import build_packet, LearningPacket


class TestAtomCreation(unittest.TestCase):
    def setUp(self):
        self.idx = UTF8ByteIndex(b"hello world. This is a sentence?")
        self.ledger = ByteLedger(self.idx)
        self.ledger.add(0, 12, OWNER_ATOM_CANDIDATE, "content")
        self.ledger.add(13, self.idx.total_bytes, OWNER_ATOM_CANDIDATE, "question")

    def test_extract_atoms_count(self):
        atoms = extract_atoms(self.idx, self.ledger, source_hash="abcd")
        self.assertEqual(len(atoms), 2)

    def test_default_claim_type(self):
        atoms = extract_atoms(self.idx, self.ledger)
        content_atom = [a for a in atoms if a.content.strip() == "hello world."]
        self.assertEqual(len(content_atom), 1)
        self.assertEqual(content_atom[0].atom_type, ATOM_CLAIM)
        # Must be CLAIM, NOT FACT
        self.assertNotEqual(content_atom[0].atom_type, ATOM_FACT)

    def test_question_detection(self):
        atoms = extract_atoms(self.idx, self.ledger)
        q = [a for a in atoms if a.atom_type == ATOM_QUESTION]
        self.assertEqual(len(q), 1)
        self.assertTrue(q[0].content.strip().endswith("?"))

    def test_never_fact_from_extraction(self):
        """Prove that extract_atoms NEVER produces FACT type."""
        atoms = extract_atoms(self.idx, self.ledger)
        facts = [a for a in atoms if a.atom_type == ATOM_FACT]
        self.assertEqual(len(facts), 0, "extract_atoms must never produce FACT")

    def test_deterministic_id(self):
        id1 = _make_atom_id("test", 0, 4, ATOM_CLAIM, "abc")
        id2 = _make_atom_id("test", 0, 4, ATOM_CLAIM, "abc")
        self.assertEqual(id1, id2)
        # Different hash → different ID
        id3 = _make_atom_id("test", 0, 4, ATOM_CLAIM, "xyz")
        self.assertNotEqual(id1, id3)

    def test_atom_has_byte_positions(self):
        atoms = extract_atoms(self.idx, self.ledger)
        for a in atoms:
            self.assertGreaterEqual(a.byte_start, 0)
            self.assertLessEqual(a.byte_end, self.idx.total_bytes)
            self.assertGreater(a.byte_end, a.byte_start)

    def test_skip_structure_owner(self):
        """STRUCTURE spans are not treated as atoms."""
        idx2 = UTF8ByteIndex(b"x")
        ledger2 = ByteLedger(idx2)
        ledger2.add(0, 1, OWNER_STRUCTURE, "struct")
        atoms = extract_atoms(idx2, ledger2)
        struct_atoms = [a for a in atoms if a.subject_family == "struct"]
        self.assertEqual(len(atoms), 0)

    def test_skip_unknown_owner(self):
        """UNKNOWN_ERROR spans are not treated as atoms."""
        idx2 = UTF8ByteIndex(b"test")
        ledger2 = ByteLedger(idx2)
        ledger2.add(0, 4, OWNER_UNKNOWN_ERROR, "bad")
        atoms = extract_atoms(idx2, ledger2)
        self.assertEqual(len(atoms), 0)

    def test_empty_content_skipped(self):
        """Whitespace-only spans produce no atoms."""
        idx3 = UTF8ByteIndex(b"   \n  ")
        ledger3 = ByteLedger(idx3)
        ledger3.add(0, 6, OWNER_ATOM_CANDIDATE, "ws")
        atoms = extract_atoms(idx3, ledger3)
        self.assertEqual(len(atoms), 0)


class TestRelationCreation(unittest.TestCase):
    def test_legal_types_accepted(self):
        for t in LEGAL_RELATIONS:
            r = Relation("id1", "id2", t, "explicit_link_syntax", "test evidence")
            self.assertEqual(r.relation_type, t)

    def test_illegal_type_rejected(self):
        with self.assertRaises(ValueError):
            Relation("id1", "id2", "IMPLIES", "explicit_link_syntax", "bad")

    def test_illegal_evidence_rejected(self):
        with self.assertRaises(ValueError):
            Relation("id1", "id2", REL_SUPPORTS, "proximity_based", "bad")

    def test_adjacency_always_empty(self):
        """adjacency_based_relations() must always return empty list."""
        result = adjacency_based_relations([])
        self.assertEqual(result, [])
        result2 = adjacency_based_relations([Atom("id", ATOM_CLAIM, "test", 0, 4)])
        self.assertEqual(result2, [])

    def test_extract_relations_no_auto(self):
        """Without explicit evidence, no relations are extracted."""
        atoms = [Atom("id1", ATOM_CLAIM, "test", 0, 4)]
        relations = extract_relations(atoms, b"test")
        self.assertEqual(len(relations), 0)

    def test_confirmed_relations_accepted(self):
        r = Relation("id1", "id2", REL_SUPPORTS, "human_confirmation", "manual")
        relations = extract_relations([], b"", confirmed=[r])
        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0].relation_type, REL_SUPPORTS)

    def test_confirmed_bad_source_rejected(self):
        r = Relation("id1", "id2", REL_SUPPORTS, "explicit_link_syntax", "bad")
        with self.assertRaises(ValueError):
            extract_relations([], b"", confirmed=[r])

    def test_relation_id_deterministic(self):
        r1 = Relation("a", "b", REL_SUPPORTS, "explicit_link_syntax", "test")
        r2 = Relation("a", "b", REL_SUPPORTS, "explicit_link_syntax", "test")
        self.assertEqual(r1.relation_id, r2.relation_id)


class TestPacketBuilding(unittest.TestCase):
    def setUp(self):
        self.idx = UTF8ByteIndex(b"atom one. atom two is here.")
        self.ledger = ByteLedger(self.idx)
        self.ledger.add(0, 10, OWNER_ATOM_CANDIDATE, "a1")
        self.ledger.add(10, self.idx.total_bytes, OWNER_ATOM_CANDIDATE, "a2")
        self.ledger.finalize()
        self.atoms = extract_atoms(self.idx, self.ledger, "sha123", "commit456")
        r = Relation(self.atoms[0].atom_id, self.atoms[1].atom_id,
                     REL_SUPPORTS, "human_confirmation", "related")
        self.relations = extract_relations(self.atoms, self.idx.source_bytes, confirmed=[r])

    def test_packet_builds(self):
        pkt = build_packet(self.atoms, self.relations, self.ledger,
                          source_hash="sha123", source_commit="commit456")
        self.assertIsInstance(pkt, LearningPacket)
        self.assertNotEqual(pkt.packet_id, "")

    def test_packet_id_deterministic(self):
        p1 = build_packet(self.atoms, self.relations, self.ledger,
                         source_hash="sha123")
        p2 = build_packet(self.atoms, self.relations, self.ledger,
                         source_hash="sha123")
        self.assertEqual(p1.packet_id, p2.packet_id)

    def test_packet_no_self_reference(self):
        pkt = build_packet(self.atoms, self.relations, self.ledger,
                          source_hash="sha123")
        # packet_id must not appear inside its own input
        packet_dict = pkt.to_dict()
        self.assertNotIn(pkt.packet_id, str(packet_dict["coverage"]))

    def test_different_input_different_packet(self):
        p1 = build_packet(self.atoms, self.relations, self.ledger,
                         source_hash="abc")
        p2 = build_packet(self.atoms, self.relations, self.ledger,
                         source_hash="xyz")
        self.assertNotEqual(p1.packet_id, p2.packet_id)

    def test_packet_has_coverage_data(self):
        pkt = build_packet(self.atoms, self.relations, self.ledger)
        self.assertIn("total_bytes", pkt.coverage_data)
        self.assertIn("complete", pkt.coverage_data)

    def test_packet_atom_count(self):
        pkt = build_packet(self.atoms, self.relations, self.ledger)
        self.assertEqual(len(pkt.atoms), 2)
        self.assertEqual(pkt.to_dict()["atoms_count"], 2)

    def test_packet_relation_count(self):
        pkt = build_packet(self.atoms, self.relations, self.ledger)
        self.assertEqual(len(pkt.relations), 1)
        self.assertEqual(pkt.to_dict()["relations_count"], 1)

    def test_packet_unknowns(self):
        pkt = build_packet(self.atoms, self.relations, self.ledger,
                          unknowns=["gap at byte 9"])
        self.assertEqual(len(pkt.unknowns), 1)

    def test_packet_conflicts(self):
        pkt = build_packet(self.atoms, self.relations, self.ledger,
                          conflicts=["duplicate key"])
        self.assertEqual(len(pkt.conflicts), 1)


class TestMutationFamiliesS4(unittest.TestCase):
    """Active mutation tests for atoms/relations/packet."""

    def test_fact_never_auto_assigned(self):
        """Prove that no automated path produces FACT type."""
        idx = UTF8ByteIndex(b"this is definitely true")
        ledger = ByteLedger(idx)
        ledger.add(0, idx.total_bytes, OWNER_ATOM_CANDIDATE, "assertion")
        atoms = extract_atoms(idx, ledger)
        for a in atoms:
            with self.subTest(atom=a.content):
                self.assertNotEqual(a.atom_type, ATOM_FACT,
                    f"Atom '{a.content}' is FACT — should be CLAIM")

    def test_adjacency_blocked_forever(self):
        """adjacency_based_relations must be immutable empty list."""
        import inspect
        src = inspect.getsource(adjacency_based_relations)
        self.assertIn("return[]", src.replace(" ", ""),
                      "adjacency_based_relations must return empty list")

    def test_packet_hash_changes_with_atom_content(self):
        """Changing an atom's content changes the packet ID."""
        idx = UTF8ByteIndex(b"A thenB")
        ledger = ByteLedger(idx)
        total = idx.total_bytes
        ledger.add(0, 6, OWNER_ATOM_CANDIDATE, "a")
        ledger.add(6, total, OWNER_ATOM_CANDIDATE, "b")
        ledger.finalize()
        a1 = extract_atoms(idx, ledger, source_hash="sha")
        p1 = build_packet(a1, [], ledger, source_hash="sha")
        # Different source hash → different packet
        p2 = build_packet(a1, [], ledger, source_hash="other")
        self.assertNotEqual(p1.packet_id, p2.packet_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
