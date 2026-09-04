from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workbuddy_slots import (  # noqa: E402
    FORBIDDEN_AUTHORITY_FIELDS,
    LEGACY_WORKBUDDY_PROJECTION,
    WORKBUDDY_REGISTRY,
    classify_workbuddy_collision,
    load_workbuddy_slots,
    normalize_workbuddy_slot,
    validate_workbuddy_slots,
    workbuddy_slot_is_executable,
)


def _write_yaml(root: Path, relpath: str, payload) -> None:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _slot(
    slot_id: str,
    task_id: str,
    epoch: int,
    issue: int,
    branch: str,
    write_path: str,
    *,
    primary: bool = False,
):
    base = f"coordination/test/{slot_id}"
    slot = {
        "worker_slot_id": slot_id,
        "agent_type": "WORKBUDDY",
        "executor_role": "WORKBUDDY_LOCAL_EXECUTOR",
        "task_id": task_id,
        "route_epoch": epoch,
        "active_issue": issue,
        "source_issue": issue,
        "pull_request": None,
        "branch": branch,
        "status": "READY",
        "execution_allowed": True,
        "activation_state": "ACTIVE",
        "closure_state": None,
        "mode": "bounded_test",
        "canonical_route": f"{base}/ROUTE.yaml",
        "work_claim": f"{base}/CLAIM.yaml",
        "task_lease": f"{base}/LEASE.yaml",
        "executor_reservation": f"{base}/RESERVATION.yaml",
        "prewrite_snapshot": f"{base}/SNAPSHOT.yaml",
        "executable_batch": f"{base}/BATCH.json",
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
        "primary_compatibility_projection": primary,
        "provenance": {"test": True},
    }
    for field in FORBIDDEN_AUTHORITY_FIELDS:
        slot[field] = False
    return slot


def _materialize_slot_refs(root: Path, slot: dict) -> None:
    route = {
        "task_id": slot["task_id"],
        "route_epoch": slot["route_epoch"],
        "active_issue": slot["active_issue"],
        "target_agent": "WORKBUDDY",
        "status": "READY",
        "execution_allowed": True,
        "release_state": "ACTIVE_READBACK_CONFIRMED",
        "execution": {
            "implementation_branch": slot["branch"],
            "executable_batch": slot["executable_batch"],
        },
        "bindings": {
            "work_claim": slot["work_claim"],
            "task_lease": slot["task_lease"],
            "executor_reservation": slot["executor_reservation"],
            "prewrite_snapshot": slot["prewrite_snapshot"],
        },
    }
    if slot["primary_compatibility_projection"]:
        route["bindings"]["active_task"] = LEGACY_WORKBUDDY_PROJECTION

    claim = {
        "task_id": slot["task_id"],
        "route_epoch": slot["route_epoch"],
        "active_issue": slot["active_issue"],
        "agent": "WORKBUDDY",
        "branch": slot["branch"],
        "claim_state": "ACTIVE",
        "status_observed": "READY",
        "execution_allowed_observed": True,
    }

    freshness = {
        "route": slot["canonical_route"],
        "work_claim": slot["work_claim"],
        "executor_reservation": slot["executor_reservation"],
        "prewrite_snapshot": slot["prewrite_snapshot"],
        "executable_batch": slot["executable_batch"],
    }
    if slot["primary_compatibility_projection"]:
        freshness["active_task"] = LEGACY_WORKBUDDY_PROJECTION
    else:
        freshness["active_registry"] = WORKBUDDY_REGISTRY

    lease = {
        "task_id": slot["task_id"],
        "route_epoch": slot["route_epoch"],
        "active_issue": slot["active_issue"],
        "agent_type": "WORKBUDDY",
        "implementation_branch": slot["branch"],
        "lease_state": "ACTIVE",
        "execution_allowed": True,
        "substantive_write_allowed": True,
        "freshness": freshness,
    }

    reservation = {
        "task_id": slot["task_id"],
        "route_epoch": slot["route_epoch"],
        "active_issue": slot["active_issue"],
        "executor_agent_type": "WORKBUDDY",
        "implementation_branch": slot["branch"],
        "reservation_state": "ACTIVE",
        "reservation_effect": {
            "execution_identity_reserved": True,
            "substantive_write_authorized_now": True,
        },
        "review_authority": False,
        "merge_authority": False,
    }

    snapshot = {
        "task_id": slot["task_id"],
        "route_epoch": slot["route_epoch"],
        "active_issue": slot["active_issue"],
        "ordered_batch": {"executable_ref": slot["executable_batch"]},
        "activation_gate": {
            "snapshot_precedes_workbuddy_branch": True,
            "requires_post_branch_fresh_readback": True,
            "activation_commit_required": True,
        },
    }

    batch = {
        "authority": "CANONICAL_BOUND_BATCH_EXECUTABLE",
        "route_authority": {
            "execution_allowed": True,
            "task_id": slot["task_id"],
            "active_issue": slot["active_issue"],
            "route_epoch": slot["route_epoch"],
            "route_ref": slot["canonical_route"],
            "claim_ref": slot["work_claim"],
            "lease_ref": slot["task_lease"],
            "snapshot_ref": slot["prewrite_snapshot"],
        },
    }

    _write_yaml(root, slot["canonical_route"], route)
    _write_yaml(root, slot["work_claim"], claim)
    _write_yaml(root, slot["task_lease"], lease)
    _write_yaml(root, slot["executor_reservation"], reservation)
    _write_yaml(root, slot["prewrite_snapshot"], snapshot)
    _write_yaml(root, slot["executable_batch"], batch)


