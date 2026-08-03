"""E40R1 bounded executable-canary tests; all use synthetic public fixtures."""

from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import threading
import unittest

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from brainops_control_plane.models import ValidationError
from brainops_control_plane.one_shot_canary import (
    E40R1_COMMENT,
    E40R1_ISSUE,
    E40R1_CANARY_ID,
    E40R1_ROUTE,
    E40R1_ROUTE_EPOCH,
    E40R1_SCOPE,
    E40R1_TASK_ID,
    OneShotCanaryExecutor,
    OneShotOwner,
    OneShotResultCode,
    OwnerPreflight,
    build_e40r1_request,
)
from brainops_control_plane.proofs import ExecutableCanaryRouteProofVerifier, ReadOnlyRouteProofVerifier, VerificationStatus
from brainops_control_plane.store import MetadataStore
from trusted_fixtures import FUTURE, NOW, approval_body, bound_approval, transport_for


E40_ACTOR = "vxz2datoubo"


def live_fixture(*, automatic: bool = True, canary: bool = True, actor: str = E40_ACTOR, expires_at: str = "2026-08-02T18:25:00Z"):
    bound = bound_approval(
        canary_id=E40R1_CANARY_ID,
        task_id=E40R1_TASK_ID,
        epoch=E40R1_ROUTE_EPOCH,
        scope=E40R1_SCOPE,
        nonce="e40r1-20260802-1425-c7a93f1b6d2e4a80",
        actor=actor,
        expires_at=expires_at,
        issue_number=E40R1_ISSUE,
        comment_id=E40R1_COMMENT,
    )
    return transport_for(
        task_id=E40R1_TASK_ID,
        epoch=E40R1_ROUTE_EPOCH,
        body=approval_body(bound),
        actor=actor,
        actors=(E40_ACTOR,),
        automatic_dispatch_allowed=automatic,
        canary_execution_allowed=canary,
        issue_number=E40R1_ISSUE,
        comment_id=E40R1_COMMENT,
    )


class E40R1RouteVerificationTests(unittest.TestCase):
    def test_executable_verifier_accepts_exact_enabled_flags(self) -> None:
        transport, _ = live_fixture()
        proof = ExecutableCanaryRouteProofVerifier().verify(E40R1_ROUTE, E40R1_TASK_ID, transport.fetch_main_route_snapshot(NOW), NOW)
        self.assertEqual(proof.status, VerificationStatus.READ_ONLY_FETCH_VERIFIED)
        self.assertTrue(proof.evidence.authority.automatic_dispatch_allowed)
        self.assertTrue(proof.evidence.authority.canary_execution_allowed)

    def test_historical_read_only_verifier_keeps_enabled_flags_fail_closed(self) -> None:
        transport, _ = live_fixture()
        proof = ReadOnlyRouteProofVerifier().verify(E40R1_ROUTE, E40R1_TASK_ID, transport.fetch_main_route_snapshot(NOW), NOW)
        self.assertEqual(proof.status, VerificationStatus.REJECTED)
        self.assertEqual(proof.reason_code, "pre_canary_route_flags_not_disabled")

    def test_executable_verifier_requires_both_enabled_flags(self) -> None:
        for automatic, canary in ((False, False), (True, False), (False, True)):
            transport, _ = live_fixture(automatic=automatic, canary=canary)
            proof = ExecutableCanaryRouteProofVerifier().verify(E40R1_ROUTE, E40R1_TASK_ID, transport.fetch_main_route_snapshot(NOW), NOW)
            self.assertEqual(proof.status, VerificationStatus.REJECTED)
            self.assertEqual(proof.reason_code, "executable_canary_route_flags_not_enabled")

    def test_live_request_rejects_wrong_approval_actor_before_reservation(self) -> None:
        transport, _ = live_fixture(actor="wrong_actor")
        with self.assertRaisesRegex(ValidationError, "approval_actor_not_authorized_by_route"):
            build_e40r1_request(transport, NOW)

    def test_live_request_rejects_expired_approval_before_reservation(self) -> None:
        transport, _ = live_fixture()
        with self.assertRaisesRegex(ValidationError, "approval_expired"):
            build_e40r1_request(transport, "2026-08-02T18:25:00Z")


