"""E37 regressions plus E38 trusted-authority adversarial tests.

All accepted objects below are created by the in-memory public GitHub API
fixture, never by a result factory or a caller-supplied document constructor.
"""

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
from brainops_control_plane.ci_identity import assert_exact_head
from brainops_control_plane.github_transport import PublicGitHubTransport, ReadOnlyTransportError
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
    ApprovalEvidence,
    ApprovalVerificationResult,
    CANONICAL_ACTIVE_TASK_PATH,
    CANONICAL_REPOSITORY,
    CanonicalApprovalBinding,
    ReadOnlyApprovalDocument,
    ReadOnlyApprovalVerifier,
    ReadOnlyRouteProofVerifier,
    RouteProofVerification,
    VerificationStatus,
    canonical_approval_ref,
    parse_canonical_approval_body,
)
from brainops_control_plane.store import MetadataStore
from trusted_fixtures import (
    ACTOR,
    FUTURE,
    ISSUE_NUMBER,
    NOW,
    bound_approval,
    approval_body,
    transport_for,
)


ROUTE = RouteRef("brainops.e38", "CODEX", 39)
TASK_ID = "CODEX-BRAINOPS-TRUSTED-APPROVAL-TRANSPORT-GIT-TREE-AND-EXACT-HEAD-CI-CLOSURE-0033-E38"
SCOPE = "public_safe_pre_canary_proof_only"


def approval(*, nonce: str = "nonce.e38.one", actor: str = ACTOR, body: str | None = None) -> BoundCanaryApproval:
    return bound_approval(
        canary_id=E36_CANARY_ID,
        task_id=TASK_ID,
        epoch=39,
        scope=SCOPE,
        nonce=nonce,
        actor=actor,
        body=body,
    )


def verified_route_and_approval(
    bound: BoundCanaryApproval | None = None,
    *,
    actor: str = ACTOR,
    actors: tuple[str, ...] = (ACTOR,),
    body: str | None = None,
):
    bound = bound or approval(actor=actor, body=body)
    body = body if body is not None else approval_body(bound)
    transport, opener = transport_for(task_id=TASK_ID, epoch=39, body=body, actor=actor, actors=actors)
    snapshot = transport.fetch_main_route_snapshot(NOW)
    route_result = ReadOnlyRouteProofVerifier().verify(ROUTE, TASK_ID, snapshot, NOW)
    comment = transport.fetch_approval_comment(ISSUE_NUMBER, 114038)
    approval_result = ReadOnlyApprovalVerifier().verify(bound, comment, route_result, NOW)
    return route_result, approval_result, transport, opener


def activation(bound: BoundCanaryApproval, *, key: str = "idem.e38.one") -> ActivationManifest:
    return ActivationManifest("activation.e38", ROUTE, 39, key, E36_CANARY_ID, TASK_ID, SCOPE, bound.nonce, bound)


def event(*, event_id: str = "event.e38.one", key: str = "idem.e38.one", payload_hash: str = "b" * 64) -> CanaryEvent:
    return CanaryEvent(event_id, "GITHUB", ROUTE, E36_CANARY_ID, key, payload_hash)


def context(
    bound: BoundCanaryApproval,
    approval_result: ApprovalVerificationResult,
    route_result: RouteProofVerification,
    *,
    key: str = "idem.e38.one",
) -> CanaryGateContext:
    return CanaryGateContext(
        activation(bound, key=key),
        RouteState.READY,
        39,
        CapabilitySet(CapabilityStatus.SUPPORTED, CapabilityStatus.UNKNOWN, CapabilityStatus.UNKNOWN),
        True,
        True,
        False,
        approval_result,
        route_result,
        NOW,
    )


