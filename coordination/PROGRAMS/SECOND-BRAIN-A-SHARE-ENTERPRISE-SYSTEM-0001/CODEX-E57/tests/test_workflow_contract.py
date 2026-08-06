from __future__ import annotations

from pathlib import Path
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = TASK_ROOT.parents[3]
WORKFLOW = REPOSITORY / ".github" / "workflows" / "codex-e57-capability-authority-closure.yml"


class WorkflowContractTests(unittest.TestCase):
    def test_workflow_has_six_matrix_jobs_one_compare_and_thirteen_artifacts(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('python-version: ["3.11", "3.13"]', text)
        self.assertIn('hash-seed: ["0", "1", "777"]', text)
        self.assertIn("provider-compare:", text)
        self.assertEqual(text.count("actions/upload-artifact@v4"), 3)
        self.assertIn("canonical-py${{ matrix.python-version }}-seed${{ matrix.hash-seed }}", text)
        self.assertIn("environment-py${{ matrix.python-version }}-seed${{ matrix.hash-seed }}", text)
        self.assertIn("name: provider-compare", text)
