from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

TESTS_DIR = Path(__file__).resolve().parent
CONTROL_TOWER_DIR = TESTS_DIR.parent
sys.path.insert(0, str(CONTROL_TOWER_DIR))
sys.path.insert(0, str(TESTS_DIR))

import test_workbuddy_slots as base  # noqa: E402
from workbuddy_slots import validate_workbuddy_slots  # noqa: E402


class WorkBuddyMultiSlotHardeningTests(unittest.TestCase):
    """Unique adversarial cases added after independent review.

    The base test module is imported only as a module alias so unittest discovery
    does not rediscover its TestCase class through this module namespace.
    """

    def _repo(self, slots, max_slots=2):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        base._write_yaml(root, base.WORKBUDDY_REGISTRY, base._registry(slots, max_slots=max_slots))
        for slot in slots:
            base._materialize_slot_refs(root, slot)
        primary = [slot for slot in slots if slot.get("primary_compatibility_projection")]
        if primary:
            base._write_yaml(root, base.LEGACY_WORKBUDDY_PROJECTION, base._legacy(primary[0]))
        return tmp, root

    @staticmethod
    def _codes(report):
        return {item["code"] for item in report["errors"]}

    def test_noncanonical_path_scopes_fail_closed(self):
        bad_paths = (
            "isolated/../shared/**",
            "isolated/./shared/**",
            "shared//nested/**",
            "C:/shared/**",
            "/shared/**",
            "shared\\nested/**",
            " shared/**",
            "shared/*/nested/**",
        )
        for bad_path in bad_paths:
            with self.subTest(path=bad_path):
                slot = base._slot("WB-A", "A", 1, 1, "workbuddy/a", bad_path, primary=True)
                tmp, root = self._repo([slot])
                try:
                    report = validate_workbuddy_slots(root)
                    self.assertIn("WORKBUDDY_PATH_SCOPE_NONCANONICAL", self._codes(report), report["errors"])
                finally:
                    tmp.cleanup()

    def test_duplicate_interface_name_cannot_hide_write_mode(self):
        slot = base._slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        slot["interfaces"] = [
            {"name": "TDXQ.RUNTIME", "mode": "write", "frozen": False},
            {"name": "TDXQ.RUNTIME", "mode": "read", "frozen": True},
        ]
        tmp, root = self._repo([slot])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_INTERFACE_NAME_DUPLICATE", self._codes(report), report["errors"])

    def test_bound_documents_cannot_grant_forbidden_authority_at_any_depth(self):
        ref_names = (
            "canonical_route",
            "work_claim",
            "task_lease",
            "executor_reservation",
            "prewrite_snapshot",
            "executable_batch",
        )
        for ref_name in ref_names:
            with self.subTest(ref=ref_name):
                slot = base._slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
                tmp, root = self._repo([slot])
                try:
                    relpath = slot[ref_name]
                    raw = yaml.safe_load((root / relpath).read_text(encoding="utf-8"))
                    raw.setdefault("nested_security_probe", {})["order_or_trade_authority"] = True
                    base._write_yaml(root, relpath, raw)
                    report = validate_workbuddy_slots(root)
                    self.assertIn("WORKBUDDY_BOUND_REF_FORBIDDEN_AUTHORITY", self._codes(report), report["errors"])
                finally:
                    tmp.cleanup()

    def test_bound_route_merge_authorized_alias_cannot_be_true(self):
        slot = base._slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        tmp, root = self._repo([slot])
        self.addCleanup(tmp.cleanup)
        route = yaml.safe_load((root / slot["canonical_route"]).read_text(encoding="utf-8"))
        route["merge_authorized"] = True
        base._write_yaml(root, slot["canonical_route"], route)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_BOUND_REF_FORBIDDEN_AUTHORITY", self._codes(report), report["errors"])


if __name__ == "__main__":
    unittest.main()
