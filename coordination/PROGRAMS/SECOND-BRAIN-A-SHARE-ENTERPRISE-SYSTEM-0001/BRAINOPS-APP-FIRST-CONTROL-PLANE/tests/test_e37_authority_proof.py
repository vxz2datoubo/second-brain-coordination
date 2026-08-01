from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from brainops_control_plane.canary import E36_CANARY_ID, CanaryGateContext, OneShotCanaryGate
from brainops_control_plane.models import (
    ActivationManifest,
    BoundCanaryApproval,
    CanaryEvent,
    CapabilitySet,
    CapabilityStatus,
    RouteRef,
    RouteState,
    ShadowOutcome,
    ValidationError,
)
from brainops_control_plane.proofs import (
    CANONICAL_ACTIVE_TASK_PATH,
    CANONICAL_COORDINATION_PATH,
    ApprovalVerificationResult,
    ReadOnlyApprovalDocument,
    ReadOnlyApprovalVerifier,
    ReadOnlyRouteProofVerifier,
    RouteFileIdentity,
    RouteProofVerification,
    RouteStateEvidence,
    VerificationStatus,
    canonical_approval_ref,
)
from brainops_control_plane.store import MetadataStore


NOW = "2026-08-02T00:00:00Z"
FUTURE = "2026-08-02T01:00:00Z"
REPOSITORY = "vxz2datoubo/second-brain-coordination"
MAIN_COMMIT = "a" * 40
ROUTE = RouteRef("brainops.e37", "CODEX", 38)
TASK_ID = "CODEX-BRAINOPS-CANARY-NONCE-AUTHORITY-AND-ROUTE-PROOF-CLOSURE-0032-E37"
SCOPE = "public_safe_pre_canary_proof_only"
ISSUE_NUMBER = 114
COMMENT_ID = 114038
ACTOR = "gpt"
BODY = "synthetic public approval body"


def _blob_sha1(content: bytes) -> str:
    return hashlib.sha1(f"blob {len(content)}\0".encode("ascii") + content).hexdigest()


def approval(*, nonce: str = "nonce.e37.one", actor: str = ACTOR, body: str = BODY) -> BoundCanaryApproval:
    return BoundCanaryApproval(
        E36_CANARY_ID,
        TASK_ID,
        38,
        SCOPE,
        FUTURE,
        nonce,
        canonical_approval_ref(REPOSITORY, ISSUE_NUMBER, COMMENT_ID),
        REPOSITORY,
        ISSUE_NUMBER,
        COMMENT_ID,
        actor,
        NOW,
        hashlib.sha256(body.encode("utf-8")).hexdigest(),
    )


def document(*, actor: str = ACTOR, body: str = BODY, issued_at: str = NOW) -> ReadOnlyApprovalDocument:
    return ReadOnlyApprovalDocument(REPOSITORY, ISSUE_NUMBER, COMMENT_ID, actor, issued_at, body)


def verification(bound: BoundCanaryApproval, fetched: ReadOnlyApprovalDocument | None = None) -> ApprovalVerificationResult:
    return ReadOnlyApprovalVerifier().verify(bound, fetched or document(), NOW)


def activation(bound: BoundCanaryApproval, *, event_key: str = "idem.e37.one") -> ActivationManifest:
    return ActivationManifest("activation.e37", ROUTE, 38, event_key, E36_CANARY_ID, TASK_ID, SCOPE, bound.nonce, bound)


def event(*, event_id: str = "event.e37.one", key: str = "idem.e37.one", payload_hash: str = "b" * 64) -> CanaryEvent:
    return CanaryEvent(event_id, "GITHUB", ROUTE, E36_CANARY_ID, key, payload_hash)


def route_evidence(
    *,
    active: bytes = b"active route document",
    coordination: bytes = b"coordination document",
    observed_at: str = NOW,
    repository: str = REPOSITORY,
    ref: str = "refs/heads/main",
    main_commit: str = MAIN_COMMIT,
    active_identity: RouteFileIdentity | None = None,
    coordination_identity: RouteFileIdentity | None = None,
) -> tuple[RouteStateEvidence, dict[str, bytes]]:
    active_identity = active_identity or RouteFileIdentity(
        CANONICAL_ACTIVE_TASK_PATH, _blob_sha1(active), hashlib.sha256(active).hexdigest()
    )
    coordination_identity = coordination_identity or RouteFileIdentity(
        CANONICAL_COORDINATION_PATH, _blob_sha1(coordination), hashlib.sha256(coordination).hexdigest()
    )
    return (
        RouteStateEvidence(ROUTE, repository, ref, main_commit, active_identity, coordination_identity, observed_at),
        {CANONICAL_ACTIVE_TASK_PATH: active, CANONICAL_COORDINATION_PATH: coordination},
    )


