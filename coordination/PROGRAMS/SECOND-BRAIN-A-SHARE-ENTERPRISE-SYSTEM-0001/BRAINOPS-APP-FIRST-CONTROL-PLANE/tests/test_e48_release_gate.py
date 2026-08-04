"""Tests for the repository-backed E48 pre-receipt gate."""

from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROGRAM_ROOT.parents[3]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from brainops_control_plane.release_gate import (  # noqa: E402
    ReleaseGateCode,
    validate_repository_release_gate,
    validate_receipt_topology,
)


class E48ReleaseGateTests(unittest.TestCase):
    def _head(self) -> str:
        import subprocess

        return subprocess.check_output(
            ["git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"], text=True
        ).strip()

    def test_wrong_exact_head_is_rejected_from_actual_git_state(self):
        result = validate_repository_release_gate(
            REPOSITORY_ROOT,
            PROGRAM_ROOT,
            "0" * 40,
            "ac17da81cd2ea019786e9f1d229eaede944756d9",
        )
        self.assertEqual(result.code, ReleaseGateCode.HEAD_MISMATCH)

    def test_fabricated_provider_pre_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence_path = Path(directory) / "provider.json"
            evidence_path.write_text(
                json.dumps(
                    {
                        "workflow": "fabricated.yml",
                        "head_sha": self._head(),
                        "required_python_versions": ["3.11", "3.13"],
                        "job_python_version": "3.13",
                        "evidence_class": "IN_JOB_POLICY_AND_CURRENT_JOB_OBSERVATION_ONLY",
                    }
                ),
                encoding="utf-8",
            )
            result = validate_repository_release_gate(
                REPOSITORY_ROOT,
                PROGRAM_ROOT,
                self._head(),
                "ac17da81cd2ea019786e9f1d229eaede944756d9",
                evidence_path,
            )
        self.assertEqual(result.code, ReleaseGateCode.PROVIDER_PRE_EVIDENCE_INVALID)

    def test_receipt_topology_rejects_a_non_child_commit(self):
        result = validate_receipt_topology(
            REPOSITORY_ROOT,
            "ac17da81cd2ea019786e9f1d229eaede944756d9",
            self._head(),
        )
        self.assertFalse(result.ready)
        self.assertIn("receipt_parent_is_not_tested_head", result.findings)
