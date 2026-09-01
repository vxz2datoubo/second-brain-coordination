"""E46 pre-receipt validators — module imports, CI, placeholder checks."""

import unittest
import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


class TestPreReceipt(unittest.TestCase):
    """S5: Pre-receipt validators."""
    
    def test_all_modules_importable(self):
        """All E46 production modules must be importable."""
        modules = [
            "qclaw_e46.capability",
            "qclaw_e46.authority",
            "qclaw_e46.master_record",
            "qclaw_e46.cognition",
            "qclaw_e46.skill_lifecycle",
            "qclaw_e46.corpus",
            "qclaw_e46.mutations",
        ]
        for mod in modules:
            try:
                __import__(mod)
            except ImportError as e:
                self.fail(f"Failed to import {mod}: {e}")
    
    def test_no_placeholder_sha_in_src(self):
        """No placeholder SHA values in source files."""
        placeholder = "0" * 40
        e46_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        src_dir = os.path.join(e46_dir, "src", "qclaw_e46")
        results = []
        for root, dirs, files in os.walk(src_dir):
            for fn in files:
                if fn.endswith(".py"):
                    fp = os.path.join(root, fn)
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                    if placeholder in content:
                        results.append(f"{fn}: contains placeholder SHA")
        self.assertEqual(len(results), 0, f"Placeholder SHAs found:\n" + "\n".join(results))
    
    def test_no_planned_todo_in_src(self):
        """No 'Planned' or 'TODO IMPLEMENT' markers in source."""
        patterns = [r"#\s*Planned:", r"#\s*TODO IMPLEMENT"]
        e46_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        src_dir = os.path.join(e46_dir, "src", "qclaw_e46")
        results = []
        for root, dirs, files in os.walk(src_dir):
            for fn in files:
                if fn.endswith(".py"):
                    fp = os.path.join(root, fn)
                    with open(fp, "r", encoding="utf-8") as f:
                        for i, line in enumerate(f, 1):
                            for pat in patterns:
                                if re.search(pat, line):
                                    results.append(f"{fn}:{i}: {line.strip()}")
        self.assertEqual(len(results), 0, f"Planned/TODO found:\n" + "\n".join(results))
    
    def test_e46_workflow_exists(self):
        """CI workflow file must exist."""
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        # tests -> E46 -> ... -> repo root (find .github directory)
        repo_root = tests_dir
        for _ in range(10):
            repo_root = os.path.dirname(repo_root)
            if os.path.isdir(os.path.join(repo_root, ".github")):
                break
        wf_path = os.path.join(repo_root, ".github", "workflows", "qclaw-e46-truthful-semantic-evidence.yml")
        self.assertTrue(os.path.isfile(wf_path), f"CI workflow not found at {wf_path}")
    
    def test_e45_source_selection_exists(self):
        """E45-SOURCE-SELECTION.yaml must exist."""
        e46_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sf_path = os.path.join(e46_dir, "E45-SOURCE-SELECTION.yaml")
        self.assertTrue(os.path.isfile(sf_path))
    
    def test_project_plan_exists(self):
        """PROJECT-PLAN.md must exist."""
        e46_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        plan_path = os.path.join(e46_dir, "PROJECT-PLAN.md")
        self.assertTrue(os.path.isfile(plan_path))
    
    def test_source_manifest_exists(self):
        """SOURCE-MANIFEST.yaml must exist."""
        e46_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sm_path = os.path.join(e46_dir, "SOURCE-MANIFEST.yaml")
        self.assertTrue(os.path.isfile(sm_path))


if __name__ == "__main__":
    unittest.main()
