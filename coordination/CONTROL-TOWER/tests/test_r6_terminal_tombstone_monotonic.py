from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worker_slots import (  # noqa: E402
    EXPECTED_R6_AUTHORITY_ID,
    MAINTENANCE_TOMBSTONES_FILE,
    validate_worker_slots,
)


REQUIRED_FIXTURE_FILES = (
    "coordination/ACTIVE-PROGRAM-LANES.yaml",
    "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml",
    "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml",
    "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION.yaml",
    "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION-R4.yaml",
    "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION-R5.yaml",
    "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION-R6.yaml",
    "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-TERMINAL-TOMBSTONES.yaml",
    "coordination/TASK-BRIEFS/CODEX-CONTROL-TOWER-GPT-ENGINEERING-WORKER-FIRST-CLASS-R144.yaml",
)


class R6TerminalTombstoneMonotonicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[3]

    def _copy_current_governance_fixture(self, destination: Path) -> None:
        for relative in REQUIRED_FIXTURE_FILES:
            source = self.repo_root / relative
            self.assertTrue(source.is_file(), f"required current-governance fixture missing: {relative}")
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    @staticmethod
    def _error_codes(report: dict) -> list[str]:
        return [str(item.get("code")) for item in report.get("errors", [])]

    def test_deleting_only_r6_tombstone_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._copy_current_governance_fixture(root)

            baseline = validate_worker_slots(root)
            self.assertNotIn(
                "MAINTENANCE_TOMBSTONE_EXPECTED_ID_MISSING",
                self._error_codes(baseline),
                baseline,
            )

            tombstone_path = root / MAINTENANCE_TOMBSTONES_FILE
            document = yaml.safe_load(tombstone_path.read_text(encoding="utf-8"))
            records = document["terminal_authorities"]
            retained = [
                record
                for record in records
                if record.get("authority_id") != EXPECTED_R6_AUTHORITY_ID
            ]
            self.assertEqual(len(retained), len(records) - 1, "fixture must contain exactly one R6 tombstone")
            document["terminal_authorities"] = retained
            tombstone_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

            report = validate_worker_slots(root)
            missing = [
                item
                for item in report.get("errors", [])
                if item.get("code") == "MAINTENANCE_TOMBSTONE_EXPECTED_ID_MISSING"
            ]
            self.assertEqual(len(missing), 1, report)
            self.assertIn(
                EXPECTED_R6_AUTHORITY_ID,
                missing[0].get("context", {}).get("missing_authority_ids", []),
                missing[0],
            )
            self.assertFalse(report["maintenance_write_allowed"])

    def test_r6_terminal_binding_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._copy_current_governance_fixture(root)

            tombstone_path = root / MAINTENANCE_TOMBSTONES_FILE
            document = yaml.safe_load(tombstone_path.read_text(encoding="utf-8"))
            r6 = next(
                record
                for record in document["terminal_authorities"]
                if record.get("authority_id") == EXPECTED_R6_AUTHORITY_ID
            )
            r6["release_parent_head"] = "0" * 40
            tombstone_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

            report = validate_worker_slots(root)
            self.assertIn("MAINTENANCE_TOMBSTONE_BINDING_MISMATCH", self._error_codes(report), report)
            self.assertFalse(report["maintenance_write_allowed"])


if __name__ == "__main__":
    unittest.main()
