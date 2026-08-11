from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from threading import Barrier, Thread
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from e64_promotion import (  # noqa: E402
    AdmissionClass,
    ApprovalPacket,
    CanonicalAdmissionEvidence,
    CanonicalGitHubApprovalEvidence,
    CandidateKnowledgePackage,
    E48DigestBundle,
    GitHubNativePromotionAdapter,
    InMemoryDurablePromotionStore,
    PromotionError,
    PromotionPolicy,
    ReplayRejected,
    UnknownOutcome,
)


NOW = datetime(2026, 8, 11, 9, 0, tzinfo=timezone.utc)
PARENT = "a" * 40
REPOSITORY_ID = "1303258074"
REPOSITORY_SLUG = "vxz2datoubo/second-brain-coordination"
TASK = "CODEX-GITHUB-ONLY-FORMAL-KNOWLEDGE-PROMOTION-0060-E64-R1"
ROUTE = 73
CONTROL = "synthetic-github-control-record-224"
CLASS_REF = "canonical-main:admission/synthetic-e64-r1"
CLASS_HASH = "4" * 64
APPROVAL_REF = "canonical-main:approval/synthetic-e64-r1"
APPROVAL_HASH = "5" * 64


class MemoryResolver:
    """Test-only resolver standing in for read-only canonical GitHub lookup."""

    def __init__(self, approval: CanonicalGitHubApprovalEvidence | None, admission: CanonicalAdmissionEvidence | None) -> None:
        self.approval = approval
        self.admission = admission

    def resolve_approval(self, evidence_ref: str) -> CanonicalGitHubApprovalEvidence | None:
        return self.approval if self.approval and evidence_ref == self.approval.evidence_ref else None

    def resolve_admission(self, evidence_ref: str) -> CanonicalAdmissionEvidence | None:
        return self.admission if self.admission and evidence_ref == self.admission.evidence_ref else None


def candidate(**overrides: object) -> CandidateKnowledgePackage:
    values: dict[str, object] = {
        "candidate_package_id": "candidate-e64-r1-synthetic-001",
        "repository_id": REPOSITORY_ID,
        "repository_slug": REPOSITORY_SLUG,
        "task_id": TASK,
        "route_epoch": ROUTE,
        "digest_bundle": E48DigestBundle("1" * 64, "2" * 64, "3" * 64),
        "source_provenance_status": "TYPED_SYNTHETIC_E48_FIXTURE",
        "target_scope": "PROJECT",
        "admission_class": AdmissionClass.PUBLIC_SAFE,
        "classification_evidence_ref": CLASS_REF,
        "classification_evidence_object_sha256": CLASS_HASH,
        "expected_canonical_main_parent": PARENT,
    }
    values.update(overrides)
    return CandidateKnowledgePackage(**values)  # type: ignore[arg-type]


def policy() -> PromotionPolicy:
    return PromotionPolicy(
        repository_id=REPOSITORY_ID,
        repository_slug=REPOSITORY_SLUG,
        task_id=TASK,
        route_epoch=ROUTE,
        required_control_record_id=CONTROL,
        allowed_source_statuses=frozenset({"TYPED_SYNTHETIC_E48_FIXTURE"}),
    )


def admission(item: CandidateKnowledgePackage, **overrides: object) -> CanonicalAdmissionEvidence:
    values: dict[str, object] = {
        "evidence_ref": CLASS_REF,
        "evidence_object_sha256": CLASS_HASH,
        "repository_id": REPOSITORY_ID,
        "candidate_identity_sha256": item.identity_sha256,
        "decision": AdmissionClass.PUBLIC_SAFE,
    }
    values.update(overrides)
    return CanonicalAdmissionEvidence(**values)  # type: ignore[arg-type]


def evidence(item: CandidateKnowledgePackage, **overrides: object) -> CanonicalGitHubApprovalEvidence:
    values: dict[str, object] = {
        "approval_id": "approval-e64-r1-001",
        "evidence_ref": APPROVAL_REF,
        "evidence_object_sha256": APPROVAL_HASH,
        "repository_id": REPOSITORY_ID,
        "repository_slug": REPOSITORY_SLUG,
        "task_id": TASK,
        "route_epoch": ROUTE,
        "candidate_identity_sha256": item.identity_sha256,
        "decision": "APPROVE",
        "github_control_object_id": CONTROL,
        "canonical_main_commit": PARENT,
        "expires_at": NOW + timedelta(hours=1),
    }
    values.update(overrides)
    return CanonicalGitHubApprovalEvidence(**values)  # type: ignore[arg-type]


