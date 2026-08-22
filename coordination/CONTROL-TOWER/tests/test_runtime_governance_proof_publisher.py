from __future__ import annotations

import copy
import json
import os
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = ROOT / ".github/workflows/runtime-governance-proof-publisher.yml"
CONTRACT_PATH = ROOT / "coordination/CONTROL-TOWER/R145-RUNTIME-GOVERNANCE-PROOF-PUBLISHER.yaml"
CONTROL_PATH = ROOT / ".github/workflows/program-control-tower.yml"

HEAD = "b" * 40
BASE = "a" * 40
WORKFLOW_ID = 424242
RUN_ID = 777001
REPO = "vxz2datoubo/second-brain-coordination"
ROOT_NAME = "Runtime governance root"
ROOT_PATH = ".github/workflows/runtime-governance-root.yml"
ROOT_FILENAME = "runtime-governance-root.yml"
WORKFLOW_METADATA_ENDPOINT = f"/repos/{REPO}/actions/workflows/{ROOT_FILENAME}"
PR_NUMBER = 418
CONTEXT = "r145/runtime-governance-live-proof"


def extract_production_python(text: str | None = None) -> str:
    raw = WORKFLOW_PATH.read_text(encoding="utf-8") if text is None else text
    start_marker = "          python3 - <<'PY'\n"
    end_marker = "\n          PY"
    start = raw.index(start_marker) + len(start_marker)
    end = raw.index(end_marker, start)
    return textwrap.dedent(raw[start:end])


def load_production_namespace(script: str | None = None) -> dict:
    code = extract_production_python() if script is None else script
    namespace = {"__name__": "r145_publisher_test"}
    exec(compile(code, "<runtime-governance-proof-publisher>", "exec"), namespace)
    return namespace


def fixtures(conclusion="success"):
    event = {
        "action": "completed",
        "repository": {"full_name": REPO},
        "workflow": {"id": WORKFLOW_ID, "name": ROOT_NAME, "path": ROOT_PATH},
        "workflow_run": {
            "id": RUN_ID,
            "workflow_id": WORKFLOW_ID,
            "name": ROOT_NAME,
            "event": "pull_request_target",
            "status": "completed",
            "conclusion": conclusion,
        },
    }
    original = {
        "id": RUN_ID,
        "workflow_id": WORKFLOW_ID,
        "name": ROOT_NAME,
        "path": ROOT_PATH + "@main",
        "event": "pull_request_target",
        "status": "completed",
        "conclusion": conclusion,
        "html_url": f"https://github.com/{REPO}/actions/runs/{RUN_ID}",
        "repository": {"full_name": REPO},
        "pull_requests": [{"number": PR_NUMBER, "head": {"sha": HEAD}, "base": {"sha": BASE}}],
    }
    expected = {"id": WORKFLOW_ID, "name": ROOT_NAME, "path": ROOT_PATH}
    current = {"number": PR_NUMBER, "head": {"sha": HEAD}, "base": {"sha": BASE}}
    return event, original, expected, current


class ProductionWorkflowSemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = extract_production_python()
        cls.ns = load_production_namespace(cls.script)
        cls.evaluate = staticmethod(cls.ns["evaluate_live_proof"])

    def assert_no_success(self, decision):
        self.assertNotEqual("success", decision["state"])

    def test_positive_success_binds_original_run_and_fixed_context(self):
        decision = self.evaluate(*fixtures())
        self.assertTrue(decision["publish"])
        self.assertEqual("success", decision["state"])
        self.assertEqual(HEAD, decision["head_sha"])
        self.assertEqual(CONTEXT, decision["context"])
        self.assertEqual(f"https://github.com/{REPO}/actions/runs/{RUN_ID}", decision["target_url"])

    def test_wrong_workflow_name_no_success(self):
        event, original, expected, current = fixtures()
        original["name"] = "Not the root"
        self.assert_no_success(self.evaluate(event, original, expected, current))

    def test_wrong_workflow_id_no_success(self):
        event, original, expected, current = fixtures()
        original["workflow_id"] += 1
        self.assert_no_success(self.evaluate(event, original, expected, current))

    def test_wrong_workflow_path_no_success(self):
        event, original, expected, current = fixtures()
        original["path"] = ".github/workflows/other.yml@main"
        self.assert_no_success(self.evaluate(event, original, expected, current))

    def test_wrong_event_no_success(self):
        event, original, expected, current = fixtures()
        original["event"] = "pull_request"
        self.assert_no_success(self.evaluate(event, original, expected, current))

    def test_wrong_repository_no_success(self):
        event, original, expected, current = fixtures()
        original["repository"]["full_name"] = "attacker/other"
        self.assert_no_success(self.evaluate(event, original, expected, current))

    def test_wrong_pr_no_success(self):
        event, original, expected, current = fixtures()
        original["pull_requests"][0]["number"] = 419
        self.assert_no_success(self.evaluate(event, original, expected, current))

    def test_empty_pr_binding_no_success(self):
        event, original, expected, current = fixtures()
        original["pull_requests"] = []
        self.assert_no_success(self.evaluate(event, original, expected, current))

    def test_ambiguous_pr_binding_no_success(self):
        event, original, expected, current = fixtures()
        original["pull_requests"].append(copy.deepcopy(original["pull_requests"][0]))
        self.assert_no_success(self.evaluate(event, original, expected, current))

    def test_missing_head_sha_fails_before_publish(self):
        event, original, expected, current = fixtures()
        original["pull_requests"][0]["head"] = {}
        decision = self.evaluate(event, original, expected, current)
        self.assertFalse(decision["publish"])
        self.assert_no_success(decision)

    def test_missing_base_sha_fails_before_publish(self):
        event, original, expected, current = fixtures()
        original["pull_requests"][0]["base"] = {}
        decision = self.evaluate(event, original, expected, current)
        self.assertFalse(decision["publish"])
        self.assert_no_success(decision)

    def test_original_root_failure_never_success(self):
        self.assertEqual("failure", self.evaluate(*fixtures("failure"))["state"])

    def test_skipped_cancelled_timed_out_never_success(self):
        for conclusion in ("skipped", "cancelled", "timed_out"):
            with self.subTest(conclusion=conclusion):
                self.assertEqual("failure", self.evaluate(*fixtures(conclusion))["state"])

    def test_unknown_conclusion_is_error(self):
        self.assertEqual("error", self.evaluate(*fixtures("mystery"))["state"])

    def test_stale_old_run_cannot_masquerade_for_new_head(self):
        event, original, expected, current = fixtures()
        current["head"]["sha"] = "c" * 40
        decision = self.evaluate(event, original, expected, current)
        self.assertEqual("error", decision["state"])
        self.assertEqual(HEAD, decision["head_sha"])
        self.assertNotEqual(current["head"]["sha"], decision["head_sha"])

    def test_target_url_binds_original_run_id(self):
        event, original, expected, current = fixtures()
        original["html_url"] = f"https://github.com/{REPO}/actions/runs/999999"
        self.assert_no_success(self.evaluate(event, original, expected, current))

    def test_status_context_is_fixed_constant(self):
        self.assertEqual(CONTEXT, self.evaluate(*fixtures())["context"])


