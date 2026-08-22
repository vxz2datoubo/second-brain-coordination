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
ROOT_WF = ROOT / ".github/workflows/runtime-governance-root.yml"
PUB_WF = ROOT / ".github/workflows/runtime-governance-proof-publisher.yml"
RECEIPT = ROOT / "coordination/CONTROL-TOWER/R145-RUNTIME-GOVERNANCE-PROOF-PUBLISHER.yaml"

REPO = "vxz2datoubo/second-brain-coordination"
PR = 418
HEAD = "b" * 40
BASE = "a" * 40
H2 = "c" * 40
B2 = "d" * 40
RUN_ID = "777001"
TARGET_URL = f"https://github.com/{REPO}/actions/runs/{RUN_ID}"
CONTEXT = "r145/runtime-governance-live-proof"
PENDING_STEP = "Validate event binding and publish pending"
FINAL_STEP = "Publish success only after all required guards"


def workflow_text() -> str:
    return ROOT_WF.read_text(encoding="utf-8")


def extract_step_python(step_name: str, text: str | None = None) -> str:
    raw = workflow_text() if text is None else text
    anchor = f"      - name: {step_name}\n"
    pos = raw.index(anchor)
    start_marker = "          python3 - <<'PY'\n"
    start = raw.index(start_marker, pos) + len(start_marker)
    end = raw.index("\n          PY", start)
    return textwrap.dedent(raw[start:end])


def load_namespace(script: str) -> dict:
    namespace = {"__name__": "r145_root_test"}
    exec(compile(script, "<runtime-governance-root-production>", "exec"), namespace)
    return namespace


def event_fixture(pr: int = PR, head: str | None = HEAD, base: str | None = BASE) -> dict:
    head_obj = {} if head is None else {"sha": head}
    base_obj = {} if base is None else {"sha": base}
    return {
        "repository": {"full_name": REPO},
        "pull_request": {
            "number": pr,
            "head": {**head_obj, "ref": "attacker-free-text"},
            "base": base_obj,
            "title": "attacker title pr=999 head=deadbeef",
            "body": "attacker body",
        },
    }


def base_env() -> dict[str, str]:
    return {
        "GITHUB_TOKEN": "test-token",
        "GITHUB_EVENT_NAME": "pull_request_target",
        "GITHUB_EVENT_ACTION": "synchronize",
        "GITHUB_REPOSITORY": REPO,
        "GITHUB_RUN_ID": RUN_ID,
        "GITHUB_SERVER_URL": "https://github.com",
    }


def run_pending(event: dict | None = None, script: str | None = None, extra_env: dict[str, str] | None = None):
    namespace = load_namespace(extract_step_python(PENDING_STEP) if script is None else script)
    calls: list[tuple[str, str, dict | None]] = []

    def fake_request(method, path, body=None):
        calls.append((method, path, copy.deepcopy(body)))
        return {"ok": True}

    namespace["request_json"] = fake_request
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as event_file:
        json.dump(event_fixture() if event is None else event, event_file)
        event_path = event_file.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as output_file:
        output_path = output_file.name
    env = base_env()
    env.update({"GITHUB_EVENT_PATH": event_path, "GITHUB_OUTPUT": output_path})
    if extra_env:
        env.update(extra_env)
    code = None
    try:
        with mock.patch.dict(namespace["os"].environ, env, clear=True):
            try:
                namespace["main"]()
            except SystemExit as exc:
                code = exc.code
        outputs: dict[str, str] = {}
        for line in Path(output_path).read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                outputs[key] = value
        return calls, code, outputs
    finally:
        os.unlink(event_path)
        os.unlink(output_path)


def run_final(
    guards_result: str,
    script: str | None = None,
    head: str = HEAD,
    base: str = BASE,
    bound_target_url: str = TARGET_URL,
    extra_env: dict[str, str] | None = None,
):
    namespace = load_namespace(extract_step_python(FINAL_STEP) if script is None else script)
    calls: list[tuple[str, str, dict | None]] = []

    def fake_request(method, path, body=None):
        calls.append((method, path, copy.deepcopy(body)))
        return {"ok": True}

    namespace["request_json"] = fake_request
    env = base_env()
    env.update({
        "HEAD_SHA": head,
        "BASE_SHA": base,
        "BOUND_TARGET_URL": bound_target_url,
        "GUARDS_RESULT": guards_result,
    })
    if extra_env:
        env.update(extra_env)
    code = None
    with mock.patch.dict(namespace["os"].environ, env, clear=True):
        try:
            namespace["main"]()
        except SystemExit as exc:
            code = exc.code
    return calls, code


