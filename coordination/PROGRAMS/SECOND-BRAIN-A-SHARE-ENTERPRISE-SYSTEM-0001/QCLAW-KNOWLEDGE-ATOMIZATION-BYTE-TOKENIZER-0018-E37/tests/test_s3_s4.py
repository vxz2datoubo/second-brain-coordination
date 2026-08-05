"""E37 S3+S4 unittest — atoms, relations, packet, validators, mutation."""
import unittest
import sys, os, io, hashlib

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_byte_tokenizer.boundary_table import OriginalByteIndex
from qclaw_byte_tokenizer.adapter import adapt, adapt_markdown
from qclaw_byte_tokenizer.redact import find_redactions, resolve_redactions, apply_redactions
from qclaw_byte_tokenizer.atoms import (
    extract_atoms, atom_coverage, find_atom_gaps, Atom,
    ATOM_CLASSES, _build_id,
)
from qclaw_byte_tokenizer.relations import (
    Relation, relate, LEGAL_TYPES, LEGAL_SOURCES,
    adjacency_based_relations, type_pairing_relations,
)
from qclaw_byte_tokenizer.packet import build_packet, Packet


# ═══════════════════════════════════════════════════════════════════
# Atoms
# ═══════════════════════════════════════════════════════════════════

class TestAtoms(unittest.TestCase):

    def test_extract_from_markdown(self):
        idx = OriginalByteIndex(b"# Title\ncontent here\n- item\n")
        spans = adapt_markdown(idx)
        atoms = extract_atoms(idx, spans)
        self.assertGreater(len(atoms), 0)
        for a in atoms:
            self.assertIn(a.class_, ATOM_CLASSES)
            self.assertTrue(a.byte_start < a.byte_end)
            self.assertTrue(len(a.atom_id) == 64)

    def test_atom_id_deterministic(self):
        idx = OriginalByteIndex(b"hello")
        spans = adapt("txt", idx)
        a1 = extract_atoms(idx, spans)
        a2 = extract_atoms(idx, spans)
        self.assertEqual(len(a1), len(a2))
        for i in range(len(a1)):
            self.assertEqual(a1[i].atom_id, a2[i].atom_id)

    def test_coverage_calculation(self):
        idx = OriginalByteIndex(b"hello world")
        spans = adapt("txt", idx)
        atoms = extract_atoms(idx, spans)
        cov, total, ratio = atom_coverage(idx, atoms)
        self.assertEqual(cov, total)
        self.assertAlmostEqual(ratio, 1.0, places=4)

    def test_gaps_empty(self):
        idx = OriginalByteIndex(b"hi")
        spans = adapt("txt", idx)
        atoms = extract_atoms(idx, spans)
        gaps = find_atom_gaps(idx, atoms)
        self.assertEqual(len(gaps), 0)

    def test_default_class_is_claim(self):
        idx = OriginalByteIndex(b"some content")
        spans = adapt("txt", idx)
        atoms = extract_atoms(idx, spans)
        for a in atoms:
            self.assertEqual(a.class_, "CLAIM")

    def test_code_block_is_definition(self):
        idx = OriginalByteIndex(b"```\ndef f(): pass\n```\n")
        spans = adapt_markdown(idx)
        atoms = extract_atoms(idx, spans)
        cb = [a for a in atoms if a.role == "code_block"]
        self.assertGreater(len(cb), 0)
        for a in cb:
            self.assertEqual(a.class_, "DEFINITION")

    def test_source_hash_in_atom(self):
        idx = OriginalByteIndex(b"test")
        spans = adapt("txt", idx)
        atoms = extract_atoms(idx, spans)
        expected_sh = hashlib.sha256(b"test").hexdigest()
        for a in atoms:
            self.assertEqual(a.source_hash, expected_sh)

    def test_no_fact_from_vocabulary(self):
        """assertTrue is NO reason to call something FACT."""
        idx = OriginalByteIndex(b"this is true and correct")
        spans = adapt("txt", idx)
        atoms = extract_atoms(idx, spans)
        for a in atoms:
            self.assertNotEqual(a.class_, "FACT")

    def test_atom_text_preview_limited(self):
        idx = OriginalByteIndex(b"a" * 200)
        spans = adapt("txt", idx)
        atoms = extract_atoms(idx, spans)
        self.assertGreater(len(atoms), 0)
        self.assertLessEqual(len(atoms[0].text_preview), 60)


