from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "coordinate_creative_executors",
    ROOT / "tools" / "coordinate_creative_executors.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
HEAD = "a" * 40


def active(agent: str, *, ready: bool) -> dict:
    payload = {
        "target_agent": agent,
        "task_id": f"{agent}-TASK" if ready else f"{agent}-PAUSED",
        "active_issue": 100 if ready else 99,
        "route_epoch": 10 if ready else 9,
        "status": "READY" if ready else "PAUSED_COMPUTE_UNAVAILABLE",
        "execution_allowed": ready,
    }
    if agent == "WORKBUDDY" and ready:
        payload["bound_source_exact_head"] = HEAD
    return payload


def baton() -> dict:
    return {
        "schema": "CreativeExecutorCoordinationBaton/v1",
        "authority": "NAVIGATION_ONLY_CANONICAL_ACTIVE_ROUTES_WIN",
        "source_checkpoint": {
            "exact_head": HEAD,
            "checkpoint_remote_ref": "refs/remotes/origin/codex/checkpoint-example",
        },
        "lanes": {
            "CODEX_CORE": {"write_surfaces": ["creative_runtime/**", "apps/cli/**"]},
            "WORKBUDDY_VERIFICATION": {"write_surfaces": []},
            "WORKBUDDY_SIMPLE": {
                "write_surfaces": ["tests/workbuddy/**", "tools/workbuddy/**"],
                "complexity_ceiling": "D1",
            },
        },
        "final_acceptance": "USER_TRIGGERED_GPT_CROSS_MODULE_REVIEW",
    }


class CreativeExecutorCoordinationTests(unittest.TestCase):
    def decide(self, *, codex=True, workbuddy=False, event="AUTO", payload=None):
        return MODULE.coordinate(
            payload or baton(),
            codex_active=active("CODEX", ready=codex),
            workbuddy_active=active("WORKBUDDY", ready=workbuddy),
            canonical_main="b" * 40,
            observed_checkpoint_head=HEAD,
            event=event,
        )

    def test_current_shape_keeps_codex_running_and_workbuddy_blocked(self) -> None:
        result = self.decide()
        self.assertEqual(result["phase"], "CODEX_RUNNING_WORKBUDDY_BLOCKED")
        self.assertTrue(result["authority"]["codex_ready"])
        self.assertFalse(result["authority"]["workbuddy_ready"])

    def test_two_ready_routes_enable_non_overlapping_parallel_work(self) -> None:
        result = self.decide(workbuddy=True)
        self.assertEqual(result["phase"], "PARALLEL_NON_OVERLAPPING_EXECUTION")
        self.assertIn("CORE_LANE", result["codex_action"])
        self.assertIn("FROZEN_HEAD", result["workbuddy_action"])

    def test_ready_workbuddy_bound_to_older_checkpoint_is_not_redirected(self) -> None:
        workbuddy = active("WORKBUDDY", ready=True)
        workbuddy["bound_source_exact_head"] = "d" * 40
        result = MODULE.coordinate(
            baton(),
            codex_active=active("CODEX", ready=True),
            workbuddy_active=workbuddy,
            canonical_main="b" * 40,
            observed_checkpoint_head=HEAD,
        )
        self.assertEqual(result["phase"], "PARALLEL_NON_OVERLAPPING_DIFFERENT_CHECKPOINT_EXECUTION")
        self.assertFalse(result["authority"]["workbuddy_checkpoint_matches_baton"])
        self.assertIn("ALREADY_BOUND_DIFFERENT_CHECKPOINT", result["workbuddy_action"])

    def test_nested_checkpoint_identity_is_parsed_from_active_projection(self) -> None:
        text = "status: READY\nsource_checkpoint:\n  exact_head: '" + HEAD + "'\n  baseline: '" + ("b" * 40) + "'\nnext: value\n"
        parsed = MODULE.parse_nested_scalars(text, "source_checkpoint")
        self.assertEqual(parsed["exact_head"], HEAD)

    def test_quota_low_hands_to_ready_workbuddy(self) -> None:
        result = self.decide(workbuddy=True, event="CODEX_QUOTA_LOW")
        self.assertEqual(result["phase"], "WORKBUDDY_ROUTE_READY")
        self.assertIn("IMMUTABLE_QUOTA_CHECKPOINT", result["codex_action"])
        self.assertIn("FIRST_READY", result["workbuddy_action"])

    def test_quota_low_without_workbuddy_route_fails_closed(self) -> None:
        result = self.decide(event="CODEX_QUOTA_LOW")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["phase"], "BLOCKED_PENDING_WORKBUDDY_ROUTE")

    def test_workbuddy_completion_returns_to_codex(self) -> None:
        result = self.decide(event="WORKBUDDY_BATCH_COMPLETE")
        self.assertEqual(result["phase"], "WORKBUDDY_RESULT_READY")
        self.assertIn("VALIDATE_WORKBUDDY_RETURN_PACKAGE", result["codex_action"])

    def test_sync_is_one_consolidated_closeout(self) -> None:
        result = self.decide(event="USER_SYNC")
        self.assertEqual(result["phase"], "CLOSEOUT_READY")
        self.assertIn("GPT_CROSS_MODULE_REVIEW", result["unique_next_action"])

    def test_stop_prohibits_new_claims(self) -> None:
        result = self.decide(event="USER_STOP")
        self.assertEqual(result["phase"], "PAUSED_BY_USER")
        self.assertIn("WITHOUT_CLAIMING_NEW_ITEM", result["workbuddy_action"])

    def test_overlapping_implementation_surfaces_are_rejected(self) -> None:
        payload = copy.deepcopy(baton())
        payload["lanes"]["WORKBUDDY_SIMPLE"]["write_surfaces"] = ["creative_runtime/tests/**"]
        with self.assertRaisesRegex(MODULE.CoordinationError, "single-writer overlap"):
            self.decide(payload=payload)

    def test_verification_lane_cannot_write(self) -> None:
        payload = copy.deepcopy(baton())
        payload["lanes"]["WORKBUDDY_VERIFICATION"]["write_surfaces"] = ["evidence/**"]
        with self.assertRaisesRegex(MODULE.CoordinationError, "must be read-only"):
            self.decide(payload=payload)

    def test_checkpoint_drift_is_rejected(self) -> None:
        with self.assertRaisesRegex(MODULE.CoordinationError, "checkpoint drift"):
            MODULE.coordinate(
                baton(),
                codex_active=active("CODEX", ready=True),
                workbuddy_active=active("WORKBUDDY", ready=True),
                canonical_main="b" * 40,
                observed_checkpoint_head="c" * 40,
            )


if __name__ == "__main__":
    unittest.main()
