"""Failing-first E49 product-release verification contract."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from brainops_control_plane.release_verifier import (  # noqa: E402
    E49ProviderEvidence,
    E49ReleaseCode,
    read_e49_receipt_documents,
    receipt_paths_are_e49_evidence_only,
    validate_e49_release,
)


class E49ProviderReleaseTests(unittest.TestCase):
    @staticmethod
    def _receipt_documents(manifest: str, ledger: str):
        return {
            "AMED-EXECUTION-RECEIPT.yaml": "agent_id: CODEX",
            "TEST-RUN-RECEIPT.json": "{}",
            "UNKNOWN-REGISTRY.yaml": "items: []",
            "AI_HANDOFF.yaml": "source_agent: CODEX",
            "RESEARCH-LEDGER.md": ledger,
            "UNPLANNED-IMPROVEMENT-LEDGER.md": "# improvements",
            "SYSTEM-DISCOVERY-AND-OPPORTUNITY-REPORT.md": "# discoveries",
            "WORK-PROCESS-AND-COORDINATION-REPORT.md": "# process",
            "RECEIPT-MANIFEST.json": manifest,
        }

    @staticmethod
    def _complete_run(head: str, run_id: int, *, expired: bool = False):
        return {
            "run_id": run_id,
            "workflow": "brainops-e49.yml",
            "head_sha": head,
            "status": "completed",
            "conclusion": "success",
            "jobs": [
                {
                    "job_id": run_id * 10 + 1,
                    "name": "e49 (3.11)",
                    "python_version": "3.11",
                    "head_sha": head,
                    "conclusion": "success",
                    "test_count": 1,
                },
                {
                    "job_id": run_id * 10 + 3,
                    "name": "e49 (3.13)",
                    "python_version": "3.13",
                    "head_sha": head,
                    "conclusion": "success",
                    "test_count": 1,
                },
            ],
            "artifacts": [
                {
                    "artifact_id": run_id * 100 + 11,
                    "name": "e49-release-evidence-3.11",
                    "head_sha": head,
                    "digest": "sha256:" + "a" * 64,
                    "expired": expired,
                },
                {
                    "artifact_id": run_id * 100 + 13,
                    "name": "e49-release-evidence-3.13",
                    "head_sha": head,
                    "digest": "sha256:" + "b" * 64,
                    "expired": expired,
                },
            ],
        }

    def test_caller_declared_success_is_not_provider_evidence(self):
        evidence = E49ProviderEvidence.from_document(
            {
                "declared_success": True,
                "tested_head": "0" * 40,
                "runs": [],
            }
        )
        result = validate_e49_release(Path("."), evidence, "0" * 40, None)
        self.assertEqual(result.code, E49ReleaseCode.PROVIDER_EVIDENCE_UNTRUSTED)
        self.assertEqual(result.findings, ("caller_declared_success_forbidden",))

    def test_placeholder_and_invalid_reproduction_command_fail_closed(self):
        evidence = E49ProviderEvidence.from_document(
            {
                "provider_source": "EXTERNAL_READ_ONLY_API",
                "tested_head": "0" * 40,
                "runs": [],
            }
        )
        result = validate_e49_release(
            Path("."),
            evidence,
            "0" * 40,
            "1" * 40,
            receipt_documents=self._receipt_documents(
                "receipt_commit_identity: EXTERNAL_POST_COMMIT_PROVIDER_FACT\n"
                '{"receipt_commit_sha":"RESOLVED_MECHANICALLY_AFTER_COMMIT"}',
                "python -m stale.command --wrong-base",
            ),
        )
        self.assertEqual(result.code, E49ReleaseCode.RECEIPT_PLACEHOLDER)

    def test_invalid_reproduction_command_is_rejected_after_identity_marker(self):
        evidence = E49ProviderEvidence.from_document(
            {
                "provider_source": "EXTERNAL_READ_ONLY_API",
                "tested_head": "0" * 40,
                "receipt_head": "1" * 40,
                "remote_branch_head": "1" * 40,
                "runs": [],
            }
        )
        result = validate_e49_release(
            Path("."),
            evidence,
            "0" * 40,
            "1" * 40,
            receipt_documents=self._receipt_documents(
                "receipt_commit_identity: EXTERNAL_POST_COMMIT_PROVIDER_FACT",
                "python -m stale.command --wrong-base",
            ),
        )
        self.assertEqual(result.code, E49ReleaseCode.REPRODUCTION_INVALID)

    def test_missing_evidence_family_is_rejected(self):
        evidence = E49ProviderEvidence.from_document(
            {"provider_source": "EXTERNAL_READ_ONLY_API", "runs": []}
        )
        result = validate_e49_release(
            Path("."),
            evidence,
            "0" * 40,
            "1" * 40,
            receipt_documents={
                "RECEIPT-MANIFEST.json": "receipt_commit_identity: EXTERNAL_POST_COMMIT_PROVIDER_FACT\n"
                "python -m brainops_control_plane.release_verifier --tested-head " + "0" * 40
            },
        )
        self.assertEqual(result.code, E49ReleaseCode.EVIDENCE_FAMILY_MISSING)

    def test_changed_remote_branch_head_is_not_accepted_as_receipt_head(self):
        evidence = E49ProviderEvidence.from_document(
            {
                "provider_source": "EXTERNAL_READ_ONLY_API",
                "tested_head": "0" * 40,
                "receipt_head": "1" * 40,
                "remote_branch_head": "2" * 40,
                "runs": [self._complete_run("0" * 40, 1), self._complete_run("1" * 40, 2)],
            }
        )
        result = validate_e49_release(
            Path("."),
            evidence,
            "0" * 40,
            "1" * 40,
            receipt_documents=self._receipt_documents(
                "receipt_commit_identity: EXTERNAL_POST_COMMIT_PROVIDER_FACT",
                "python -m brainops_control_plane.release_verifier --tested-head " + "0" * 40,
            ),
        )
        self.assertEqual(result.code, E49ReleaseCode.PROVIDER_RUN_INVALID)

    def test_expired_provider_artifacts_are_rejected(self):
        evidence = E49ProviderEvidence.from_document(
            {
                "provider_source": "EXTERNAL_READ_ONLY_API",
                "tested_head": "0" * 40,
                "receipt_head": "1" * 40,
                "remote_branch_head": "1" * 40,
                "runs": [
                    self._complete_run("0" * 40, 1, expired=True),
                    self._complete_run("1" * 40, 2),
                ],
            }
        )
        result = validate_e49_release(
            Path("."),
            evidence,
            "0" * 40,
            "1" * 40,
            receipt_documents=self._receipt_documents(
                "receipt_commit_identity: EXTERNAL_POST_COMMIT_PROVIDER_FACT",
                "python -m brainops_control_plane.release_verifier --tested-head " + "0" * 40,
            ),
        )
        self.assertEqual(result.code, E49ReleaseCode.PROVIDER_ARTIFACT_INVALID)

    def test_wrong_provider_job_head_is_rejected(self):
        tested = "0" * 40
        receipt = "1" * 40
        bad_run = self._complete_run(tested, 1)
        bad_run["jobs"][0]["head_sha"] = "2" * 40
        evidence = E49ProviderEvidence.from_document(
            {
                "provider_source": "EXTERNAL_READ_ONLY_API",
                "tested_head": tested,
                "receipt_head": receipt,
                "remote_branch_head": receipt,
                "runs": [bad_run, self._complete_run(receipt, 2)],
            }
        )
        result = validate_e49_release(
            Path("."),
            evidence,
            tested,
            receipt,
            receipt_documents=self._receipt_documents(
                "receipt_commit_identity: EXTERNAL_POST_COMMIT_PROVIDER_FACT",
                "python -m brainops_control_plane.release_verifier --tested-head " + tested,
            ),
        )
        self.assertEqual(result.code, E49ReleaseCode.PROVIDER_JOB_INVALID)

    def test_receipt_topology_allows_only_nonempty_evidence_paths(self):
        self.assertTrue(
            receipt_paths_are_e49_evidence_only(
                [
                    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/E49/RECEIPT/TEST-RUN-RECEIPT.json"
                ]
            )
        )
        self.assertFalse(receipt_paths_are_e49_evidence_only([]))
        self.assertFalse(
            receipt_paths_are_e49_evidence_only(
                [
                    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/src/brainops_control_plane/execution_lease.py"
                ]
            )
        )

    def test_unreadable_receipt_directory_is_an_empty_evidence_family(self):
        self.assertEqual(read_e49_receipt_documents(Path("missing-receipt")), {})

    def test_in_job_observation_is_pre_review_only(self):
        evidence = E49ProviderEvidence.from_document(
            {
                "provider_source": "IN_JOB_POLICY_AND_CURRENT_JOB_OBSERVATION_ONLY",
                "tested_head": "0" * 40,
                "runs": [],
            }
        )
        result = validate_e49_release(
            Path("."), evidence, "0" * 40, None, mode="pre_review"
        )
        self.assertEqual(result.code, E49ReleaseCode.PRE_REVIEW_EVIDENCE_RECORDED)
