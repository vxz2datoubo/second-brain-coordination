from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "unified-execution-fabric.yml"


class ExactHeadCIGovernanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def _step(self, name: str) -> str:
        marker = f"      - name: {name}\n"
        start = self.workflow.find(marker)
        self.assertNotEqual(start, -1, f"workflow step missing: {name}")
        next_step = self.workflow.find("\n      - ", start + len(marker))
        if next_step == -1:
            return self.workflow[start:]
        return self.workflow[start:next_step]

    def test_workflow_dispatch_requires_expected_head(self) -> None:
        self.assertRegex(
            self.workflow,
            re.compile(
                r"^  workflow_dispatch:\n"
                r"    inputs:\n"
                r"      expected_head:\n"
                r"(?:        .*\n)*?"
                r"        required: true\n"
                r"        type: string\n",
                re.MULTILINE,
            ),
        )

    def test_expected_head_is_full_40_hex_and_invalid_or_short_sha_fails_closed(self) -> None:
        validation = self._step("Validate exact-head dispatch contract")
        self.assertIn("^[0-9a-fA-F]{40}$", validation)
        self.assertIn("validation_exit_code=64", validation)
        self.assertIn('exit "${validation_exit_code}"', validation)

        full_sha = re.compile(r"^[0-9a-fA-F]{40}$")
        self.assertIsNotNone(full_sha.fullmatch("7907e57dce45a025511e5cded00bfdafac882848"))
        for invalid in (
            "7907e57",
            "7907e57dce45a025511e5cded00bfdafac88284",
            "7907e57dce45a025511e5cded00bfdafac8828480",
            "z907e57dce45a025511e5cded00bfdafac882848",
            "",
        ):
            self.assertIsNone(full_sha.fullmatch(invalid), invalid)

    def test_exact_checkout_is_explicitly_bound_to_expected_head(self) -> None:
        checkout = self._step("Exact-head checkout")
        self.assertIn("if: github.event_name == 'workflow_dispatch'", checkout)
        self.assertIn("uses: actions/checkout@v4", checkout)
        self.assertIn("ref: ${{ inputs.expected_head }}", checkout)
        self.assertIn("fetch-depth: 0", checkout)
        self.assertNotIn("github.sha", checkout)
        self.assertNotIn("pull_request", checkout)

    def test_rev_parse_identity_equality_is_mechanical_and_fail_closed(self) -> None:
        identity = self._step("Prove exact checkout identity")
        self.assertIn('actual_checkout_sha="$(git log -1 --format=%H)"', identity)
        self.assertIn('rev_parse_head="$(git rev-parse HEAD)"', identity)
        self.assertIn('"${actual_checkout_sha}" != "${EXPECTED_HEAD}"', identity)
        self.assertIn('"${rev_parse_head}" != "${EXPECTED_HEAD}"', identity)
        self.assertIn("identity_exit_code=67", identity)
        self.assertIn("identity_exit_code=68", identity)
        self.assertIn('exit "${identity_exit_code}"', identity)

    def test_pull_request_synthetic_merge_is_never_labeled_exact_head_authority(self) -> None:
        pr_checkout = self._step("Bootstrap PR checkout (NOT exact-head authority)")
        classification = self._step("Classify pull-request checkout as bootstrap only")
        evidence = self._step("Publish exact-head audit evidence")

        self.assertIn("if: github.event_name == 'pull_request'", pr_checkout)
        self.assertNotIn("ref: ${{ inputs.expected_head }}", pr_checkout)
        self.assertIn("exact_head_authority=false", classification)
        self.assertIn("PULL_REQUEST_BOOTSTRAP_NOT_EXACT_HEAD_AUTHORITY", classification)
        self.assertIn("pull_request_synthetic_merge_may_be_present=true", classification)
        self.assertIn("if: always() && github.event_name == 'workflow_dispatch'", evidence)
        self.assertIn("exact_head_authority=true", evidence)

    def test_exact_head_authority_uses_canonical_workflow_definition(self) -> None:
        validation = self._step("Validate exact-head dispatch contract")
        self.assertIn('expected_workflow_ref="refs/heads/${DEFAULT_BRANCH}"', validation)
        self.assertIn('"${GITHUB_REF}" != "${expected_workflow_ref}"', validation)
        self.assertIn("validation_exit_code=65", validation)
        self.assertIn("workflow_ref=${{ github.workflow_ref }}", self.workflow)
        self.assertIn("workflow_sha=${{ github.workflow_sha }}", self.workflow)

    def test_required_unified_execution_tests_and_single_canonical_python_runtime_remain(self) -> None:
        command = "python -m unittest discover -s tests -p 'test_unified_execution*.py' -v"
        self.assertIn(command, self.workflow)
        self.assertEqual(self.workflow.count("python-version: '3.11'"), 1)
        self.assertNotIn("python-version: '3.13'", self.workflow)
        self.assertNotIn("matrix:", self.workflow)

    def test_durable_exact_head_evidence_contains_required_identity_and_result_fields(self) -> None:
        job_identity = self._step("Resolve durable Actions job identity")
        evidence = self._step("Publish exact-head audit evidence")

        self.assertIn("/actions/runs/${GITHUB_RUN_ID}/jobs", job_identity)
        self.assertIn("job_id=${job_id}", job_identity)
        for token in (
            "requested_expected_head=",
            "actual_checkout_sha=",
            "git_rev_parse_head=",
            "workflow_run_id=",
            "job_id=",
            "event=",
            "command_set=",
            "validation_exit_code=",
            "identity_exit_code=",
            "test_exit_code=",
            "test_result=",
            "stdout_sha256=",
            "stderr_sha256=",
            "hygiene_exit_code=",
            "checkout_identity_class=WORKFLOW_DISPATCH_EXACT_COMMIT",
        ):
            self.assertIn(token, evidence)
        self.assertIn("GITHUB_STEP_SUMMARY", evidence)

    def test_historical_full_commit_is_not_restricted_to_current_pr_or_branch(self) -> None:
        validation = self._step("Validate exact-head dispatch contract")
        checkout = self._step("Exact-head checkout")
        identity = self._step("Prove exact checkout identity")
        combined = validation + checkout + identity

        self.assertIn("ref: ${{ inputs.expected_head }}", checkout)
        for forbidden in (
            "github.event.pull_request.head.sha",
            "git merge-base --is-ancestor",
            "git branch --contains",
            "refs/pull/",
        ):
            self.assertNotIn(forbidden, combined)


if __name__ == "__main__":
    unittest.main()
