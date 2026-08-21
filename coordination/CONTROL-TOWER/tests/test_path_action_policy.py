from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from path_action_constraints import PathActionConstraint, validate_diff  # noqa: E402
from path_action_policy import (  # noqa: E402
    validate_full_diff_write_surface,
    validate_required_anchor,
)

SLOT = "GPT-WORKER-R145-PROGRAMMING-1"
LANE = "LANE-A-HARNESS-INTEGRATION"
TASK = "GPT-GLOBAL-SIGNAL-TOWER-S0F-CROSS-DOMAIN-ROUTING-ISOLATION-R145"
ROUTE_FILE = "coordination/ROUTES/GPT-GLOBAL-SIGNAL-TOWER-S0F-CROSS-DOMAIN-ROUTING-ISOLATION-R145.yaml"
ANCHOR_FILE = "coordination/CONTROL-TOWER/R145-BOOTSTRAP-CLEANUP-SCOPE-AMENDMENT.yaml"
EXACT = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0F-CROSS-DOMAIN-ROUTING-ISOLATION/BOOTSTRAP-NON-EXECUTABLE.yaml"
OTHER_S0F = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0F-CROSS-DOMAIN-ROUTING-ISOLATION/OTHER.yaml"
S0D_FILE = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0D-READ-ONLY-SHADOW/runtime.py"
FINAL_GATE = ".github/workflows/r145-final-active-gate.yml"
ROOT_WORKFLOW = ".github/workflows/runtime-governance-root.yml"
POLICY = "coordination/CONTROL-TOWER/path_action_policy.py"
ACTION = "coordination/CONTROL-TOWER/path_action_constraints.py"
BASELINE = "6c59f197ef515b1c282aa6a08c7759ed96749957"
BASE_WRITES = [
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0D-READ-ONLY-SHADOW/**",
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY/**",
    EXACT,
]
PROTECTED = [FINAL_GATE, ROOT_WORKFLOW, ACTION, POLICY, ANCHOR_FILE]
CONSTRAINT = [
    {
        "path": EXACT,
        "allowed_actions": ["DELETE"],
        "transition_baseline_sha": BASELINE,
        "required_final_state": "ABSENT",
    }
]


class PolicyFixture:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def close(self) -> None:
        self.temp.cleanup()

    def write_yaml(self, path: str, payload: dict) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")

    def build(self, constraints=None, anchor=None, writes=None) -> None:
        constraints = CONSTRAINT if constraints is None else constraints
        writes = BASE_WRITES if writes is None else writes
        anchor = anchor or {
            "amendment": {
                "exact_path": EXACT,
                "allowed_actions": ["DELETE"],
                "transition_baseline_sha": BASELINE,
                "required_final_state": "ABSENT",
                "general_s0f_write_allowed": False,
                "runtime_workflow_write_allowed": False,
                "protected_enforcement_paths": PROTECTED,
            }
        }
        self.write_yaml(
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
                        "write_paths": writes,
                        "path_action_constraints": constraints,
                    }
                ]
            },
        )
        self.write_yaml(
            "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml",
            {
                "claims": [
                    {
                        "lane_id": LANE,
                        "worker_slot_id": SLOT,
                        "route_binding": {
                            "task_id": TASK,
                            "route_epoch": 145,
                            "issue": 415,
                            "pr": 418,
                            "branch": "gpt/r145-cross-domain-routing-isolation-runtime",
                        },
                        "write_paths": writes,
                        "path_action_constraints": constraints,
                    }
                ]
            },
        )
        self.write_yaml(
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
                "write_scope": {"implementation": writes, "exact_action_constraints": constraints},
            },
        )
        self.write_yaml(ANCHOR_FILE, anchor)

    def check(self):
        return validate_required_anchor(
            self.root,
            worker_slot_id=SLOT,
            lane_id=LANE,
            route_file=ROUTE_FILE,
            required_contract_file=ANCHOR_FILE,
        )


class RequiredContractAnchorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = PolicyFixture()

    def tearDown(self) -> None:
        self.repo.close()

    def test_exact_required_contract_passes(self):
        self.repo.build()
        result = self.repo.check()
        self.assertEqual("PASS", result["status"])
        self.assertEqual(result["required"], result["actual"])
        self.assertEqual(sorted(PROTECTED), sorted(result["protected_enforcement_paths"]))

    def test_all_three_constraints_removed_fails(self):
        self.repo.build(constraints=[])
        result = self.repo.check()
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_REQUIRED_CONTRACT_MISMATCH", {item["code"] for item in result["findings"]})

    def test_all_three_constraints_coherently_weakened_to_modify_fails(self):
        weakened = [{**CONSTRAINT[0], "allowed_actions": ["MODIFY"]}]
        self.repo.build(constraints=weakened)
        result = self.repo.check()
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_REQUIRED_CONTRACT_MISMATCH", {item["code"] for item in result["findings"]})

    def test_all_three_constraints_change_baseline_fails(self):
        weakened = [{**CONSTRAINT[0], "transition_baseline_sha": "a" * 40}]
        self.repo.build(constraints=weakened)
        result = self.repo.check()
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_REQUIRED_CONTRACT_MISMATCH", {item["code"] for item in result["findings"]})

    def test_all_three_constraints_change_final_state_fails(self):
        weakened = [{**CONSTRAINT[0], "required_final_state": "PRESENT"}]
        self.repo.build(constraints=weakened)
        result = self.repo.check()
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_REQUIRED_CONTRACT_MISMATCH", {item["code"] for item in result["findings"]})

    def test_anchor_must_explicitly_forbid_general_s0f(self):
        anchor = {
            "amendment": {
                "exact_path": EXACT,
                "allowed_actions": ["DELETE"],
                "transition_baseline_sha": BASELINE,
                "required_final_state": "ABSENT",
                "general_s0f_write_allowed": True,
                "runtime_workflow_write_allowed": False,
                "protected_enforcement_paths": PROTECTED,
            }
        }
        self.repo.build(anchor=anchor)
        result = self.repo.check()
        self.assertEqual("FAIL", result["status"])
        self.assertIn(
            "PATH_ACTION_REQUIRED_CONTRACT_GENERAL_S0F_NOT_FORBIDDEN",
            {item["code"] for item in result["findings"]},
        )

    def test_anchor_must_forbid_runtime_workflow_writes(self):
        anchor = {
            "amendment": {
                "exact_path": EXACT,
                "allowed_actions": ["DELETE"],
                "transition_baseline_sha": BASELINE,
                "required_final_state": "ABSENT",
                "general_s0f_write_allowed": False,
                "runtime_workflow_write_allowed": True,
                "protected_enforcement_paths": PROTECTED,
            }
        }
        self.repo.build(anchor=anchor)
        result = self.repo.check()
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_RUNTIME_WORKFLOW_WRITE_NOT_FORBIDDEN", {item["code"] for item in result["findings"]})

    def test_runtime_write_surface_must_not_cover_protected_enforcement_root(self):
        self.repo.build(writes=BASE_WRITES + [".github/workflows/*r145*"])
        result = self.repo.check()
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_PROTECTED_ENFORCEMENT_ROOT_WRITABLE", {item["code"] for item in result["findings"]})


class FullWriteSurfaceGitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=self.root, check=True)
        target = self.root / EXACT
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("bootstrap\n", encoding="utf-8")
        allowed = self.root / S0D_FILE
        allowed.parent.mkdir(parents=True, exist_ok=True)
        allowed.write_text("old\n", encoding="utf-8")
        for workflow_path in (FINAL_GATE, ROOT_WORKFLOW):
            workflow = self.root / workflow_path
            workflow.parent.mkdir(parents=True, exist_ok=True)
            workflow.write_text("name: trusted\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.root, check=True)
        self.base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def commit(self, message: str) -> str:
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", message], cwd=self.root, check=True)
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()

    def check(self, head: str):
        return validate_full_diff_write_surface(
            self.root,
            base_sha=self.base,
            head_sha=head,
            write_paths=BASE_WRITES,
            protected_paths=PROTECTED,
        )

    def exact_delete_constraint(self):
        return {
            EXACT: PathActionConstraint(
                path=EXACT,
                allowed_actions=("DELETE",),
                transition_baseline_sha=self.base,
                required_final_state="ABSENT",
            )
        }

    def test_authorized_s0d_modify_passes(self):
        (self.root / S0D_FILE).write_text("new\n", encoding="utf-8")
        head = self.commit("authorized")
        self.assertEqual("PASS", self.check(head)["status"])

    def test_delete_exact_plus_add_unauthorized_s0f_fails(self):
        (self.root / EXACT).unlink()
        other = self.root / OTHER_S0F
        other.write_text("totally unrelated replacement body\n" * 20, encoding="utf-8")
        head = self.commit("d-plus-a")
        result = self.check(head)
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_DIFF_OUTSIDE_WRITE_SURFACE", {item["code"] for item in result["findings"]})

    def test_low_similarity_move_rewrite_fails_as_unauthorized_new_path(self):
        (self.root / EXACT).unlink()
        other = self.root / OTHER_S0F
        other.write_text("new schema\n" + ("x" * 4000), encoding="utf-8")
        head = self.commit("low-similarity-move")
        result = self.check(head)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any(item["evidence"]["path"] == OTHER_S0F for item in result["findings"]))

    def test_copy_recreate_to_unauthorized_s0f_fails(self):
        source = (self.root / EXACT).read_text(encoding="utf-8")
        (self.root / OTHER_S0F).write_text(source, encoding="utf-8")
        head = self.commit("copy-recreate")
        result = self.check(head)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any(item["evidence"]["path"] == OTHER_S0F for item in result["findings"]))

    def test_modify_protected_final_gate_fails_even_without_other_changes(self):
        (self.root / FINAL_GATE).write_text("name: disabled\n", encoding="utf-8")
        head = self.commit("disable-final-gate")
        result = self.check(head)
        codes = {item["code"] for item in result["findings"]}
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_PROTECTED_ENFORCEMENT_ROOT_CHANGED", codes)
        self.assertIn("PATH_ACTION_DIFF_OUTSIDE_WRITE_SURFACE", codes)

    def test_f04_attack_modify_guard_delete_marker_add_s0f_fails(self):
        (self.root / FINAL_GATE).write_text("name: bypassed\n", encoding="utf-8")
        (self.root / EXACT).unlink()
        (self.root / OTHER_S0F).write_text("unauthorized replacement\n", encoding="utf-8")
        head = self.commit("f04-attack")
        result = self.check(head)
        codes = {item["code"] for item in result["findings"]}
        self.assertEqual("FAIL", result["status"])
        self.assertIn("PATH_ACTION_PROTECTED_ENFORCEMENT_ROOT_CHANGED", codes)
        self.assertIn("PATH_ACTION_DIFF_OUTSIDE_WRITE_SURFACE", codes)

    @unittest.skipIf(os.name == "nt", "Git type-change symlink regression requires POSIX")
    def test_real_git_type_change_on_exact_path_is_rejected_by_action_guard(self):
        target = self.root / EXACT
        target.unlink()
        target.symlink_to("/tmp/r145-type-change-nonexistent-target")
        head = self.commit("type-change")

        surface = self.check(head)
        self.assertEqual("PASS", surface["status"], "the exact path remains inside the common write surface")

        action = validate_diff(
            self.root,
            base_sha=self.base,
            head_sha=head,
            constraints=self.exact_delete_constraint(),
        )
        self.assertEqual("FAIL", action["status"])
        violations = [item for item in action["findings"] if item["code"] == "PATH_ACTION_DIFF_VIOLATION"]
        self.assertTrue(violations)
        self.assertEqual("MODIFY", violations[0]["evidence"]["derived_action"])
        self.assertTrue(str(violations[0]["evidence"]["git_status"]).startswith("T"))


class RuntimeGovernanceRootWorkflowTests(unittest.TestCase):
    def test_root_is_base_trusted_and_invokes_both_runtime_guards(self):
        repo_root = Path(__file__).resolve().parents[3]
        workflow = (repo_root / ROOT_WORKFLOW).read_text(encoding="utf-8")
        self.assertIn("pull_request_target:", workflow)
        self.assertIn("github.event.pull_request.number == 418", workflow)
        self.assertIn("github.event.pull_request.base.sha", workflow)
        self.assertIn("github.event.pull_request.head.sha", workflow)
        self.assertIn("--enforce-transition-lineage", workflow)
        self.assertIn("--enforce-full-write-surface", workflow)
        self.assertIn("path_action_constraints.py", workflow)
        self.assertIn("path_action_policy.py", workflow)
        self.assertNotIn("checkout@v4\n        with:\n          ref: ${{ github.event.pull_request.head.sha }}", workflow)


if __name__ == "__main__":
    unittest.main()
