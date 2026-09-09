from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "coordination" / "CONTROL-TOWER"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


slots = _load("workbuddy_slots", CONTROL / "workbuddy_slots.py")
selection = _load("workbuddy_slot_selection", CONTROL / "workbuddy_slot_selection.py")

SHA = "a" * 40
DIGEST = "sha256:" + "b" * 64
PATH_DIGEST = "c" * 64


def slot(task: str, slot_id: str, *, state: str = "DECLARED", main: str = SHA, legacy=False):
    return {
        "canonical_main_sha": main,
        "worker_slot_id": slot_id,
        "task_id": task,
        "logical_state": state,
        "authority_chain_receipt_digest": DIGEST,
        "writer_lease_identity": "LEASE-ID-" + task,
        "legacy_default": legacy,
    }


def resource_lease(*, slot_id="WB-SLOT-A", executor="EXEC-1", run="RUN-1", generation=4, current=4,
                   fencing="FENCE-4", current_fencing="FENCE-4", superseded=False):
    return {
        "resource_lease_id": "RES-CPU-1",
        "resource_type": "CPU_THREAD_TOKEN",
        "holder_executor_id": executor,
        "worker_slot_id": slot_id,
        "run_id": run,
        "requested_quantity": 1,
        "granted_quantity": 1,
        "unit": "logical_thread",
        "generation": generation,
        "current_generation": current,
        "lease_state": "ACQUIRED",
        "superseded": superseded,
        "scheduler_admission_receipt_digest": "d" * 64,
        "authority_graph_digest": "e" * 64,
        "exclusive_or_mutable": True,
        "fencing_token": fencing,
        "current_fencing_token": current_fencing,
    }


def runtime_envelope(**overrides):
    value = {
        "executor_id": "EXEC-1",
        "run_id": "RUN-1",
        "worker_slot_id": "WB-SLOT-A",
        "canonical_main_sha": SHA,
        "authority_chain_receipt_digest": DIGEST,
        "writer_lease_identity": "LEASE-ID-TASK-A",
        "worktree_id": "WT-EXEC-1-RUN-1",
        "worktree_path_digest": PATH_DIGEST,
        "acquired_resource_leases": [resource_lease()],
        "process_ownership_receipt": {
            "executor_id": "EXEC-1",
            "run_id": "RUN-1",
            "worker_slot_id": "WB-SLOT-A",
            "root_pid": 4242,
            "process_tree_digest": "f" * 64,
            "status": "PROVEN",
        },
        "carrier_teardown_capability": "PROVEN",
    }
    value.update(overrides)
    return value


class WorkBuddyMultiSlotSelectionTests(unittest.TestCase):
    def test_legal_multiple_slots_bare_selector_is_safe_ambiguity(self):
        result = selection.select_workbuddy_slot([
            slot("TASK-A", "WB-SLOT-A"),
            slot("TASK-B", "WB-SLOT-B"),
        ])
        self.assertEqual(result.status, selection.AMBIGUOUS)
        self.assertEqual(result.candidate_count, 2)
        self.assertFalse(result.process_start_authorized)

    def test_legal_multiple_slots_explicit_task_selector_succeeds(self):
        result = selection.select_workbuddy_slot([
            slot("TASK-A", "WB-SLOT-A"),
            slot("TASK-B", "WB-SLOT-B"),
        ], task_id="TASK-B")
        self.assertEqual(result.status, selection.SELECTED)
        self.assertEqual(result.selected_worker_slot_id, "WB-SLOT-B")
        self.assertTrue(result.explicit_selector_used)
        self.assertFalse(result.process_start_authorized)

    def test_explicit_worker_slot_selector_succeeds(self):
        result = selection.select_workbuddy_slot([
            slot("TASK-A", "WB-SLOT-A"),
            slot("TASK-B", "WB-SLOT-B"),
        ], worker_slot_id="WB-SLOT-A")
        self.assertEqual(result.status, selection.SELECTED)
        self.assertEqual(result.selected_task_id, "TASK-A")

    def test_conflicting_explicit_selectors_fail_closed(self):
        result = selection.select_workbuddy_slot([
            slot("TASK-A", "WB-SLOT-A"),
            slot("TASK-B", "WB-SLOT-B"),
        ], task_id="TASK-A", worker_slot_id="WB-SLOT-B")
        self.assertEqual(result.status, selection.CONFLICTING_SELECTOR)
        self.assertFalse(result.process_start_authorized)

    def test_unknown_or_typo_state_never_becomes_executable(self):
        result = selection.select_workbuddy_slot([
            slot("TASK-A", "WB-SLOT-A", state="RUNNIGN"),
        ])
        self.assertEqual(result.status, selection.NO_ELIGIBLE)

    def test_duplicate_worker_slot_identity_fails_closed(self):
        with self.assertRaises(selection.SlotSelectionError):
            selection.select_workbuddy_slot([
                slot("TASK-A", "WB-SLOT-X"),
                slot("TASK-B", "WB-SLOT-X"),
            ])

    def test_candidates_from_different_main_snapshots_fail_closed(self):
        with self.assertRaises(selection.SlotSelectionError):
            selection.select_workbuddy_slot([
                slot("TASK-A", "WB-SLOT-A", main="1" * 40),
                slot("TASK-B", "WB-SLOT-B", main="2" * 40),
            ])


