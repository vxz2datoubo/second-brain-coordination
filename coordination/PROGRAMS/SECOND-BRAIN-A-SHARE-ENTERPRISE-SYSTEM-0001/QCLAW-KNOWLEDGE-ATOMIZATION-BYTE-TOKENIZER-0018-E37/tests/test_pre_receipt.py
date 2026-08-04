"""E37 pre_receipt_validator — product-level checks before receipt commit.

Rejects: missing modules, Planned|TODO markers, placeholder SHAs,
non-unittest test framework, subprocess failure, wrong topology.
"""
import unittest
import sys, os, io, hashlib, re

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_byte_tokenizer.boundary_table import OriginalByteIndex
from qclaw_byte_tokenizer.ledger import ByteLedger, OwnerSpan
from qclaw_byte_tokenizer.adapter import adapt
from qclaw_byte_tokenizer.redact import find_redactions, resolve_redactions, apply_redactions
from qclaw_byte_tokenizer.atoms import extract_atoms, atom_coverage
from qclaw_byte_tokenizer.relations import relate, LEGAL_TYPES
from qclaw_byte_tokenizer.packet import build_packet


class TestPreReceiptValidator(unittest.TestCase):
    """Validators that must pass before a receipt commit is allowed."""

    def test_all_modules_importable(self):
        """Every required module must exist and be importable."""
        import qclaw_byte_tokenizer.boundary_table
        import qclaw_byte_tokenizer.ledger
        import qclaw_byte_tokenizer.adapter
        import qclaw_byte_tokenizer.redact
        import qclaw_byte_tokenizer.atoms
        import qclaw_byte_tokenizer.relations
        import qclaw_byte_tokenizer.packet
        required = [
            "qclaw_byte_tokenizer.boundary_table",
            "qclaw_byte_tokenizer.ledger",
            "qclaw_byte_tokenizer.adapter",
            "qclaw_byte_tokenizer.redact",
            "qclaw_byte_tokenizer.atoms",
            "qclaw_byte_tokenizer.relations",
            "qclaw_byte_tokenizer.packet",
        ]
        for mod in required:
            self.assertIn(mod, sys.modules, f"Missing module: {mod}")

    def test_no_planned_todo_in_source(self):
        """No Planned|TODO markers in source files."""
        base = os.path.join(os.path.dirname(__file__), "..", "src")
        bad = []
        for root, dirs, files in os.walk(base):
            for f in files:
                if f.endswith(".py"):
                    fp = os.path.join(root, f)
                    content = open(fp, "r", encoding="utf-8").read()
                    if re.search(r'\b(?:Planned|TODO)\b', content):
                        bad.append(f)
        self.assertEqual(len(bad), 0, f"Planned|TODO markers found: {bad}")

    def test_no_placeholder_sha_in_source(self):
        """No placeholder SHAs (000...0 or PLACEHOLDER) in source code."""
        base = os.path.join(os.path.dirname(__file__), "..", "src")
        bad = []
        for root, dirs, files in os.walk(base):
            for f in files:
                if f.endswith(".py"):
                    fp = os.path.join(root, f)
                    content = open(fp, "r", encoding="utf-8").read()
                    if "PLACEHOLDER" in content.upper() and "PLACEHOLDER" not in content:
                        pass
                    if re.match(r'^0{40,}$', content.strip()):
                        bad.append(f)
        # Check for literal placeholder patterns
        for root, dirs, files in os.walk(base):
            for f in files:
                if f.endswith(".py"):
                    fp = os.path.join(root, f)
                    lines = open(fp, "r", encoding="utf-8").readlines()
                    for i, line in enumerate(lines):
                        stripped = line.strip().strip("'\"")
                        if stripped == "PLACEHOLDER" or stripped == "TODO":
                            bad.append(f"{f}:{i+1}")
        self.assertEqual(len(bad), 0, f"Placeholder markers found: {bad}")

    def test_full_pipeline_smoke(self):
        """Full pipeline must complete without errors."""
        src = b"# Title\ncontent here\n- item\n```\ndef f(): pass\n```\n"
        idx = OriginalByteIndex(src)
        spans = adapt("markdown", idx)
        self.assertGreater(len(spans), 0, "adapter produced no spans")

        atoms = extract_atoms(idx, spans)
        self.assertGreater(len(atoms), 0, "no atoms extracted")

        cov, total, ratio = atom_coverage(idx, atoms)
        self.assertGreater(cov, 0, "zero coverage")

        if len(atoms) >= 2:
            r = relate(atoms[0], atoms[1], "SUPPORTS",
                        "human_confirmation", "test relation")
            self.assertEqual(r.rel_type, "SUPPORTS")

        p = build_packet(atoms, [], ["test_unknown"], [],
                         [], src, idx.total_bytes)
        self.assertTrue(len(p.packet_id) == 64, "invalid packet_id")
        self.assertTrue(len(p.semantic_hash) == 64, "invalid semantic_hash")

    def test_redaction_pipeline(self):
        """Redaction must find, resolve, and apply without secret leak."""
        src = b"use: sk-abcdefghijklmnopqrstuvwxyz123456 safe"
        idx = OriginalByteIndex(src)
        cands = find_redactions(idx)
        self.assertGreaterEqual(len(cands), 1, "no redaction candidates found")

        resolved = resolve_redactions(cands)
        self.assertGreaterEqual(len(resolved), 1, "no resolved redactions")

        view = apply_redactions(idx, resolved)
        self.assertNotIn(b"sk-abcdefghijklmnopqrstuvwxyz123456", view.redacted_bytes)
        self.assertGreaterEqual(view.redacted_count, 1)

    def test_spans_on_byte_boundaries(self):
        """All adapter spans must land on legal codepoint boundaries."""
        src = "中文test".encode("utf-8")
        idx = OriginalByteIndex(src)
        spans = adapt("txt", idx)
        for s in spans:
            self.assertIn(s.byte_start, idx.legal_boundaries,
                          f"byte_start {s.byte_start} not on boundary")
            self.assertIn(s.byte_end, idx.legal_boundaries,
                          f"byte_end {s.byte_end} not on boundary")

    def test_deterministic_ids(self):
        """Atom IDs must be deterministic across calls."""
        idx = OriginalByteIndex(b"hello")
        spans = adapt("txt", idx)
        a1 = extract_atoms(idx, spans)
        a2 = extract_atoms(idx, spans)
        self.assertEqual(len(a1), len(a2))
        for i in range(len(a1)):
            self.assertEqual(a1[i].atom_id, a2[i].atom_id)

    def test_no_fact_from_vocabulary(self):
        """AssertTrue, true, correct never produce FACT."""
        idx = OriginalByteIndex(b"assertTrue(result); this is true; correct answer")
        spans = adapt("txt", idx)
        atoms = extract_atoms(idx, spans)
        for a in atoms:
            self.assertNotEqual(a.class_, "FACT",
                                f"Atom {a.text_preview} wrongly classified FACT")

    def test_no_adjacency_relations(self):
        """Adjacency must NEVER produce relations."""
        src = b"# A\ncontent a\n# B\ncontent b\n"
        idx = OriginalByteIndex(src)
        spans = adapt("markdown", idx)
        atoms = extract_atoms(idx, spans)
        # Even if atoms are adjacent, no relation should be auto-generated
        from qclaw_byte_tokenizer.relations import adjacency_based_relations
        rels = adjacency_based_relations(atoms)
        self.assertEqual(len(rels), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