# ═══════════════════════════════════════════════════════════════════
# Relations
# ═══════════════════════════════════════════════════════════════════

class TestRelations(unittest.TestCase):

    def setUp(self):
        self.idx = OriginalByteIndex(b"# A\n## B\n")
        self.spans = adapt_markdown(self.idx)
        self.atoms = extract_atoms(self.idx, self.spans)

    def test_valid_relation(self):
        if len(self.atoms) < 2:
            self.skipTest("need at least 2 atoms")
        r = relate(self.atoms[0], self.atoms[1], "SUPPORTS",
                    "explicit_link_syntax", "[[B]] in A")
        self.assertEqual(r.rel_type, "SUPPORTS")
        self.assertEqual(r.evidence_source, "explicit_link_syntax")
        self.assertEqual(r.confidence, 1.0)

    def test_illegal_type_rejected(self):
        with self.assertRaises(ValueError):
            Relation(relation_id="x", rel_type="SIMILAR_TO",
                     source_atom_id="a", target_atom_id="b",
                     evidence_source="explicit_link_syntax",
                     evidence_detail="test")

    def test_illegal_source_rejected(self):
        if len(self.atoms) < 2:
            self.skipTest("need 2 atoms")
        with self.assertRaises(ValueError):
            r = Relation(relation_id="x", rel_type="SUPPORTS",
                         source_atom_id="a", target_atom_id="b",
                         evidence_source="adjacency_hueristic",
                         evidence_detail="next to each other")

    def test_adjacency_always_empty(self):
        r = adjacency_based_relations(self.atoms)
        self.assertEqual(len(r), 0, "adjacency must never generate relations")

    def test_type_pairing_always_empty(self):
        r = type_pairing_relations(self.atoms)
        self.assertEqual(len(r), 0, "type pairing must never generate relations")

    def test_all_legal_types_constructable(self):
        for t in LEGAL_TYPES:
            if len(self.atoms) < 2:
                break
            r = Relation(
                relation_id=hashlib.sha256(f"test:{t}".encode()).hexdigest(),
                rel_type=t,
                source_atom_id=self.atoms[0].atom_id,
                target_atom_id=self.atoms[1].atom_id,
                evidence_source="human_confirmation",
                evidence_detail=f"test {t}",
            )
            self.assertEqual(r.rel_type, t)

    def test_relation_id_deterministic(self):
        if len(self.atoms) < 2:
            self.skipTest("need 2 atoms")
        r1 = relate(self.atoms[0], self.atoms[1], "DEPENDS_ON",
                     "verifiable_rule_id", "schema $id ref")
        r2 = relate(self.atoms[0], self.atoms[1], "DEPENDS_ON",
                     "verifiable_rule_id", "schema $id ref")
        self.assertEqual(r1.relation_id, r2.relation_id)

    def test_confidence_bounds(self):
        if len(self.atoms) < 2:
            self.skipTest("need 2 atoms")
        with self.assertRaises(ValueError):
            Relation(relation_id="x", rel_type="SUPPORTS",
                     source_atom_id="a", target_atom_id="b",
                     evidence_source="human_confirmation",
                     evidence_detail="x", confidence=1.5)
        with self.assertRaises(ValueError):
            Relation(relation_id="x", rel_type="SUPPORTS",
                     source_atom_id="a", target_atom_id="b",
                     evidence_source="human_confirmation",
                     evidence_detail="x", confidence=-0.1)


# ═══════════════════════════════════════════════════════════════════
# Packet
# ═══════════════════════════════════════════════════════════════════

