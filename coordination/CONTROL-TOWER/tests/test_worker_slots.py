from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from authorization_witness import authorization_witness, verify_authorization_witness  # noqa: E402
from control_tower import render_projection_block  # noqa: E402
from lane_claims import validate_claims  # noqa: E402
from worker_slots import load_worker_slots, validate_worker_slots  # noqa: E402

GPT = "GPT_ENGINEERING_WORKER"
REVIEWER = "GPT_INDEPENDENT_REVIEWER"


def _slot(
    slot_id: str = "SLOT-A",
    *,
    task_id: str = "GPT-T1",
    route_epoch: int = 144,
    issue: int = 406,
    pr: int | None = None,
    branch: str = "gpt/slot-a",
    execution_allowed: bool = True,
    status: str = "READY",
    write_paths: list[str] | None = None,
    authority_claims: list[str] | None = None,
    executor_role: str = GPT,
    model_id: str = "GPT-5.6 Sol",
    reviewer_role: str = REVIEWER,
    activation_state: str = "ACTIVE",
    closure_state: str | None = None,
) -> dict:
    return {
        "worker_slot_id": slot_id,
        "agent_type": GPT,
        "executor_role": executor_role,
        "model_id": model_id,
        "task_id": task_id,
        "route_epoch": route_epoch,
        "issue": issue,
        "pr": pr,
        "branch": branch,
        "status": status,
        "execution_allowed": execution_allowed,
        "write_paths": write_paths if write_paths is not None else ["runtime/a.py"],
        "read_paths": [],
        "interfaces": [],
        "read_domains": [],
        "write_domains": ["W2_RUNTIME"],
        "authority_claims": authority_claims if authority_claims is not None else ["W2_RUNTIME_IMPL"],
        "resource_class": "LIGHT_TO_MEDIUM_IMPLEMENTATION",
        "provenance": {"historical_executor": "CODEX", "historical_model_id": "GPT-5.6 Sol"},
        "reviewer_role": reviewer_role,
        "reviewer_separation": "EXECUTION_IDENTITY_NOT_ACCEPTANCE_AUTHORITY",
        "activation_state": activation_state,
        "closure_state": closure_state,
    }


def _active_claim(
    *,
    slot_id: str = "SLOT-A",
    task_id: str = "GPT-T1",
    route_epoch: int = 144,
    issue: int = 406,
    pr: int | None = None,
    branch: str = "gpt/slot-a",
    write_paths: list[str] | None = None,
    authority_claims: list[str] | None = None,
    omit_slot_id: bool = False,
) -> dict:
    binding: dict = {
        "task_id": task_id,
        "route_epoch": route_epoch,
        "issue": issue,
        "pr": pr,
        "branch": branch,
    }
    if not omit_slot_id:
        binding["worker_slot_id"] = slot_id
    claim = {
        "lane_id": "A",
        "claim_state": "ACTIVE_IMPLEMENTATION",
        "execution_agent": GPT,
        "resource_class": "LIGHT_TO_MEDIUM_IMPLEMENTATION",
        "route_binding": binding,
        "write_paths": write_paths if write_paths is not None else ["runtime/a.py"],
        "read_paths": [],
        "interfaces": [],
        "read_domains": [],
        "write_domains": ["W2_RUNTIME"],
        "authority_claims": authority_claims if authority_claims is not None else ["W2_RUNTIME_IMPL"],
    }
    if not omit_slot_id:
        claim["worker_slot_id"] = slot_id
    return claim


def _held_claim(lane_id: str, write_root: str, read_path: str = "docs/x.md") -> dict:
    return {
        "lane_id": lane_id,
        "claim_state": "HELD_PROPOSAL_ONLY",
        "execution_agent": None,
        "route_binding": None,
        "safe_start_after_foundation": {"runtime_write_allowed": False, "implementation_route_allowed": False},
        "write_paths": [write_root],
        "read_paths": [read_path],
        "interfaces": [],
        "read_domains": ["W8"],
        "write_domains": [],
        "authority_claims": [],
    }