class E40R1OneShotExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        transport, _ = live_fixture()
        self.request, self.approval, self.route = build_e40r1_request(transport, NOW)
        self.temp = TemporaryDirectory()
        self.store = MetadataStore(Path(self.temp.name))
        self.executor = OneShotCanaryExecutor()

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def execute(self, **kwargs):
        return self.executor.execute(self.store, self.request, self.approval, self.route, NOW, **kwargs)

    def test_valid_app_claim_reserves_and_reaches_terminal_success(self) -> None:
        result = self.execute()
        self.assertEqual(result.code, OneShotResultCode.SUCCEEDED)
        self.assertEqual(result.selected_owner, OneShotOwner.CODEX_APP)
        self.assertEqual(result.non_attempted_owner, OneShotOwner.CODEX_CLI)
        self.assertTrue(result.normal_dispatch_disabled)
        self.assertEqual(self.store.list_canary_events()[0]["selected_owner"], "CODEX_APP")
        outcome = self.store.list_one_shot_execution_outcomes()[0]
        self.assertEqual(outcome["terminal_state"], "SUCCEEDED")
        self.assertEqual(outcome["normal_dispatch_disabled"], 1)
        self.assertEqual(len(self.store.list_approval_consumptions()), 1)
        self.assertEqual(len(self.store.list_verified_route_state_evidence()), 1)

    def test_second_app_claim_is_suppressed_without_second_effect(self) -> None:
        self.assertEqual(self.execute().code, OneShotResultCode.SUCCEEDED)
        self.assertEqual(self.execute().code, OneShotResultCode.DUPLICATE_SUPPRESSED)
        self.assertEqual(len(self.store.list_one_shot_execution_outcomes()), 1)

    def test_cli_cannot_claim_when_app_is_available(self) -> None:
        request = type(self.request)(
            self.request.activation,
            self.request.event,
            OneShotOwner.CODEX_CLI,
            OwnerPreflight(app_available=True, cli_available=True),
        )
        result = self.executor.execute(self.store, request, self.approval, self.route, NOW)
        self.assertEqual(result.code, OneShotResultCode.WOULD_BLOCK)
        self.assertEqual(result.terminal_reason, "cli_fallback_forbidden_after_app_available")
        self.assertEqual(self.store.list_one_shot_execution_outcomes(), [])

    def test_cli_is_allowed_only_after_app_preflight_unavailable(self) -> None:
        request = type(self.request)(
            self.request.activation,
            self.request.event,
            OneShotOwner.CODEX_CLI,
            OwnerPreflight(app_available=False, cli_available=True),
        )
        result = self.executor.execute(self.store, request, self.approval, self.route, NOW)
        self.assertEqual(result.code, OneShotResultCode.SUCCEEDED)
        self.assertEqual(result.selected_owner, OneShotOwner.CODEX_CLI)
        self.assertEqual(result.non_attempted_owner, OneShotOwner.CODEX_APP)

    def test_app_unavailable_blocks_without_consuming_nonce(self) -> None:
        request = type(self.request)(
            self.request.activation,
            self.request.event,
            OneShotOwner.CODEX_APP,
            OwnerPreflight(app_available=False, cli_available=True),
        )
        result = self.executor.execute(self.store, request, self.approval, self.route, NOW)
        self.assertEqual(result.code, OneShotResultCode.WOULD_BLOCK)
        self.assertEqual(self.store.list_approval_consumptions(), [])

    def test_failure_is_terminal_and_consumes_the_only_count(self) -> None:
        result = self.execute(terminal_state=OneShotResultCode.FAILED, terminal_reason="bounded_engineering_failure")
        self.assertEqual(result.code, OneShotResultCode.FAILED)
        self.assertEqual(self.execute().code, OneShotResultCode.DUPLICATE_SUPPRESSED)
        self.assertEqual(self.store.list_one_shot_execution_outcomes()[0]["terminal_state"], "FAILED")

    def test_terminal_state_cannot_be_reopened(self) -> None:
        self.execute()
        self.assertFalse(self.store.finalize_one_shot_execution(self.request.event.event_id, "FAILED", "late_failure", NOW))

    def test_concurrent_claims_have_one_winner(self) -> None:
        results = []
        lock = threading.Lock()

        def claim() -> None:
            value = self.execute()
            with lock:
                results.append(value.code)

        threads = [threading.Thread(target=claim) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(results.count(OneShotResultCode.SUCCEEDED), 1)
        self.assertEqual(results.count(OneShotResultCode.DUPLICATE_SUPPRESSED), 3)

    def test_invalid_terminal_state_is_rejected_without_consuming_nonce(self) -> None:
        with self.assertRaisesRegex(ValidationError, "terminal state"):
            self.execute(terminal_state=OneShotResultCode.WOULD_BLOCK)
        self.assertEqual(self.store.list_approval_consumptions(), [])


if __name__ == "__main__":
    unittest.main()
