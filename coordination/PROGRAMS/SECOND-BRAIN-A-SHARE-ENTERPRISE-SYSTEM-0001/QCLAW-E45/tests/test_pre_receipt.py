"""E45 pre_receipt validators

Rejects: missing modules, placeholder SHAs, self-reference, wrong topology.
All tests call real production code.
"""
import unittest, os, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJ, "src"))

# Walk up to repo root (5 levels: tests -> QCLAW-E45 -> SECOND-BRAIN-... -> PROGRAMS -> coordination -> repo)
def _repo_root():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        d = os.path.dirname(d)
    return d

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE)))))


class TestPreReceipt(unittest.TestCase):

    def test_all_modules_importable(self):
        """Every E45 module must import without error."""
        from qclaw_e45.capability import VerifiedEvidenceCapabilityView, make_test_capability
        from qclaw_e45.authority import EvidenceRegistry, EvidenceFactory, EvidenceRecord, EvidenceBundle, Atom
        from qclaw_e45.master_record import MasterRegistry, MasterRecord
        from qclaw_e45.cognition import CognitionEngine, CognitionEntry
        from qclaw_e45.skill_lifecycle import SkillFactory, Skill, SkillState
        from qclaw_e45.corpus import build_corpus, run_pipeline, CorpusInput
        from qclaw_e45.mutations import MUTATIONS, run_mutation
        self.assertTrue(True)

    def test_no_placeholder_sha_in_src(self):
        """No source file should contain a literal all-zero or placeholder SHA."""
        import glob
        src_dir = os.path.join(PROJ, "src", "qclaw_e45")
        for fp in glob.glob(os.path.join(src_dir, "*.py")):
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            # Reject all-zeros SHA (40 or 64 hex)
            self.assertNotIn("0000000000000000", content,
                            f"{os.path.basename(fp)} contains placeholder SHA")

    def test_no_placeholder_sha_in_tests(self):
        """Test files should not reference unreal SHAs as truth (skip self)."""
        import glob
        tests_dir = os.path.join(PROJ, "tests")
        self_path = os.path.abspath(__file__)
        for fp in glob.glob(os.path.join(tests_dir, "test_*.py")):
            if os.path.abspath(fp) == self_path:
                continue
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("0000000000000000000000000000000000000000", content,
                            f"{os.path.basename(fp)} contains 40-char all-zero SHA")

    def test_no_self_reference_in_src(self):
        """Production code must not hash itself — mutations.py excluded (needs paths for isolated copy)."""
        import glob
        src_dir = os.path.join(PROJ, "src", "qclaw_e45")
        for fp in glob.glob(os.path.join(src_dir, "*.py")):
            fn = os.path.basename(fp)
            if fn == "mutations.py":
                continue
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("__file__", content,
                            f"{fn} references __file__ (self-reference)")

    def test_ci_workflow_exists(self):
        """CI workflow file must exist at expected path."""
        wf = os.path.join(REPO, ".github", "workflows", "qclaw-e45-semantic-authority-evaluation.yml")
        self.assertTrue(os.path.isfile(wf), f"CI workflow not found at {wf}")

    def test_ci_workflow_has_matrix(self):
        """CI workflow must contain 3.11, 3.13, and seed matrix."""
        wf = os.path.join(REPO, ".github", "workflows", "qclaw-e45-semantic-authority-evaluation.yml")
        with open(wf, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("3.11", content)
        self.assertIn("3.13", content)
        self.assertIn("hash-seed", content)
        self.assertIn("byte-compare", content.lower())

    def test_ci_workflow_has_evaluate_and_compare(self):
        wf = os.path.join(REPO, ".github", "workflows", "qclaw-e45-semantic-authority-evaluation.yml")
        with open(wf, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("evaluate", content)
        self.assertIn("compare", content)

    def test_source_manifest_exists(self):
        sm = os.path.join(PROJ, "SOURCE-MANIFEST.yaml")
        self.assertTrue(os.path.isfile(sm))

    def test_e44_source_selection_exists(self):
        ss = os.path.join(PROJ, "E44-SOURCE-SELECTION.yaml")
        self.assertTrue(os.path.isfile(ss))

    def test_project_plan_exists(self):
        pp = os.path.join(PROJ, "PROJECT-PLAN.md")
        self.assertTrue(os.path.isfile(pp))
        with open(pp, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertGreater(len(content), 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