def status_posts(calls):
    return [call for call in calls if call[0] == "POST" and "/statuses/" in call[1]]


def assert_pending_contract(calls, outputs):
    posts = status_posts(calls)
    assert len(posts) == 1
    assert posts[0][1] == f"/repos/{REPO}/statuses/{HEAD}"
    assert posts[0][2]["state"] == "pending"
    assert posts[0][2]["context"] == CONTEXT
    assert posts[0][2]["target_url"] == TARGET_URL
    assert outputs == {"head_sha": HEAD, "base_sha": BASE, "target_url": TARGET_URL}


def assert_static_contract(text: str):
    data = yaml.safe_load(text)
    assert data["permissions"] == {"contents": "read", "statuses": "write"}
    jobs = data["jobs"]
    assert jobs["r145-runtime-root-guards"]["strategy"]["matrix"]["python-version"] == ["3.11", "3.13"]
    assert jobs["r145-runtime-root-guards"]["needs"] == "r145-live-proof-bind"
    final = jobs["r145-live-proof-finalize"]
    assert final["needs"] == ["r145-live-proof-bind", "r145-runtime-root-guards"]
    assert "always()" in final["if"]
    assert "needs.r145-live-proof-bind.result == 'success'" in final["if"]
    assert "ref: ${{ needs.r145-live-proof-bind.outputs.base_sha }}" in text
    assert 'git fetch --no-tags origin "$HEAD_SHA"' in text
    assert 'git cat-file -e "${HEAD_SHA}^{commit}"' in text
    assert "python path_action_constraints.py" in text
    assert "--enforce-transition-lineage" in text
    assert "python path_action_policy.py" in text
    assert "--enforce-full-write-surface" in text
    assert "R145_BASE_TRUSTED_ENFORCEMENT_ROOT_MUTATION_FORBIDDEN" in text
    assert ".github/workflows/runtime-governance-root.yml" in text
    assert "GITHUB_SHA" not in text
    assert "pull_request.title" not in text
    assert "pull_request.body" not in text
    assert "pull_request.head.ref" not in text
    pending_script = extract_step_python(PENDING_STEP, text)
    assert '"state": "pending"' in pending_script
    assert '"state": "success"' not in pending_script


class ProductionRootPendingTests(unittest.TestCase):
    def test_pending_targets_exact_event_bound_head(self):
        calls, code, outputs = run_pending()
        self.assertIsNone(code)
        assert_pending_contract(calls, outputs)

    def test_pending_target_url_is_current_root_run(self):
        calls, code, _ = run_pending()
        self.assertIsNone(code)
        self.assertEqual(TARGET_URL, status_posts(calls)[0][2]["target_url"])

    def test_wrong_pr_number_fails_closed_without_status(self):
        calls, code, _ = run_pending(event_fixture(pr=419))
        self.assertEqual("ROOT_PR_NUMBER_MISMATCH", code)
        self.assertEqual([], status_posts(calls))

    def test_malformed_or_missing_head_never_targets_other_sha(self):
        for head in ("bad", None):
            with self.subTest(head=head):
                calls, code, _ = run_pending(event_fixture(head=head))
                self.assertEqual([], status_posts(calls))
                self.assertIn("HEAD_SHA", str(code))

    def test_malformed_or_missing_base_never_writes_status(self):
        for base in ("bad", None):
            with self.subTest(base=base):
                calls, code, _ = run_pending(event_fixture(base=base))
                self.assertEqual([], status_posts(calls))
                self.assertIn("BASE_SHA", str(code))

    def test_pr_title_body_and_branch_free_text_do_not_bind(self):
        event = event_fixture()
        event["pull_request"]["title"] = "R145_LIVE_ROOT pr=999 head=" + H2 + " base=" + B2
        event["pull_request"]["body"] = "statuses/" + H2
        event["pull_request"]["head"]["ref"] = "evil-branch-" + H2
        calls, code, outputs = run_pending(event)
        self.assertIsNone(code)
        assert_pending_contract(calls, outputs)

    def test_wrong_event_name_or_action_fails_closed(self):
        for env in ({"GITHUB_EVENT_NAME": "pull_request"}, {"GITHUB_EVENT_ACTION": "closed"}):
            with self.subTest(env=env):
                calls, _, _ = run_pending(extra_env=env)
                self.assertEqual([], status_posts(calls))


