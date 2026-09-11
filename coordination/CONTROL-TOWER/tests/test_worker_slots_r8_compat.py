from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml

CONTROL_TOWER = Path(__file__).resolve().parents[1]
if str(CONTROL_TOWER) not in sys.path:
    sys.path.insert(0, str(CONTROL_TOWER))

from worker_lifecycle import (  # noqa: E402
    LIFECYCLE_RELEASED,
    LIFECYCLE_UNKNOWN,
    audit_worker_registry_lifecycle,
    registry_schema_supported,
    resolve_worker_lifecycle,
)
from worker_slots import (  # noqa: E402
    GPT_WORKERS_REGISTRY,
    R7_AUTHORITY_ID,
    R7_MAINTENANCE_ADOPTION_FILE,
    R8_MAINTENANCE_ADOPTION_FILE,
    MAINTENANCE_TOMBSTONES_FILE,
    _slot_required_field_findings,
    load_worker_slots,
    normalize_worker_slot,
    validate_worker_slots,
    worker_slot_is_executable,
    worker_slot_route_witness,
)


class R8WorkerSlotsCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[3]

    def test_current_schema_15_registry_is_supported_by_legacy_surface(self) -> None:
        registry = yaml.safe_load((self.repo_root / GPT_WORKERS_REGISTRY).read_text(encoding="utf-8"))
        self.assertEqual(registry["schema_version"], "1.5")
        self.assertTrue(registry_schema_supported("1.5"))
        self.assertTrue(registry_schema_supported("1.0"))
        self.assertFalse(registry_schema_supported("999"))

        report = validate_worker_slots(self.repo_root)
        self.assertEqual(report["worker_slot_structural_check"], "PASS", report["errors"])
        self.assertEqual(report["active_executable_slots"], [])

    def test_current_capacity_is_derived_from_canonical_lifecycle_audit(self) -> None:
        audit = audit_worker_registry_lifecycle(self.repo_root)
        self.assertTrue(audit.valid_for_observability, audit.findings)
        self.assertEqual(audit.occupied_capacity_count, 0)
        self.assertEqual(audit.free_capacity_count, 2)
        self.assertFalse(audit.successor_release_authority)

    def test_r182_r183_are_terminal_non_executable_through_both_surfaces(self) -> None:
        slots = {slot.worker_slot_id: slot for slot in load_worker_slots(self.repo_root)}
        targets = (
            "GPT-WORKER-R182-W2-MARKET-SEMANTICS-1",
            "GPT-WORKER-R183-DS10-RESEARCH-INTEGRITY-1",
        )
        for slot_id in targets:
            slot = slots[slot_id]
            material = worker_slot_route_witness(slot)
            material.pop("fingerprint", None)
            resolution = resolve_worker_lifecycle(material)
            self.assertEqual(resolution.lifecycle_state, LIFECYCLE_RELEASED)
            self.assertFalse(resolution.executable)
            self.assertFalse(resolution.occupies_capacity)
            self.assertTrue(resolution.terminal)
            self.assertFalse(resolution.current_write_authority)
            self.assertFalse(worker_slot_is_executable(slot))

    def test_unknown_lifecycle_remains_fail_closed(self) -> None:
        slot = normalize_worker_slot(
            {
                "worker_slot_id": "GPT-WORKER-UNKNOWN-R8-TEST",
                "agent_type": "GPT_ENGINEERING_WORKER",
                "executor_role": "GPT_ENGINEERING_WORKER",
                "model_id": "GPT-5.6 Sol",
                "task_id": "R8-UNKNOWN-TEST",
                "route_epoch": 999,
                "issue": 572,
                "pr": 999,
                "branch": "gpt/r8-test",
                "status": "ALIEN",
                "execution_allowed": True,
                "write_paths": ["coordination/CONTROL-TOWER/worker_slots.py"],
                "read_paths": [],
                "interfaces": [],
                "read_domains": ["CONTROL_TOWER"],
                "write_domains": ["CONTROL_TOWER"],
                "authority_claims": [],
                "resource_class": "LIGHT_TO_MEDIUM_IMPLEMENTATION",
                "provenance": {"source_issue": 572},
                "reviewer_role": "GPT_INDEPENDENT_REVIEWER",
                "reviewer_separation": "EXECUTION_IDENTITY_NOT_ACCEPTANCE_AUTHORITY",
                "activation_state": "ALIEN",
                "closure_state": None,
            }
        )
        material = worker_slot_route_witness(slot)
        material.pop("fingerprint", None)
        self.assertEqual(resolve_worker_lifecycle(material).lifecycle_state, LIFECYCLE_UNKNOWN)
        self.assertFalse(worker_slot_is_executable(slot))
        self.assertIn(
            "WORKER_SLOT_LIFECYCLE_UNKNOWN",
            {finding.code for finding in _slot_required_field_findings(slot)},
        )

    def test_r7_is_monotonically_released_and_r8_is_new_active_identity(self) -> None:
        r7 = yaml.safe_load((self.repo_root / R7_MAINTENANCE_ADOPTION_FILE).read_text(encoding="utf-8"))
        r8 = yaml.safe_load((self.repo_root / R8_MAINTENANCE_ADOPTION_FILE).read_text(encoding="utf-8"))
        tombstones = yaml.safe_load((self.repo_root / MAINTENANCE_TOMBSTONES_FILE).read_text(encoding="utf-8"))
        records = {item["authority_id"]: item for item in tombstones["terminal_authorities"]}

        self.assertEqual(r7["authority_id"], R7_AUTHORITY_ID)
        self.assertEqual(r7["state"], "RELEASED")
        self.assertFalse(records[R7_AUTHORITY_ID]["reactivation_allowed"])
        self.assertEqual(records[R7_AUTHORITY_ID]["terminal_state"], "RELEASED")
        self.assertEqual(r8["state"], "ACTIVE")
        self.assertNotEqual(r8["authority_id"], r7["authority_id"])
        self.assertEqual(r8["predecessor_authority"]["authority_id"], R7_AUTHORITY_ID)
        for key in (
            "execution_allowed",
            "runtime_write_allowed",
            "trade_allowed",
            "merge_authority",
            "acceptance_authority",
            "self_review_allowed",
            "successor_release_authority",
            "real_capture_allowed",
            "operational_w3_write_allowed",
        ):
            self.assertIs(r8[key], False)

    def test_worker_slots_is_adapter_not_second_lifecycle_table(self) -> None:
        source = (self.repo_root / "coordination/CONTROL-TOWER/worker_slots.py").read_text(encoding="utf-8")
        self.assertIn("resolve_worker_lifecycle", source)
        self.assertIn("audit_worker_registry_lifecycle", source)
        self.assertIn("registry_schema_supported", source)
        self.assertNotIn("ALLOWED_ACTIVATION_STATES", source)
        self.assertNotIn("ALLOWED_CLOSURE_STATES", source)


if __name__ == "__main__":
    unittest.main()
