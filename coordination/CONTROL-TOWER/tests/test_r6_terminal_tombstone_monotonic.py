from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worker_slots import (  # noqa: E402
    MAINTENANCE_ADOPTION_FILE,
    MAINTENANCE_TOMBSTONES_FILE,
    R3_MAINTENANCE_ADOPTION_FILE,
    R4_MAINTENANCE_ADOPTION_FILE,
    R6_MAINTENANCE_ADOPTION_FILE,
    R144_TASK_BRIEF_FILE,
    _terminal_tombstone_findings,
    validate_worker_slots,
)

R6_AUTHORITY_ID = "R144-GPT-ARCHITECTURE-OWNER-MAINTENANCE-ADOPTION-R6-0001"

_COPY_PATHS = (
    "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml",
    "coordination/ACTIVE-PROGRAM-LANES.yaml",
    "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml",
    R3_MAINTENANCE_ADOPTION_FILE,
    R4_MAINTENANCE_ADOPTION_FILE,
    MAINTENANCE_ADOPTION_FILE,
    R6_MAINTENANCE_ADOPTION_FILE,
    MAINTENANCE_TOMBSTONES_FILE,
    R144_TASK_BRIEF_FILE,
)


class R6TerminalTombstoneMonotonicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[3]

    def _build_tree(self, root: Path) -> Path:
        for rel in _COPY_PATHS:
            src = self.repo_root / rel
            if not src.exists():
                continue
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, target)
        return root

    def test_complete_r4_r5_r6_terminal_registry_has_no_missing_expected_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_tree(Path(tmp))
            findings = _terminal_tombstone_findings(root)
            codes = {finding.code for finding in findings}
            self.assertNotIn("MAINTENANCE_TOMBSTONE_EXPECTED_ID_MISSING", codes)
            self.assertNotIn("MAINTENANCE_TERMINAL_AUTHORITY_REACTIVATION", codes)

    def test_deleting_only_r6_tombstone_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_tree(Path(tmp))
            tomb_path = root / MAINTENANCE_TOMBSTONES_FILE
            doc = yaml.safe_load(tomb_path.read_text(encoding="utf-8"))
            doc["terminal_authorities"] = [
                record
                for record in doc["terminal_authorities"]
                if record.get("authority_id") != R6_AUTHORITY_ID
            ]
            tomb_path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")

            findings = _terminal_tombstone_findings(root)
            codes = {finding.code for finding in findings}
            self.assertIn("MAINTENANCE_TOMBSTONE_EXPECTED_ID_MISSING", codes)
            missing = [
                finding
                for finding in findings
                if finding.code == "MAINTENANCE_TOMBSTONE_EXPECTED_ID_MISSING"
            ]
            self.assertTrue(missing)
            self.assertEqual(
                set(missing[0].evidence.get("missing_authority_ids", [])),
                {R6_AUTHORITY_ID},
            )

            result = validate_worker_slots(root)
            self.assertFalse(result["maintenance_write_allowed"])

    def test_r6_authority_reactivation_is_monotonic_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_tree(Path(tmp))
            r6_path = root / R6_MAINTENANCE_ADOPTION_FILE
            doc = yaml.safe_load(r6_path.read_text(encoding="utf-8"))
            doc["state"] = "ACTIVE"
            r6_path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")

            findings = _terminal_tombstone_findings(root)
            codes = {finding.code for finding in findings}
            self.assertIn("MAINTENANCE_TERMINAL_AUTHORITY_REACTIVATION", codes)


if __name__ == "__main__":
    unittest.main()