class ProductionRootFinalTests(unittest.TestCase):
    def test_success_posts_only_for_successful_guard_aggregate(self):
        calls, code = run_final("success")
        self.assertIsNone(code)
        post = status_posts(calls)[0]
        self.assertEqual(f"/repos/{REPO}/statuses/{HEAD}", post[1])
        self.assertEqual("success", post[2]["state"])
        self.assertEqual(CONTEXT, post[2]["context"])
        self.assertEqual(TARGET_URL, post[2]["target_url"])

    def test_guard_failure_posts_failure_to_same_head(self):
        calls, code = run_final("failure")
        self.assertEqual(2, code)
        post = status_posts(calls)[0]
        self.assertEqual(f"/repos/{REPO}/statuses/{HEAD}", post[1])
        self.assertEqual("failure", post[2]["state"])
        self.assertEqual(TARGET_URL, post[2]["target_url"])

    def test_nonstandard_guard_result_posts_error(self):
        for result in ("cancelled", "skipped", "unknown"):
            with self.subTest(result=result):
                calls, code = run_final(result)
                self.assertEqual(2, code)
                self.assertEqual("error", status_posts(calls)[0][2]["state"])

    def test_bound_target_url_mismatch_posts_error_with_current_run_url(self):
        calls, code = run_final("success", bound_target_url="https://attacker.invalid/run")
        self.assertEqual(2, code)
        post = status_posts(calls)[0]
        self.assertEqual("error", post[2]["state"])
        self.assertEqual(TARGET_URL, post[2]["target_url"])

    def test_invalid_final_head_or_base_does_not_write_other_sha(self):
        for head, base in (("bad", BASE), (HEAD, "bad")):
            with self.subTest(head=head, base=base):
                calls, code = run_final("failure", head=head, base=base)
                self.assertEqual([], status_posts(calls))
                self.assertEqual("ROOT_FINAL_BINDING_INVALID", code)