def _closed_claim(lane_id: str) -> dict:
    return {
        "lane_id": lane_id,
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


class WorkerRepo:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def _write(self, relpath: str, payload: dict) -> None:
        path = self.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    def build(
        self,
        slots: list[dict],
        claim_a: dict | None = None,
        *,
        capacity: int = 2,
        include_gate: bool = False,
    ) -> Path:
        registry = {
            "program_lanes": [{"lane_id": "A"}, {"lane_id": "B"}, {"lane_id": "C"}],
            "portfolio_capacity_policy": {
                "codex_active_execution_routes_max": 1,
                "qclaw_active_execution_routes_max": 1,
                "workbuddy_active_execution_routes_max": 1,
                "gpt_engineering_worker_active_slots_max": capacity,
            },
            "current_user_release_policy": {"held_lanes": []},
            "cross_lane_overlap_matrix": [],
        }
        self._write("coordination/ACTIVE-PROGRAM-LANES.yaml", registry)
        self._write(
            "coordination/ACTIVE-CODEX-TASK.yaml",
            {"task_id": "C-DONE", "route_epoch": 1, "status": "DONE", "execution_allowed": False},
        )
        self._write(
            "coordination/ACTIVE-QCLAW-TASK.yaml",
            {"task_id": "Q", "route_epoch": 1, "status": "PAUSED", "execution_allowed": False},
        )
        self._write(
            "coordination/ACTIVE-WORKBUDDY-TASK.yaml",
            {"task_id": "W", "route_epoch": 1, "status": "PAUSED", "execution_allowed": False},
        )
        self._write(
            "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml",
            {"agent_type": GPT, "worker_slots": slots},
        )
        claims = [
            claim_a if claim_a is not None else _active_claim(),
            _held_claim("B", "proposal/B"),
            _closed_claim("C"),
        ]
        self._write(
            "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml",
            {"claims_id": "TEST", "proposal_roots": {"B": "proposal/B"}, "claims": claims},
        )
        if include_gate:
            self._write(
                "coordination/CONTROL-TOWER/RELEASE-GATE.yaml",
                {
                    "foundation_state": "SAFE_FOR_GPT_DRY_RUN",
                    "lane_release_state": "HOLD_BY_USER",
                    "automatic_lane_release": False,
                    "passing_ci_does_not_release_lanes": True,
                },
            )
        return self.root


class WorkerSlotRegistryTests(unittest.TestCase):
    def test_a_valid_slot_registry_passes(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()])
        report = validate_worker_slots(root)
        self.assertEqual(report["worker_slot_structural_check"], "PASS")
        self.assertEqual(len(load_worker_slots(root)), 1)

    def test_i_gpt_worker_impersonating_codex_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot(executor_role="CODEX")])
        report = validate_worker_slots(root)
        self.assertEqual(report["worker_slot_structural_check"], "FAIL")
        self.assertTrue(any(item["code"] == "WORKER_SLOT_IMPERSONATION" for item in report["errors"]))

    def test_self_review_slot_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot(reviewer_role=GPT)])
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_SELF_REVIEW" for item in report["errors"]))

    def test_j_two_slots_same_write_surface_fail(self) -> None:
        repo = WorkerRepo()
        root = repo.build(
            [_slot("SLOT-A", write_paths=["runtime/shared.py"]), _slot("SLOT-B", write_paths=["runtime/shared.py"], branch="gpt/slot-b")]
        )
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_COLLISION" for item in report["errors"]))

    def test_k_two_slots_same_authority_fail(self) -> None:
        repo = WorkerRepo()
        root = repo.build(
            [
                _slot("SLOT-A", authority_claims=["W3_CANONICAL"]),
                _slot("SLOT-B", authority_claims=["W3_CANONICAL"], branch="gpt/slot-b"),
            ]
        )
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_COLLISION" for item in report["errors"]))

    def test_l_two_slots_non_overlap_pass(self) -> None:
        repo = WorkerRepo()
        root = repo.build(
            [
                _slot("SLOT-A", write_paths=["runtime/a.py"], authority_claims=["W2_IMPL"]),
                _slot("SLOT-B", write_paths=["runtime/b.py"], authority_claims=["W8_IMPL"], branch="gpt/slot-b"),
            ]
        )
        report = validate_worker_slots(root)
        self.assertEqual(report["worker_slot_structural_check"], "PASS")
        self.assertEqual(report["active_executable_slots"], ["SLOT-A", "SLOT-B"])

    def test_m_same_slot_double_booked_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build(
            [_slot("SLOT-A", task_id="GPT-T1"), _slot("SLOT-A", task_id="GPT-T2")]
        )
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_DUPLICATE_ID" for item in report["errors"]))

    def test_n_silent_slot_overwrite_fails(self) -> None:
        # Same slot_id reappearing with a different task is a silent overwrite and must fail closed.
        repo = WorkerRepo()
        root = repo.build(
            [_slot("SLOT-A", task_id="GPT-T1"), _slot("SLOT-A", task_id="GPT-T1", route_epoch=145)]
        )
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_DUPLICATE_ID" for item in report["errors"]))

    def test_capacity_exceeded_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build(
            [
                _slot("SLOT-A", write_paths=["runtime/a.py"], authority_claims=["A_IMPL"]),
                _slot("SLOT-B", write_paths=["runtime/b.py"], authority_claims=["B_IMPL"], branch="gpt/slot-b"),
                _slot("SLOT-C", write_paths=["runtime/c.py"], authority_claims=["C_IMPL"], branch="gpt/slot-c"),
            ],
            capacity=2,
        )
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_CAPACITY_EXCEEDED" for item in report["errors"]))

    def test_r_released_slot_with_lease_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot("SLOT-A", activation_state="RELEASED", execution_allowed=True)])
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_CLOSED_HAS_LEASE" for item in report["errors"]))

    def test_s_closed_slot_tombstone_passes(self) -> None:
        repo = WorkerRepo()
        root = repo.build(
            [_slot("SLOT-A", activation_state="RELEASED", execution_allowed=False, status="DONE_HISTORICAL")]
        )
        report = validate_worker_slots(root)
        self.assertEqual(report["worker_slot_structural_check"], "PASS")
        self.assertEqual(report["active_executable_slots"], [])


