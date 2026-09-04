from __future__ import annotations

import sys
import unittest
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_workbuddy_slots import resolve_selection_from_validated_report  # noqa: E402
from workbuddy_slot_selection import select_workbuddy_slot  # noqa: E402
from workbuddy_slots import normalize_workbuddy_slot  # noqa: E402


def _slot(slot_id: str, task_id: str, *, status="READY", allowed=True, active="ACTIVE"):
    raw = {
        "worker_slot_id": slot_id,
        "agent_type": "WORKBUDDY",
        "executor_role": "WORKBUDDY_LOCAL_EXECUTOR",
        "task_id": task_id,
        "route_epoch": 1,
        "active_issue": 1,
        "pull_request": None,
        "branch": f"workbuddy/{slot_id.lower()}",
        "status": status,
        "execution_allowed": allowed,
        "activation_state": active,
        "closure_state": None,
        "canonical_route": f"coordination/{slot_id}/route.yaml",
        "work_claim": f"coordination/{slot_id}/claim.yaml",
        "task_lease": f"coordination/{slot_id}/lease.yaml",
        "executor_reservation": f"coordination/{slot_id}/reservation.yaml",
        "prewrite_snapshot": f"coordination/{slot_id}/snapshot.yaml",
        "executable_batch": f"coordination/{slot_id}/batch.json",
        "completion_signal": f"{slot_id}_COMPLETE",
        "write_paths": [f"coordination/{slot_id}/**"],
        "read_paths": [],
        "interfaces": [],
        "read_domains": [],
        "write_domains": [],
        "authority_claims": [],
        "exclusive_resources": [],
        "shared_read_resources": [],
        "mutable_runtime_resources": [],
        "credential_surfaces": [],
        "real_data_surfaces": [],
        "order_or_trade_authority": False,
        "review_authority": False,
        "merge_authority": False,
        "acceptance_authority": False,
        "canonical_truth_authority": False,
        "canonical_knowledge_authority": False,
        "account_authority": False,
        "credential_authority": False,
        "broker_authority": False,
        "funds_authority": False,
        "position_authority": False,
        "primary_compatibility_projection": False,
    }
    return normalize_workbuddy_slot(raw)