class RootStaticSecurityTests(unittest.TestCase):
    def test_exact_permissions_are_contents_read_and_statuses_write_only(self):
        assert_static_contract(workflow_text())

    def test_success_job_is_structurally_after_both_guard_lanes(self):
        text = workflow_text()
        assert_static_contract(text)
        self.assertIn("needs: [r145-live-proof-bind, r145-runtime-root-guards]", text)
        self.assertIn("GUARDS_RESULT: ${{ needs.r145-runtime-root-guards.result }}", text)

    def test_canonical_base_only_checkout_and_head_data_only_are_retained(self):
        text = workflow_text()
        self.assertIn("ref: ${{ needs.r145-live-proof-bind.outputs.base_sha }}", text)
        self.assertIn('git fetch --no-tags origin "$HEAD_SHA"', text)
        self.assertIn('git cat-file -e "${HEAD_SHA}^{commit}"', text)
        self.assertNotIn("git checkout \"$HEAD_SHA\"", text)
        self.assertNotIn("ref: ${{ github.event.pull_request.head.sha }}", text)

    def test_github_sha_cannot_substitute_for_pr_head(self):
        self.assertNotIn("GITHUB_SHA", workflow_text())

    def test_protected_enforcement_roots_remain_guarded(self):
        text = workflow_text()
        for path in (
            ".github/workflows/r145-final-active-gate.yml",
            ".github/workflows/runtime-governance-root.yml",
            "coordination/CONTROL-TOWER/path_action_constraints.py",
            "coordination/CONTROL-TOWER/path_action_policy.py",
            "coordination/CONTROL-TOWER/R145-BOOTSTRAP-CLEANUP-SCOPE-AMENDMENT.yaml",
        ):
            self.assertIn(path, text)
        self.assertIn("R145_BASE_TRUSTED_ENFORCEMENT_ROOT_MUTATION_FORBIDDEN", text)

    def test_root_is_only_active_writer_for_fixed_context(self):
        self.assertFalse(PUB_WF.exists())
        writers = []
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            if CONTEXT in path.read_text(encoding="utf-8"):
                writers.append(path.name)
        self.assertEqual(["runtime-governance-root.yml"], sorted(writers))

    def test_receipt_declares_single_current_authority_and_stop_gate(self):
        receipt = yaml.safe_load(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual("STOP_BEFORE_G1_G5", receipt["runtime_hold"])
        self.assertEqual("RUNTIME_GOVERNANCE_ROOT_DIRECT_STATUS", receipt["architecture"]["current_primary_writer"])
        self.assertEqual("ABSENT_FROM_CANONICAL_TREE", receipt["publisher_retirement"]["workflow_state"])
        self.assertEqual({"contents": "read", "statuses": "write"}, receipt["architecture"]["root_permissions"])


class ProductionOnlyMutationSensitivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = workflow_text()
        cls.pending = extract_step_python(PENDING_STEP)
        cls.final = extract_step_python(FINAL_STEP)

    def test_permission_mutation_is_detected(self):
        mutated = self.text.replace("  statuses: write\n", "  issues: write\n", 1)
        with self.assertRaises(AssertionError):
            assert_static_contract(mutated)

    def test_head_binding_mutation_to_github_sha_is_detected(self):
        old = 'head_sha = _sha(head.get("sha"))'
        new = 'head_sha = _sha(os.environ.get("GITHUB_SHA"))'
        self.assertIn(old, self.pending)
        calls, _, outputs = run_pending(script=self.pending.replace(old, new, 1), extra_env={"GITHUB_SHA": H2})
        with self.assertRaises(AssertionError):
            assert_pending_contract(calls, outputs)

    def test_base_binding_mutation_is_detected(self):
        old = 'base_sha = _sha(base.get("sha"))'
        new = 'base_sha = _sha(os.environ.get("MUTATED_BASE_SHA"))'
        self.assertIn(old, self.pending)
        calls, _, outputs = run_pending(script=self.pending.replace(old, new, 1), extra_env={"MUTATED_BASE_SHA": B2})
        with self.assertRaises(AssertionError):
            assert_pending_contract(calls, outputs)

    def test_target_url_mutation_is_detected(self):
        old = 'return f"{server}/{repo}/actions/runs/{run_id}"'
        new = 'return f"{server}/{repo}/actions/runs/999"'
        self.assertIn(old, self.pending)
        calls, _, outputs = run_pending(script=self.pending.replace(old, new, 1))
        with self.assertRaises(AssertionError):
            assert_pending_contract(calls, outputs)

    def test_success_ordering_mutation_is_detected(self):
        old = "needs: [r145-live-proof-bind, r145-runtime-root-guards]"
        new = "needs: r145-live-proof-bind"
        self.assertIn(old, self.text)
        with self.assertRaises(AssertionError):
            assert_static_contract(self.text.replace(old, new, 1))

    def test_failure_mapping_mutation_is_detected(self):
        old = '"state": "failure",\n                      "head_sha": head_sha,'
        new = '"state": "success",\n                      "head_sha": head_sha,'
        self.assertIn(old, self.final)
        calls, _ = run_final("failure", script=self.final.replace(old, new, 1))
        with self.assertRaises(AssertionError):
            self.assertEqual("failure", status_posts(calls)[0][2]["state"])

    def test_guard_removal_mutation_is_detected(self):
        old = "python path_action_policy.py"
        self.assertIn(old, self.text)
        with self.assertRaises(AssertionError):
            assert_static_contract(self.text.replace(old, "python removed_guard.py", 1))

    def test_protected_root_guard_removal_is_detected(self):
        old = "R145_BASE_TRUSTED_ENFORCEMENT_ROOT_MUTATION_FORBIDDEN"
        self.assertIn(old, self.text)
        with self.assertRaises(AssertionError):
            assert_static_contract(self.text.replace(old, "REMOVED_PROTECTED_ROOT_GUARD", 1))


if __name__ == "__main__":
    unittest.main()
