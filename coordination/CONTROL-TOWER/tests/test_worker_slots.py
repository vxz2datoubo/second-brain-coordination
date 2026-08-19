from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from authorization_witness import authorization_witness, verify_authorization_witness  # noqa: E402
from control_tower import render_projection_block  # noqa: E402
from lane_claims import validate_claims  # noqa: E402
from worker_slots import (  # noqa: E402
    MAINTENANCE_ADOPTION_FILE,
    MAINTENANCE_TOMBSTONES_FILE,
    R3_MAINTENANCE_ADOPTION_FILE,
    R4_MAINTENANCE_ADOPTION_FILE,
    R144_TASK_BRIEF_FILE,
    load_worker_slots,
    validate_worker_slots,
)

GPT = "GPT_ENGINEERING_WORKER"
REVIEWER = "GPT_INDEPENDENT_REVIEWER"
R5_TASK_ID = "CODEX-CONTROL-TOWER-GPT-ENGINEERING-WORKER-FIRST-CLASS-R144"
R5_BRANCH = "codex/r144-control-tower-gpt-worker-first-class"
R5_HEAD = "8a2eb5c41f9b67328211569ac7c8d4c71d0cf6d1"
R5_REVIEW = 4974860616
R5_AUTHORITY_ID = "R144-GPT-ARCHITECTURE-OWNER-MAINTENANCE-ADOPTION-R5-0001"
R4_AUTHORITY_ID = "R144-GPT-ARCHITECTURE-OWNER-MAINTENANCE-ADOPTION-R4-0001"
R3_AUTHORITY_ID = "R144-GPT-ARCHITECTURE-OWNER-MAINTENANCE-ADOPTION-0001"
RELEASED_SCOPE = "NO_FURTHER_MODIFIER_WRITES_AUTHORIZED_BY_THIS_ARTIFACT"
R4_RELEASE_COMMIT = "8a2eb5c41f9b67328211569ac7c8d4c71d0cf6d1"


def _slot(
    slot_id: str = "SLOT-A",
    *,
    task_id: str = "GPT-T1",
    route_epoch: int = 144,
    issue: int = 406,
    pr: int | None = 408,
    branch: str = "gpt/slot-a",
    execution_allowed: Any = True,
    status: str = "READY",
    write_paths: list[str] | None = None,
    authority_claims: list[str] | None = None,
    executor_role: str | None = GPT,
    agent_type: str | None = GPT,
    model_id: str = "GPT-5.6 Sol",
    reviewer_role: str = REVIEWER,
    activation_state: str = "ACTIVE",
    closure_state: str | None = None,
    resource_class: str = "LIGHT_TO_MEDIUM_IMPLEMENTATION",
) -> dict:
    result = {
        "worker_slot_id": slot_id,
        "agent_type": agent_type,
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
        "resource_class": resource_class,
        "provenance": {"source": "TEST", "executor_role": GPT, "model_id": model_id},
        "reviewer_role": reviewer_role,
        "reviewer_separation": "EXECUTION_IDENTITY_NOT_ACCEPTANCE_AUTHORITY",
        "activation_state": activation_state,
        "closure_state": closure_state,
    }
    if agent_type is None:
        result.pop("agent_type")
    if executor_role is None:
        result.pop("executor_role")
    return result