class WorkBuddySlotSelectionTests(unittest.TestCase):
    def test_bare_selection_chooses_only_executable_slot(self):
        selection = select_workbuddy_slot([_slot("WB-A", "TASK-A")])
        self.assertEqual(selection.status, "SELECTED")
        self.assertEqual(selection.code, "SOLE_EXECUTABLE_WORKBUDDY_SLOT_SELECTED")
        self.assertEqual(selection.selected_worker_slot_id, "WB-A")
        self.assertFalse(selection.execution_authority_granted)
        self.assertFalse(selection.runtime_exclusivity_proven)

    def test_bare_selection_fails_closed_when_multiple_slots_execute(self):
        selection = select_workbuddy_slot([_slot("WB-A", "TASK-A"), _slot("WB-B", "TASK-B")])
        self.assertEqual(selection.status, "BLOCKED")
        self.assertEqual(selection.code, "AMBIGUOUS_WORKBUDDY_SLOT_SELECTION")
        self.assertIsNone(selection.selected_worker_slot_id)

    def test_exact_slot_selector_selects_only_requested_slot(self):
        selection = select_workbuddy_slot(
            [_slot("WB-A", "TASK-A"), _slot("WB-B", "TASK-B")],
            requested_worker_slot_id="WB-B",
        )
        self.assertEqual(selection.status, "SELECTED")
        self.assertEqual(selection.code, "EXPLICIT_WORKBUDDY_SLOT_SELECTED")
        self.assertEqual(selection.selected_worker_slot_id, "WB-B")

    def test_exact_task_selector_selects_unique_task(self):
        selection = select_workbuddy_slot(
            [_slot("WB-A", "TASK-A"), _slot("WB-B", "TASK-B")],
            requested_task_id="TASK-B",
        )
        self.assertEqual(selection.status, "SELECTED")
        self.assertEqual(selection.selected_worker_slot_id, "WB-B")

    def test_conflicting_slot_and_task_selectors_fail_closed(self):
        selection = select_workbuddy_slot(
            [_slot("WB-A", "TASK-A"), _slot("WB-B", "TASK-B")],
            requested_worker_slot_id="WB-A",
            requested_task_id="TASK-B",
        )
        self.assertEqual(selection.status, "BLOCKED")
        self.assertEqual(selection.code, "REQUESTED_WORKBUDDY_SLOT_NOT_EXECUTABLE_OR_NOT_FOUND")

    def test_requested_non_executable_slot_is_not_selected(self):
        selection = select_workbuddy_slot(
            [_slot("WB-A", "TASK-A", status="PAUSED", allowed=False), _slot("WB-B", "TASK-B")],
            requested_worker_slot_id="WB-A",
        )
        self.assertEqual(selection.status, "BLOCKED")
        self.assertEqual(selection.code, "REQUESTED_WORKBUDDY_SLOT_NOT_EXECUTABLE_OR_NOT_FOUND")

    def test_duplicate_task_selector_is_ambiguous(self):
        selection = select_workbuddy_slot(
            [_slot("WB-A", "TASK-X"), _slot("WB-B", "TASK-X")],
            requested_task_id="TASK-X",
        )
        self.assertEqual(selection.status, "BLOCKED")
        self.assertEqual(selection.code, "AMBIGUOUS_EXPLICIT_WORKBUDDY_SLOT_SELECTION")

    def test_no_executable_slot_is_blocked(self):
        selection = select_workbuddy_slot([_slot("WB-A", "TASK-A", status="PAUSED", allowed=False)])
        self.assertEqual(selection.status, "BLOCKED")
        self.assertEqual(selection.code, "NO_EXECUTABLE_WORKBUDDY_SLOT")

    def test_unknown_slot_selector_is_blocked(self):
        selection = select_workbuddy_slot([_slot("WB-A", "TASK-A")], requested_worker_slot_id="WB-Z")
        self.assertEqual(selection.status, "BLOCKED")
        self.assertEqual(selection.code, "REQUESTED_WORKBUDDY_SLOT_NOT_EXECUTABLE_OR_NOT_FOUND")

    def test_empty_selector_is_invalid(self):
        selection = select_workbuddy_slot([_slot("WB-A", "TASK-A")], requested_worker_slot_id="")
        self.assertEqual(selection.status, "BLOCKED")
        self.assertEqual(selection.code, "INVALID_WORKBUDDY_SLOT_SELECTOR")

    def test_cli_resolution_consumes_exact_validated_snapshot_only(self):
        report = {
            "structural_check": "PASS",
            "validated_registry_sha256": "snapshot-a",
            "slots": [asdict(_slot("WB-A", "TASK-A"))],
        }
        selection, exit_code = resolve_selection_from_validated_report(
            report,
            requested_worker_slot_id="WB-A",
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(selection["status"], "SELECTED")
        self.assertEqual(selection["selected_worker_slot_id"], "WB-A")
        self.assertFalse(selection["execution_authority_granted"])
        self.assertFalse(selection["runtime_exclusivity_proven"])

    def test_cli_resolution_rejects_malformed_validated_snapshot(self):
        report = {
            "structural_check": "PASS",
            "validated_registry_sha256": "snapshot-a",
            "slots": "not-a-list",
        }
        selection, exit_code = resolve_selection_from_validated_report(report)
        self.assertEqual(exit_code, 3)
        self.assertEqual(selection["status"], "BLOCKED")
        self.assertEqual(selection["code"], "VALIDATED_WORKBUDDY_SLOT_SNAPSHOT_MALFORMED")


if __name__ == "__main__":
    unittest.main()