def route_proof(**kwargs: object) -> RouteProofVerification:
    evidence, documents = route_evidence(**kwargs)  # type: ignore[arg-type]
    return ReadOnlyRouteProofVerifier().verify(evidence, documents, REPOSITORY, MAIN_COMMIT, NOW)


def context(
    bound: BoundCanaryApproval,
    *,
    event_key: str = "idem.e37.one",
    approval_result: ApprovalVerificationResult | None = None,
    proof: RouteProofVerification | None = None,
    automatic: bool = True,
) -> CanaryGateContext:
    return CanaryGateContext(
        activation(bound, event_key=event_key),
        RouteState.READY,
        38,
        CapabilitySet(CapabilityStatus.SUPPORTED, CapabilityStatus.UNKNOWN, CapabilityStatus.UNKNOWN),
        True,
        automatic,
        False,
        approval_result or verification(bound),
        proof or route_proof(),
        NOW,
    )


class E37ApprovalProofTests(unittest.TestCase):
    def test_read_only_document_binds_exact_repository_comment_actor_body_and_payload(self) -> None:
        bound = approval()
        result = verification(bound)
        self.assertEqual(result.status, VerificationStatus.READ_ONLY_FETCH_VERIFIED)
        self.assertIsNone(result.validates(bound, NOW))

    def test_forged_approval_ref_is_rejected(self) -> None:
        forged = replace(approval(), approval_ref=canonical_approval_ref(REPOSITORY, ISSUE_NUMBER, COMMENT_ID + 1))
        result = verification(forged)
        self.assertEqual(result.status, VerificationStatus.REJECTED)
        self.assertEqual(result.reason_code, "approval_ref_mismatch")

    def test_actor_mismatch_is_rejected(self) -> None:
        result = verification(approval(), document(actor="other_agent"))
        self.assertEqual(result.status, VerificationStatus.REJECTED)
        self.assertEqual(result.reason_code, "approval_actor_mismatch")

    def test_body_hash_mismatch_is_rejected(self) -> None:
        result = verification(approval(), document(body="different body"))
        self.assertEqual(result.status, VerificationStatus.REJECTED)
        self.assertEqual(result.reason_code, "approval_body_hash_mismatch")

    def test_unknown_result_cannot_be_promoted_to_authority(self) -> None:
        unknown = ApprovalVerificationResult.unknown(NOW, "read_only_fetch_unavailable")
        self.assertEqual(unknown.validates(approval(), NOW), "approval_read_only_verification_required")

    def test_callers_cannot_construct_a_verified_result_from_a_boolean_or_ref(self) -> None:
        with self.assertRaises(ValidationError):
            ApprovalVerificationResult(VerificationStatus.READ_ONLY_FETCH_VERIFIED, None, NOW, "forged_result")

    def test_future_approval_issue_time_is_rejected(self) -> None:
        result = verification(approval(), document(issued_at="2026-08-02T00:00:01Z"))
        self.assertEqual(result.status, VerificationStatus.REJECTED)
        self.assertEqual(result.reason_code, "approval_issued_at_mismatch")


class E37RouteProofTests(unittest.TestCase):
    def test_exact_remote_main_two_file_proof_is_verified(self) -> None:
        self.assertEqual(route_proof().status, VerificationStatus.READ_ONLY_FETCH_VERIFIED)

    def test_route_repository_mismatch_is_rejected(self) -> None:
        evidence, documents = route_evidence(repository="other/repository")
        result = ReadOnlyRouteProofVerifier().verify(evidence, documents, REPOSITORY, MAIN_COMMIT, NOW)
        self.assertEqual(result.reason_code, "route_repository_mismatch")

    def test_route_commit_mismatch_is_rejected(self) -> None:
        evidence, documents = route_evidence(main_commit="c" * 40)
        result = ReadOnlyRouteProofVerifier().verify(evidence, documents, REPOSITORY, MAIN_COMMIT, NOW)
        self.assertEqual(result.reason_code, "route_main_commit_mismatch")

    def test_non_main_ref_is_rejected_by_the_contract(self) -> None:
        with self.assertRaises(ValidationError):
            route_evidence(ref="refs/heads/feature")

    def test_noncanonical_route_path_is_rejected_by_the_contract(self) -> None:
        with self.assertRaises(ValidationError):
            RouteFileIdentity("coordination/other.yaml", "b" * 40, "c" * 64)

    def test_route_blob_mismatch_is_rejected(self) -> None:
        evidence, documents = route_evidence(active=b"one")
        documents[CANONICAL_ACTIVE_TASK_PATH] = b"two"
        result = ReadOnlyRouteProofVerifier().verify(evidence, documents, REPOSITORY, MAIN_COMMIT, NOW)
        self.assertEqual(result.reason_code, "route_blob_hash_mismatch")

    def test_route_content_mismatch_is_rejected(self) -> None:
        active = b"active route document"
        bad_identity = RouteFileIdentity(CANONICAL_ACTIVE_TASK_PATH, _blob_sha1(active), "f" * 64)
        evidence, documents = route_evidence(active=active, active_identity=bad_identity)
        result = ReadOnlyRouteProofVerifier().verify(evidence, documents, REPOSITORY, MAIN_COMMIT, NOW)
        self.assertEqual(result.reason_code, "route_content_hash_mismatch")

    def test_future_route_observation_is_rejected(self) -> None:
        evidence, documents = route_evidence(observed_at="2026-08-02T00:00:01Z")
        result = ReadOnlyRouteProofVerifier().verify(evidence, documents, REPOSITORY, MAIN_COMMIT, NOW)
        self.assertEqual(result.reason_code, "route_observation_in_future")

    def test_stale_route_observation_is_rejected(self) -> None:
        evidence, documents = route_evidence(observed_at="2026-08-01T23:54:59Z")
        result = ReadOnlyRouteProofVerifier().verify(evidence, documents, REPOSITORY, MAIN_COMMIT, NOW)
        self.assertEqual(result.reason_code, "route_proof_stale")


