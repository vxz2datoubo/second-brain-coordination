from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

import test_workbuddy_slots as base
import workbuddy_slots as target
from workbuddy_slots import validate_workbuddy_slots


class WorkBuddySnapshotV3Tests(unittest.TestCase):
    @staticmethod
    def _codes(report):
        return {item["code"] for item in report["errors"]}

    def _repo(self, slots):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        base._write_yaml(root, base.WORKBUDDY_REGISTRY, base._registry(slots))
        for slot in slots:
            base._materialize_slot_refs(root, slot)
        primary = [slot for slot in slots if slot.get("primary_compatibility_projection")]
        if primary:
            base._write_yaml(root, base.LEGACY_WORKBUDDY_PROJECTION, base._legacy(primary[0]))
        return tmp, root

    @staticmethod
    def _rewrite_claim_scope(root: Path, slot: dict, scope: str):
        path = root / slot["work_claim"]
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        payload["authorized_paths"] = [scope]
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    def test_glob_identity_keeps_single_level_and_recursive_scopes_distinct(self):
        self.assertEqual(target._glob_preserving_paths(["path/a/*"]), ["path/a/*"])
        self.assertEqual(target._glob_preserving_paths(["path/a/**"]), ["path/a/**"])
        self.assertNotEqual(
            target._glob_preserving_paths(["path/a/*"]),
            target._glob_preserving_paths(["path/a/**"]),
        )

    def test_single_level_authority_cannot_validate_recursive_registry_scope(self):
        slot = base._slot(
            "WB-A", "TASK-A", 11, 101, "workbuddy/a", "coordination/test/path/**", primary=True
        )
        tmp, root = self._repo([slot]); self.addCleanup(tmp.cleanup)
        self._rewrite_claim_scope(root, slot, "coordination/test/path/*")
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_BOUND_WRITE_SURFACE_DRIFT", self._codes(report), report["errors"])

    def test_recursive_authority_cannot_validate_single_level_registry_scope(self):
        slot = base._slot(
            "WB-A", "TASK-A", 11, 101, "workbuddy/a", "coordination/test/path/*", primary=True
        )
        tmp, root = self._repo([slot]); self.addCleanup(tmp.cleanup)
        self._rewrite_claim_scope(root, slot, "coordination/test/path/**")
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_BOUND_WRITE_SURFACE_DRIFT", self._codes(report), report["errors"])

    def test_legacy_projection_cannot_collapse_glob_depth(self):
        slot = base._slot(
            "WB-A", "TASK-A", 11, 101, "workbuddy/a", "coordination/test/path/**", primary=True
        )
        tmp, root = self._repo([slot]); self.addCleanup(tmp.cleanup)
        legacy = base._legacy(slot)
        legacy["authorized_paths"] = ["coordination/test/path/*"]
        base._write_yaml(root, base.LEGACY_WORKBUDDY_PROJECTION, legacy)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_COMPATIBILITY_PROJECTION_DRIFT", self._codes(report), report["errors"])

    def test_duplicate_completion_signal_across_executable_slots_fails_closed(self):
        first = base._slot("WB-A", "TASK-A", 11, 101, "workbuddy/a", "path/a/**", primary=True)
        second = base._slot("WB-B", "TASK-B", 12, 102, "workbuddy/b", "path/b/**")
        second["completion_signal"] = first["completion_signal"]
        tmp, root = self._repo([first, second]); self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_DUPLICATE_COMPLETION_SIGNAL", self._codes(report), report["errors"])

    def test_stable_validation_emits_full_authority_closure_witness(self):
        slot = base._slot("WB-A", "TASK-A", 11, 101, "workbuddy/a", "path/a/**", primary=True)
        tmp, root = self._repo([slot]); self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertEqual(report["structural_check"], "PASS", report["errors"])
        self.assertRegex(report["validated_authority_closure_sha256"], r"^[0-9a-f]{64}$")
        inputs = report["validated_authority_inputs"]
        expected = {
            base.WORKBUDDY_REGISTRY,
            base.LEGACY_WORKBUDDY_PROJECTION,
            slot["canonical_route"],
            slot["work_claim"],
            slot["task_lease"],
            slot["executor_reservation"],
            slot["prewrite_snapshot"],
            slot["executable_batch"],
        }
        self.assertTrue(expected.issubset(inputs.keys()), inputs)

    def _assert_mid_validation_change_detected(self, mutate):
        slot = base._slot("WB-A", "TASK-A", 11, 101, "workbuddy/a", "path/a/**", primary=True)
        tmp, root = self._repo([slot]); self.addCleanup(tmp.cleanup)
        original = target._V2_WORKBUDDY_SLOT_FINDINGS

        def validate_then_mutate(repo_root):
            findings = original(repo_root)
            mutate(root, slot)
            return findings

        with mock.patch.object(target, "_V2_WORKBUDDY_SLOT_FINDINGS", side_effect=validate_then_mutate):
            report = validate_workbuddy_slots(root)
        self.assertIn(
            "WORKBUDDY_AUTHORITY_INPUT_CHANGED_DURING_VALIDATION",
            self._codes(report),
            report["errors"],
        )
        self.assertEqual(report["structural_check"], "FAIL")
        self.assertEqual(report["slots"], [])

    def test_lease_mutation_after_authority_read_fails_closed(self):
        def mutate(root, slot):
            path = root / slot["task_lease"]
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            payload["lease_state"] = "RELEASED"
            path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

        self._assert_mid_validation_change_detected(mutate)

    def test_reservation_deletion_after_authority_read_fails_closed(self):
        def mutate(root, slot):
            (root / slot["executor_reservation"]).unlink()

        self._assert_mid_validation_change_detected(mutate)

    def test_route_replacement_after_authority_read_fails_closed(self):
        def mutate(root, slot):
            path = root / slot["canonical_route"]
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            payload["release_state"] = "REPLACED_AFTER_VALIDATION"
            path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

        self._assert_mid_validation_change_detected(mutate)


if __name__ == "__main__":
    unittest.main()