def _registry(slots, max_slots=2):
    primary = [slot for slot in slots if slot.get("primary_compatibility_projection")]
    primary_id = primary[0]["worker_slot_id"] if primary else "MISSING"
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
        "same_mutable_surface_writers_max": 1,
        "unknown_collision_disposition": "FAIL_CLOSED",
        "compatibility_projection": {
            "path": LEGACY_WORKBUDDY_PROJECTION,
            "mode": "PRIMARY_SLOT_COMPATIBILITY_PROJECTION",
            "canonical_authority_after_r579": False,
            "mismatch_disposition": "FAIL_CLOSED",
            "primary_slot_id": primary_id,
        },
        "worker_slots": slots,
        "migration_boundary": {
            "registry_only_does_not_release_new_slot_authority": True,
        },
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

    def _codes(self, report):
        return {item["code"] for item in report["errors"]}

    def test_disjoint_film_and_a_share_slots_are_parallel_eligible(self):
        film = _slot(
            "WB-FILM",
            "FILM",
            175,
            532,
            "workbuddy/film",
            "tests/workbuddy/**",
            primary=True,
        )
        ashare = _slot(
            "WB-ASHARE",
            "ASHARE",
            184,
            553,
            "workbuddy/ashare",
            "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/W2-P0B/**",
        )
        ashare["shared_read_resources"] = ["TDXQUANT_RUNTIME_READONLY"]
        ashare["real_data_surfaces"] = ["TDXQUANT_HISTORICAL_PUBLIC_SAMPLE"]
        tmp, root = self._repo([film, ashare])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertEqual(report["structural_check"], "PASS", report["errors"])
        executable = [slot for slot in load_workbuddy_slots(root) if workbuddy_slot_is_executable(slot)]
        self.assertEqual(len(executable), 2)

    def test_unknown_status_is_not_executable_and_fails_schema(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        first["status"] = "READYY"
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        slot = load_workbuddy_slots(root)[0]
        self.assertFalse(workbuddy_slot_is_executable(slot))
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_SLOT_STATUS_UNKNOWN", self._codes(report))

    def test_same_write_surface_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "tools/workbuddy/**", primary=True)
        second = _slot("WB-B", "B", 2, 2, "workbuddy/b", "tools/workbuddy/subtree/**")
        tmp, root = self._repo([first, second])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_EXECUTABLE_SLOT_COLLISION", self._codes(report))

    def test_same_branch_ownership_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/shared", "path/a/**", primary=True)
        second = _slot("WB-B", "B", 2, 2, "workbuddy/shared", "path/b/**")
        tmp, root = self._repo([first, second])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_EXECUTABLE_SLOT_COLLISION", self._codes(report))
        collision = classify_workbuddy_collision(
            normalize_workbuddy_slot(first), normalize_workbuddy_slot(second)
        )
        self.assertEqual(collision["reason"], "SAME_MUTABLE_BRANCH_OWNERSHIP")

    def test_mutable_runtime_resource_collision_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        second = _slot("WB-B", "B", 2, 2, "workbuddy/b", "path/b/**")
        first["mutable_runtime_resources"] = ["TDXQUANT_RUNTIME_CONFIG"]
        second["shared_read_resources"] = ["TDXQUANT_RUNTIME_CONFIG"]
        tmp, root = self._repo([first, second])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_EXECUTABLE_SLOT_COLLISION", self._codes(report))

    def test_credential_surface_collision_is_o4(self):
        left = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        right = _slot("WB-B", "B", 2, 2, "workbuddy/b", "path/b/**")
        left["credential_surfaces"] = ["LICENSE_X"]
        right["credential_surfaces"] = ["LICENSE_X"]
        collision = classify_workbuddy_collision(
            normalize_workbuddy_slot(left), normalize_workbuddy_slot(right)
        )
        self.assertEqual(collision["level"], "O4")

    def test_malformed_collision_scalar_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        first["write_paths"] = "shared/**"
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_COLLISION_FIELD_MALFORMED", self._codes(report))

    def test_malformed_collision_non_string_entry_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        first["real_data_surfaces"] = ["PUBLIC", {"bad": True}]
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_COLLISION_FIELD_MALFORMED", self._codes(report))

    def test_same_task_cannot_hold_two_slots(self):
        first = _slot("WB-A", "SAME", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        second = _slot("WB-B", "SAME", 1, 1, "workbuddy/b", "path/b/**")
        tmp, root = self._repo([first, second])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_SAME_TASK_DOUBLE_SLOT", self._codes(report))

    def test_caller_flags_cannot_enable_nested_parallelism(self):
        first = _slot("WB-A", "SAME", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        second = _slot("WB-B", "SAME", 1, 1, "workbuddy/b", "path/b/**")
        tmp, root = self._repo([first, second])
        self.addCleanup(tmp.cleanup)
        registry = _registry([first, second])
        registry["nested_parallelism"] = True
        registry["same_task_multiple_active_slots_allowed"] = True
        _write_yaml(root, WORKBUDDY_REGISTRY, registry)
        report = validate_workbuddy_slots(root)
        codes = self._codes(report)
        self.assertIn("WORKBUDDY_NESTED_PARALLELISM_UNAUTHORIZED", codes)
        self.assertIn("WORKBUDDY_SAME_TASK_OVERRIDE_FORBIDDEN", codes)
        self.assertIn("WORKBUDDY_SAME_TASK_DOUBLE_SLOT", codes)

    def test_capacity_limit_is_enforced(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        second = _slot("WB-B", "B", 2, 2, "workbuddy/b", "path/b/**")
        tmp, root = self._repo([first, second], max_slots=1)
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_ACTIVE_SLOT_CAPACITY_EXCEEDED", self._codes(report))

    def test_legacy_projection_drift_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        legacy = _legacy(first)
        legacy["route_epoch"] = 999
        _write_yaml(root, LEGACY_WORKBUDDY_PROJECTION, legacy)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_COMPATIBILITY_PROJECTION_DRIFT", self._codes(report))

    def test_compatibility_metadata_tamper_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        registry = _registry([first])
        registry["compatibility_projection"]["canonical_authority_after_r579"] = True
        _write_yaml(root, WORKBUDDY_REGISTRY, registry)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_COMPATIBILITY_METADATA_INVALID", self._codes(report))

    def test_bound_lease_identity_drift_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        lease = yaml.safe_load((root / first["task_lease"]).read_text(encoding="utf-8"))
        lease["route_epoch"] = 999
        _write_yaml(root, first["task_lease"], lease)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_BOUND_REF_IDENTITY_DRIFT", self._codes(report))

    def test_missing_bound_identity_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        claim = yaml.safe_load((root / first["work_claim"]).read_text(encoding="utf-8"))
        claim.pop("active_issue")
        _write_yaml(root, first["work_claim"], claim)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_BOUND_REF_IDENTITY_INCOMPLETE", self._codes(report))

    def test_released_lease_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        lease = yaml.safe_load((root / first["task_lease"]).read_text(encoding="utf-8"))
        lease["lease_state"] = "RELEASED"
        _write_yaml(root, first["task_lease"], lease)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_BOUND_REF_STATE_INVALID", self._codes(report))

    def test_disabled_claim_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        claim = yaml.safe_load((root / first["work_claim"]).read_text(encoding="utf-8"))
        claim["execution_allowed_observed"] = False
        _write_yaml(root, first["work_claim"], claim)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_BOUND_REF_STATE_INVALID", self._codes(report))

    def test_prewrite_snapshot_and_batch_chain_is_required(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        snapshot = yaml.safe_load((root / first["prewrite_snapshot"]).read_text(encoding="utf-8"))
        snapshot["ordered_batch"]["executable_ref"] = "coordination/wrong.json"
        _write_yaml(root, first["prewrite_snapshot"], snapshot)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_BOUND_REF_STATE_INVALID", self._codes(report))

    def test_executable_batch_route_chain_drift_fails_closed(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        batch = yaml.safe_load((root / first["executable_batch"]).read_text(encoding="utf-8"))
        batch["route_authority"]["lease_ref"] = "coordination/wrong.yaml"
        _write_yaml(root, first["executable_batch"], batch)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_BOUND_REF_STATE_INVALID", self._codes(report))

    def test_registry_cannot_grant_any_forbidden_authority(self):
        for field in FORBIDDEN_AUTHORITY_FIELDS:
            with self.subTest(field=field):
                first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
                first[field] = True
                tmp, root = self._repo([first])
                try:
                    report = validate_workbuddy_slots(root)
                    self.assertIn("WORKBUDDY_FORBIDDEN_AUTHORITY_MINT", self._codes(report))
                finally:
                    tmp.cleanup()

    def test_unknown_authority_like_field_is_rejected_by_closed_schema(self):
        first = _slot("WB-A", "A", 1, 1, "workbuddy/a", "path/a/**", primary=True)
        first["superuser_authority"] = True
        tmp, root = self._repo([first])
        self.addCleanup(tmp.cleanup)
        report = validate_workbuddy_slots(root)
        self.assertIn("WORKBUDDY_SLOT_UNKNOWN_FIELD", self._codes(report))


if __name__ == "__main__":
    unittest.main()