class E38ApprovalContractTests(unittest.TestCase):
    def test_public_verified_factories_are_absent(self) -> None:
        self.assertFalse(hasattr(ApprovalVerificationResult, "verified"))
        self.assertFalse(hasattr(RouteProofVerification, "verified"))

    def test_external_constructors_cannot_mint_verified_results(self) -> None:
        evidence = ApprovalEvidence(CANONICAL_REPOSITORY, ISSUE_NUMBER, 114038, ACTOR, NOW, "a" * 64, canonical_approval_ref(CANONICAL_REPOSITORY, ISSUE_NUMBER, 114038), "b" * 64)
        with self.assertRaises(ValidationError):
            ApprovalVerificationResult(VerificationStatus.READ_ONLY_FETCH_VERIFIED, evidence, NOW, "forged_result")
        with self.assertRaises(ValidationError):
            RouteProofVerification(VerificationStatus.READ_ONLY_FETCH_VERIFIED, None, NOW, "forged_result")

    def test_external_comment_constructor_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ReadOnlyApprovalDocument(CANONICAL_REPOSITORY, ISSUE_NUMBER, 114038, ACTOR, NOW, "body")

    def test_canonical_approval_block_round_trips(self) -> None:
        bound = approval()
        parsed = parse_canonical_approval_body(approval_body(bound))
        self.assertEqual(parsed.task_id, TASK_ID)
        self.assertEqual(parsed.nonce, bound.nonce)

    def test_duplicate_approval_keys_fail_closed(self) -> None:
        duplicate = '```brainops-approval-v1\n{"canary_id":"BRAINOPS-E36-CANARY-0001","canary_id":"BRAINOPS-E36-CANARY-0001","expires_at":"2026-08-02T01:00:00Z","nonce":"nonce.e38.one","route_epoch":39,"scope":"public_safe_pre_canary_proof_only","task_id":"CODEX-BRAINOPS-TRUSTED-APPROVAL-TRANSPORT-GIT-TREE-AND-EXACT-HEAD-CI-CLOSURE-0033-E38"}\n```'
        _, result, _, _ = verified_route_and_approval(approval(), body=duplicate)
        self.assertEqual(result.status, VerificationStatus.REJECTED)

    def test_extra_approval_binding_field_fails_closed(self) -> None:
        raw = CanonicalApprovalBinding(TASK_ID, 39, E36_CANARY_ID, SCOPE, FUTURE, "nonce.e38.one").canonical_json()
        malformed = f"```brainops-approval-v1\n{raw[:-1]},\"extra\":true}}\n```"
        _, result, _, _ = verified_route_and_approval(approval(), body=malformed)
        self.assertEqual(result.status, VerificationStatus.REJECTED)

    def test_wrong_authorized_actor_fails_closed(self) -> None:
        bound = approval(actor="other_actor")
        _, result, _, _ = verified_route_and_approval(bound, actor="other_actor", actors=(ACTOR,))
        self.assertEqual(result.reason_code, "approval_actor_not_authorized_by_route")

    def test_body_binding_mismatch_fails_closed(self) -> None:
        bound = approval()
        wrong = approval(nonce="nonce.e38.other")
        _, result, _, _ = verified_route_and_approval(bound, body=approval_body(wrong))
        self.assertEqual(result.reason_code, "approval_body_binding_mismatch")

    def test_expired_approval_fails_closed(self) -> None:
        bound = bound_approval(canary_id=E36_CANARY_ID, task_id=TASK_ID, epoch=39, scope=SCOPE, nonce="nonce.e38.expired", expires_at="2026-08-01T23:59:59Z")
        _, result, _, _ = verified_route_and_approval(bound)
        self.assertEqual(result.status, VerificationStatus.REJECTED)

    def test_unrelated_issue_comment_fails_closed(self) -> None:
        bound = approval()
        body = approval_body(bound)
        transport, _ = transport_for(task_id=TASK_ID, epoch=39, body=body, issue_url="https://api.github.com/repos/vxz2datoubo/second-brain-coordination/issues/999")
        proof = ReadOnlyRouteProofVerifier().verify(ROUTE, TASK_ID, transport.fetch_main_route_snapshot(NOW), NOW)
        with self.assertRaises(ReadOnlyTransportError):
            transport.fetch_approval_comment(ISSUE_NUMBER, 114038)
        self.assertEqual(proof.status, VerificationStatus.READ_ONLY_FETCH_VERIFIED)


