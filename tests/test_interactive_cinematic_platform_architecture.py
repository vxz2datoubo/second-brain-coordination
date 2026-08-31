"""Tests for the repository-resident interactive cinematic control plane."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools.verify_interactive_cinematic_platform import (
    EXPECTED_PROGRAM_ID,
    PROGRAM_RELATIVE,
    VerificationError,
    validate,
)


ROOT = Path(__file__).resolve().parents[1]


class InteractiveCinematicPlatformArchitectureTests(unittest.TestCase):
    def test_committed_control_plane_validates(self) -> None:
        receipt = validate(ROOT)
        self.assertEqual("pass", receipt["status"])
        self.assertEqual(EXPECTED_PROGRAM_ID, receipt["program_id"])
        self.assertFalse(receipt["external_calls_performed"])
        self.assertFalse(receipt["private_data_read"])
        self.assertGreaterEqual(receipt["contract_count"], 29)

    def test_duplicate_contract_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            copy_root = Path(temporary) / "repo"
            shutil.copytree(ROOT / "coordination", copy_root / "coordination")
            manifest_path = copy_root / PROGRAM_RELATIVE / "CONTROL-PLANE-MANIFEST.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["contract_schemas"].append("ScriptPackage/v1")
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(VerificationError, "duplicate schema"):
                validate(copy_root)

    def test_missing_required_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            copy_root = Path(temporary) / "repo"
            shutil.copytree(ROOT / "coordination", copy_root / "coordination")
            (copy_root / PROGRAM_RELATIVE / "RUNBOOK.md").unlink()
            with self.assertRaisesRegex(VerificationError, "missing or empty"):
                validate(copy_root)

    def test_wrong_collaboration_prefix_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            copy_root = Path(temporary) / "repo"
            shutil.copytree(ROOT / "coordination", copy_root / "coordination")
            manifest_path = copy_root / PROGRAM_RELATIVE / "CONTROL-PLANE-MANIFEST.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["branch_prefixes"][0] = "codex/wrong-prefix-"
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(VerificationError, "branch prefixes"):
                validate(copy_root)


if __name__ == "__main__":
    unittest.main()