def _active_claim(
    *,
    lane_id: str = "A",
    slot_id: str = "SLOT-A",
    task_id: str = "GPT-T1",
    route_epoch: int = 144,
    issue: int = 406,
    pr: int | None = 408,
    branch: str = "gpt/slot-a",
    write_paths: list[str] | None = None,
    authority_claims: list[str] | None = None,
    omit_slot_id: bool = False,
    resource_class: str = "LIGHT_TO_MEDIUM_IMPLEMENTATION",
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
        "lane_id": lane_id,
        "claim_state": "ACTIVE_IMPLEMENTATION",
        "execution_agent": GPT,
        "resource_class": resource_class,
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


def _reserved_claim(
    *,
    lane_id: str = "A",
    slot_id: str = "SLOT-A",
    task_id: str = "GPT-T1",
    route_epoch: int = 144,
    issue: int = 406,
    pr: int | None = 408,
    branch: str = "gpt/slot-a",
) -> dict:
    return {
        "lane_id": lane_id,
        "claim_state": "RESERVED_IMPLEMENTATION_NON_EXECUTABLE",
        "execution_agent": GPT,
        "worker_slot_id": slot_id,
        "resource_class": "LIGHT_TO_MEDIUM_IMPLEMENTATION_RESERVATION",
        "route_binding": {
            "worker_slot_id": slot_id,
            "task_id": task_id,
            "route_epoch": route_epoch,
            "issue": issue,
            "pr": pr,
            "branch": branch,
        },
        "implementation_scope": {"global_reconciliation_receipt": "TEST"},
        "write_paths": ["runtime/a.py"],
        "read_paths": [],
        "interfaces": [],
        "read_domains": [],
        "write_domains": ["W2_RUNTIME"],
        "authority_claims": ["W2_RUNTIME_IMPL"],
    }


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


def _r3_released_authority() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "authority_id": R3_AUTHORITY_ID,
        "authority_type": "GPT_ARCHITECTURE_OWNER_CORRECTIVE_MAINTENANCE_ADOPTION",
        "issuer": "USER",
        "actor": "GPT_ARCHITECTURE_OWNER",
        "state": "RELEASED",
        "release_reason": "R3_COMPLETE",
        "released_scope_status": RELEASED_SCOPE,
    }


def _r4_released_authority() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "authority_id": R4_AUTHORITY_ID,
        "authority_type": "GPT_ARCHITECTURE_OWNER_CORRECTIVE_MAINTENANCE_ADOPTION",
        "issuer": "USER",
        "actor": "GPT_ARCHITECTURE_OWNER",
        "state": "RELEASED",
        "release_reason": "CORRECTIVE_PATCH_COMPLETE_PENDING_SEPARATE_INDEPENDENT_REVIEW",
        "released_scope_status": RELEASED_SCOPE,
        "release_transition": {
            "from_state": "ACTIVE",
            "to_state": "RELEASED",
            "terminal_for_authority_id": True,
            "next_activation_requires_new_user_issued_authority_id": True,
        },
    }


def _maintenance_authority(**overrides: Any) -> dict:
    doc: dict[str, Any] = {
        "schema_version": "1.0",
        "authority_id": R5_AUTHORITY_ID,
        "authority_type": "GPT_ARCHITECTURE_OWNER_CORRECTIVE_MAINTENANCE_ADOPTION",
        "issuer": "USER",
        "actor": "GPT_ARCHITECTURE_OWNER",
        "state": "ACTIVE",
        "predecessor_authority": {
            "path": R4_MAINTENANCE_ADOPTION_FILE,
            "authority_id": R4_AUTHORITY_ID,
            "required_state": "RELEASED",
            "required_terminal_scope_status": RELEASED_SCOPE,
        },
        "task_id": R5_TASK_ID,
        "route_epoch": 144,
        "issue": 406,
        "pr": 408,
        "branch": R5_BRANCH,
        "trigger_review": R5_REVIEW,
        "adopted_candidate_input_head": R5_HEAD,
        "activation_parent_head": R5_HEAD,
        "execution_allowed": False,
        "runtime_write_allowed": False,
        "trade_allowed": False,
        "merge_authority": False,
        "acceptance_authority": False,
        "self_review_allowed": False,
        "retroactive_workbuddy_authorization": False,
        "independent_review_required": True,
        "same_pr_required": True,
        "fresh_exact_head_ci_required": True,
        "allowed_write_paths": ["coordination/CONTROL-TOWER/worker_slots.py"],
        "state_machine": {
            "active_scope_status": "BOUNDED_CORRECTIVE_MAINTENANCE_OPEN",
            "released_scope_status_required": RELEASED_SCOPE,
            "released_is_terminal_for_authority_id": True,
            "next_activation_requires_new_user_issued_authority_id": True,
            "terminality_must_not_depend_on_mutable_release_receipt_presence": True,
        },
        "provenance": {"source": "USER_RELAYED_INDEPENDENT_REVIEW_AND_BOUNDED_CONTINUATION"},
    }
    doc.update(overrides)
    return doc


