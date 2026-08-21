from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from path_action_constraints import (  # noqa: E402
    PathActionConstraint,
    validate_contract,
    validate_diff_actions,
    validate_transition_lineage,
)

SLOT = "GPT-WORKER-R145-PROGRAMMING-1"
LANE = "LANE-A-HARNESS-INTEGRATION"
TASK = "GPT-GLOBAL-SIGNAL-TOWER-S0F-CROSS-DOMAIN-ROUTING-ISOLATION-R145"
ROUTE_FILE = "coordination/ROUTES/GPT-GLOBAL-SIGNAL-TOWER-S0F-CROSS-DOMAIN-ROUTING-ISOLATION-R145.yaml"
EXACT = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0F-CROSS-DOMAIN-ROUTING-ISOLATION/BOOTSTRAP-NON-EXECUTABLE.yaml"
BASELINE = "6c59f197ef515b1c282aa6a08c7759ed96749957"
BASE_WRITES = [
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0D-READ-ONLY-SHADOW/**",
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY/**",
    ".github/workflows/*r145*",
    EXACT,
]
CONSTRAINT = [
    {
        "path": EXACT,
        "allowed_actions": ["DELETE"],
        "transition_baseline_sha": BASELINE,
        "required_final_state": "ABSENT",
    }
]


class RepoFixture:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def close(self) -> None:
        self.temp.cleanup()

    def write(self, path: str, payload: dict) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")

    def build(
        self,
        *,
        worker_constraints=None,
        claim_constraints=None,
        route_constraints=None,
        worker_writes=None,
        claim_writes=None,
        route_writes=None,
    ) -> None:
        worker_constraints = CONSTRAINT if worker_constraints is None else worker_constraints
        claim_constraints = CONSTRAINT if claim_constraints is None else claim_constraints
        route_constraints = CONSTRAINT if route_constraints is None else route_constraints
        worker_writes = BASE_WRITES if worker_writes is None else worker_writes
        claim_writes = BASE_WRITES if claim_writes is None else claim_writes
        route_writes = BASE_WRITES if route_writes is None else route_writes

        self.write(
            "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml",
            {
                "worker_slots": [
                    {
                        "worker_slot_id": SLOT,
                        "task_id": TASK,
                        "route_epoch": 145,
                        "issue": 415,
                        "pr": 418,
                        "branch": "gpt/r145-cross-domain-routing-isolation-runtime",
                        "write_paths": worker_writes,
                        "path_action_constraints": worker_constraints,
                    }
                ]
            },
        )
        self.write(
            "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml",
            {
                "claims": [
                    {
                        "lane_id": LANE,
                        "worker_slot_id": SLOT,
                        "route_binding": {
                            "worker_slot_id": SLOT,
                            "task_id": TASK,
                            "route_epoch": 145,
                            "issue": 415,
                            "pr": 418,
                            "branch": "gpt/r145-cross-domain-routing-isolation-runtime",
                        },
                        "write_paths": claim_writes,
                        "path_action_constraints": claim_constraints,
                    }
                ]
            },
        )
        self.write(
            ROUTE_FILE,
            {
                "binding": {
                    "task_id": TASK,
                    "route_epoch": 145,
                    "issue": 415,
                    "implementation_pr": 418,
                    "implementation_branch": "gpt/r145-cross-domain-routing-isolation-runtime",
                },
                "executor": {"worker_slot_id": SLOT},
                "write_scope": {
                    "implementation": route_writes,
                    "exact_action_constraints": route_constraints,
                },
            },
        )


class PathActionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = RepoFixture()

    def tearDown(self) -> None:
        self.repo.close()

    def check(self):
        return validate_contract(self.repo.root, worker_slot_id=SLOT, lane_id=LANE, route_file=ROUTE_FILE)

    def test_delete_only_contract_passes(self):
        self.repo.build()
        result = self.check()
        self.assertEqual("PASS", result["status"])
        self.assertEqual(["DELETE"], result["constraints"][EXACT]["allowed_actions"])
        self.assertEqual(BASELINE, result["constraints"][EXACT]["transition_baseline_sha"])
        self.assertEqual("ABSENT", result["constraints"][EXACT]["required_final_state"])

    def test_missing_claim_constraint_fails_closed(self):
        self.repo.build(claim_constraints=[])
        result = self.check()
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_CONSTRAINT_DRIFT", {item["code"] for item in result["findings"]})

    def test_worker_claim_route_action_mismatch_fails(self):
        mismatch = [{**CONSTRAINT[0], "allowed_actions": ["MODIFY"]}]
        self.repo.build(route_constraints=mismatch)
        result = self.check()
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_CONSTRAINT_DRIFT", {item["code"] for item in result["findings"]})

    def test_transition_baseline_mismatch_fails(self):
        mismatch = [{**CONSTRAINT[0], "transition_baseline_sha": "a" * 40}]
        self.repo.build(route_constraints=mismatch)
        result = self.check()
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_CONSTRAINT_DRIFT", {item["code"] for item in result["findings"]})

    def test_general_s0f_wildcard_bypass_fails(self):
        broad = list(BASE_WRITES) + [
            "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0F-CROSS-DOMAIN-ROUTING-ISOLATION/**"
        ]
        self.repo.build(worker_writes=broad, claim_writes=broad, route_writes=broad)
        result = self.check()
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_BROADER_WRITE_BYPASS", {item["code"] for item in result["findings"]})

    def test_write_surface_drift_fails(self):
        self.repo.build(claim_writes=BASE_WRITES[:-1])
        result = self.check()
        self.assertEqual("FAIL", result["status"])
        codes = {item["code"] for item in result["findings"]}
        self.assertIn("PATH_ACTION_WRITE_SURFACE_DRIFT", codes)
        self.assertIn("PATH_ACTION_CONSTRAINED_PATH_NOT_WRITABLE", codes)


class PathActionDiffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.constraints = {
            EXACT: PathActionConstraint(
                path=EXACT,
                allowed_actions=("DELETE",),
                transition_baseline_sha=BASELINE,
                required_final_state="ABSENT",
            )
        }

    def test_delete_passes(self):
        findings = validate_diff_actions(self.constraints, [("D", (EXACT,))])
        self.assertEqual([], findings)

    def test_modify_fails(self):
        findings = validate_diff_actions(self.constraints, [("M", (EXACT,))])
        self.assertEqual("PATH_ACTION_DIFF_VIOLATION", findings[0].code)
        self.assertEqual("MODIFY", findings[0].evidence["derived_action"])

    def test_create_fails(self):
        findings = validate_diff_actions(self.constraints, [("A", (EXACT,))])
        self.assertEqual("PATH_ACTION_DIFF_VIOLATION", findings[0].code)
        self.assertEqual("CREATE", findings[0].evidence["derived_action"])

    def test_rename_fails(self):
        findings = validate_diff_actions(self.constraints, [("R100", (EXACT, EXACT + ".bak"))])
        self.assertEqual("PATH_ACTION_DIFF_VIOLATION", findings[0].code)
        self.assertEqual("UNSUPPORTED", findings[0].evidence["derived_action"])

    def test_unrelated_diff_is_ignored(self):
        findings = validate_diff_actions(self.constraints, [("M", ("elsewhere.txt",))])
        self.assertEqual([], findings)


class TransitionLineageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=self.root, check=True)
        target = self.root / EXACT
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("bootstrap\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.root, check=True)
        self.baseline = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def constraint(self, *, final_state="ABSENT", baseline=None):
        return {
            EXACT: PathActionConstraint(
                path=EXACT,
                allowed_actions=("DELETE",),
                transition_baseline_sha=baseline or self.baseline,
                required_final_state=final_state,
            )
        }

    def commit_delete(self) -> str:
        (self.root / EXACT).unlink()
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "delete"], cwd=self.root, check=True)
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()

    def test_baseline_present_final_absent_exact_delete_passes(self):
        head = self.commit_delete()
        result = validate_transition_lineage(self.root, head_sha=head, constraints=self.constraint())
        self.assertEqual("PASS", result["status"])
        self.assertTrue(result["checked"][EXACT]["baseline_is_ancestor"])
        self.assertEqual([["D", [EXACT]]], result["checked"][EXACT]["transition_entries"])

    def test_final_present_fails(self):
        result = validate_transition_lineage(self.root, head_sha=self.baseline, constraints=self.constraint())
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_REQUIRED_FINAL_STATE_VIOLATION", {item["code"] for item in result["findings"]})

    def test_non_ancestor_baseline_fails(self):
        head = self.commit_delete()
        bogus = "a" * 40
        result = validate_transition_lineage(self.root, head_sha=head, constraints=self.constraint(baseline=bogus))
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_TRANSITION_BASELINE_NOT_ANCESTOR", {item["code"] for item in result["findings"]})

    def test_modify_then_final_present_fails(self):
        target = self.root / EXACT
        target.write_text("modified\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "modify"], cwd=self.root, check=True)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()
        result = validate_transition_lineage(self.root, head_sha=head, constraints=self.constraint())
        codes = {item["code"] for item in result["findings"]}
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_DIFF_VIOLATION", codes)
        self.assertIn("PATH_ACTION_REQUIRED_FINAL_STATE_VIOLATION", codes)


if __name__ == "__main__":
    unittest.main()