class E38RouteProofTests(unittest.TestCase):
    def test_ref_commit_tree_path_blob_content_route_proof_is_verified(self) -> None:
        proof, _, _, opener = verified_route_and_approval()
        self.assertEqual(proof.status, VerificationStatus.READ_ONLY_FETCH_VERIFIED)
        self.assertEqual(proof.evidence.main_tree_sha1, "e" * 40)
        self.assertEqual(len(opener.requests), 7)
        self.assertEqual(assert_exact_head("a" * 40, "a" * 40), "a" * 40)
        with self.assertRaisesRegex(ValidationError, "ci_checkout_sha_differs"):
            assert_exact_head("a" * 40, "b" * 40)
        workflow = (Path(__file__).resolve().parents[5] / ".github" / "workflows" / "brainops-e40r1.yml").read_text(encoding="utf-8")
        self.assertIn("ref: ${{ github.event.pull_request.head.sha }}", workflow)
        self.assertIn("Assert exact pull-request head checkout", workflow)

    def test_main_ref_drift_fails_closed(self) -> None:
        bound = approval()
        transport, _ = transport_for(task_id=TASK_ID, epoch=39, body=approval_body(bound), main_ref_values=("d" * 40, "c" * 40))
        with self.assertRaisesRegex(ReadOnlyTransportError, "github_main_ref_drift"):
            transport.fetch_main_route_snapshot(NOW)

    def test_missing_actor_policy_fails_closed(self) -> None:
        bound = approval()
        transport, _ = transport_for(task_id=TASK_ID, epoch=39, body=approval_body(bound), actors=())
        proof = ReadOnlyRouteProofVerifier().verify(ROUTE, TASK_ID, transport.fetch_main_route_snapshot(NOW), NOW)
        self.assertEqual(proof.status, VerificationStatus.REJECTED)

    def test_wrong_epoch_in_route_fails_closed(self) -> None:
        bound = approval()
        transport, _ = transport_for(task_id=TASK_ID, epoch=38, body=approval_body(bound))
        proof = ReadOnlyRouteProofVerifier().verify(ROUTE, TASK_ID, transport.fetch_main_route_snapshot(NOW), NOW)
        self.assertEqual(proof.reason_code, "route_epoch_mismatch")
        transport, _ = transport_for(task_id="CODEX-BRAINOPS-OTHER", epoch=39, body=approval_body(bound))
        proof = ReadOnlyRouteProofVerifier().verify(ROUTE, TASK_ID, transport.fetch_main_route_snapshot(NOW), NOW)
        self.assertEqual(proof.reason_code, "route_task_id_mismatch")
        for flags in (
            {"status": "PAUSED"},
            {"execution_allowed": False},
            {"automatic_dispatch_allowed": True},
            {"canary_execution_allowed": True},
        ):
            transport, _ = transport_for(task_id=TASK_ID, epoch=39, body=approval_body(bound), **flags)
            proof = ReadOnlyRouteProofVerifier().verify(ROUTE, TASK_ID, transport.fetch_main_route_snapshot(NOW), NOW)
            self.assertEqual(proof.status, VerificationStatus.REJECTED)

    def test_stale_route_snapshot_fails_closed(self) -> None:
        bound = approval()
        transport, _ = transport_for(task_id=TASK_ID, epoch=39, body=approval_body(bound))
        proof = ReadOnlyRouteProofVerifier().verify(ROUTE, TASK_ID, transport.fetch_main_route_snapshot("2026-08-01T23:54:59Z"), NOW)
        self.assertEqual(proof.reason_code, "route_proof_stale")

    def test_unsealed_route_snapshot_fails_closed(self) -> None:
        bound = approval()
        transport, _ = transport_for(
            task_id=TASK_ID,
            epoch=39,
            body=approval_body(bound),
            omit_tree_path=CANONICAL_ACTIVE_TASK_PATH,
        )
        with self.assertRaisesRegex(ReadOnlyTransportError, "github_tree_route_path_missing"):
            transport.fetch_main_route_snapshot(NOW)
        result = ReadOnlyRouteProofVerifier().verify(ROUTE, TASK_ID, object(), NOW)  # type: ignore[arg-type]
        self.assertEqual(result.reason_code, "route_snapshot_not_transport_bound")

    def test_transport_rejects_redirected_response(self) -> None:
        bound = approval()
        transport, opener = transport_for(task_id=TASK_ID, epoch=39, body=approval_body(bound))
        first_url = next(iter(opener.responses))
        opener.responses[first_url][0]._url = "https://evil.example/redirect"
        with self.assertRaisesRegex(ReadOnlyTransportError, "github_redirect_rejected"):
            transport.fetch_main_route_snapshot(NOW)

    def test_transport_rejects_wrong_media_type(self) -> None:
        bound = approval()
        transport, opener = transport_for(task_id=TASK_ID, epoch=39, body=approval_body(bound))
        first_url = next(iter(opener.responses))
        opener.responses[first_url][0].headers["Content-Type"] = "text/html"
        with self.assertRaisesRegex(ReadOnlyTransportError, "github_unexpected_media_type"):
            transport.fetch_main_route_snapshot(NOW)