class WorkerClaimTests(unittest.TestCase):
    def test_a_valid_slot_and_exact_claim_passes(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()])
        report = validate_claims(root)
        self.assertEqual(report["claim_structural_check"], "PASS")

    def test_b_active_claim_bound_to_non_executable_slot_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot(execution_allowed=False)])
        report = validate_claims(root)
        self.assertTrue(any(item["code"] == "ACTIVE_CLAIM_ROUTE_NOT_EXECUTABLE" for item in report["errors"]))

    def test_c_stale_task_id_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], claim_a=_active_claim(task_id="GPT-STALE"))
        self.assertTrue(any(item["code"] == "ACTIVE_CLAIM_ROUTE_STALE" for item in validate_claims(root)["errors"]))

    def test_d_stale_route_epoch_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], claim_a=_active_claim(route_epoch=143))
        self.assertTrue(any(item["code"] == "ACTIVE_CLAIM_ROUTE_STALE" for item in validate_claims(root)["errors"]))

    def test_e_stale_issue_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], claim_a=_active_claim(issue=999))
        self.assertTrue(any(item["code"] == "ACTIVE_CLAIM_ROUTE_STALE" for item in validate_claims(root)["errors"]))

    def test_f_stale_pr_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot(pr=401)], claim_a=_active_claim(pr=402))
        self.assertTrue(any(item["code"] == "ACTIVE_CLAIM_ROUTE_STALE" for item in validate_claims(root)["errors"]))

    def test_g_stale_branch_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], claim_a=_active_claim(branch="gpt/wrong"))
        self.assertTrue(any(item["code"] == "ACTIVE_CLAIM_ROUTE_STALE" for item in validate_claims(root)["errors"]))

    def test_h_stale_slot_identity_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot("SLOT-A")], claim_a=_active_claim(slot_id="SLOT-B"))
        report = validate_claims(root)
        self.assertTrue(any(item["code"] == "ACTIVE_CLAIM_WORKER_SLOT_UNKNOWN" for item in report["errors"]))

    def test_claim_without_slot_identity_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot("SLOT-A")], claim_a=_active_claim(omit_slot_id=True))
        report = validate_claims(root)
        self.assertTrue(any(item["code"] == "ACTIVE_CLAIM_WORKER_SLOT_MISSING" for item in report["errors"]))

    def test_t_existing_codex_claim_still_passes(self) -> None:
        # A CODEX active claim must remain valid alongside the GPT worker registry.
        repo = WorkerRepo()
        codex_claim = {
            "lane_id": "A",
            "claim_state": "ACTIVE_IMPLEMENTATION",
            "execution_agent": "CODEX",
            "resource_class": "LIGHT_TO_MEDIUM_IMPLEMENTATION",
            "route_binding": {
                "task_id": "C-DONE",
                "route_epoch": 1,
                "issue": None,
                "pr": None,
                "branch": "codex/x",
            },
            "write_paths": ["runtime/codex.py"],
            "read_paths": [],
            "interfaces": [],
            "read_domains": ["W3"],
            "write_domains": ["W3_RUNTIME"],
            "authority_claims": ["W3_RUNTIME_IMPL"],
        }
        # CODEX route must be executable for the active claim to pass.
        repo.build([_slot()], claim_a=codex_claim)
        self._rewrite_codex_executable(repo.root)
        report = validate_claims(repo.root)
        self.assertEqual(report["claim_structural_check"], "PASS")

    @staticmethod
    def _rewrite_codex_executable(root: Path) -> None:
        path = root / "coordination/ACTIVE-CODEX-TASK.yaml"
        path.write_text(
            yaml.safe_dump(
                {
                    "task_id": "C-DONE",
                    "route_epoch": 1,
                    "active_issue": None,
                    "implementation_pr": None,
                    "implementation_branch": "codex/x",
                    "status": "READY",
                    "execution_allowed": True,
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )


class WorkerWitnessTests(unittest.TestCase):
    def test_unchanged_worker_authorization_fresh(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], include_gate=True)
        witness = authorization_witness(root, "A")
        self.assertTrue(verify_authorization_witness(root, witness)["fresh"])

    def test_o_worker_route_change_invalidates_witness(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], include_gate=True)
        witness = authorization_witness(root, "A")
        repo.build([_slot(task_id="GPT-T2")], include_gate=True)
        self.assertFalse(verify_authorization_witness(root, witness)["fresh"])

    def test_slot_change_invalidates_witness(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot("SLOT-A")], include_gate=True)
        witness = authorization_witness(root, "A")
        repo.build([_slot("SLOT-A", branch="gpt/changed")], include_gate=True)
        self.assertFalse(verify_authorization_witness(root, witness)["fresh"])

    def test_p_peer_claim_change_invalidates_witness(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], include_gate=True)
        witness = authorization_witness(root, "A")
        # Change the peer (lane B) read surface to collide with runtime.
        repo.build([_slot()], include_gate=True)
        path = root / "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for claim in data["claims"]:
            if claim["lane_id"] == "B":
                claim["read_paths"] = ["runtime/a.py"]
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        self.assertFalse(verify_authorization_witness(root, witness)["fresh"])

    def test_q_release_policy_change_invalidates_witness(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], include_gate=True)
        witness = authorization_witness(root, "A")
        path = root / "coordination/ACTIVE-PROGRAM-LANES.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["current_user_release_policy"] = {"held_lanes": ["B"], "decision": "CHANGED"}
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        self.assertFalse(verify_authorization_witness(root, witness)["fresh"])


class ProjectionDeterminismTests(unittest.TestCase):
    def test_w_projection_generator_deterministic_and_idempotent(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()])
        first = render_projection_block(root)
        second = render_projection_block(root)
        self.assertEqual(first, second)
        self.assertIn("GPT Engineering Worker slots", first)
        self.assertIn("SLOT-A", first)


if __name__ == "__main__":
    unittest.main()