def packet(**overrides: object) -> ApprovalPacket:
    values: dict[str, object] = {
        "approval_id": "approval-e64-r1-001",
        "approval_evidence_ref": APPROVAL_REF,
        "approval_evidence_object_sha256": APPROVAL_HASH,
    }
    values.update(overrides)
    return ApprovalPacket(**values)  # type: ignore[arg-type]


class E64R1PromotionTests(unittest.TestCase):
    def prepared(self, item: CandidateKnowledgePackage | None = None, **evidence_overrides: object):
        item = item or candidate()
        resolver = MemoryResolver(evidence(item, **evidence_overrides), admission(item))
        store = InMemoryDurablePromotionStore()
        adapter = GitHubNativePromotionAdapter(policy(), resolver, store)
        request = adapter.prepare(item, packet(), NOW)
        return adapter, store, item, request, resolver

    def test_public_safe_candidate_has_idempotent_immutable_receipt(self) -> None:
        adapter, _, _, request, _ = self.prepared()
        first = adapter.consume_candidate(request, PARENT)
        second = adapter.consume_candidate(request, PARENT)
        self.assertTrue(first.consumed_now)
        self.assertFalse(second.consumed_now)
        self.assertEqual(first.promotion_id, second.promotion_id)
        self.assertFalse(first.formal_knowledge_written)

    def test_nonexistent_approval_evidence_is_rejected(self) -> None:
        item = candidate()
        adapter = GitHubNativePromotionAdapter(policy(), MemoryResolver(None, admission(item)), InMemoryDurablePromotionStore())
        with self.assertRaises(PromotionError):
            adapter.prepare(item, packet(), NOW)

    def test_wrong_repository_approval_evidence_is_rejected(self) -> None:
        item = candidate()
        resolver = MemoryResolver(evidence(item, repository_id="different-repository"), admission(item))
        adapter = GitHubNativePromotionAdapter(policy(), resolver, InMemoryDurablePromotionStore())
        with self.assertRaises(PromotionError):
            adapter.prepare(item, packet(), NOW)

    def test_wrong_candidate_approval_evidence_is_rejected(self) -> None:
        item = candidate()
        resolver = MemoryResolver(evidence(item, candidate_identity_sha256="f" * 64), admission(item))
        adapter = GitHubNativePromotionAdapter(policy(), resolver, InMemoryDurablePromotionStore())
        with self.assertRaises(PromotionError):
            adapter.prepare(item, packet(), NOW)

    def test_wrong_route_decision_and_control_record_are_rejected(self) -> None:
        item = candidate()
        for changes in ({"route_epoch": 72}, {"decision": "REQUEST"}, {"github_control_object_id": "invented-control"}):
            resolver = MemoryResolver(evidence(item, **changes), admission(item))
            adapter = GitHubNativePromotionAdapter(policy(), resolver, InMemoryDurablePromotionStore())
            with self.assertRaises(PromotionError):
                adapter.prepare(item, packet(), NOW)

    def test_wrong_evidence_object_identity_is_rejected(self) -> None:
        item = candidate()
        resolver = MemoryResolver(evidence(item), admission(item))
        adapter = GitHubNativePromotionAdapter(policy(), resolver, InMemoryDurablePromotionStore())
        with self.assertRaises(PromotionError):
            adapter.prepare(item, packet(approval_evidence_object_sha256="6" * 64), NOW)

    def test_expired_approval_evidence_fails_closed(self) -> None:
        item = candidate()
        resolver = MemoryResolver(evidence(item, expires_at=NOW), admission(item))
        adapter = GitHubNativePromotionAdapter(policy(), resolver, InMemoryDurablePromotionStore())
        with self.assertRaises(PromotionError):
            adapter.prepare(item, packet(), NOW)

    def test_changed_digest_after_evidence_is_rejected(self) -> None:
        original = candidate()
        changed = candidate(digest_bundle=E48DigestBundle("7" * 64, "2" * 64, "3" * 64))
        resolver = MemoryResolver(evidence(original), admission(changed))
        adapter = GitHubNativePromotionAdapter(policy(), resolver, InMemoryDurablePromotionStore())
        with self.assertRaises(PromotionError):
            adapter.prepare(changed, packet(), NOW)

    def test_classification_evidence_mismatch_is_rejected(self) -> None:
        item = candidate()
        bad = admission(item, candidate_identity_sha256="e" * 64)
        adapter = GitHubNativePromotionAdapter(policy(), MemoryResolver(evidence(item), bad), InMemoryDurablePromotionStore())
        with self.assertRaises(PromotionError):
            adapter.prepare(item, packet(), NOW)

    def test_non_public_admission_classes_are_rejected(self) -> None:
        for classification in (AdmissionClass.PRIVATE_OR_SENSITIVE, AdmissionClass.SECRET_CREDENTIAL):
            item = candidate(admission_class=classification)
            adapter = GitHubNativePromotionAdapter(policy(), MemoryResolver(evidence(item), admission(item)), InMemoryDurablePromotionStore())
            with self.assertRaises(PromotionError):
                adapter.prepare(item, packet(), NOW)

    def test_invalid_target_and_candidate_route_are_rejected(self) -> None:
        with self.assertRaises(PromotionError):
            candidate(target_scope="UNSCOPED")
        item = candidate(route_epoch=72)
        adapter = GitHubNativePromotionAdapter(policy(), MemoryResolver(evidence(item), admission(item)), InMemoryDurablePromotionStore())
        with self.assertRaises(PromotionError):
            adapter.prepare(item, packet(), NOW)

    def test_missing_classification_evidence_is_rejected(self) -> None:
        item = candidate()
        adapter = GitHubNativePromotionAdapter(policy(), MemoryResolver(evidence(item), None), InMemoryDurablePromotionStore())
        with self.assertRaises(PromotionError):
            adapter.prepare(item, packet(), NOW)

    def test_stale_parent_does_not_consume_durable_marker(self) -> None:
        adapter, _, _, request, _ = self.prepared()
        with self.assertRaises(PromotionError):
            adapter.consume_candidate(request, "b" * 40)
        self.assertTrue(adapter.consume_candidate(request, PARENT).consumed_now)

    def test_two_independent_adapters_share_one_durable_consumer(self) -> None:
        item = candidate()
        resolver = MemoryResolver(evidence(item), admission(item))
        store = InMemoryDurablePromotionStore()
        first_adapter = GitHubNativePromotionAdapter(policy(), resolver, store)
        second_adapter = GitHubNativePromotionAdapter(policy(), resolver, store)
        first_request = first_adapter.prepare(item, packet(), NOW)
        second_request = second_adapter.prepare(item, packet(), NOW)
        barrier = Barrier(2)
        receipts = []

        def consume(adapter, request) -> None:
            barrier.wait()
            receipts.append(adapter.consume_candidate(request, PARENT))

        threads = [Thread(target=consume, args=(first_adapter, first_request)), Thread(target=consume, args=(second_adapter, second_request))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(receipt.consumed_now for receipt in receipts), 1)
        self.assertEqual(receipts[0].promotion_id, receipts[1].promotion_id)

    def test_marker_already_exists_with_other_request_is_rejected(self) -> None:
        adapter, store, _, request, _ = self.prepared()
        store.seed_conflicting_marker(replace(request, promotion_id="8" * 64))
        with self.assertRaises(ReplayRejected):
            adapter.consume_candidate(request, PARENT)

    def test_unknown_outcome_retry_does_not_issue_second_capability(self) -> None:
        adapter, store, _, request, _ = self.prepared()
        store.force_unknown_once = True
        with self.assertRaises(UnknownOutcome):
            adapter.consume_candidate(request, PARENT)
        with self.assertRaises(UnknownOutcome):
            adapter.consume_candidate(request, PARENT)

    def test_malformed_partial_packet_and_wrong_source_fail_closed(self) -> None:
        with self.assertRaises(PromotionError):
            packet(approval_evidence_ref="")
        item = candidate(source_provenance_status="UNACCEPTED_E48_R1")
        with self.assertRaises(PromotionError):
            self.prepared(item)


if __name__ == "__main__":
    unittest.main()
