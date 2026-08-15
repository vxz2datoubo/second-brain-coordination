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
                    "resource_class": "LIGHT_TO_MEDIUM_IMPLEMENTATION",
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

    def _route_doc(self, root: Path) -> tuple[Path, dict]:
        path = root / "coordination/ACTIVE-CODEX-TASK.yaml"
        return path, yaml.safe_load(path.read_text(encoding="utf-8"))

    def _claim_c(self, root: Path) -> tuple[Path, dict, dict]:
        path = root / "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        claim = next(item for item in data["claims"] if item["lane_id"] == "C")
        return path, data, claim

    def _reserve_lane_c(self, root: Path, *, executable_route: bool = False, receipt: bool = True) -> None:
        route_path, route = self._route_doc(root)
        route["status"] = "PREPARED_AWAITING_POST_MERGE_RECONCILIATION"
        route["execution_allowed"] = executable_route
        route_path.write_text(yaml.safe_dump(route, sort_keys=False), encoding="utf-8")

        path, data, claim = self._claim_c(root)
        claim["claim_state"] = "RESERVED_IMPLEMENTATION_NON_EXECUTABLE"
        claim["resource_class"] = "LIGHT_TO_MEDIUM_IMPLEMENTATION_RESERVATION"
        claim["implementation_scope"] = {
            "global_reconciliation_receipt": "coordination/CONTROL-TOWER/GLOBAL-RECONCILIATION-RECEIPT-RX.yaml"
        } if receipt else {}
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def _close_lane_c(self, root: Path, *, violation: str | None = None) -> None:
        path, data, claim = self._claim_c(root)
        claim.update(
            {
                "claim_state": "CLOSED_NO_ACTIVE_IMPLEMENTATION",
                "execution_agent": None,
                "route_binding": None,
                "resource_class": "NO_ACTIVE_IMPLEMENTATION",
                "write_paths": [],
                "read_paths": [],
                "interfaces": [],
                "read_domains": [],
                "write_domains": [],
                "authority_claims": [],
                "closure_receipt": {"issue": 99, "merge_commit": "abc123"},
            }
        )
        if violation == "agent":
            claim["execution_agent"] = "CODEX"
        elif violation == "resource":
            claim["resource_class"] = "HEAVY_IMPLEMENTATION"
        elif violation == "route":
            claim["route_binding"] = {"task_id": "C1", "route_epoch": 5}
        elif violation == "surface":
            claim["write_paths"] = ["runtime/context.py"]
        elif violation == "receipt":
            claim["closure_receipt"] = None
        elif violation == "receipt_evidence":
            claim["closure_receipt"] = {"note": "closed because we say so"}
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def test_valid_active_route_and_isolated_proposals_are_release_candidate(self) -> None:
        report = validate_claims(self._repo())
        self.assertEqual(report["claim_structural_check"], "PASS")
        self.assertEqual(report["proposal_only_candidate"], "ELIGIBLE_FOR_GPT_RELEASE_DECISION")

    def test_active_claim_bound_to_non_executable_route_fails(self) -> None:
        root = self._repo()
        route_path, route = self._route_doc(root)
        route["execution_allowed"] = False
        route_path.write_text(yaml.safe_dump(route, sort_keys=False), encoding="utf-8")
        report = validate_claims(root)
        self.assertTrue(any(item["code"] == "ACTIVE_CLAIM_ROUTE_NOT_EXECUTABLE" for item in report["errors"]))

    def test_reserved_non_executable_claim_passes_and_keeps_surface_reserved(self) -> None:
        root = self._repo()
        self._reserve_lane_c(root)
        report = validate_claims(root)
        self.assertEqual(report["claim_structural_check"], "PASS")
        self.assertFalse(any(item["code"].startswith("RESERVED_CLAIM_") for item in report["errors"]))
        self.assertTrue(any("C" in item["pair"] for item in report["pairwise"]))

    def test_reserved_claim_must_not_bind_executable_route(self) -> None:
        root = self._repo()
        self._reserve_lane_c(root, executable_route=True)
        report = validate_claims(root)
        self.assertTrue(any(item["code"] == "RESERVED_CLAIM_ROUTE_EXECUTABLE" for item in report["errors"]))

    def test_reserved_claim_requires_global_reconciliation_receipt(self) -> None:
        root = self._repo()
        self._reserve_lane_c(root, receipt=False)
        report = validate_claims(root)
        self.assertTrue(any(item["code"] == "RESERVED_CLAIM_RECONCILIATION_RECEIPT_MISSING" for item in report["errors"]))

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

    def test_closed_lane_releases_execution_lease_and_keeps_proposals_valid(self) -> None:
        root = self._repo()
        self._close_lane_c(root)
        report = validate_claims(root)
        self.assertEqual(report["claim_structural_check"], "PASS")
        self.assertEqual(report["proposal_only_candidate"], "ELIGIBLE_FOR_GPT_RELEASE_DECISION")
        self.assertFalse(report["proposal_only_collision_blockers"])

    def test_closed_lane_with_execution_agent_fails(self) -> None:
        root = self._repo()
        self._close_lane_c(root, violation="agent")
        report = validate_claims(root)
        self.assertTrue(any(item["code"] == "CLOSED_CLAIM_HAS_EXECUTION_AGENT" for item in report["errors"]))

    def test_closed_lane_with_active_resource_class_fails(self) -> None:
        root = self._repo()
        self._close_lane_c(root, violation="resource")
        report = validate_claims(root)
        self.assertTrue(any(item["code"] == "CLOSED_CLAIM_RESOURCE_CLASS_INVALID" for item in report["errors"]))

    def test_closed_lane_with_route_binding_fails(self) -> None:
        root = self._repo()
        self._close_lane_c(root, violation="route")
        report = validate_claims(root)
        self.assertTrue(any(item["code"] == "CLOSED_CLAIM_HAS_ROUTE_BINDING" for item in report["errors"]))

    def test_closed_lane_with_active_surface_fails(self) -> None:
        root = self._repo()
        self._close_lane_c(root, violation="surface")
        report = validate_claims(root)
        self.assertTrue(any(item["code"] == "CLOSED_CLAIM_HAS_ACTIVE_SURFACE" for item in report["errors"]))

    def test_closed_lane_requires_closure_receipt(self) -> None:
        root = self._repo()
        self._close_lane_c(root, violation="receipt")
        report = validate_claims(root)
        self.assertTrue(any(item["code"] == "CLOSED_CLAIM_RECEIPT_MISSING" for item in report["errors"]))

    def test_closed_lane_receipt_requires_durable_evidence_reference(self) -> None:
        root = self._repo()
        self._close_lane_c(root, violation="receipt_evidence")
        report = validate_claims(root)
        self.assertTrue(any(item["code"] == "CLOSED_CLAIM_RECEIPT_EVIDENCE_MISSING" for item in report["errors"]))


if __name__ == "__main__":
    unittest.main()