def _released_maintenance_authority(**overrides: Any) -> dict:
    doc = _maintenance_authority(
        state="RELEASED",
        release_reason="CORRECTIVE_PATCH_COMPLETE_PENDING_SEPARATE_INDEPENDENT_REVIEW",
        released_scope_status=RELEASED_SCOPE,
        release_transition={
            "from_state": "ACTIVE",
            "to_state": "RELEASED",
            "terminal_for_authority_id": True,
            "next_activation_requires_new_user_issued_authority_id": True,
        },
    )
    doc.update(overrides)
    return doc


def _terminal_tombstones(*, include_r5: bool = False) -> dict[str, Any]:
    records: list[dict[str, Any]] = [
        {
            "authority_id": R4_AUTHORITY_ID,
            "authority_file": R4_MAINTENANCE_ADOPTION_FILE,
            "terminal_state": "RELEASED",
            "release_commit": R4_RELEASE_COMMIT,
            "released_scope_status": RELEASED_SCOPE,
            "reactivation_allowed": False,
            "terminality_source_review": R5_REVIEW,
        }
    ]
    if include_r5:
        records.append(
            {
                "authority_id": R5_AUTHORITY_ID,
                "authority_file": MAINTENANCE_ADOPTION_FILE,
                "terminal_state": "RELEASED",
                "release_parent_head": "d" * 40,
                "released_scope_status": RELEASED_SCOPE,
                "reactivation_allowed": False,
                "terminality_source_review": R5_REVIEW,
            }
        )
    return {
        "schema_version": "1.0",
        "registry_id": "R144-GPT-MAINTENANCE-TERMINAL-TOMBSTONES-0001",
        "semantics": "MONOTONIC_TERMINAL_AUTHORITY_IDS / DELETE_OR_REWRITE_FAILS_CLOSED",
        "terminal_authorities": records,
    }


