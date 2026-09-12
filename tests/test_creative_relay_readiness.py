from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_creative_relay_readiness",
    ROOT / "tools" / "audit_creative_relay_readiness.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
HEAD = "a" * 40
BASE = "b" * 40
MAIN = "c" * 40
CHECKPOINT_REF = "refs/remotes/origin/codex/checkpoint-test"


def package(executable: bool) -> dict:
    route = {
        "status": "READY" if executable else "PAUSED",
        "execution_allowed": executable,
        "task_id": "WB-CIF-1" if executable else None,
        "active_issue": 900 if executable else None,
        "route_epoch": 200 if executable else None,
        "route_ref": "coordination/ROUTES/wb.yaml" if executable else None,
        "claim_ref": "coordination/PROGRAMS/wb/WORK-CLAIM.yaml" if executable else None,
        "lease_ref": "coordination/PROGRAMS/wb/TASK-LEASE.yaml" if executable else None,
        "snapshot_ref": "issuecomment-1" if executable else None,
    }
    return {
        "schema": "CreativeExecutorRelayPackage/v1",
        "package_id": "P1",
        "source": {
            "agent": "CODEX",
            "branch": "codex/example",
            "checkpoint_remote_ref": CHECKPOINT_REF,
            "baseline": BASE,
            "exact_head": HEAD,
            "pushed": True,
            "worktree_clean_at_checkpoint": True,
            "write_surfaces": ["creative_runtime/**"],
        },
        "target": {
            "agent": "WORKBUDDY",
            "proposed_branch": "workbuddy/example",
            "route_authority": route,
            "write_surfaces_after_future_route": ["tests/workbuddy/**"],
        },
        "relay_state": "WORKBUDDY_ROUTE_READY" if executable else "BLOCKED_PENDING_TARGET_ROUTE",
        "verification_plan": {
            "commands": [f"runner --expected-head {HEAD} --remote-ref {CHECKPOINT_REF}"],
            "receipt_semantics": {"independent_acceptance": False, "may_ready_or_merge": False},
        },
    }


def active_yaml(*, ready: bool = True, task_id: str = "WB-CIF-1") -> str:
    return (
        'target_agent: "WORKBUDDY"\n'
        f'task_id: "{task_id}"\n'
        "active_issue: 900\n"
        "route_epoch: 200\n"
        f'status: "{"READY" if ready else "PAUSED"}"\n'
        f'execution_allowed: {"true" if ready else "false"}\n'
        "nested:\n"
        "  status: SHOULD_BE_IGNORED\n"
    )


class RelayReadinessTests(unittest.TestCase):
    def _audit(self, payload: dict, active_text: str, checkpoint_head: str = HEAD):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package_path = root / "package.json"
            package_path.write_text(json.dumps(payload), encoding="utf-8")

            def fake_git(repo, *args):
                if args[:1] == ("show",):
                    return active_text
                if args == ("rev-parse", "origin/main"):
                    return MAIN
                if args == ("rev-parse", CHECKPOINT_REF):
                    return checkpoint_head
                raise AssertionError(args)

            with mock.patch.object(MODULE, "_git", side_effect=fake_git):
                return MODULE.audit_readiness(
                    repo=root,
                    main_ref="origin/main",
                    package_path=package_path,
                )

    def test_ready_route_and_checkpoint_pass(self) -> None:
        result = self._audit(package(True), active_yaml())
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["blockers"], [])

    def test_paused_canonical_route_blocks(self) -> None:
        result = self._audit(package(False), active_yaml(ready=False))
        codes = {item["code"] for item in result["blockers"]}
        self.assertIn("ACTIVE_WORKBUDDY_EXECUTION_DISABLED", codes)
        self.assertIn("RELAY_PACKAGE_NOT_BOUND_TO_EXECUTABLE_ROUTE", codes)

    def test_checkpoint_head_drift_blocks(self) -> None:
        result = self._audit(package(True), active_yaml(), checkpoint_head="d" * 40)
        self.assertIn("CHECKPOINT_REMOTE_HEAD_MISMATCH", {item["code"] for item in result["blockers"]})

    def test_active_and_package_route_identity_must_match(self) -> None:
        result = self._audit(package(True), active_yaml(task_id="OTHER"))
        self.assertIn("ROUTE_IDENTITY_MISMATCH", {item["code"] for item in result["blockers"]})

    def test_top_level_parser_ignores_nested_projection(self) -> None:
        parsed = MODULE.parse_top_level_scalars(active_yaml())
        self.assertEqual(parsed["status"], "READY")
        self.assertTrue(parsed["execution_allowed"])


if __name__ == "__main__":
    unittest.main()