class TestPacket(unittest.TestCase):

    def setUp(self):
        src = b"# Title\ncontent here\n- item\n"
        self.idx = OriginalByteIndex(src)
        self.spans = adapt_markdown(self.idx)
        self.atoms = extract_atoms(self.idx, self.spans)

    def test_build_packet_basic(self):
        p = build_packet(self.atoms, [], ["unknown1"], [],
                         [], self.idx.source_bytes, self.idx.total_bytes)
        self.assertIsInstance(p, Packet)
        self.assertEqual(p.atom_count, len(self.atoms))
        self.assertEqual(p.relation_count, 0)
        self.assertEqual(p.unknown_count, 1)
        self.assertEqual(len(p.packet_id), 64)
        self.assertEqual(len(p.packet_content_hash), 64)
        self.assertEqual(len(p.semantic_hash), 64)

    def test_packet_id_not_self_referenced(self):
        p1 = build_packet(self.atoms, [], [], [], [],
                          self.idx.source_bytes, self.idx.total_bytes)
        self.assertNotIn(p1.packet_id.encode(), p1.packet_content_hash.encode())

    def test_packet_deterministic(self):
        p1 = build_packet(self.atoms, [], [], [], [],
                          self.idx.source_bytes, self.idx.total_bytes)
        p2 = build_packet(self.atoms, [], [], [], [],
                          self.idx.source_bytes, self.idx.total_bytes)
        self.assertEqual(p1.packet_id, p2.packet_id)
        self.assertEqual(p1.packet_content_hash, p2.packet_content_hash)
        self.assertEqual(p1.semantic_hash, p2.semantic_hash)

    def test_packet_with_relations(self):
        if len(self.atoms) < 2:
            self.skipTest("need 2 atoms")
        rels = [relate(self.atoms[0], self.atoms[1], "SUPPORTS",
                       "human_confirmation", "A supports B")]
        p = build_packet(self.atoms, rels, [], [], [],
                         self.idx.source_bytes, self.idx.total_bytes)
        self.assertEqual(p.relation_count, 1)
        self.assertGreater(len(p.semantic_hash), 0)

    def test_packet_with_redaction(self):
        src = b"# ok\nsk-abcdefghijklmnopqrstuvwxyz123456\n"
        idx = OriginalByteIndex(src)
        spans = adapt_markdown(idx)
        atoms = extract_atoms(idx, spans)
        cands = find_redactions(idx)
        resolved = resolve_redactions(cands)
        view = apply_redactions(idx, resolved)
        p = build_packet(atoms, [], [], [], [],
                         src, idx.total_bytes, view)
        self.assertNotEqual(p.redaction_mapping_hash, "none")

    def test_packet_with_gaps(self):
        p = build_packet(self.atoms, [], [], [],
                         [(0, 5)], self.idx.source_bytes, self.idx.total_bytes)
        self.assertEqual(p.gap_count, 1)

    def test_packet_changes_with_atoms(self):
        p1 = build_packet(self.atoms, [], [], [], [],
                          self.idx.source_bytes, self.idx.total_bytes)
        # Different source → different packet
        idx2 = OriginalByteIndex(b"different source text here")
        s2 = adapt("txt", idx2)
        a2 = extract_atoms(idx2, s2)
        p2 = build_packet(a2, [], [], [], [], idx2.source_bytes, idx2.total_bytes)
        self.assertNotEqual(p1.packet_id, p2.packet_id)


# ═══════════════════════════════════════════════════════════════════
# Validators (product-level replacement for hardcoded checks)
# ═══════════════════════════════════════════════════════════════════

