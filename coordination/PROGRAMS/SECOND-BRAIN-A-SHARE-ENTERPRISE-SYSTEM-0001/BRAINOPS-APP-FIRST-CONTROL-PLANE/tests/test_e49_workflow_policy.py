"""Policy tests for the E49 exact-head workflow."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROGRAM_ROOT.parents[3]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from brainops_control_plane.e49_workflow_policy import (  # noqa: E402
    E49WorkflowPolicyCode,
    validate_e49_workflow,
)


class E49WorkflowPolicyTests(unittest.TestCase):
    def test_actual_workflow_policy_is_complete(self):
        result = validate_e49_workflow(
            REPOSITORY_ROOT / ".github" / "workflows" / "brainops-e49.yml"
        )
        self.assertEqual(result.code, E49WorkflowPolicyCode.READY)

    def test_merge_ref_and_self_finalization_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow = Path(directory) / "brainops-e49.yml"
            text = (REPOSITORY_ROOT / ".github" / "workflows" / "brainops-e49.yml").read_text(
                encoding="utf-8"
            )
            workflow.write_text(
                text.replace(
                    "ref: ${{ github.event.pull_request.head.sha || github.sha }}",
                    "ref: refs/pull/159/merge",
                ),
                encoding="utf-8",
            )
            result = validate_e49_workflow(workflow)
        self.assertEqual(result.code, E49WorkflowPolicyCode.MISSING_EXACT_HEAD)

    def test_repository_generated_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow = Path(directory) / "brainops-e49.yml"
            text = (REPOSITORY_ROOT / ".github" / "workflows" / "brainops-e49.yml").read_text(
                encoding="utf-8"
            )
            workflow.write_text(
                text.replace("E49_EVIDENCE_DIR=$RUNNER_TEMP/e49-", "E49_EVIDENCE_DIR=."),
                encoding="utf-8",
            )
            result = validate_e49_workflow(workflow)
        self.assertEqual(result.code, E49WorkflowPolicyCode.MISSING_EXTERNAL_EVIDENCE_DIR)
