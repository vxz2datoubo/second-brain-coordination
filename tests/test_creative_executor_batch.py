from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "evaluate_creative_executor_batch",
    ROOT / "tools" / "evaluate_creative_executor_batch.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def batch(*, executable: bool = True) -> dict:
    route = {
        "execution_allowed": executable,
        "task_id": "WB-CIF-200" if executable else None,
        "active_issue": 900 if executable else None,
        "route_epoch": 200 if executable else None,
        "route_ref": "coordination/ROUTES/wb.yaml" if executable else None,
        "claim_ref": "coordination/PROGRAMS/wb/WORK-CLAIM.yaml" if executable else None,
        "lease_ref": "coordination/PROGRAMS/wb/TASK-LEASE.yaml" if executable else None,
        "snapshot_ref": "issuecomment-1" if executable else None,
    }
    return {
        "schema": "CreativeExecutorWorkBatch/v1",
        "batch_id": "B1",
        "source_checkpoint": {
            "branch": "codex/example",
            "exact_head": "a" * 40,
            "checkpoint_remote_ref": "refs/remotes/origin/codex/checkpoint-example",
        },
        "route_authority": route,
        "codex_retained_write_surfaces": ["creative_runtime/**", "apps/cli/**"],
        "items": [
            {
                "item_id": "WB-V1",
                "owner": "WORKBUDDY",
                "kind": "CLEAN_REPRODUCTION",
                "status": "PLANNED",
                "complexity": "D1",
                "depends_on": [],
                "write_paths": [],
                "acceptance_commands": [
                    "verify --expected-head "
                    + "a" * 40
                    + " --remote-ref refs/remotes/origin/codex/checkpoint-example"
                ],
                "architecture_change": False,
                "acceptance_oracle_change": False,
                "receipt_ref": None,
            },
            {
                "item_id": "WB-S1",
                "owner": "WORKBUDDY",
                "kind": "SIMPLE_IMPLEMENTATION",
                "status": "PLANNED",
                "complexity": "D1",
                "depends_on": ["WB-V1"],
                "write_paths": ["tests/workbuddy/**"],
                "acceptance_commands": ["python -m unittest tests.workbuddy"],
                "architecture_change": False,
                "acceptance_oracle_change": False,
                "receipt_ref": None,
            },
        ],
    }


class CreativeExecutorBatchTests(unittest.TestCase):
    def test_executable_batch_selects_first_ready_item(self) -> None:
        result = MODULE.evaluate_batch(batch())
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["ready_items"], ["WB-V1"])

    def test_disabled_route_fails_closed(self) -> None:
        result = MODULE.evaluate_batch(batch(executable=False))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["blockers"][0]["code"], "WORKBUDDY_ROUTE_NOT_EXECUTABLE")

    def test_completed_dependency_unlocks_next_item(self) -> None:
        payload = batch()
        payload["items"][0]["status"] = "COMPLETE"
        payload["items"][0]["receipt_ref"] = "evidence/WB-V1.json"
        result = MODULE.evaluate_batch(payload)
        self.assertEqual(result["ready_items"], ["WB-S1"])

    def test_all_complete_returns_to_codex(self) -> None:
        payload = batch()
        for item in payload["items"]:
            item["status"] = "COMPLETE"
            item["receipt_ref"] = f"evidence/{item['item_id']}.json"
        result = MODULE.evaluate_batch(payload)
        self.assertEqual(result["status"], "RETURN_TO_CODEX")

    def test_verification_item_cannot_write(self) -> None:
        payload = batch()
        payload["items"][0]["write_paths"] = ["tests/workbuddy/**"]
        with self.assertRaisesRegex(MODULE.BatchValidationError, "cannot declare write paths"):
            MODULE.evaluate_batch(payload)

    def test_simple_work_cannot_overlap_codex(self) -> None:
        payload = batch()
        payload["items"][1]["write_paths"] = ["creative_runtime/**"]
        with self.assertRaisesRegex(MODULE.BatchValidationError, "single-writer overlap"):
            MODULE.evaluate_batch(payload)

    def test_workbuddy_cannot_take_architecture_decision(self) -> None:
        payload = batch()
        payload["items"][1]["architecture_change"] = True
        with self.assertRaisesRegex(MODULE.BatchValidationError, "reserved Codex decision"):
            MODULE.evaluate_batch(payload)

    def test_workbuddy_implementation_ceiling_is_d1(self) -> None:
        payload = batch()
        payload["items"][1]["complexity"] = "D2"
        with self.assertRaisesRegex(MODULE.BatchValidationError, "complexity ceiling"):
            MODULE.evaluate_batch(payload)

    def test_dependency_cycle_is_rejected(self) -> None:
        payload = batch()
        payload["items"][0]["depends_on"] = ["WB-S1"]
        with self.assertRaisesRegex(MODULE.BatchValidationError, "dependency cycle"):
            MODULE.evaluate_batch(payload)

    def test_complete_item_requires_receipt(self) -> None:
        payload = batch()
        payload["items"][0]["status"] = "COMPLETE"
        with self.assertRaisesRegex(MODULE.BatchValidationError, "requires receipt_ref"):
            MODULE.evaluate_batch(payload)

    def test_clean_reproduction_must_bind_checkpoint_identity(self) -> None:
        payload = batch()
        payload["items"][0]["acceptance_commands"] = ["python -m unittest"]
        with self.assertRaisesRegex(MODULE.BatchValidationError, "bind the declared exact head"):
            MODULE.evaluate_batch(payload)

    def test_secret_like_command_is_rejected(self) -> None:
        payload = batch()
        payload["items"][1]["acceptance_commands"] = ["runner --token exposed"]
        with self.assertRaisesRegex(MODULE.BatchValidationError, "secret material"):
            MODULE.evaluate_batch(payload)


if __name__ == "__main__":
    unittest.main()