class E38AtomicRegressionTests(unittest.TestCase):
    def test_verified_provenance_preserves_atomic_nonce_suppression(self) -> None:
        bound = approval(nonce="nonce.e38.reused")
        route, result, _, _ = verified_route_and_approval(bound)
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                gate = OneShotCanaryGate()
                first = gate.evaluate(store, event(), context(bound, result, route))
                second = gate.evaluate(
                    store,
                    event(event_id="event.e38.two", key="idem.e38.two", payload_hash="c" * 64),
                    context(replace(bound, nonce="nonce.e38.reused"), result, route, key="idem.e38.two"),
                )
                self.assertEqual(first.outcome, ShadowOutcome.CANARY_ELIGIBLE_SHADOW_ONLY)
                self.assertEqual(second.outcome, ShadowOutcome.DUPLICATE_SUPPRESSED)
                self.assertEqual(len(store.list_approval_consumptions()), 1)
            finally:
                store.close()

    def test_unverified_approval_still_blocks_before_persistence(self) -> None:
        bound = approval()
        route, _, _, _ = verified_route_and_approval(bound)
        blocked = ApprovalVerificationResult.unknown(NOW, "trusted_transport_unavailable")
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                decision = OneShotCanaryGate().evaluate(store, event(), context(bound, blocked, route))
                self.assertEqual(decision.reason_code, "approval_read_only_verification_required")
                self.assertEqual(store.list_approval_consumptions(), [])
            finally:
                store.close()

    def test_unverified_route_still_blocks_before_persistence(self) -> None:
        bound = approval()
        _, result, _, _ = verified_route_and_approval(bound)
        blocked = RouteProofVerification.unknown(NOW, "trusted_transport_unavailable")
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                decision = OneShotCanaryGate().evaluate(store, event(), context(bound, result, blocked))
                self.assertEqual(decision.reason_code, "route_read_only_verification_required")
                self.assertEqual(store.list_canary_events(), [])
            finally:
                store.close()

    def test_persistence_retains_hashes_but_not_comment_body(self) -> None:
        bound = approval()
        route, result, _, _ = verified_route_and_approval(bound)
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                self.assertTrue(store.reserve_canary_event(event(), activation(bound), result, route, NOW))
                persisted = str(store.list_approval_consumptions() + store.list_verified_route_state_evidence())
                self.assertNotIn("brainops-approval-v1", persisted)
                self.assertIn(hashlib.sha256(approval_body(bound).encode("utf-8")).hexdigest(), persisted)
                self.assertEqual(store.list_verified_route_state_evidence()[0]["main_tree_sha1"], "e" * 40)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
