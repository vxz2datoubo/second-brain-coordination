"""E39 live route actor policy and pre-canary readiness tests."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from brainops_control_plane.ci_identity import assert_exact_head
from brainops_control_plane.models import RouteRef, ValidationError
from brainops_control_plane.proofs import ReadOnlyRouteProofVerifier, VerificationStatus
from brainops_control_plane.route_readiness import (
    E39_EXPECTED_AUTHORIZED_ACTORS,
    E39_ROUTE,
    E39_ROUTE_EPOCH,
    E39_TASK_ID,
    LiveRoutePreCanaryReadinessObserver,
    PreCanaryReadinessCode,
    PreCanaryReadinessProof,
)
from trusted_fixtures import NOW, transport_for


class E39RouteReadinessTests(unittest.TestCase):
    def _verified_route(self, *, actors: tuple[str, ...] = E39_EXPECTED_AUTHORIZED_ACTORS):
        transport, _ = transport_for(task_id=E39_TASK_ID, epoch=E39_ROUTE_EPOCH, body="not-an-approval", actors=actors)
        snapshot = transport.fetch_main_route_snapshot(NOW)
        return ReadOnlyRouteProofVerifier().verify(E39_ROUTE, E39_TASK_ID, snapshot, NOW)

    def test_authorized_actor_policy_accepts_repository_owner_only(self) -> None:
        proof = self._verified_route()
        self.assertEqual(proof.status, VerificationStatus.READ_ONLY_FETCH_VERIFIED)
        self.assertEqual(proof.evidence.authority.authorized_approval_actors, ("vxz2datoubo",))
        self.assertFalse(proof.evidence.authority.automatic_dispatch_allowed)
        self.assertFalse(proof.evidence.authority.canary_execution_allowed)

    def test_no_approval_returns_exact_blocked_pre_canary_state(self) -> None:
        proof = self._verified_route()
        readiness = LiveRoutePreCanaryReadinessObserver().evaluate(proof, NOW)
        self.assertEqual(readiness.result_code, PreCanaryReadinessCode.APPROVAL_NOT_SUPPLIED_CANARY_BLOCKED)
        self.assertFalse(readiness.approval_supplied)
        self.assertFalse(readiness.canary_executed)
        self.assertIn("trusted execution boundary", readiness.trust_boundary)
        self.assertIn("not cryptographic isolation", readiness.trust_boundary)

    def test_observer_fetches_route_proof_from_snapshot_instead_of_caller_verified_fact(self) -> None:
        transport, _ = transport_for(task_id=E39_TASK_ID, epoch=E39_ROUTE_EPOCH, body="not-an-approval", actors=E39_EXPECTED_AUTHORIZED_ACTORS)
        readiness = LiveRoutePreCanaryReadinessObserver().observe_snapshot(transport.fetch_main_route_snapshot(NOW), NOW)
        self.assertEqual(readiness.result_code, PreCanaryReadinessCode.APPROVAL_NOT_SUPPLIED_CANARY_BLOCKED)
        self.assertEqual(readiness.main_tree_sha1, "e" * 40)

    def test_wrong_actor_policy_is_not_pre_canary_ready(self) -> None:
        proof = self._verified_route(actors=("other_actor",))
        readiness = LiveRoutePreCanaryReadinessObserver().evaluate(proof, NOW)
        self.assertEqual(readiness.result_code, PreCanaryReadinessCode.ROUTE_ACTOR_POLICY_MISMATCH)
        self.assertEqual(readiness.authorized_approval_actors, ("other_actor",))

    def test_missing_actor_policy_still_fails_closed(self) -> None:
        proof = self._verified_route(actors=())
        readiness = LiveRoutePreCanaryReadinessObserver().evaluate(proof, NOW)
        self.assertEqual(readiness.result_code, PreCanaryReadinessCode.ROUTE_AUTHORITY_UNVERIFIED)
        self.assertEqual(readiness.route_proof_status, VerificationStatus.REJECTED)

    def test_route_flags_must_remain_disabled(self) -> None:
        for flag in ("automatic_dispatch_allowed", "canary_execution_allowed"):
            kwargs = {flag: True}
            transport, _ = transport_for(task_id=E39_TASK_ID, epoch=E39_ROUTE_EPOCH, body="not-an-approval", actors=E39_EXPECTED_AUTHORIZED_ACTORS, **kwargs)
            proof = ReadOnlyRouteProofVerifier().verify(E39_ROUTE, E39_TASK_ID, transport.fetch_main_route_snapshot(NOW), NOW)
            readiness = LiveRoutePreCanaryReadinessObserver().evaluate(proof, NOW)
            self.assertEqual(readiness.result_code, PreCanaryReadinessCode.ROUTE_AUTHORITY_UNVERIFIED)

    def test_no_public_api_can_create_executed_readiness_proof(self) -> None:
        with self.assertRaises(ValidationError):
            PreCanaryReadinessProof(
                route=E39_ROUTE,
                checked_at=NOW,
                result_code=PreCanaryReadinessCode.APPROVAL_NOT_SUPPLIED_CANARY_BLOCKED,
                route_proof_status=VerificationStatus.READ_ONLY_FETCH_VERIFIED,
                route_reason_code="manual_fact",
                main_commit_sha1="d" * 40,
                main_tree_sha1="e" * 40,
                active_task_blob_sha1="a" * 40,
                active_task_content_sha256="a" * 64,
                coordination_blob_sha1="b" * 40,
                coordination_content_sha256="b" * 64,
                authorized_approval_actors=E39_EXPECTED_AUTHORIZED_ACTORS,
                approval_supplied=False,
                automatic_dispatch_allowed=False,
                canary_execution_allowed=False,
                canary_executed=True,
            )

    def test_exact_head_helper_and_e39_workflow_identity_are_present(self) -> None:
        self.assertEqual(assert_exact_head("a" * 40, "a" * 40), "a" * 40)
        workflow = (Path(__file__).resolve().parents[5] / ".github" / "workflows" / "brainops-e39.yml").read_text(encoding="utf-8")
        self.assertIn("ref: ${{ github.event.pull_request.head.sha }}", workflow)
        self.assertIn("Run BrainOps E35 through E39 tests", workflow)
        self.assertIn("verified_head=", workflow)

    def test_observer_rejects_wrong_route_object(self) -> None:
        transport, _ = transport_for(task_id=E39_TASK_ID, epoch=E39_ROUTE_EPOCH, body="not-an-approval", actors=E39_EXPECTED_AUTHORIZED_ACTORS)
        wrong_route = RouteRef("brainops.e39.wrong", "CODEX", E39_ROUTE_EPOCH)
        proof = ReadOnlyRouteProofVerifier().verify(wrong_route, E39_TASK_ID, transport.fetch_main_route_snapshot(NOW), NOW)
        self.assertEqual(proof.reason_code, "trusted_main_ref_commit_tree_path_blob_content_and_route_flags_verified")
        readiness = LiveRoutePreCanaryReadinessObserver().evaluate(proof, NOW)
        self.assertEqual(readiness.result_code, PreCanaryReadinessCode.ROUTE_AUTHORITY_UNVERIFIED)
        self.assertNotEqual(proof.evidence.route, E39_ROUTE)


if __name__ == "__main__":
    unittest.main()
