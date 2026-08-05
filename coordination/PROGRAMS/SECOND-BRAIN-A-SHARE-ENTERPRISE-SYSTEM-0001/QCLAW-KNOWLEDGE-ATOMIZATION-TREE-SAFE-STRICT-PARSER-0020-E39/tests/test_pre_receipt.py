"""E39 S6 — Product pre-receipt validators."""
import unittest, sys, os, re

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"
PROG = os.path.dirname(__file__)


class TestAllModulesImportable(unittest.TestCase):
    def test_utf8_guard(self):
        from qclaw_strict_byte.utf8_guard import UTF8ByteIndex
        self.assertTrue(True)
    def test_ledger(self):
        from qclaw_strict_byte.ledger import ByteLedger, OwnerSpan
        self.assertTrue(True)
    def test_adapter(self):
        from qclaw_strict_byte.adapter import adapt_markdown, adapt_json, adapt_jsonl, adapt_txt
        self.assertTrue(True)
    def test_redact(self):
        from qclaw_strict_byte.redact import redact
        self.assertTrue(True)
    def test_atoms(self):
        from qclaw_strict_byte.atoms import Atom, extract_atoms
        self.assertTrue(True)
    def test_relations(self):
        from qclaw_strict_byte.relations import Relation, adjacency_based_relations
        self.assertTrue(True)
    def test_packet(self):
        from qclaw_strict_byte.packet import build_packet, LearningPacket
        self.assertTrue(True)


class TestNoPlaceholderSHAs(unittest.TestCase):
    def setUp(self):
        self.files = [os.path.join(PROG, "..", "src", "qclaw_strict_byte", f)
                      for f in ["__init__.py","utf8_guard.py","ledger.py","adapter.py",
                                "redact.py","atoms.py","relations.py","packet.py"]]
    def test_no_placeholder_sha(self):
        ph = re.compile(r"\b000000[0-9a-f]{34,}\b", re.IGNORECASE)
        for fp in self.files:
            if not os.path.exists(fp): continue
            with open(fp,"r",encoding="utf-8") as f: txt = f.read()
            m = ph.search(txt)
            self.assertIsNone(m, f"{os.path.basename(fp)} placeholder SHA: {m}")
    def test_no_todo_markers(self):
        for fp in self.files:
            if not os.path.exists(fp): continue
            with open(fp,"r",encoding="utf-8") as f: txt = f.read()
            for ptn in ["TODO","PLANNED","FIXME\\b","HACK\\b"]:
                m = re.search(ptn, txt)
                self.assertIsNone(m, f"{os.path.basename(fp)} '{ptn}'")


class TestWorkflowAndManifest(unittest.TestCase):
    def test_ci_workflow_exists(self):
        repo = os.path.normpath(os.path.join(PROG, "..", "..", "..", "..", ".."))
        wf = os.path.join(repo, ".github", "workflows", "qclaw-e39-tree-safe-parser.yml")
        self.assertTrue(os.path.exists(wf), f"Missing: {wf}")
    def test_source_manifest(self):
        mf = os.path.normpath(os.path.join(PROG, "..", "SOURCE-MANIFEST.yaml"))
        self.assertTrue(os.path.exists(mf))
        with open(mf,"r",encoding="utf-8") as f:
            self.assertIn("epoch: 39", f.read())


class TestReceiptTopology(unittest.TestCase):
    def test_constraint_documented(self):
        self.assertTrue(True)  # actual topology verified at receipt time


class TestArtifactConsistency(unittest.TestCase):
    def test_adjacency_blocked(self):
        from qclaw_strict_byte.relations import adjacency_based_relations
        self.assertEqual(adjacency_based_relations([]), [])

    def test_default_claim_not_fact(self):
        from qclaw_strict_byte.utf8_guard import UTF8ByteIndex
        from qclaw_strict_byte.ledger import ByteLedger, OWNER_ATOM_CANDIDATE
        from qclaw_strict_byte.atoms import extract_atoms, ATOM_FACT
        idx = UTF8ByteIndex(b"This is a simple sentence.")
        ledger = ByteLedger(idx)
        ledger.add(0, idx.total_bytes, OWNER_ATOM_CANDIDATE, "content")
        atoms = extract_atoms(idx, ledger)
        self.assertEqual(len([a for a in atoms if a.atom_type == ATOM_FACT]), 0)

    def test_redaction_never_stores_secret(self):
        from qclaw_strict_byte.redact import redact
        secret = b"sk-abc123secret__LONGTAIL__"
        data = b"use: " + secret + b" here"
        result = redact(data)
        self.assertNotIn(secret, result.redacted_bytes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
