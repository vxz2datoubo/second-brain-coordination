from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_workbuddy_slots as base  # noqa: E402
from workbuddy_slots import validate_workbuddy_slots  # noqa: E402


class WorkBuddyO2AndGlobHardeningTests(unittest.TestCase):
    def _repo(self, slots):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        base._write_yaml(root, base.WORKBUDDY_REGISTRY, base._registry(slots, max_slots=2))
        for slot in slots:
            base._materialize_slot_refs(root, slot)
        primary = [slot for slot in slots if slot.get("primary_compatibility_projection")]
        if primary:
            base._write_yaml(root, base.LEGACY_WORKBUDDY_PROJECTION, base._legacy(primary[0]))
        return tmp, root

    @staticmethod
    def _codes(report):
        return {item["code"] for item in report["errors"]}

    def test_question_mark_glob_metacharacter_fails_closed(self):
        slot = base._slot("WB-A", "A", 1, 1, "workbuddy/a", "shared/?/**", primary=True)
        tmp, root = self._repo([slot])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_PATH_SCOPE_NONCANONICAL", self._codes(report), report["errors"])

    def test_character_class_glob_metacharacter_fails_closed(self):
        slot = base._slot("WB-A", "A", 1, 1, "workbuddy/a", "shared/[ab]/**", primary=True)
        tmp, root = self._repo([slot])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_PATH_SCOPE_NONCANONICAL", self._codes(report), report["errors"])

    def test_same_write_domain_o2_is_escalated_to_collision(self):
        a = base._slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        b = base._slot("WB-B", "B", 2, 2, "workbuddy/b", "path/b/**")
        a["write_domains"] = ["SHARED_MUTABLE_DOMAIN"]
        b["write_domains"] = ["SHARED_MUTABLE_DOMAIN"]
        tmp, root = self._repo([a, b])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_EXECUTABLE_SLOT_COLLISION", self._codes(report), report["errors"])
        reasons = [
            item["evidence"].get("collision", {}).get("reason")
            for item in report["errors"]
            if item["code"] == "WORKBUDDY_EXECUTABLE_SLOT_COLLISION"
        ]
        self.assertIn("O2_DOMAIN_SINGLE_WRITER_VIOLATION", reasons)

    def test_two_frozen_write_interfaces_o2_are_escalated_to_collision(self):
        a = base._slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        b = base._slot("WB-B", "B", 2, 2, "workbuddy/b", "path/b/**")
        a["interfaces"] = [{"name": "FROZEN.CONTRACT", "mode": "write", "frozen": True}]
        b["interfaces"] = [{"name": "FROZEN.CONTRACT", "mode": "write", "frozen": True}]
        tmp, root = self._repo([a, b])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_EXECUTABLE_SLOT_COLLISION", self._codes(report), report["errors"])

    def test_one_writer_one_reader_on_frozen_interface_remains_parallel_eligible(self):
        a = base._slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        b = base._slot("WB-B", "B", 2, 2, "workbuddy/b", "path/b/**")
        a["interfaces"] = [{"name": "FROZEN.CONTRACT", "mode": "write", "frozen": True}]
        b["interfaces"] = [{"name": "FROZEN.CONTRACT", "mode": "read", "frozen": True}]
        tmp, root = self._repo([a, b])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertEqual(report["structural_check"], "PASS", report["errors"])


if __name__ == "__main__":
    unittest.main()