class E37AtomicReservationTests(unittest.TestCase):
    def test_nonce_reuse_with_new_event_key_and_payload_is_suppressed(self) -> None:
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                gate = OneShotCanaryGate()
                bound = approval(nonce="nonce.e37.reused")
                first = gate.evaluate(store, event(), context(bound))
                second = gate.evaluate(
                    store,
                    event(event_id="event.e37.two", key="idem.e37.two", payload_hash="c" * 64),
                    context(bound, event_key="idem.e37.two"),
                )
                self.assertEqual(first.outcome, ShadowOutcome.CANARY_ELIGIBLE_SHADOW_ONLY)
                self.assertEqual(second.outcome, ShadowOutcome.DUPLICATE_SUPPRESSED)
                self.assertEqual(len(store.list_approval_consumptions()), 1)
                self.assertEqual(len(store.list_canary_events()), 1)
            finally:
                store.close()

    def test_failed_event_insert_rolls_back_nonce_consumption(self) -> None:
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                first = approval(nonce="nonce.e37.first")
                second = approval(nonce="nonce.e37.rollback")
                self.assertTrue(store.reserve_canary_event(event(), activation(first), verification(first), route_proof(), NOW))
                self.assertFalse(
                    store.reserve_canary_event(
                        event(key="idem.e37.two"), activation(second, event_key="idem.e37.two"), verification(second), route_proof(), NOW
                    )
                )
                self.assertTrue(
                    store.reserve_canary_event(
                        event(event_id="event.e37.after.rollback", key="idem.e37.three"),
                        activation(second, event_key="idem.e37.three"),
                        verification(second),
                        route_proof(),
                        NOW,
                    )
                )
                self.assertEqual(len(store.list_approval_consumptions()), 2)
                self.assertEqual(len(store.list_canary_events()), 2)
            finally:
                store.close()

    def test_unverified_approval_blocks_before_nonce_consumption(self) -> None:
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                bound = approval()
                unknown = ApprovalVerificationResult.unknown(NOW, "read_only_fetch_unavailable")
                decision = OneShotCanaryGate().evaluate(store, event(), context(bound, approval_result=unknown))
                self.assertEqual(decision.reason_code, "approval_read_only_verification_required")
                self.assertEqual(store.list_approval_consumptions(), [])
            finally:
                store.close()

    def test_unverified_route_proof_blocks_before_nonce_consumption(self) -> None:
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                bound = approval()
                unknown = RouteProofVerification.unknown(NOW, "route_fetch_unavailable")
                decision = OneShotCanaryGate().evaluate(store, event(), context(bound, proof=unknown))
                self.assertEqual(decision.reason_code, "route_read_only_verification_required")
                self.assertEqual(store.list_approval_consumptions(), [])
            finally:
                store.close()

    def test_persistence_omits_raw_approval_comment_and_event_bodies(self) -> None:
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                bound = approval()
                self.assertTrue(store.reserve_canary_event(event(), activation(bound), verification(bound), route_proof(), NOW))
                persisted = str(store.list_approval_consumptions() + store.list_canary_events() + store.list_verified_route_state_evidence())
                self.assertNotIn(BODY, persisted)
                self.assertNotIn("active route document", persisted)
                self.assertNotIn("coordination document", persisted)
            finally:
                store.close()

    def test_e37_changed_modules_have_no_executor_or_network_client_surface(self) -> None:
        source = SOURCE_ROOT / "brainops_control_plane"
        text = "\n".join((source / name).read_text(encoding="utf-8") for name in ("proofs.py", "canary.py", "store.py"))
        for forbidden in ("subprocess", "requests", "http.client", "selenium", "playwright", "dispatch(", "run_canary"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
