from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from authorization_witness import authorization_witness, verify_authorization_witness  # noqa: E402


class AuthorizationWitnessTests(unittest.TestCase):
    def _write(self, root: Path, relpath: str, payload: dict) -> None:
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    def _repo(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self._write(
            root,
            "coordination/ACTIVE-PROGRAM-LANES.yaml",
            {
                "current_user_release_policy": {"held_lanes": []},
                "portfolio_capacity_policy": {"codex_active_execution_routes_max": 1},
                "cross_lane_overlap_matrix": [],
                "program_lanes": [{"lane_id": "C", "desired_state": "ACTIVE"}],
            },
        )
        self._write(
            root,
            "coordination/ACTIVE-CODEX-TASK.yaml",
            {
                "task_id": "T1",
                "route_epoch": 7,
                "active_issue": 1,
                "implementation_pr": 2,
                "implementation_branch": "codex/c",
                "status": "READY",
                "execution_allowed": True,
            },
        )
        self._write(root, "coordination/ACTIVE-QCLAW-TASK.yaml", {"task_id": "Q", "route_epoch": 1, "status": "PAUSED", "execution_allowed": False})
        self._write(root, "coordination/ACTIVE-WORKBUDDY-TASK.yaml", {"task_id": "W", "route_epoch": 1, "status": "PAUSED", "execution_allowed": False})
        self._write(
            root,
            "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml",
            {
                "claims_id": "TEST",
                "proposal_roots": {},
                "claims": [
                    {
                        "lane_id": "C",
                        "claim_state": "ACTIVE_IMPLEMENTATION",
                        "execution_agent": "CODEX",
                        "route_binding": {"task_id": "T1", "route_epoch": 7, "issue": 1, "pr": 2, "branch": "codex/c"},
                        "write_paths": ["runtime/c.py"],
                        "read_paths": [],
                        "interfaces": [],
                        "read_domains": [],
                        "write_domains": ["W3_RUNTIME"],
                        "authority_claims": ["W3_RUNTIME_IMPL"],
                    }
                ],
            },
        )
        self._write(
            root,
            "coordination/CONTROL-TOWER/RELEASE-GATE.yaml",
            {
                "foundation_state": "SAFE_FOR_GPT_DRY_RUN",
                "lane_release_state": "HOLD_BY_USER",
                "automatic_lane_release": False,
                "passing_ci_does_not_release_lanes": True,
            },
        )
        return root

    def test_unchanged_authorization_remains_fresh(self) -> None:
        root = self._repo()
        witness = authorization_witness(root, "C")
        self.assertTrue(verify_authorization_witness(root, witness)["fresh"])

    def test_route_change_invalidates_full_authorization(self) -> None:
        root = self._repo()
        witness = authorization_witness(root, "C")
        self._write(
            root,
            "coordination/ACTIVE-CODEX-TASK.yaml",
            {
                "task_id": "T2",
                "route_epoch": 8,
                "active_issue": 3,
                "implementation_pr": 4,
                "implementation_branch": "codex/new",
                "status": "READY",
                "execution_allowed": True,
            },
        )
        report = verify_authorization_witness(root, witness)
        self.assertFalse(report["fresh"])
        self.assertEqual(report["reason"], "AUTHORIZATION_MATERIAL_CHANGED")

    def test_policy_change_invalidates_full_authorization(self) -> None:
        root = self._repo()
        witness = authorization_witness(root, "C")
        self._write(
            root,
            "coordination/ACTIVE-PROGRAM-LANES.yaml",
            {
                "current_user_release_policy": {"held_lanes": ["C"]},
                "portfolio_capacity_policy": {"codex_active_execution_routes_max": 1},
                "cross_lane_overlap_matrix": [],
                "program_lanes": [{"lane_id": "C", "desired_state": "PAUSED"}],
            },
        )
        self.assertFalse(verify_authorization_witness(root, witness)["fresh"])


if __name__ == "__main__":
    unittest.main()
