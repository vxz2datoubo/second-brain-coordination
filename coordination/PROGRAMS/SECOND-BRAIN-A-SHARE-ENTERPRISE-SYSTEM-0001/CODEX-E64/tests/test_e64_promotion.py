from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from threading import Barrier, Thread
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from e64_promotion import (  # noqa: E402
    AdmissionClass,
    ApprovalPacket,
    CandidateKnowledgePackage,
    E48DigestBundle,
    GitHubNativePromotionAdapter,
    PromotionError,
    PromotionPolicy,
    PromotionState,
    ReplayRejected,
)


NOW = datetime(2026, 8, 11, 8, 0, tzinfo=timezone.utc)
PARENT = "a" * 64


def candidate(**overrides: object) -> CandidateKnowledgePackage:
    values: dict[str, object] = {
        "candidate_package_id": "candidate-e64-synthetic-001",
        "repository_id": "synthetic-repository-id-101",
        "repository_slug": "vxz2datoubo/second-brain-coordination",
        "task_id": "CODEX-GITHUB-ONLY-FORMAL-KNOWLEDGE-PROMOTION-0060-E64",
        "route_epoch": 72,
        "digest_bundle": E48DigestBundle("1" * 64, "2" * 64, "3" * 64),
        "source_provenance_status": "TYPED_SYNTHETIC_E48_FIXTURE",
        "target_scope": "PROJECT",
        "admission_class": AdmissionClass.PUBLIC_SAFE,
        "expected_canonical_main_parent": PARENT,
    }
    values.update(overrides)
    return CandidateKnowledgePackage(**values)  # type: ignore[arg-type]


def policy() -> PromotionPolicy:
    return PromotionPolicy(
        repository_id="synthetic-repository-id-101",
        repository_slug="vxz2datoubo/second-brain-coordination",
        task_id="CODEX-GITHUB-ONLY-FORMAL-KNOWLEDGE-PROMOTION-0060-E64",
        route_epoch=72,
        allowed_source_statuses=frozenset({"TYPED_SYNTHETIC_E48_FIXTURE"}),
    )


def approval(item: CandidateKnowledgePackage, **overrides: object) -> ApprovalPacket:
    values: dict[str, object] = {
        "approval_id": "approval-e64-001",
        "candidate_identity_sha256": item.identity_sha256,
        "approval_actor_ref": "github-issue-224#user-approval",
        "gpt_review_ref": "github-issue-224#review-1",
        "approved_at": NOW,
        "expires_at": NOW + timedelta(hours=1),
    }
    values.update(overrides)
    return ApprovalPacket(**values)  # type: ignore[arg-type]


class E64PromotionTests(unittest.TestCase):
    def prepared(self, item: CandidateKnowledgePackage | None = None) -> tuple[GitHubNativePromotionAdapter, CandidateKnowledgePackage, ApprovalPacket]:
        item = item or candidate()
        packet = approval(item)
        adapter = GitHubNativePromotionAdapter(policy())
        adapter.register_approval(item, packet)
        return adapter, item, packet

    def test_public_safe_candidate_promotes_to_receipt_once(self) -> None:
        adapter, item, packet = self.prepared()
        promotion_id = adapter.claim(item, packet.approval_id, NOW)
        receipt = adapter.promote_candidate(packet.approval_id, promotion_id, PARENT)
        self.assertEqual(receipt.state, PromotionState.PROMOTED_CANDIDATE)
        self.assertFalse(receipt.formal_knowledge_written)
        with self.assertRaises(ReplayRejected):
            adapter.promote_candidate(packet.approval_id, promotion_id, PARENT)

    def test_exact_same_promotion_replay_rejected(self) -> None:
        adapter, item, packet = self.prepared()
        adapter.claim(item, packet.approval_id, NOW)
        with self.assertRaises(ReplayRejected):
            adapter.claim(item, packet.approval_id, NOW)

    def test_two_promotions_from_one_approval_rejected(self) -> None:
        adapter, item, packet = self.prepared()
        adapter.claim(item, packet.approval_id, NOW)
        with self.assertRaises(ReplayRejected):
            adapter.register_approval(item, packet)

    def test_changed_digest_after_approval_rejected(self) -> None:
        adapter, _, packet = self.prepared()
        changed = candidate(digest_bundle=E48DigestBundle("4" * 64, "2" * 64, "3" * 64))
        with self.assertRaises(PromotionError):
            adapter.claim(changed, packet.approval_id, NOW)

    def test_wrong_provenance_status_rejected(self) -> None:
        item = candidate(source_provenance_status="UNACCEPTED_E48_PRODUCER")
        with self.assertRaises(PromotionError):
            self.prepared(item)

    def test_wrong_target_rejected_at_candidate_construction(self) -> None:
        with self.assertRaises(PromotionError):
            candidate(target_scope="UNSCOPED")

    def test_wrong_repository_identity_rejected(self) -> None:
        item = candidate(repository_id="other-repository")
        with self.assertRaises(PromotionError):
            self.prepared(item)

    def test_wrong_route_epoch_rejected(self) -> None:
        item = candidate(route_epoch=71)
        with self.assertRaises(PromotionError):
            self.prepared(item)

    def test_missing_gpt_review_reference_rejected(self) -> None:
        item = candidate()
        with self.assertRaises(PromotionError):
            approval(item, gpt_review_ref="")

    def test_stale_expected_parent_rejected(self) -> None:
        adapter, item, packet = self.prepared()
        promotion_id = adapter.claim(item, packet.approval_id, NOW)
        with self.assertRaises(PromotionError):
            adapter.promote_candidate(packet.approval_id, promotion_id, "b" * 64)

    def test_expired_approval_fails_closed(self) -> None:
        adapter, item, packet = self.prepared()
        with self.assertRaises(PromotionError):
            adapter.claim(item, packet.approval_id, NOW + timedelta(hours=2))
        with self.assertRaises(ReplayRejected):
            adapter.claim(item, packet.approval_id, NOW)

    def test_revoked_approval_cannot_promote(self) -> None:
        adapter, item, packet = self.prepared()
        adapter.revoke(packet.approval_id)
        with self.assertRaises(ReplayRejected):
            adapter.claim(item, packet.approval_id, NOW)

    def test_private_or_sensitive_is_blocked(self) -> None:
        item = candidate(admission_class=AdmissionClass.PRIVATE_OR_SENSITIVE)
        with self.assertRaises(PromotionError):
            self.prepared(item)

    def test_secret_credential_is_blocked(self) -> None:
        item = candidate(admission_class=AdmissionClass.SECRET_CREDENTIAL)
        with self.assertRaises(PromotionError):
            self.prepared(item)

    def test_malformed_partial_approval_packet_rejected(self) -> None:
        item = candidate()
        with self.assertRaises(PromotionError):
            approval(item, approval_actor_ref="")

    def test_concurrent_duplicate_claim_has_one_winner(self) -> None:
        adapter, item, packet = self.prepared()
        barrier = Barrier(2)
        results: list[str] = []

        def run_claim() -> None:
            barrier.wait()
            try:
                results.append(adapter.claim(item, packet.approval_id, NOW))
            except ReplayRejected:
                results.append("rejected")

        threads = [Thread(target=run_claim) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(results), ["promotion:approval-e64-001", "rejected"])


if __name__ == "__main__":
    unittest.main()
