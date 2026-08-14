from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lane_claims import validate_claims  # noqa: E402


class LaneClaimTests(unittest.TestCase):
    def _write_yaml(self, root: Path, relpath: str, payload: dict) -> None:
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    def _repo(self, *, stale_epoch: bool = False, proposal_escape: bool = False, proposal_reads_runtime: bool = False) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        registry = {
            "program_lanes": [
                {"lane_id": "A"},
                {"lane_id": "B"},
                {"lane_id": "C"},
            ]
        }
        self._write_yaml(root, "coordination/ACTIVE-PROGRAM-LANES.yaml", registry)
        self._write_yaml(
            root,
            "coordination/ACTIVE-CODEX-TASK.yaml",
            {
                "task_id": "C1",
                "route_epoch": 5,
                "active_issue": 10,
                "implementation_pr": 11,
                "implementation_branch": "codex/c",
                "status": "READY",
                "execution_allowed": True,
            },
        )
        self._write_yaml(
            root,
            "coordination/ACTIVE-QCLAW-TASK.yaml",
            {"task_id": "Q", "route_epoch": 1, "status": "PAUSED", "execution_allowed": False},
        )
        self._write_yaml(
            root,
            "coordination/ACTIVE-WORKBUDDY-TASK.yaml",
            {"task_id": "W", "route_epoch": 1, "status": "PAUSED", "execution_allowed": False},
        )
        claims = {
            "claims_id": "TEST",
            "proposal_roots": {"A": "proposal/A", "B": "proposal/B"},
            "claims": [
                {
                    "lane_id": "C",
                    "claim_state": "ACTIVE_IMPLEMENTATION",
                    "execution_agent": "CODEX",
                    "route_binding": {
                        "task_id": "C1",
                        "route_epoch": 4 if stale_epoch else 5,
                        "issue": 10,
                        "pr": 11,
                        "branch": "codex/c",
                    },
                    "write_paths": ["runtime/context.py"],
                    "read_paths": [],
                    "interfaces": [{"name": "Context/v1", "mode": "write", "frozen": False}],
                    "read_domains": ["W3"],
                    "write_domains": ["W3_RUNTIME"],
                    "authority_claims": ["W3_RUNTIME_IMPL"],
                },
                {
                    "lane_id": "A",
                    "claim_state": "HELD_PROPOSAL_ONLY",
                    "execution_agent": None,
                    "route_binding": None,
                    "safe_start_after_foundation": {"runtime_write_allowed": False, "implementation_route_allowed": False},
                    "write_paths": ["runtime/escape.py" if proposal_escape else "proposal/A"],
                    "read_paths": ["runtime/context.py"] if proposal_reads_runtime else ["docs/harness.md"],
                    "interfaces": [],
                    "read_domains": ["W8"],
                    "write_domains": [],
                    "authority_claims": [],
                },
                {
                    "lane_id": "B",
                    "claim_state": "HELD_PROPOSAL_ONLY",
                    "execution_agent": None,
                    "route_binding": None,
                    "safe_start_after_foundation": {"runtime_write_allowed": False, "implementation_route_allowed": False},
                    "write_paths": ["proposal/B"],
                    "read_paths": ["docs/trading.md"],
                    "interfaces": [],
                    "read_domains": ["W2", "W3"],
                    "write_domains": [],
                    "authority_claims": [],
                },
            ],
        }
        self._write_yaml(root, "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml", claims)
        return root

    def test_valid_active_route_and_isolated_proposals_are_release_candidate(self) -> None:
        report = validate_claims(self._repo())
        self.assertEqual(report["claim_structural_check"], "PASS")
        self.assertEqual(report["proposal_only_candidate"], "ELIGIBLE_FOR_GPT_RELEASE_DECISION")

    def test_stale_route_epoch_fails_closed(self) -> None:
        report = validate_claims(self._repo(stale_epoch=True))
        self.assertEqual(report["claim_structural_check"], "FAIL")
        self.assertTrue(any(item["code"] == "ACTIVE_CLAIM_ROUTE_STALE" for item in report["errors"]))

    def test_proposal_write_outside_isolated_root_fails(self) -> None:
        report = validate_claims(self._repo(proposal_escape=True))
        self.assertEqual(report["claim_structural_check"], "FAIL")
        self.assertTrue(any(item["code"] == "PROPOSAL_WRITE_OUTSIDE_ROOT" for item in report["errors"]))

    def test_proposal_read_against_mutating_runtime_is_not_release_candidate(self) -> None:
        report = validate_claims(self._repo(proposal_reads_runtime=True))
        self.assertEqual(report["claim_structural_check"], "PASS")
        self.assertEqual(report["proposal_only_candidate"], "NOT_READY")
        self.assertTrue(any(item["level"] == "O3" for item in report["proposal_only_collision_blockers"]))


if __name__ == "__main__":
    unittest.main()