class ProductionWorkflowMainPathTests(unittest.TestCase):
    def run_main(self, event, original, expected, current, script=None):
        namespace = load_production_namespace(script)
        calls = []

        def fake_request(method, path, body=None):
            calls.append((method, path, copy.deepcopy(body)))
            if method == "GET" and path == WORKFLOW_METADATA_ENDPOINT:
                return copy.deepcopy(expected)
            if method == "GET" and path == f"/repos/{REPO}/actions/runs/{RUN_ID}?exclude_pull_requests=false":
                return copy.deepcopy(original)
            if method == "GET" and path == f"/repos/{REPO}/pulls/{PR_NUMBER}":
                return copy.deepcopy(current)
            if method == "POST" and path == f"/repos/{REPO}/statuses/{HEAD}":
                return {"ok": True}
            raise AssertionError((method, path, body))

        namespace["request_json"] = fake_request
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            json.dump(event, handle)
            event_path = handle.name
        try:
            with mock.patch.dict(namespace["os"].environ, {"GITHUB_EVENT_PATH": event_path, "GITHUB_TOKEN": "test"}, clear=False):
                exit_code = None
                try:
                    namespace["main"]()
                except SystemExit as exc:
                    exit_code = exc.code
            return calls, exit_code
        finally:
            os.unlink(event_path)

    @staticmethod
    def status_posts(calls):
        return [call for call in calls if call[0] == "POST" and "/statuses/" in call[1]]

    def test_workflow_metadata_get_uses_exact_filename_endpoint(self):
        calls, code = self.run_main(*fixtures())
        self.assertIsNone(code)
        metadata_gets = [call for call in calls if call[0] == "GET" and "/actions/workflows/" in call[1]]
        self.assertEqual([("GET", WORKFLOW_METADATA_ENDPOINT, None)], metadata_gets)

    def test_positive_main_posts_success_to_bound_head_with_original_url_and_fixed_context(self):
        calls, code = self.run_main(*fixtures())
        self.assertIsNone(code)
        posts = self.status_posts(calls)
        self.assertEqual(1, len(posts))
        _, path, payload = posts[0]
        self.assertEqual(f"/repos/{REPO}/statuses/{HEAD}", path)
        self.assertEqual("success", payload["state"])
        self.assertEqual(CONTEXT, payload["context"])
        self.assertEqual(f"https://github.com/{REPO}/actions/runs/{RUN_ID}", payload["target_url"])

    def test_correct_filename_but_metadata_path_wrong_fails_closed(self):
        event, original, expected, current = fixtures()
        expected["path"] = ".github/workflows/other.yml"
        calls, code = self.run_main(event, original, expected, current)
        self.assertEqual(2, code)
        self.assertEqual([], self.status_posts(calls))
        self.assertIn(("GET", WORKFLOW_METADATA_ENDPOINT, None), calls)

    def test_correct_filename_but_workflow_id_or_name_wrong_fails_closed(self):
        for mutation in ("id", "name"):
            with self.subTest(mutation=mutation):
                event, original, expected, current = fixtures()
                if mutation == "id":
                    expected["id"] += 1
                else:
                    expected["name"] = "Wrong root name"
                calls, code = self.run_main(event, original, expected, current)
                self.assertEqual(2, code)
                self.assertEqual([], self.status_posts(calls))

    def test_stale_main_posts_error_to_original_bound_head_never_current_head(self):
        event, original, expected, current = fixtures()
        current["head"]["sha"] = "c" * 40
        calls, code = self.run_main(event, original, expected, current)
        self.assertEqual(2, code)
        posts = self.status_posts(calls)
        self.assertEqual(1, len(posts))
        self.assertEqual(f"/repos/{REPO}/statuses/{HEAD}", posts[0][1])
        self.assertEqual("error", posts[0][2]["state"])

    def test_wrong_workflow_identity_main_publishes_nothing(self):
        event, original, expected, current = fixtures()
        original["workflow_id"] += 1
        calls, code = self.run_main(event, original, expected, current)
        self.assertEqual(2, code)
        self.assertEqual([], self.status_posts(calls))

    def test_failure_main_posts_failure_not_success(self):
        calls, code = self.run_main(*fixtures("failure"))
        self.assertIsNone(code)
        posts = self.status_posts(calls)
        self.assertEqual("failure", posts[0][2]["state"])

    def test_bad_target_url_main_publishes_nothing(self):
        event, original, expected, current = fixtures()
        original["html_url"] = "https://github.com/attacker/run/1"
        calls, code = self.run_main(event, original, expected, current)
        self.assertEqual(2, code)
        self.assertEqual([], self.status_posts(calls))


class F02ProductionEndpointMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = extract_production_python()

    def assert_transport_rejects(self, mutated_script):
        helper = ProductionWorkflowMainPathTests()
        with self.assertRaises(AssertionError):
            helper.run_main(*fixtures(), script=mutated_script)

    def test_full_repo_path_used_as_workflow_id_is_detected(self):
        old = 'f"/repos/{REPO}/actions/workflows/{ROOT_FILENAME}"'
        new = 'f"/repos/{REPO}/actions/workflows/{ROOT_PATH}"'
        self.assertIn(old, self.script)
        self.assert_transport_rejects(self.script.replace(old, new, 1))

    def test_dotgithub_workflows_multisegment_endpoint_is_detected(self):
        old = 'f"/repos/{REPO}/actions/workflows/{ROOT_FILENAME}"'
        new = 'f"/repos/{REPO}/actions/workflows/.github/workflows/{ROOT_FILENAME}"'
        self.assertIn(old, self.script)
        self.assert_transport_rejects(self.script.replace(old, new, 1))

    def test_wrong_workflow_filename_is_detected(self):
        old = 'ROOT_FILENAME = "runtime-governance-root.yml"'
        new = 'ROOT_FILENAME = "wrong-root.yml"'
        self.assertIn(old, self.script)
        self.assert_transport_rejects(self.script.replace(old, new, 1))


class ProductionOnlyMutationSensitivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = extract_production_python()

    def assert_safety_property(self, script, case):
        namespace = load_production_namespace(script)
        evaluate = namespace["evaluate_live_proof"]
        event, original, expected, current = fixtures()
        if case == "workflow_id":
            original["workflow_id"] += 1
            self.assertNotEqual("success", evaluate(event, original, expected, current)["state"])
        elif case == "workflow_path":
            original["path"] = ".github/workflows/other.yml@main"
            self.assertNotEqual("success", evaluate(event, original, expected, current)["state"])
        elif case == "pr_binding":
            original["pull_requests"].append(copy.deepcopy(original["pull_requests"][0]))
            self.assertNotEqual("success", evaluate(event, original, expected, current)["state"])
        elif case == "head_validation":
            original["pull_requests"][0]["head"] = {}
            self.assertFalse(evaluate(event, original, expected, current)["publish"])
        elif case == "stale":
            current["head"]["sha"] = "c" * 40
            self.assertNotEqual("success", evaluate(event, original, expected, current)["state"])
        elif case == "context":
            self.assertEqual(CONTEXT, evaluate(event, original, expected, current)["context"])
        elif case == "target_url":
            original["html_url"] = "https://github.com/attacker/run/1"
            self.assertNotEqual("success", evaluate(event, original, expected, current)["state"])
        elif case == "failure_mapping":
            event, original, expected, current = fixtures("failure")
            self.assertNotEqual("success", evaluate(event, original, expected, current)["state"])
        elif case == "status_target_sha":
            current["head"]["sha"] = "c" * 40
            helper = ProductionWorkflowMainPathTests()
            calls, _ = helper.run_main(event, original, expected, current, script=script)
            posts = helper.status_posts(calls)
            self.assertEqual(f"/repos/{REPO}/statuses/{HEAD}", posts[0][1])
        elif case == "payload_context":
            helper = ProductionWorkflowMainPathTests()
            calls, _ = helper.run_main(event, original, expected, current, script=script)
            posts = helper.status_posts(calls)
            self.assertEqual(CONTEXT, posts[0][2]["context"])
        elif case == "payload_target_url":
            helper = ProductionWorkflowMainPathTests()
            calls, _ = helper.run_main(event, original, expected, current, script=script)
            posts = helper.status_posts(calls)
            self.assertEqual(f"https://github.com/{REPO}/actions/runs/{RUN_ID}", posts[0][2]["target_url"])
        else:
            raise AssertionError(case)

    def test_production_only_security_mutations_are_detected_without_policy_module(self):
        mutations = [
            ("workflow_id", 'if wf.get("id") != expected_id or wr.get("workflow_id") != expected_id or original.get("workflow_id") != expected_id:', 'if wf.get("id") != expected_id or wr.get("workflow_id") != expected_id:'),
            ("workflow_path", 'if not isinstance(original_path, str) or original_path.split("@", 1)[0] != ROOT_PATH:', "if False:"),
            ("pr_binding", 'if not isinstance(bindings, list) or len(bindings) != 1:', 'if not isinstance(bindings, list):'),
            ("head_validation", "if head_sha is None:", "if False:"),
            ("stale", 'if current_head.get("sha") != head_sha or current_base.get("sha") != base_sha:', "if False:"),
            ("context", 'CONTEXT = "r145/runtime-governance-live-proof"', 'CONTEXT = "attacker/context"'),
            ("target_url", "if target_url != expected_url:", "if False:"),
            ("failure_mapping", 'if conclusion == "success":', 'if conclusion in {"success", "failure"}:'),
            ("status_target_sha", 'request_json("POST", f\'/repos/{REPO}/statuses/{decision["head_sha"]}\', payload)', 'request_json("POST", f\'/repos/{REPO}/statuses/{current_pr["head"]["sha"]}\', payload)'),
            ("payload_context", '"context": decision["context"],', '"context": "attacker/context",'),
            ("payload_target_url", '"target_url": decision["target_url"],', '"target_url": "https://attacker.invalid/",'),
        ]
        for case, old, new in mutations:
            with self.subTest(case=case):
                self.assertIn(old, self.script)
                mutated = self.script.replace(old, new, 1)
                self.assertNotEqual(mutated, self.script)
                with self.assertRaises((AssertionError, IndexError)):
                    self.assert_safety_property(mutated, case)


class PublisherWorkflowStaticSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW_PATH.read_text(encoding="utf-8")
        cls.doc = yaml.safe_load(cls.text)
        cls.script = extract_production_python(cls.text)

    def test_publisher_has_no_checkout_or_head_execution_surface(self):
        for forbidden in ("actions/checkout", "github.event.pull_request.head", "secrets.", "actions/cache", "download-artifact", "GITHUB_SHA"):
            self.assertNotIn(forbidden, self.text)

    def test_publisher_permissions_are_exactly_bounded(self):
        self.assertEqual({"actions": "read", "pull-requests": "read", "statuses": "write"}, self.doc["permissions"])

    def test_workflow_run_is_completed_and_root_identity_fixed(self):
        self.assertIn('workflows: ["Runtime governance root"]', self.text)
        self.assertIn("types: [completed]", self.text)
        self.assertIn('ROOT_NAME = "Runtime governance root"', self.script)
        self.assertIn('ROOT_PATH = ".github/workflows/runtime-governance-root.yml"', self.script)
        self.assertIn('ROOT_FILENAME = "runtime-governance-root.yml"', self.script)
        self.assertIn("PR_NUMBER = 418", self.script)

    def test_metadata_endpoint_uses_filename_but_retains_full_path_identity_check(self):
        self.assertIn('expected = request_json("GET", f"/repos/{REPO}/actions/workflows/{ROOT_FILENAME}")', self.script)
        self.assertNotIn('actions/workflows/{ROOT_PATH}', self.script)
        self.assertIn('expected.get("name") != ROOT_NAME or expected.get("path") != ROOT_PATH', self.script)

    def test_status_target_and_context_are_not_pr_controlled(self):
        self.assertIn('CONTEXT = "r145/runtime-governance-live-proof"', self.script)
        self.assertIn('expected_url = f"https://github.com/{REPO}/actions/runs/{run_id}"', self.script)
        self.assertNotIn("pull_request.title", self.script)
        self.assertNotIn("pull_request.body", self.script)

    def test_program_control_tower_observes_publisher_workflow(self):
        self.assertIn(".github/workflows/runtime-governance-proof-publisher.yml", CONTROL_PATH.read_text(encoding="utf-8"))

    def test_no_shadow_policy_import_or_second_executable_policy_source(self):
        self.assertNotIn("runtime_governance_proof_policy", self.script)
        self.assertFalse((ROOT / "coordination/CONTROL-TOWER/runtime_governance_proof_policy.py").exists())
        self.assertIn("def evaluate_live_proof(", self.script)
        self.assertIn("decision = evaluate_live_proof(event, original, expected, current_pr)", self.script)


class PublisherContractTests(unittest.TestCase):
    def test_contract_declares_pointer_not_acceptance_authority(self):
        contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual("STOP_BEFORE_G1_G5", contract["runtime_hold"])
        self.assertEqual("DISCOVERY_HINT / LIVE_PROOF_POINTER / NOT_ACCEPTANCE_AUTHORITY", contract["proof_contract"]["status_role"])
        self.assertFalse(contract["architecture"]["publisher"]["checkout_repository"])
        self.assertFalse(contract["architecture"]["publisher"]["executes_pr_head_code"])
        self.assertTrue(contract["security"]["commit_status_never_substitutes_original_logs"])
        self.assertEqual("ABSENT", contract["f01_remediation"]["shadow_policy_module"])
        self.assertEqual("TESTED_POLICY_IS_THE_PRIVILEGED_EXECUTION_PATH", contract["f01_remediation"]["invariant"])


if __name__ == "__main__":
    unittest.main()