class WorkerRepo:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def _write(self, relpath: str, payload: Any) -> None:
        path = self.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    def build(
        self,
        slots: list[Any],
        claim_a: dict | None = None,
        claim_b: dict | None = None,
        *,
        capacity: int = 2,
        include_gate: bool = False,
        registry_parallel: bool = True,
        nested_parallelism: str = "FORBIDDEN",
        maintenance: dict | None = None,
    ) -> Path:
        registry = {
            "program_lanes": [{"lane_id": "A"}, {"lane_id": "B"}, {"lane_id": "C"}],
            "portfolio_capacity_policy": {
                "codex_active_execution_routes_max": 1,
                "qclaw_active_execution_routes_max": 1,
                "workbuddy_active_execution_routes_max": 1,
                "gpt_engineering_worker_parallel_routes_allowed": registry_parallel,
                "gpt_engineering_worker_active_slots_max": capacity,
                "local_heavy_stage_concurrency_max": 1,
                "nested_parallelism": nested_parallelism,
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
            {
                "schema_version": "1.0",
                "registry_id": "ACTIVE-GPT-ENGINEERING-WORKERS-0001",
                "agent_type": GPT,
                "parallel_routes_allowed": registry_parallel,
                "boundary": "GOVERNANCE_AND_OBSERVABILITY / NO_TRADE",
                "worker_slots": slots,
            },
        )
        if maintenance is not None:
            self._write(
                R144_TASK_BRIEF_FILE,
                {
                    "schema_version": "1.0",
                    "task_id": R5_TASK_ID,
                    "route_epoch": 144,
                    "issue": 406,
                    "planned_branch": R5_BRANCH,
                },
            )
            self._write(R3_MAINTENANCE_ADOPTION_FILE, _r3_released_authority())
            self._write(R4_MAINTENANCE_ADOPTION_FILE, _r4_released_authority())
            self._write(
                MAINTENANCE_TOMBSTONES_FILE,
                _terminal_tombstones(include_r5=maintenance.get("state") == "RELEASED"),
            )
            self._write(MAINTENANCE_ADOPTION_FILE, maintenance)
        claims = [
            claim_a if claim_a is not None else _active_claim(),
            claim_b if claim_b is not None else _held_claim("B", "proposal/B"),
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

    def test_r2_non_list_worker_slots_fails_closed(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()])
        path = root / "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["worker_slots"] = {"SLOT-A": _slot()}
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_REGISTRY_SLOTS_NOT_LIST" for item in report["errors"]))

    def test_r2_non_mapping_slot_entry_fails_closed(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot(), "corrupt-slot"])
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_REGISTRY_SLOT_NOT_MAPPING" for item in report["errors"]))

    def test_r2_registry_identity_missing_fails_closed(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()])
        path = root / "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data.pop("schema_version")
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_REGISTRY_IDENTITY_INVALID" for item in report["errors"]))

    def test_r2_parallel_policy_drift_fails_closed(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()])
        path = root / "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["parallel_routes_allowed"] = False
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_REGISTRY_PARALLEL_POLICY_DRIFT" for item in report["errors"]))

    def test_r3_required_registry_missing_fails_closed(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()])
        (root / "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml").unlink()
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_REGISTRY_MISSING" for item in report["errors"]))
        self.assertEqual(report["worker_slot_structural_check"], "FAIL")

    def test_r3_execution_allowed_strings_fail_closed(self) -> None:
        for malformed in ("false", "0"):
            with self.subTest(malformed=malformed):
                repo = WorkerRepo()
                root = repo.build([_slot(execution_allowed=malformed)])
                report = validate_worker_slots(root)
                self.assertTrue(
                    any(item["code"] == "WORKER_SLOT_EXECUTION_ALLOWED_TYPE_INVALID" for item in report["errors"])
                )
                self.assertEqual(report["active_executable_slots"], [])

    def test_r3_missing_explicit_agent_identity_fails_closed(self) -> None:
        for field in ("agent_type", "executor_role"):
            with self.subTest(field=field):
                repo = WorkerRepo()
                kwargs = {field: None}
                root = repo.build([_slot(**kwargs)])
                report = validate_worker_slots(root)
                self.assertTrue(any(item["code"] == "WORKER_SLOT_IDENTITY_FIELD_MISSING" for item in report["errors"]))
                self.assertEqual(report["active_executable_slots"], [])

    def test_r2_active_slot_without_work_claim_fails_closed(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], claim_a=_held_claim("A", "proposal/A"))
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_EXACT_CLAIM_CARDINALITY" for item in report["errors"]))

    def test_r2_claim_surface_drift_fails_closed(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], claim_a=_active_claim(write_paths=["runtime/other.py"]))
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_CLAIM_SURFACE_DRIFT" for item in report["errors"]))

    def test_r2_active_slot_missing_pr_fails_closed(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot(pr=None)], claim_a=_active_claim(pr=None))
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_LIVE_BINDING_INCOMPLETE" for item in report["errors"]))

    def test_r2_reserved_slot_cannot_be_executable(self) -> None:
        repo = WorkerRepo()
        root = repo.build(
            [_slot(activation_state="RESERVED", execution_allowed=True, resource_class="LIGHT_TO_MEDIUM_IMPLEMENTATION_RESERVATION")],
            claim_a=_reserved_claim(),
        )
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_RESERVED_EXECUTABLE" for item in report["errors"]))
        self.assertEqual(report["active_executable_slots"], [])

    def test_r2_nested_parallel_same_task_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build(
            [
                _slot("SLOT-A", task_id="GPT-T1", write_paths=["runtime/a.py"], authority_claims=["A_IMPL"]),
                _slot("SLOT-B", task_id="GPT-T1", branch="gpt/slot-b", write_paths=["runtime/b.py"], authority_claims=["B_IMPL"]),
            ],
            claim_b=_active_claim(
                lane_id="B",
                slot_id="SLOT-B",
                task_id="GPT-T1",
                branch="gpt/slot-b",
                write_paths=["runtime/b.py"],
                authority_claims=["B_IMPL"],
            ),
        )
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_NESTED_PARALLELISM_FORBIDDEN" for item in report["errors"]))

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
            [
                _slot("SLOT-A", task_id="GPT-T1", write_paths=["runtime/shared.py"]),
                _slot("SLOT-B", task_id="GPT-T2", write_paths=["runtime/shared.py"], branch="gpt/slot-b"),
            ]
        )
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_COLLISION" for item in report["errors"]))

    def test_k_two_slots_same_authority_fail(self) -> None:
        repo = WorkerRepo()
        root = repo.build(
            [
                _slot("SLOT-A", task_id="GPT-T1", authority_claims=["W3_CANONICAL"]),
                _slot("SLOT-B", task_id="GPT-T2", authority_claims=["W3_CANONICAL"], branch="gpt/slot-b"),
            ]
        )
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_COLLISION" for item in report["errors"]))

    def test_l_two_slots_non_overlap_pass(self) -> None:
        repo = WorkerRepo()
        root = repo.build(
            [
                _slot("SLOT-A", task_id="GPT-T1", write_paths=["runtime/a.py"], authority_claims=["W2_IMPL"]),
                _slot("SLOT-B", task_id="GPT-T2", write_paths=["runtime/b.py"], authority_claims=["W8_IMPL"], branch="gpt/slot-b"),
            ],
            claim_a=_active_claim(task_id="GPT-T1", write_paths=["runtime/a.py"], authority_claims=["W2_IMPL"]),
            claim_b=_active_claim(
                lane_id="B",
                slot_id="SLOT-B",
                task_id="GPT-T2",
                branch="gpt/slot-b",
                write_paths=["runtime/b.py"],
                authority_claims=["W8_IMPL"],
            ),
        )
        report = validate_worker_slots(root)
        self.assertEqual(report["worker_slot_structural_check"], "PASS")
        self.assertEqual(report["active_executable_slots"], ["SLOT-A", "SLOT-B"])

    def test_m_same_slot_double_booked_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot("SLOT-A", task_id="GPT-T1"), _slot("SLOT-A", task_id="GPT-T2")])
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_DUPLICATE_ID" for item in report["errors"]))

    def test_n_silent_slot_overwrite_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot("SLOT-A", task_id="GPT-T1"), _slot("SLOT-A", task_id="GPT-T1", route_epoch=145)])
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "WORKER_SLOT_DUPLICATE_ID" for item in report["errors"]))

    def test_capacity_exceeded_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build(
            [
                _slot("SLOT-A", task_id="GPT-T1", write_paths=["runtime/a.py"], authority_claims=["A_IMPL"]),
                _slot("SLOT-B", task_id="GPT-T2", write_paths=["runtime/b.py"], authority_claims=["B_IMPL"], branch="gpt/slot-b"),
                _slot("SLOT-C", task_id="GPT-T3", write_paths=["runtime/c.py"], authority_claims=["C_IMPL"], branch="gpt/slot-c"),
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
        root = repo.build([_slot("SLOT-A", activation_state="RELEASED", execution_allowed=False, status="DONE_HISTORICAL")])
        report = validate_worker_slots(root)
        self.assertEqual(report["worker_slot_structural_check"], "PASS")
        self.assertEqual(report["active_executable_slots"], [])

    def test_r5_active_maintenance_exact_binding_and_r4_tombstone_pass(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], maintenance=_maintenance_authority())
        report = validate_worker_slots(root)
        self.assertEqual(report["maintenance_adoption_structural_check"], "PASS")
        self.assertTrue(report["maintenance_write_allowed"])
        self.assertEqual(report["maintenance_authority_state"], "ACTIVE")

    def test_r5_wrong_exact_bindings_fail_closed(self) -> None:
        mutations = {
            "task_id": "WRONG-TASK",
            "route_epoch": 999,
            "issue": 999,
            "pr": 123,
            "branch": "wrong/branch",
            "trigger_review": 1,
            "adopted_candidate_input_head": "b" * 40,
            "activation_parent_head": "c" * 40,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                repo = WorkerRepo()
                root = repo.build([_slot()], maintenance=_maintenance_authority(**{field: value}))
                report = validate_worker_slots(root)
                self.assertTrue(
                    any(item["code"] == "MAINTENANCE_ADOPTION_BINDING_MISMATCH" for item in report["errors"])
                )
                self.assertFalse(report["maintenance_write_allowed"])

    def test_r5_wrong_authority_identity_fails_closed(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], maintenance=_maintenance_authority(authority_id="WRONG-AUTHORITY"))
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "MAINTENANCE_ADOPTION_IDENTITY_INVALID" for item in report["errors"]))
        self.assertFalse(report["maintenance_write_allowed"])

    def test_r5_r4_predecessor_must_remain_released(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], maintenance=_maintenance_authority())
        path = root / R4_MAINTENANCE_ADOPTION_FILE
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["state"] = "ACTIVE"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "MAINTENANCE_TERMINAL_AUTHORITY_REACTIVATION" for item in report["errors"]))
        self.assertFalse(report["maintenance_write_allowed"])

    def test_r5_review_exact_bypass_released_to_active_and_delete_all_receipts_fails(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], maintenance=_maintenance_authority())
        path = root / R4_MAINTENANCE_ADOPTION_FILE
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["state"] = "ACTIVE"
        for field in ("release_reason", "released_scope_status", "release_transition"):
            data.pop(field, None)
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "MAINTENANCE_TERMINAL_AUTHORITY_REACTIVATION" for item in report["errors"]))
        self.assertFalse(report["maintenance_write_allowed"])

    def test_r5_r4_tombstone_cannot_be_deleted(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], maintenance=_maintenance_authority())
        path = root / MAINTENANCE_TOMBSTONES_FILE
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["terminal_authorities"] = []
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "MAINTENANCE_TOMBSTONE_EXPECTED_ID_MISSING" for item in report["errors"]))
        self.assertFalse(report["maintenance_write_allowed"])

    def test_r5_r4_tombstone_exact_binding_cannot_drift(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], maintenance=_maintenance_authority())
        path = root / MAINTENANCE_TOMBSTONES_FILE
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["terminal_authorities"][0]["release_commit"] = "e" * 40
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "MAINTENANCE_TOMBSTONE_BINDING_MISMATCH" for item in report["errors"]))
        self.assertFalse(report["maintenance_write_allowed"])

    def test_r5_missing_current_authority_fails_when_history_exists(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], maintenance=_maintenance_authority())
        (root / MAINTENANCE_ADOPTION_FILE).unlink()
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "MAINTENANCE_ADOPTION_MISSING" for item in report["errors"]))
        self.assertFalse(report["maintenance_write_allowed"])

    def test_r5_released_is_non_writable_when_tombstoned(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], maintenance=_released_maintenance_authority())
        report = validate_worker_slots(root)
        self.assertEqual(report["maintenance_adoption_structural_check"], "PASS")
        self.assertEqual(report["maintenance_authority_state"], "RELEASED")
        self.assertFalse(report["maintenance_write_allowed"])

    def test_r5_released_requires_release_receipt_fields(self) -> None:
        cases = (
            ("release_reason", None, "MAINTENANCE_ADOPTION_RELEASE_RECEIPT_MISSING"),
            ("released_scope_status", "WRONG", "MAINTENANCE_ADOPTION_RELEASE_SCOPE_INVALID"),
            ("release_transition", None, "MAINTENANCE_ADOPTION_RELEASE_TRANSITION_INVALID"),
        )
        for field, value, code in cases:
            with self.subTest(field=field):
                repo = WorkerRepo()
                doc = _released_maintenance_authority()
                if value is None:
                    doc.pop(field, None)
                else:
                    doc[field] = value
                root = repo.build([_slot()], maintenance=doc)
                report = validate_worker_slots(root)
                self.assertTrue(any(item["code"] == code for item in report["errors"]))
                self.assertFalse(report["maintenance_write_allowed"])

    def test_r5_current_release_markers_prevent_simple_reactivation(self) -> None:
        repo = WorkerRepo()
        doc = _released_maintenance_authority()
        doc["state"] = "ACTIVE"
        root = repo.build([_slot()], maintenance=doc)
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "MAINTENANCE_ADOPTION_REACTIVATION_FORBIDDEN" for item in report["errors"]))
        self.assertFalse(report["maintenance_write_allowed"])

    def test_r5_maintenance_cannot_gain_merge_authority(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], maintenance=_maintenance_authority(merge_authority=True))
        report = validate_worker_slots(root)
        self.assertTrue(any(item["code"] == "MAINTENANCE_ADOPTION_UNSAFE_AUTHORITY" for item in report["errors"]))
        self.assertFalse(report["maintenance_write_allowed"])


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
        repo.build([_slot(task_id="GPT-T2")], claim_a=_active_claim(task_id="GPT-T2"), include_gate=True)
        self.assertFalse(verify_authorization_witness(root, witness)["fresh"])

    def test_slot_change_invalidates_witness(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot("SLOT-A")], include_gate=True)
        witness = authorization_witness(root, "A")
        repo.build([_slot("SLOT-A", branch="gpt/changed")], claim_a=_active_claim(branch="gpt/changed"), include_gate=True)
        self.assertFalse(verify_authorization_witness(root, witness)["fresh"])

    def test_p_peer_claim_change_invalidates_witness(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], include_gate=True)
        witness = authorization_witness(root, "A")
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

    def test_r2_worker_registry_policy_change_invalidates_witness(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], include_gate=True)
        witness = authorization_witness(root, "A")
        path = root / "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["semantics"] = {"policy_revision": "R2_CHANGED"}
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        result = verify_authorization_witness(root, witness)
        self.assertFalse(result["fresh"])
        self.assertNotEqual(witness["worker_registry_fingerprint"], result["current"]["worker_registry_fingerprint"])

    def test_r3_malformed_slot_mutation_invalidates_witness(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], include_gate=True)
        witness = authorization_witness(root, "A")
        path = root / "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["worker_slots"].append("corrupt-slot")
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        result = verify_authorization_witness(root, witness)
        self.assertFalse(result["fresh"])
        self.assertEqual(result["reason"], "AUTHORIZATION_MATERIAL_INVALID")

    def test_r3_string_false_authority_refuses_witness(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], include_gate=True)
        witness = authorization_witness(root, "A")
        path = root / "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["worker_slots"][0]["execution_allowed"] = "false"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        result = verify_authorization_witness(root, witness)
        self.assertFalse(result["fresh"])
        self.assertEqual(result["reason"], "AUTHORIZATION_MATERIAL_INVALID")

    def test_r5_maintenance_authority_change_invalidates_witness(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], include_gate=True, maintenance=_maintenance_authority())
        witness = authorization_witness(root, "A")
        path = root / MAINTENANCE_ADOPTION_FILE
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["allowed_write_paths"].append("coordination/CONTROL-TOWER/tests")
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        result = verify_authorization_witness(root, witness)
        self.assertFalse(result["fresh"])
        self.assertEqual(result["reason"], "AUTHORIZATION_MATERIAL_CHANGED")

    def test_r5_tombstone_change_invalidates_or_refuses_witness(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], include_gate=True, maintenance=_maintenance_authority())
        witness = authorization_witness(root, "A")
        path = root / MAINTENANCE_TOMBSTONES_FILE
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["terminal_authorities"][0]["release_commit"] = "f" * 40
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        result = verify_authorization_witness(root, witness)
        self.assertFalse(result["fresh"])
        self.assertEqual(result["reason"], "AUTHORIZATION_MATERIAL_INVALID")

    def test_r5_release_transition_invalidates_active_witness(self) -> None:
        repo = WorkerRepo()
        root = repo.build([_slot()], include_gate=True, maintenance=_maintenance_authority())
        witness = authorization_witness(root, "A")
        repo._write(MAINTENANCE_ADOPTION_FILE, _released_maintenance_authority())
        repo._write(MAINTENANCE_TOMBSTONES_FILE, _terminal_tombstones(include_r5=True))
        result = verify_authorization_witness(root, witness)
        self.assertFalse(result["fresh"])
        self.assertEqual(result["reason"], "AUTHORIZATION_MATERIAL_CHANGED")


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
