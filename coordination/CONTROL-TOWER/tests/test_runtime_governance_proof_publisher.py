from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime_governance_proof_policy import (  # noqa: E402
    EXPECTED_PR_NUMBER,
    EXPECTED_REPOSITORY,
    EXPECTED_WORKFLOW_NAME,
    EXPECTED_WORKFLOW_PATH,
    STATUS_CONTEXT,
    evaluate_live_proof,
)

HEAD = "b" * 40
BASE = "a" * 40
WORKFLOW_ID = 424242
RUN_ID = 777001


def fixtures(conclusion="success"):
    event = {
        "action": "completed",
        "repository": {"full_name": EXPECTED_REPOSITORY},
        "workflow": {"id": WORKFLOW_ID, "name": EXPECTED_WORKFLOW_NAME, "path": EXPECTED_WORKFLOW_PATH},
        "workflow_run": {
            "id": RUN_ID,
            "workflow_id": WORKFLOW_ID,
            "name": EXPECTED_WORKFLOW_NAME,
            "event": "pull_request_target",
            "status": "completed",
            "conclusion": conclusion,
        },
    }
    original = {
        "id": RUN_ID,
        "workflow_id": WORKFLOW_ID,
        "name": EXPECTED_WORKFLOW_NAME,
        "path": EXPECTED_WORKFLOW_PATH + "@main",
        "event": "pull_request_target",
        "status": "completed",
        "conclusion": conclusion,
        "html_url": f"https://github.com/{EXPECTED_REPOSITORY}/actions/runs/{RUN_ID}",
        "repository": {"full_name": EXPECTED_REPOSITORY},
        "pull_requests": [{"number": EXPECTED_PR_NUMBER, "head": {"sha": HEAD}, "base": {"sha": BASE}}],
    }
    expected = {"id": WORKFLOW_ID, "name": EXPECTED_WORKFLOW_NAME, "path": EXPECTED_WORKFLOW_PATH}
    current = {"number": EXPECTED_PR_NUMBER, "head": {"sha": HEAD}, "base": {"sha": BASE}}
    return event, original, expected, current


class ProofPolicyAdversarialTests(unittest.TestCase):
    def assert_no_success(self, decision):
        self.assertNotEqual("success", decision.state)

    def test_positive_success_binds_original_run_and_fixed_context(self):
        decision = evaluate_live_proof(*fixtures())
        self.assertTrue(decision.publish)
        self.assertEqual("success", decision.state)
        self.assertEqual(HEAD, decision.head_sha)
        self.assertEqual(STATUS_CONTEXT, decision.context)
        self.assertEqual(f"https://github.com/{EXPECTED_REPOSITORY}/actions/runs/{RUN_ID}", decision.target_url)

    def test_wrong_workflow_name_no_success(self):
        event, original, expected, current = fixtures()
        original["name"] = "Not the root"
        self.assert_no_success(evaluate_live_proof(event, original, expected, current))

    def test_wrong_workflow_id_no_success(self):
        event, original, expected, current = fixtures()
        original["workflow_id"] += 1
        self.assert_no_success(evaluate_live_proof(event, original, expected, current))

    def test_wrong_workflow_path_no_success(self):
        event, original, expected, current = fixtures()
        original["path"] = ".github/workflows/other.yml@main"
        self.assert_no_success(evaluate_live_proof(event, original, expected, current))

    def test_wrong_event_no_success(self):
        event, original, expected, current = fixtures()
        original["event"] = "pull_request"
        self.assert_no_success(evaluate_live_proof(event, original, expected, current))

    def test_wrong_repository_no_success(self):
        event, original, expected, current = fixtures()
        original["repository"]["full_name"] = "attacker/other"
        self.assert_no_success(evaluate_live_proof(event, original, expected, current))

    def test_wrong_pr_no_success(self):
        event, original, expected, current = fixtures()
        original["pull_requests"][0]["number"] = 419
        self.assert_no_success(evaluate_live_proof(event, original, expected, current))

    def test_empty_pr_binding_no_success(self):
        event, original, expected, current = fixtures()
        original["pull_requests"] = []
        self.assert_no_success(evaluate_live_proof(event, original, expected, current))

    def test_ambiguous_pr_binding_no_success(self):
        event, original, expected, current = fixtures()
        original["pull_requests"].append(copy.deepcopy(original["pull_requests"][0]))
        self.assert_no_success(evaluate_live_proof(event, original, expected, current))

    def test_missing_head_sha_no_success(self):
        event, original, expected, current = fixtures()
        original["pull_requests"][0]["head"] = {}
        self.assert_no_success(evaluate_live_proof(event, original, expected, current))

    def test_original_root_failure_never_success(self):
        decision = evaluate_live_proof(*fixtures("failure"))
        self.assertEqual("failure", decision.state)

    def test_skipped_cancelled_timed_out_never_success(self):
        for conclusion in ("skipped", "cancelled", "timed_out"):
            with self.subTest(conclusion=conclusion):
                decision = evaluate_live_proof(*fixtures(conclusion))
                self.assertEqual("failure", decision.state)

    def test_stale_old_run_cannot_masquerade_for_new_head(self):
        event, original, expected, current = fixtures()
        current["head"]["sha"] = "c" * 40
        decision = evaluate_live_proof(event, original, expected, current)
        self.assertEqual("error", decision.state)
        self.assertEqual(HEAD, decision.head_sha)
        self.assertNotEqual(current["head"]["sha"], decision.head_sha)

    def test_target_url_binds_original_run_id(self):
        event, original, expected, current = fixtures()
        original["html_url"] = f"https://github.com/{EXPECTED_REPOSITORY}/actions/runs/999999"
        self.assert_no_success(evaluate_live_proof(event, original, expected, current))

    def test_status_context_is_fixed_constant(self):
        decision = evaluate_live_proof(*fixtures())
        self.assertEqual("r145/runtime-governance-live-proof", decision.context)


class PublisherWorkflowStaticSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / ".github/workflows/runtime-governance-proof-publisher.yml"
        cls.text = cls.path.read_text(encoding="utf-8")
        cls.doc = yaml.safe_load(cls.text)

    def test_publisher_has_no_checkout_or_head_execution_surface(self):
        self.assertNotIn("actions/checkout", self.text)
        self.assertNotIn("github.event.pull_request.head", self.text)
        self.assertNotIn("secrets.", self.text)
        self.assertNotIn("actions/cache", self.text)
        self.assertNotIn("download-artifact", self.text)
        self.assertNotIn("GITHUB_SHA", self.text)

    def test_publisher_permissions_are_exactly_bounded(self):
        self.assertIn("actions: read", self.text)
        self.assertIn("pull-requests: read", self.text)
        self.assertIn("statuses: write", self.text)
        for forbidden in ("contents: write", "issues: write", "pull-requests: write", "deployments: write", "packages: write"):
            self.assertNotIn(forbidden, self.text)

    def test_workflow_run_is_completed_and_root_name_fixed(self):
        self.assertIn('workflows: ["Runtime governance root"]', self.text)
        self.assertIn("types: [completed]", self.text)
        self.assertIn('ROOT_NAME = "Runtime governance root"', self.text)
        self.assertIn('ROOT_PATH = ".github/workflows/runtime-governance-root.yml"', self.text)
        self.assertIn("PR_NUMBER = 418", self.text)

    def test_actual_head_comes_from_original_run_pr_binding_not_github_sha(self):
        self.assertIn('bindings = original.get("pull_requests")', self.text)
        self.assertIn('head_sha = head.get("sha")', self.text)
        self.assertNotIn("GITHUB_SHA", self.text)

    def test_current_pr_cross_check_prevents_stale_success(self):
        self.assertIn('request_json("GET", f"/repos/{REPO}/pulls/{PR_NUMBER}")', self.text)
        self.assertIn('"STALE_ROOT_RUN_FOR_OLDER_PR_HEAD"', self.text)

    def test_status_target_and_context_are_not_pr_controlled(self):
        self.assertIn('CONTEXT = "r145/runtime-governance-live-proof"', self.text)
        self.assertIn('expected_url = f"https://github.com/{REPO}/actions/runs/{run_id}"', self.text)
        self.assertNotIn("pull_request.title", self.text)
        self.assertNotIn("pull_request.body", self.text)

    def test_program_control_tower_observes_publisher_workflow(self):
        control = (ROOT / ".github/workflows/program-control-tower.yml").read_text(encoding="utf-8")
        self.assertIn('.github/workflows/runtime-governance-proof-publisher.yml', control)

    def test_root_workflow_is_not_part_of_candidate_mutation(self):
        publisher = self.text
        self.assertNotIn('contents: read', publisher)
        self.assertNotIn('contents: write', publisher)


class PublisherContractTests(unittest.TestCase):
    def test_contract_declares_pointer_not_acceptance_authority(self):
        contract = yaml.safe_load((ROOT / "coordination/CONTROL-TOWER/R145-RUNTIME-GOVERNANCE-PROOF-PUBLISHER.yaml").read_text(encoding="utf-8"))
        self.assertEqual("STOP_BEFORE_G1_G5", contract["runtime_hold"])
        self.assertEqual("DISCOVERY_HINT / LIVE_PROOF_POINTER / NOT_ACCEPTANCE_AUTHORITY", contract["proof_contract"]["status_role"])
        self.assertFalse(contract["architecture"]["publisher"]["checkout_repository"])
        self.assertFalse(contract["architecture"]["publisher"]["executes_pr_head_code"])
        self.assertTrue(contract["security"]["commit_status_never_substitutes_original_logs"])


if __name__ == "__main__":
    unittest.main()
