from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

import test_workbuddy_slots as base
from workbuddy_slots import validate_workbuddy_slots


class WorkBuddyTrustRootAndLegacyProjectionTests(unittest.TestCase):
    @staticmethod
    def _codes(report):
        return {item["code"] for item in report["errors"]}

    def _repo(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        slot = base._slot("WB-A", "TASK-A", 11, 101, "workbuddy/a", "coordination/test/WB-A/**", primary=True)
        base._write_yaml(root, base.WORKBUDDY_REGISTRY, base._registry([slot]))
        base._materialize_slot_refs(root, slot)
        base._write_yaml(root, base.LEGACY_WORKBUDDY_PROJECTION, base._legacy(slot))
        return tmp, root, slot

    @staticmethod
    def _valid_claim_payload(root: Path, slot: dict):
        return yaml.safe_load((root / slot["work_claim"]).read_text(encoding="utf-8"))

    def test_absolute_bound_reference_cannot_escape_repository(self):
        tmp, root, slot = self._repo(); self.addCleanup(tmp.cleanup)
        outside = tempfile.TemporaryDirectory(); self.addCleanup(outside.cleanup)
        attacker = Path(outside.name) / "claim.yaml"
        attacker.write_text(yaml.safe_dump(self._valid_claim_payload(root, slot)), encoding="utf-8")
        slot["work_claim"] = str(attacker)
        base._write_yaml(root, base.WORKBUDDY_REGISTRY, base._registry([slot]))
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_BOUND_REF_OUTSIDE_TRUST_ROOT", self._codes(report), report["errors"])

    def test_parent_traversal_bound_reference_cannot_escape_repository(self):
        tmp, root, slot = self._repo(); self.addCleanup(tmp.cleanup)
        attacker = root.parent / f"{root.name}-claim.yaml"
        self.addCleanup(lambda: attacker.unlink(missing_ok=True))
        attacker.write_text(yaml.safe_dump(self._valid_claim_payload(root, slot)), encoding="utf-8")
        slot["work_claim"] = f"../{attacker.name}"
        base._write_yaml(root, base.WORKBUDDY_REGISTRY, base._registry([slot]))
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_BOUND_REF_OUTSIDE_TRUST_ROOT", self._codes(report), report["errors"])

    def test_symlink_bound_reference_cannot_escape_repository(self):
        tmp, root, slot = self._repo(); self.addCleanup(tmp.cleanup)
        outside = tempfile.TemporaryDirectory(); self.addCleanup(outside.cleanup)
        attacker = Path(outside.name) / "claim.yaml"
        attacker.write_text(yaml.safe_dump(self._valid_claim_payload(root, slot)), encoding="utf-8")
        link = root / "coordination/test/WB-A/CLAIM-LINK.yaml"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(attacker)
        slot["work_claim"] = "coordination/test/WB-A/CLAIM-LINK.yaml"
        base._write_yaml(root, base.WORKBUDDY_REGISTRY, base._registry([slot]))
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_BOUND_REF_OUTSIDE_TRUST_ROOT", self._codes(report), report["errors"])

    def test_legacy_projection_route_reference_drift_fails_closed(self):
        tmp, root, slot = self._repo(); self.addCleanup(tmp.cleanup)
        legacy = base._legacy(slot)
        legacy["canonical_route"] = "coordination/ROUTES/ATTACKER.yaml"
        base._write_yaml(root, base.LEGACY_WORKBUDDY_PROJECTION, legacy)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_COMPATIBILITY_PROJECTION_DRIFT", self._codes(report), report["errors"])

    def test_legacy_projection_authorized_paths_drift_fails_closed(self):
        tmp, root, slot = self._repo(); self.addCleanup(tmp.cleanup)
        legacy = base._legacy(slot)
        legacy["authorized_paths"] = ["shared/attacker/**"]
        base._write_yaml(root, base.LEGACY_WORKBUDDY_PROJECTION, legacy)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_COMPATIBILITY_PROJECTION_DRIFT", self._codes(report), report["errors"])

    def test_executable_scalar_identity_types_fail_closed(self):
        bad_values = (
            ("route_epoch", {"bad": 1}),
            ("active_issue", [101]),
            ("branch", {"bad": "branch"}),
            ("pull_request", "580"),
            ("work_claim", ["coordination/test/WB-A/CLAIM.yaml"]),
        )
        for field, bad in bad_values:
            with self.subTest(field=field):
                tmp, root, slot = self._repo()
                try:
                    slot[field] = bad
                    base._write_yaml(root, base.WORKBUDDY_REGISTRY, base._registry([slot]))
                    report = validate_workbuddy_slots(root)
                    self.assertIn("WORKBUDDY_SLOT_IDENTITY_TYPE_INVALID", self._codes(report), report["errors"])
                finally:
                    tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