class WorkBuddyRuntimeBindingTests(unittest.TestCase):
    def setUp(self):
        self.slot = slot("TASK-A", "WB-SLOT-A")

    def test_valid_structural_runtime_binding_still_cannot_start_process(self):
        result = selection.validate_runtime_binding(self.slot, runtime_envelope())
        self.assertEqual(result.status, selection.PROCESS_START_BLOCKED)
        self.assertFalse(result.process_start_authorized)
        self.assertIn("SEPARATE_PHYSICAL_CANARY_GATE_REQUIRED", result.blockers)
        self.assertEqual(result.acquired_resource_lease_ids, ("RES-CPU-1",))

    def test_cross_run_resource_lease_fails_closed(self):
        env = runtime_envelope(acquired_resource_leases=[resource_lease(run="RUN-OLD")])
        with self.assertRaises(selection.SlotSelectionError):
            selection.validate_runtime_binding(self.slot, env)

    def test_cross_executor_resource_lease_fails_closed(self):
        env = runtime_envelope(acquired_resource_leases=[resource_lease(executor="EXEC-OLD")])
        with self.assertRaises(selection.SlotSelectionError):
            selection.validate_runtime_binding(self.slot, env)

    def test_stale_resource_generation_fails_closed(self):
        env = runtime_envelope(acquired_resource_leases=[resource_lease(generation=3, current=4)])
        with self.assertRaises(selection.SlotSelectionError):
            selection.validate_runtime_binding(self.slot, env)

    def test_superseded_resource_lease_fails_closed(self):
        env = runtime_envelope(acquired_resource_leases=[resource_lease(superseded=True)])
        with self.assertRaises(selection.SlotSelectionError):
            selection.validate_runtime_binding(self.slot, env)

    def test_stale_fencing_token_fails_closed(self):
        env = runtime_envelope(acquired_resource_leases=[resource_lease(fencing="FENCE-3", current_fencing="FENCE-4")])
        with self.assertRaises(selection.SlotSelectionError):
            selection.validate_runtime_binding(self.slot, env)

    def test_missing_process_ownership_remains_blocking(self):
        env = runtime_envelope(process_ownership_receipt=None)
        result = selection.validate_runtime_binding(self.slot, env)
        self.assertIn("PROCESS_OWNERSHIP_NOT_PROVEN", result.blockers)
        self.assertFalse(result.process_start_authorized)

    def test_unknown_teardown_capability_remains_blocking(self):
        env = runtime_envelope(carrier_teardown_capability="UNKNOWN")
        result = selection.validate_runtime_binding(self.slot, env)
        self.assertIn("CARRIER_TEARDOWN_CAPABILITY_NOT_PROVEN", result.blockers)
        self.assertFalse(result.process_start_authorized)

    def test_empty_acquired_resource_set_remains_blocking(self):
        env = runtime_envelope(acquired_resource_leases=[])
        result = selection.validate_runtime_binding(self.slot, env)
        self.assertIn("NO_ACQUIRED_RESOURCE_LEASES_RECORDED", result.blockers)
        self.assertFalse(result.process_start_authorized)

    def test_caller_cannot_switch_process_start_authority_on(self):
        env = runtime_envelope(process_start_authorized=True, trusted=True, independent=True)
        result = selection.validate_runtime_binding(self.slot, env)
        self.assertFalse(result.process_start_authorized)
        self.assertEqual(result.status, selection.PROCESS_START_BLOCKED)

    def test_slot_authority_receipt_mismatch_fails_closed(self):
        env = runtime_envelope(authority_chain_receipt_digest="sha256:" + "0" * 64)
        with self.assertRaises(selection.SlotSelectionError):
            selection.validate_runtime_binding(self.slot, env)

    def test_writer_lease_identity_mismatch_fails_closed(self):
        env = runtime_envelope(writer_lease_identity="OTHER")
        with self.assertRaises(selection.SlotSelectionError):
            selection.validate_runtime_binding(self.slot, env)


