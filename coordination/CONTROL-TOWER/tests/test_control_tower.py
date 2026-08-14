from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from control_tower import (  # noqa: E402
    classify_collision,
    normalize_route,
    replace_projection_block,
    route_witness,
    verify_route_witness,
)


class CollisionTests(unittest.TestCase):
    def test_o4_authority_collision_fails_closed(self) -> None:
        left = {"authority_claims": ["W3_KNOWLEDGE_CANONICAL"]}
        right = {"authority_claims": ["W3_KNOWLEDGE_CANONICAL"]}
        self.assertEqual(classify_collision(left, right)["level"], "O4")

    def test_o3_mutable_interface(self) -> None:
        left = {"interfaces": [{"name": "ContextBundle/v1", "mode": "write", "frozen": False}]}
        right = {"interfaces": [{"name": "ContextBundle/v1", "mode": "read", "frozen": False}]}
        self.assertEqual(classify_collision(left, right)["level"], "O3")

    def test_o2_frozen_shared_contract(self) -> None:
        left = {"interfaces": [{"name": "EvidenceQuery/v1", "mode": "write", "frozen": True}]}
        right = {"interfaces": [{"name": "EvidenceQuery/v1", "mode": "read", "frozen": True}]}
        self.assertEqual(classify_collision(left, right)["level"], "O2")

    def test_o1_read_read_does_not_overblock(self) -> None:
        left = {"read_domains": ["W3"]}
        right = {"read_domains": ["W3"]}
        self.assertEqual(classify_collision(left, right)["level"], "O1")

    def test_o0_unrelated_work(self) -> None:
        left = {"read_domains": ["W2"], "write_paths": ["a/one"]}
        right = {"read_domains": ["W8"], "write_paths": ["b/two"]}
        self.assertEqual(classify_collision(left, right)["level"], "O0")

    def test_path_write_read_is_o3(self) -> None:
        left = {"write_paths": ["coordination/shared"]}
        right = {"read_paths": ["coordination/shared/schema.yaml"]}
        self.assertEqual(classify_collision(left, right)["level"], "O3")


class WitnessTests(unittest.TestCase):
    def test_route_epoch_change_invalidates_commit_witness(self) -> None:
        route = normalize_route(
            "CODEX",
            {
                "task_id": "T1",
                "route_epoch": 1,
                "active_issue": 1,
                "implementation_pr": 2,
                "implementation_branch": "x",
                "status": "READY",
                "execution_allowed": True,
                "completion_signal": "DONE1",
            },
        )
        witness = route_witness(route)
        newer = normalize_route(
            "CODEX",
            {
                "task_id": "T2",
                "route_epoch": 2,
                "active_issue": 3,
                "implementation_pr": 4,
                "implementation_branch": "y",
                "status": "READY",
                "execution_allowed": True,
                "completion_signal": "DONE2",
            },
        )
        self.assertFalse(verify_route_witness(witness, newer))

    def test_same_route_keeps_witness_fresh(self) -> None:
        data = {"task_id": "T1", "route_epoch": 1, "status": "READY", "execution_allowed": True}
        route = normalize_route("QCLAW", data)
        self.assertTrue(verify_route_witness(route_witness(route), normalize_route("QCLAW", data)))


class NormalizationTests(unittest.TestCase):
    def test_qclaw_active_pull_request_is_normalized(self) -> None:
        route = normalize_route(
            "QCLAW",
            {
                "task_id": "Q1",
                "route_epoch": 60,
                "active_issue": 296,
                "active_pull_request": 304,
                "planned_branch": "qclaw/x",
                "status": "PAUSED",
                "execution_allowed": False,
            },
        )
        self.assertEqual(route.pr, 304)
        self.assertEqual(route.branch, "qclaw/x")

    def test_workbuddy_frozen_branch_is_normalized(self) -> None:
        route = normalize_route(
            "WORKBUDDY",
            {
                "task_id": "W1",
                "route_epoch": 15,
                "active_issue": 89,
                "pull_request": 97,
                "frozen_branch": "workbuddy/x",
                "status": "PAUSED_COMPUTE_UNAVAILABLE",
                "execution_allowed": False,
            },
        )
        self.assertEqual(route.pr, 97)
        self.assertEqual(route.branch, "workbuddy/x")


class ProjectionTests(unittest.TestCase):
    def test_insert_projection_after_heading(self) -> None:
        original = "# Tower\n\nStatic text\n"
        block = "<!-- CONTROL_TOWER_AUTOGEN:START -->\nX\n<!-- CONTROL_TOWER_AUTOGEN:END -->"
        updated = replace_projection_block(original, block)
        self.assertTrue(updated.startswith("# Tower\n\n<!-- CONTROL_TOWER_AUTOGEN:START -->"))
        self.assertIn("Static text", updated)

    def test_replace_projection_is_idempotent(self) -> None:
        first = "<!-- CONTROL_TOWER_AUTOGEN:START -->\nA\n<!-- CONTROL_TOWER_AUTOGEN:END -->"
        second = "<!-- CONTROL_TOWER_AUTOGEN:START -->\nB\n<!-- CONTROL_TOWER_AUTOGEN:END -->"
        text = "# Tower\n\n" + first + "\n\nStatic"
        once = replace_projection_block(text, second)
        twice = replace_projection_block(once, second)
        self.assertEqual(once, twice)
        self.assertNotIn("\nA\n", once)


if __name__ == "__main__":
    unittest.main()