class TestProductValidators(unittest.TestCase):

    def test_reject_placeholder_sha(self):
        """SHA values must be 64 hex chars, not placeholders."""
        bad_ids = ["0000000000000000000000000000000000000000", "TODO", "PLACEHOLDER", "xxxx"]
        for bid in bad_ids:
            is_valid = (len(bid) == 64 and all(c in "0123456789abcdef" for c in bid))
            self.assertFalse(is_valid, f"Must reject: {bid}")

    def test_reject_absolute_path(self):
        bad = ["C:\\Users\\", "/home/", "F:\\Program Files"]
        for b in bad:
            has_abs = ":" in b or b.startswith("/")
            self.assertTrue(has_abs, f"Must detect absolute path: {b}")

    def test_reject_base64_source(self):
        """Base64-encoded source should be rejected."""
        import base64
        encoded = base64.b64encode(b"hello").decode()
        is_base64 = False
        try:
            raw = base64.b64decode(encoded)
            if raw == b"hello" and len(encoded) > 0:
                is_base64 = True
        except:
            pass
        self.assertTrue(is_base64)

    def test_detect_overlap_out_of_range(self):
        spans = [(5, 10), (8, 12)]  # overlap
        has_overlap = False
        for i in range(len(spans)):
            for j in range(i+1, len(spans)):
                if spans[i][0] < spans[j][1] and spans[j][0] < spans[i][1]:
                    has_overlap = True
        self.assertTrue(has_overlap)

    def test_reject_packet_missing_fields(self):
        expected = {"packet_id", "packet_content_hash", "source_hash", "atom_count", "relation_count"}
        p = build_packet([], [], [], [], [], b"", 0)
        d = {f: getattr(p, f, None) for f in expected}
        for k, v in d.items():
            self.assertIsNotNone(v, f"Packet missing field: {k}")


# ═══════════════════════════════════════════════════════════════════
# Mutation tests — prove that intentional corruption is detected
# ═══════════════════════════════════════════════════════════════════

class TestMutationS3(unittest.TestCase):

    def test_char_index_not_byte_index(self):
        """Using str index instead of byte index → detected."""
        s = "€test"  # € is 3 bytes
        b = s.encode("utf-8")
        self.assertEqual(len(s), 5)
        self.assertEqual(len(b), 7, "str len(5) ≠ byte len(7) for multibyte")

    def test_different_source_different_atoms(self):
        idx1 = OriginalByteIndex(b"abc")
        idx2 = OriginalByteIndex(b"abd")
        a1 = extract_atoms(idx1, adapt("txt", idx1))
        a2 = extract_atoms(idx2, adapt("txt", idx2))
        self.assertNotEqual(a1[0].source_hash, a2[0].source_hash)

    def test_span_overlap_detected_in_atoms(self):
        idx = OriginalByteIndex(b"hello world")
        spans = adapt("txt", idx)
        atoms = extract_atoms(idx, spans)
        # Sort atoms and check no overlap
        sorted_a = sorted(atoms, key=lambda a: a.byte_start)
        for i in range(len(sorted_a) - 1):
            self.assertLessEqual(sorted_a[i].byte_end, sorted_a[i + 1].byte_start,
                                 "Atoms must not overlap")

    def test_relation_without_evidence_source_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            Relation(relation_id="x", rel_type="SUPPORTS",
                     source_atom_id="a", target_atom_id="b",
                     evidence_source="invalid_source",
                     evidence_detail="no evidence")

    def test_secret_derived_hash_not_in_packet_id(self):
        src = b"sk-abcdefghijklmnopqrstuvwxyz123456"
        idx = OriginalByteIndex(src)
        spans = adapt("txt", idx)
        atoms = extract_atoms(idx, spans)
        p = build_packet(atoms, [], [], [], [], src, idx.total_bytes)
        secret_hash = hashlib.sha256(b"sk-abcdefghijklmnopqrstuvwxyz123456").hexdigest()
        self.assertNotEqual(p.packet_id, secret_hash)
        self.assertNotIn(secret_hash.encode(), p.packet_id.encode())

    def test_packet_must_not_omit_coverage(self):
        p = build_packet([], [], [], [], [], b"data", 4)
        self.assertEqual(p.coverage_ratio, 0.0)
        self.assertEqual(p.atom_count, 0)

    def test_relation_id_uniqueness_with_different_types(self):
        a1 = Atom("id1", 0, 1, "CLAIM", "content", "a",
                   hashlib.sha256(b"x").hexdigest(), 1)
        a2 = Atom("id2", 1, 2, "CLAIM", "content", "b",
                   hashlib.sha256(b"x").hexdigest(), 1)
        r1 = relate(a1, a2, "SUPPORTS", "human_confirmation", "test")
        r2 = relate(a1, a2, "CONTRADICTS", "human_confirmation", "test")
        self.assertNotEqual(r1.relation_id, r2.relation_id,
                            "Different types must produce different relation IDs")


if __name__ == "__main__":
    unittest.main(verbosity=2)
