from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
import sys
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = Path(os.environ.get("E57_REPO_ROOT", str(TASK_ROOT.parents[3])))
sys.path.insert(0, str(TASK_ROOT / "src"))

from e57_authority.core import AuthorityError
from e57_authority.provider import (
    DualProviderEvidence,
    E57_PROVIDER_CONTRACT,
    ProviderArtifact,
    ProviderEvidenceSet,
    ProviderJob,
    verify_dual_provider_evidence,
)
from e57_authority.topology import inspect_history_hygiene, verify_plan_commit
from tests.e57_fixtures import provider_evidence as evidence


class ProviderTopologyTests(unittest.TestCase):
    def test_separate_tested_and_receipt_evidence_verify(self) -> None:
        tested_head, receipt_head = "1" * 40, "2" * 40
        pair = DualProviderEvidence(evidence("TESTED", tested_head, 1001, 0), evidence("RECEIPT", receipt_head, 1002, 1000))
        verify_dual_provider_evidence(pair, E57_PROVIDER_CONTRACT, tested_head=tested_head, receipt_head=receipt_head)

    def test_shared_run_is_rejected(self) -> None:
        tested_head, receipt_head = "1" * 40, "2" * 40
        pair = DualProviderEvidence(evidence("TESTED", tested_head, 1001, 0), evidence("RECEIPT", receipt_head, 1001, 1000))
        with self.assertRaises(AuthorityError):
            verify_dual_provider_evidence(pair, E57_PROVIDER_CONTRACT, tested_head=tested_head, receipt_head=receipt_head)

    def test_shared_artifact_ids_are_rejected(self) -> None:
        tested_head, receipt_head = "1" * 40, "2" * 40
        tested = evidence("TESTED", tested_head, 1001, 0)
        distinct_jobs = evidence("RECEIPT", receipt_head, 1002, 1000)
        receipt = replace(
            distinct_jobs,
            artifacts=tuple(replace(artifact, artifact_id=tested.artifacts[index].artifact_id) for index, artifact in enumerate(distinct_jobs.artifacts)),
        )
        pair = DualProviderEvidence(tested, receipt)
        with self.assertRaises(AuthorityError):
            verify_dual_provider_evidence(pair, E57_PROVIDER_CONTRACT, tested_head=tested_head, receipt_head=receipt_head)

    def test_wrong_head_is_rejected(self) -> None:
        tested_head, receipt_head = "1" * 40, "2" * 40
        pair = DualProviderEvidence(evidence("TESTED", "3" * 40, 1001, 0), evidence("RECEIPT", receipt_head, 1002, 1000))
        with self.assertRaises(AuthorityError):
            verify_dual_provider_evidence(pair, E57_PROVIDER_CONTRACT, tested_head=tested_head, receipt_head=receipt_head)

    def test_contract_has_exactly_seven_jobs_and_thirteen_artifacts(self) -> None:
        self.assertEqual(len(E57_PROVIDER_CONTRACT.job_names), 7)
        self.assertEqual(len(E57_PROVIDER_CONTRACT.artifact_bindings), 13)

    def test_role_substitution_is_rejected(self) -> None:
        tested_head, receipt_head = "1" * 40, "2" * 40
        pair = DualProviderEvidence(evidence("RECEIPT", tested_head, 1001, 0), evidence("TESTED", receipt_head, 1002, 1000))
        with self.assertRaises(AuthorityError):
            verify_dual_provider_evidence(pair, E57_PROVIDER_CONTRACT, tested_head=tested_head, receipt_head=receipt_head)

    def test_exact_plan_commit_is_observed_in_real_worktree(self) -> None:
        parent, paths = verify_plan_commit(
            REPOSITORY,
            base_sha="437b0f7e1a78d868342a0a4b205e47ffb719aebb",
            plan_sha="b283056b43c8d46f83d9b46cc8db6961158db0c3",
            plan_path="coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CODEX-E57/PROJECT-PLAN.md",
        )
        self.assertEqual(parent, "437b0f7e1a78d868342a0a4b205e47ffb719aebb")
        self.assertEqual(paths, ("coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CODEX-E57/PROJECT-PLAN.md",))

    def test_history_hygiene_reports_generated_paths_in_real_range(self) -> None:
        report = inspect_history_hygiene(
            REPOSITORY,
            base_sha="437b0f7e1a78d868342a0a4b205e47ffb719aebb",
            end_sha="8a5dcb0d13920ff4f3770996f5303c5c677d7125",
            allowed_prefixes=("coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CODEX-E57/",),
        )
        self.assertGreaterEqual(len(report.generated_or_runtime_paths), 7)
        self.assertFalse(report.retained_generated_or_runtime_paths)
        self.assertGreaterEqual(len(report.transient_generated_or_runtime_paths), 7)
        self.assertFalse(report.outside_allowlist_paths)
