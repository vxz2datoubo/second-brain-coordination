"""E48 workflow policy tests run without claiming provider execution."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROGRAM_ROOT.parents[3]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from brainops_control_plane.workflow_policy import (  # noqa: E402
    WorkflowPolicyCode,
    validate_e48_workflow,
)


class E48WorkflowPolicyTests(unittest.TestCase):
    def test_actual_workflow_policy_is_complete(self):
        result = validate_e48_workflow(
            REPOSITORY_ROOT / ".github" / "workflows" / "brainops-e48.yml"
        )
        self.assertEqual(result.code, WorkflowPolicyCode.READY)

    def test_merge_ref_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow = Path(directory) / "brainops-e48.yml"
            workflow.write_text(
                "uses: actions/checkout@v4\nref: refs/pull/154/merge\n",
                encoding="utf-8",
            )
            result = validate_e48_workflow(workflow)
        self.assertEqual(result.code, WorkflowPolicyCode.MISSING_EXACT_HEAD)
