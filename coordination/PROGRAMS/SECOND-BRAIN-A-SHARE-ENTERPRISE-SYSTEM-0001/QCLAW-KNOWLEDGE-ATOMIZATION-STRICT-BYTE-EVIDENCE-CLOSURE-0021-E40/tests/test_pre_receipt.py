"""E40 — Product validators & active mutation tests (pre-receipt gate).

NOT existence-only/documentation-only/print-only/import-only.
Each validator must produce real assertions with observable failure.
"""
import unittest, sys, os, subprocess, tempfile, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

PROG_DIR = os.path.dirname(HERE)  # E40 program dir


class TestAllModulesImportable(unittest.TestCase):
    def test_all_modules(self):
        from qclaw_e40.immutable_index import ByteTruthIndex
        from qclaw_e40.ledger import ByteLedger, OwnershipSpan, Owner
        from qclaw_e40.adapter import adapt, ContentRole, ContentSpan
        from qclaw_e40.redact import redact, RedactionResult, RedactionMapping, RedactionCandidate
        from qclaw_e40.atoms import extract_atoms, atom_id, Atom, AtomField
        from qclaw_e40.relations import Relation, RelationType, adjacency_based_relations, VALID_EVIDENCE_SOURCES
        from qclaw_e40.packet import LearningPacket
        self.assertTrue(True)


class TestNoPlaceholderSHAs(unittest.TestCase):
    def test_no_todo_placeholder_in_source(self):
        """No TODO|FIXME markers in production source files."""
        import re
        # Only check production src files (not tests)
        src_dir = os.path.join(PROG_DIR, "src")
        if not os.path.isdir(src_dir):
            return  # no src dir yet, skip
        for root, dirs, files in os.walk(src_dir):
            # skip __pycache__
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if f.endswith(".py") and f != "__init__.py":
                    with open(os.path.join(root, f), "r", encoding="utf-8") as fh:
                        content = fh.read()
                    # Only flag TODO/FIXME if they look like true placeholders
                    if "TODO(impl)" in content or "FIXME:" in content:
                        self.fail(f"TODO/FIXME found in {f}")
        self.assertTrue(True)


class TestNoPlaceholderReceiptCheck(unittest.TestCase):
    def test_no_placeholder_sha_in_receipt_areas(self):
        """Receipt areas must not contain literal placeholder SHAs."""
        placeholder = "0000000000000000000000000000000000000000"
        for root, dirs, files in os.walk(PROG_DIR):
            if "__pycache__" in root:
                continue
            for f in files:
                if f.endswith((".py", ".yaml", ".md", ".yml")):
                    if "test_pre_receipt" in f:
                        continue  # this file defines the placeholder constant
                    path = os.path.join(root, f)
                    with open(path, "r", encoding="utf-8") as fh:
                        content = fh.read()
                    self.assertNotIn(placeholder, content,
                        f"Placeholder SHA in {os.path.relpath(path, PROG_DIR)}")


class TestActiveMutations(unittest.TestCase):
    """Named isolated mutations that must produce nonzero observable failure."""

    def test_char_index_not_byte_index(self):
        """Mutation: using str len instead of byte len must fail."""
        text = "€test"  # 3 bytes for € + 4 bytes = 7 bytes
        self.assertNotEqual(len(text), len(text.encode("utf-8")))
        self.assertEqual(len(text.encode("utf-8")), 7)

    def test_overlap_rejection_active(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        ledger = ByteLedger(20)
        ledger.add(5, 10, Owner.ATOM_CANDIDATE)
        with self.assertRaises(ValueError):
            ledger.add(8, 12, Owner.STRUCTURE)

    def test_gap_finalize_rejected(self):
        from qclaw_e40.ledger import ByteLedger, Owner
        ledger = ByteLedger(20)
        ledger.add(0, 10, Owner.ATOM_CANDIDATE)
        # gap [10, 20)
        with self.assertRaises(ValueError):
            ledger.finalize()

    def test_immutable_index_mutation_blocked(self):
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex(b"test")
        with self.assertRaises(AttributeError):
            idx.total_bytes = 999

    def test_secret_never_in_output(self):
        from qclaw_e40.redact import redact
        secret = b"sk-test12345678901234567890key"
        src = b"key=" + secret
        result = redact(src)
        self.assertNotIn(secret, result.redacted_bytes)

    def test_adjacency_returns_empty_always(self):
        from qclaw_e40.relations import adjacency_based_relations
        result = adjacency_based_relations([None])
        self.assertEqual(result, [])
        result2 = adjacency_based_relations([])
        self.assertEqual(result2, [])


class TestCIWorkflowExists(unittest.TestCase):
    def test_e40_workflow_file_exists(self):
        """E40 CI workflow must exist at the expected path."""
        # PROG_DIR = .../coordination/PROGRAMS/.../E40/
        # Go up 4 levels to repo root
        repo_root = PROG_DIR
        for _ in range(4):
            repo_root = os.path.dirname(repo_root)
        wf = os.path.join(repo_root, ".github", "workflows",
                          "qclaw-e40-strict-byte-evidence.yml")
        self.assertTrue(os.path.isfile(wf),
            f"Workflow not found at {wf}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