class WorkBuddyProjectionInvariantTests(unittest.TestCase):
    def test_cached_reader_prevents_second_read_aba_influence(self):
        calls = []
        values = [b"FIRST", b"TRANSIENT", b"FIRST"]

        def changing_reader(path):
            calls.append(path)
            return values[min(len(calls) - 1, len(values) - 1)]

        read, cache = slots._cached_exact_sha_reader(changing_reader)
        self.assertEqual(read("coordination/a.yaml"), b"FIRST")
        self.assertEqual(read("coordination/a.yaml"), b"FIRST")
        self.assertEqual(calls, ["coordination/a.yaml"])
        self.assertEqual(cache["coordination/a.yaml"], b"FIRST")

    def test_stable_slot_id_is_derived_without_r175_constant(self):
        authority = {
            "control_plane_repository": "vxz2datoubo/second-brain-coordination",
            "execution_repository": "vxz2datoubo/second-brain-coordination",
            "project_id": "SECOND_BRAIN",
            "task_id": "TASK-X",
            "route_epoch": 901,
        }
        first = slots._stable_worker_slot_id(authority)
        second = slots._stable_worker_slot_id(dict(authority))
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("WB-SLOT-"))

    def test_registry_path_traversal_fails_closed(self):
        raw = b'{"schema":"UNIFIED_ACTIVE_TASK_INDEX_REGISTRY/v1","control_plane_repository":"vxz2datoubo/second-brain-coordination","registry_status":"ACTIVE","entries":[{"active_task_index_ref":"../evil.yaml","status":"REGISTERED","legacy_default":true}]}'
        with self.assertRaises(Exception):
            slots._parse_registry_metadata(raw)

    def test_duplicate_registry_refs_fail_closed(self):
        ref = "coordination/ACTIVE-WORKBUDDY-TASK.yaml"
        raw = ("{\"schema\":\"UNIFIED_ACTIVE_TASK_INDEX_REGISTRY/v1\","
               "\"control_plane_repository\":\"vxz2datoubo/second-brain-coordination\","
               "\"registry_status\":\"ACTIVE\",\"entries\":["
               f"{{\"active_task_index_ref\":\"{ref}\",\"status\":\"REGISTERED\",\"legacy_default\":true}},"
               f"{{\"active_task_index_ref\":\"{ref}\",\"status\":\"REGISTERED\",\"legacy_default\":false}}]}}"
              ).encode()
        with self.assertRaises(slots.WorkBuddySlotError):
            slots._parse_registry_metadata(raw)

    def test_legacy_projection_is_explicitly_non_authoritative_and_plural_aware(self):
        a = slots.WorkBuddySlot(
            schema=slots.SLOT_SCHEMA, canonical_main_sha=SHA,
            active_task_index_ref="coordination/ACTIVE-WORKBUDDY-TASK.yaml", legacy_default=True,
            worker_slot_id="WB-SLOT-A", project_id="P", task_id="TASK-A", route_epoch=1,
            execution_repository="repo", implementation_branch="a", exact_base_sha=SHA,
            collision_domain="C1", authority_chain_receipt_digest=DIGEST,
            writer_lease_identity="L1", authorized_paths=("x",), completion_signal="DONE-A",
            logical_state="DECLARED", declared_execution_allowed=True, declared_active=True,
            declared_blocked_by=None, process_start_status=slots.PROCESS_START_STATUS,
            worktree_identity_state="UNBOUND_UNTIL_RUNTIME_ADMISSION",
            process_ownership_state=slots.UNKNOWN_RUNTIME_EVIDENCE,
            carrier_teardown_capability=slots.UNKNOWN_RUNTIME_EVIDENCE,
        )
        b = slots.WorkBuddySlot(
            **{**a.__dict__, "active_task_index_ref":"coordination/EXECUTION/ACTIVE-B.yaml",
               "legacy_default":False, "worker_slot_id":"WB-SLOT-B", "task_id":"TASK-B",
               "route_epoch":2, "implementation_branch":"b", "collision_domain":"C2",
               "writer_lease_identity":"L2", "completion_signal":"DONE-B"}
        )
        slot_set = slots.WorkBuddySlotSet(
            schema=slots.PROJECTION_SCHEMA, canonical_main_sha=SHA,
            registry_ref="coordination/EXECUTION/ACTIVE-TASK-INDEX-REGISTRY.json",
            registry_digest=DIGEST, legacy_default_ref="coordination/ACTIVE-WORKBUDDY-TASK.yaml",
            slots=(a,b), process_start_authorized=False, physical_parallelism_proven=False,
        )
        projection = slots.compatibility_legacy_projection(slot_set)
        self.assertFalse(projection["projection_is_authority"])
        self.assertEqual(projection["observed_workbuddy_slot_count"], 2)
        self.assertTrue(projection["explicit_selection_required_when_multiple"])

    def test_stage2_source_does_not_hardcode_r175_or_create_second_registry(self):
        source = (CONTROL / "workbuddy_slots.py").read_text(encoding="utf-8")
        selector = (CONTROL / "workbuddy_slot_selection.py").read_text(encoding="utf-8")
        self.assertNotIn("WORKBUDDY-R175", source)
        self.assertNotIn("WORKBUDDY-R175", selector)
        self.assertNotIn("ACTIVE-WORKBUDDY-TASKS.yaml", source)
        self.assertNotIn("ACTIVE-WORKBUDDY-TASKS.yaml", selector)

    def test_projection_module_never_reads_mutable_authority_with_path_read_text(self):
        source = (CONTROL / "workbuddy_slots.py").read_text(encoding="utf-8")
        self.assertNotIn(".read_text(", source)
        self.assertIn("_protected_open", source)
        self.assertIn("_terminal_remote_main_recheck", source)


if __name__ == "__main__":
    unittest.main()
