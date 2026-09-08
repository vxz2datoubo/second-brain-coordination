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
        self.assertIn("id: exact_checkout", checkout)
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

    def test_exact_head_authority_uses_canonical_workflow_definition(self) -> None:
        validation = self._step("Validate exact-head dispatch contract")
        self.assertIn('expected_workflow_ref="refs/heads/${DEFAULT_BRANCH}"', validation)
        self.assertIn('"${GITHUB_REF}" != "${expected_workflow_ref}"', validation)
        self.assertIn("validation_exit_code=65", validation)
        self.assertIn("workflow_ref=${WORKFLOW_REF}", self.workflow)
        self.assertIn("workflow_sha=${WORKFLOW_SHA}", self.workflow)

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
            "validation_outcome=",
            "checkout_outcome=",
            "identity_outcome=",
            "job_id_outcome=",
            "test_outcome=",
            "hygiene_outcome=",
            "validation_exit_code=",
            "identity_exit_code=",
            "test_exit_code=",
            "test_result=",
            "stdout_sha256=",
            "stderr_sha256=",
            "hygiene_exit_code=",
            "audit_record_status=",
            "failure_reason=",
            "exact_head_authority=",
            "checkout_identity_class=",
            "authority_promotion_condition=ALL_REQUIRED_GATES_SUCCESS_AND_REQUIRED_OUTPUTS_COMPLETE",
        ):
            self.assertIn(token, evidence)
        self.assertIn("GITHUB_STEP_SUMMARY", evidence)

    def test_audit_publisher_runs_after_failure_but_authority_defaults_false(self) -> None:
        evidence = self._step("Publish exact-head audit evidence")
        self.assertIn("if: always() && github.event_name == 'workflow_dispatch'", evidence)
        default_pos = evidence.find("exact_head_authority=false")
        promotion_pos = evidence.find("exact_head_authority=true")
        self.assertGreaterEqual(default_pos, 0)
        self.assertGreater(promotion_pos, default_pos)
        self.assertIn(
            'checkout_identity_class="WORKFLOW_DISPATCH_EXACT_COMMIT_FAILED_OR_INCOMPLETE"',
            evidence,
        )
        self.assertIn('audit_record_status="FAILURE_OR_INCOMPLETE"', evidence)

    def test_validation_failure_or_skip_cannot_promote_authority(self) -> None:
        evidence = self._step("Publish exact-head audit evidence")
        self.assertIn(
            'VALIDATION_OUTCOME: ${{ steps.validate_expected_head.outcome }}', evidence
        )
        self.assertIn(
            'require_success_outcome "VALIDATION" "${VALIDATION_OUTCOME}"', evidence
        )
        self.assertIn('"${VALIDATION_EXIT_CODE}" != "0"', evidence)
        self.assertIn("VALIDATION_EXIT_CODE_NOT_ZERO", evidence)

    def test_checkout_or_identity_failure_or_skip_cannot_promote_authority(self) -> None:
        evidence = self._step("Publish exact-head audit evidence")
        self.assertIn('CHECKOUT_OUTCOME: ${{ steps.exact_checkout.outcome }}', evidence)
        self.assertIn('IDENTITY_OUTCOME: ${{ steps.exact_identity.outcome }}', evidence)
        self.assertIn('require_success_outcome "CHECKOUT" "${CHECKOUT_OUTCOME}"', evidence)
        self.assertIn('require_success_outcome "IDENTITY" "${IDENTITY_OUTCOME}"', evidence)
        self.assertIn("ACTUAL_CHECKOUT_SHA_MISMATCH", evidence)
        self.assertIn("REV_PARSE_HEAD_MISMATCH", evidence)
        self.assertIn('"${IDENTITY_EXIT_CODE}" != "0"', evidence)

    def test_job_id_failure_skip_or_missing_output_cannot_promote_authority(self) -> None:
        evidence = self._step("Publish exact-head audit evidence")
        self.assertIn('JOB_ID_OUTCOME: ${{ steps.job_identity.outcome }}', evidence)
        self.assertIn('require_success_outcome "JOB_ID" "${JOB_ID_OUTCOME}"', evidence)
        self.assertIn('require_nonempty "JOB_ID" "${JOB_ID}"', evidence)
        self.assertIn('! "${JOB_ID}" =~ ^[0-9]+$', evidence)
        self.assertIn("JOB_ID_NOT_NUMERIC", evidence)

    def test_required_test_failure_or_skip_cannot_promote_authority(self) -> None:
        evidence = self._step("Publish exact-head audit evidence")
        self.assertIn('TEST_OUTCOME: ${{ steps.unified_tests.outcome }}', evidence)
        self.assertIn('require_success_outcome "TESTS" "${TEST_OUTCOME}"', evidence)
        self.assertIn('"${TEST_EXIT_CODE}" != "0"', evidence)
        self.assertIn('"${TEST_RESULT}" != "PASS"', evidence)

    def test_hygiene_failure_or_skip_cannot_promote_authority(self) -> None:
        evidence = self._step("Publish exact-head audit evidence")
        self.assertIn('HYGIENE_OUTCOME: ${{ steps.hygiene.outcome }}', evidence)
        self.assertIn('require_success_outcome "HYGIENE" "${HYGIENE_OUTCOME}"', evidence)
        self.assertIn('"${HYGIENE_EXIT_CODE}" != "0"', evidence)
        self.assertIn("HYGIENE_EXIT_CODE_NOT_ZERO", evidence)

    def test_missing_required_evidence_output_cannot_promote_authority(self) -> None:
        evidence = self._step("Publish exact-head audit evidence")
        required_outputs = (
            "REQUESTED_HEAD",
            "NORMALIZED_HEAD",
            "ACTUAL_CHECKOUT_SHA",
            "REV_PARSE_HEAD",
            "VALIDATION_EXIT_CODE",
            "IDENTITY_EXIT_CODE",
            "JOB_ID",
            "TEST_EXIT_CODE",
            "TEST_RESULT",
            "STDOUT_SHA256",
            "STDERR_SHA256",
            "HYGIENE_EXIT_CODE",
            "WORKFLOW_REF",
            "WORKFLOW_SHA",
            "WORKFLOW_RUN_ID",
        )
        for output in required_outputs:
            self.assertIn(f'require_nonempty "{output}"', evidence)
        self.assertIn('failure_reasons+=("MISSING_OUTPUT_${label}")', evidence)

    def test_only_all_prerequisites_pass_and_outputs_complete_promotes_authority(self) -> None:
        evidence = self._step("Publish exact-head audit evidence")
        self.assertEqual(evidence.count("exact_head_authority=true"), 1)
        self.assertRegex(
            evidence,
            re.compile(
                r'if \[\[ "\$\{#failure_reasons\[@\]\}" -eq 0 \]\]; then\n'
                r'\s+exact_head_authority=true\n'
                r'\s+checkout_identity_class="WORKFLOW_DISPATCH_EXACT_COMMIT"\n'
                r'\s+audit_record_status="AUTHORITATIVE"\n'
                r'\s+failure_reason="NONE"'
            ),
        )
        self.assertIn(
            "authority_promotion_condition=ALL_REQUIRED_GATES_SUCCESS_AND_REQUIRED_OUTPUTS_COMPLETE",
            evidence,
        )

    def test_failure_or_incomplete_reason_is_durable_and_self_contained(self) -> None:
        evidence = self._step("Publish exact-head audit evidence")
        self.assertIn('failure_reason="$(IFS=\';\'; echo "${failure_reasons[*]}")"', evidence)
        self.assertIn('echo "failure_reason=${failure_reason}" >> "${GITHUB_OUTPUT}"', evidence)
        self.assertIn("failure_reason=${failure_reason}", evidence)
        self.assertIn("WORKFLOW_DISPATCH_EXACT_COMMIT_FAILED_OR_INCOMPLETE", evidence)

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
