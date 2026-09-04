from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workbuddy_slots import (  # noqa: E402
    LEGACY_WORKBUDDY_PROJECTION,
    WORKBUDDY_REGISTRY,
    classify_workbuddy_collision,
    load_workbuddy_slots,
    normalize_workbuddy_slot,
    validate_workbuddy_slots,
)


def _write_yaml(root: Path, relpath: str, payload) -> None:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _slot(slot_id: str, task_id: str, epoch: int, issue: int, branch: str, write_path: str, *, primary=False):
    base = f"coordination/test/{slot_id}"
    return {
        "worker_slot_id": slot_id,
        "agent_type": "WORKBUDDY",
        "executor_role": "WORKBUDDY_LOCAL_EXECUTOR",
        "task_id": task_id,
        "route_epoch": epoch,
        "active_issue": issue,
        "pull_request": None,
        "branch": branch,
        "status": "READY",
        "execution_allowed": True,
        "activation_state": "ACTIVE",
        "closure_state": None,
        "canonical_route": f"{base}/ROUTE.yaml",
        "work_claim": f"{base}/CLAIM.yaml",
        "task_lease": f"{base}/LEASE.yaml",
        "executor_reservation": f"{base}/RESERVATION.yaml",
        "completion_signal": f"{task_id}_COMPLETE",
        "write_paths": [write_path],
        "read_paths": [],
        "interfaces": [],
        "read_domains": [],
        "write_domains": [f"DOMAIN_{slot_id}"],
        "authority_claims": [f"AUTH_{slot_id}"],
        "exclusive_resources": [],
        "shared_read_resources": [],
        "mutable_runtime_resources": [],
        "credential_surfaces": [],
        "real_data_surfaces": [],
        "order_or_trade_authority": False,
        "primary_compatibility_projection": primary,
    }


def _bound_doc(slot: dict, *, branch_key="branch"):
    return {
        "task_id": slot["task_id"],
        "route_epoch": slot["route_epoch"],
        "active_issue": slot["active_issue"],
        branch_key: slot["branch"],
    }


def _materialize_slot_refs(root: Path, slot: dict) -> None:
    _write_yaml(root, slot["canonical_route"], _bound_doc(slot))
    _write_yaml(root, slot["work_claim"], _bound_doc(slot))
    _write_yaml(root, slot["task_lease"], _bound_doc(slot, branch_key="implementation_branch"))
    _write_yaml(root, slot["executor_reservation"], _bound_doc(slot, branch_key="implementation_branch"))


def _registry(slots, max_slots=2):
    return {
        "schema_version": "1.0",
        "registry_id": "ACTIVE-WORKBUDDY-TASKS-0001",
        "repository": "vxz2datoubo/second-brain-coordination",
        "canonical_agent_type": "WORKBUDDY",
        "status": "ACTIVE",
        "parallel_routes_allowed": True,
        "active_slots_max": max_slots,
        "nested_parallelism": False,
        "same_task_multiple_active_slots_allowed": False,
        "worker_slots": slots,
    }


def _legacy(slot):
    return {
        "task_id": slot["task_id"],
        "route_epoch": slot["route_epoch"],
        "active_issue": slot["active_issue"],
        "pull_request": slot["pull_request"],
        "implementation_branch": slot["branch"],
        "status": slot["status"],
        "execution_allowed": slot["execution_allowed"],
        "completion_signal": slot["completion_signal"],
    }


class WorkBuddyMultiSlotTests(unittest.TestCase):
    def _repo(self, slots, max_slots=2):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        _write_yaml(root, WORKBUDDY_REGISTRY, _registry(slots, max_slots=max_slots))
        for slot in slots:
            _materialize_slot_refs(root, slot)
        primary = [slot for slot in slots if slot.get("primary_compatibility_projection")]
        if primary:
            _write_yaml(root, LEGACY_WORKBUDDY_PROJECTION, _legacy(primary[0]))
        return tmp, root

    def test_disjoint_film_and_a_share_slots_are_parallel_eligible(self):
        film = _slot("WB-FILM", "FILM", 175, 532, "workbuddy/film", "tests/workbuddy/**", primary=True)
        ashare = _slot("WB-ASHARE", "ASHARE", 184, 553, "workbuddy/ashare", "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/W2-P0B/**")
        ashare["shared_read_resources"] = ["TDXQUANT_RUNTIME_READONLY"]
        ashare["real_data_surfaces"] = ["TDXQUANT_HISTORICAL_PUBLIC_SAMPLE"]
        tmp, root = self._repo([film, ashare])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertEqual(report["structural_check"], "PASS", report["errors"])
        self.assertEqual(len([slot for slot in load_workbuddy_slots(root) if slot.execution_allowed]), 2)

    def test_same_write_surface_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "tools/workbuddy/**", primary=True)
        second = _slot("WB-B", "B", 2, 2, "workbuddy/b", "tools/workbuddy/subtree/**")
        tmp, root = self._repo([first, second])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("WORKBUDDY_EXECUTABLE_SLOT_COLLISION", codes)

    def test_mutable_runtime_resource_collision_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        second = _slot("WB-B", "B", 2, 2, "workbuddy/b", "path/b/**")
        first["mutable_runtime_resources"] = ["TDXQUANT_RUNTIME_CONFIG"]
        second["shared_read_resources"] = ["TDXQUANT_RUNTIME_CONFIG"]
        tmp, root = self._repo([first, second])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_EXECUTABLE_SLOT_COLLISION", {item["code"] for item in report["errors"]})

    def test_credential_surface_collision_is_o4(self):
        left = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        right = _slot("WB-B", "B", 2, 2, "workbuddy/b", "path/b/**")
        left["credential_surfaces"] = ["LICENSE_X"]
        right["credential_surfaces"] = ["LICENSE_X"]
        collision = classify_workbuddy_collision(normalize_workbuddy_slot(left), normalize_workbuddy_slot(right))
        self.assertEqual(collision["level"], "O4")

    def test_same_task_cannot_hold_two_slots(self):
        first = _slot("WB-A", "SAME", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        second = _slot("WB-B", "SAME", 1, 1, "workbuddy/a2", "path/b/**")
        tmp, root = self._repo([first, second])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_SAME_TASK_DOUBLE_SLOT", {item["code"] for item in report["errors"]})

    def test_capacity_limit_is_enforced(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        second = _slot("WB-B", "B", 2, 2, "workbuddy/b", "path/b/**")
        tmp, root = self._repo([first, second], max_slots=1)
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_ACTIVE_SLOT_CAPACITY_EXCEEDED", {item["code"] for item in report["errors"]})

    def test_legacy_projection_drift_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        legacy = _legacy(first)
        legacy["route_epoch"] = 999
        _write_yaml(root, LEGACY_WORKBUDDY_PROJECTION, legacy)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_COMPATIBILITY_PROJECTION_DRIFT", {item["code"] for item in report["errors"]})

    def test_bound_lease_identity_drift_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        lease = _bound_doc(first, branch_key="implementation_branch")
        lease["route_epoch"] = 999
        _write_yaml(root, first["task_lease"], lease)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_BOUND_REF_IDENTITY_DRIFT", {item["code"] for item in report["errors"]})

    def test_registry_cannot_grant_trade_authority(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        first["order_or_trade_authority"] = True
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_SLOT_TRADE_AUTHORITY_FORBIDDEN", {item["code"] for item in report["errors"]})


if __name__ == "__main__":
    unittest.main()
