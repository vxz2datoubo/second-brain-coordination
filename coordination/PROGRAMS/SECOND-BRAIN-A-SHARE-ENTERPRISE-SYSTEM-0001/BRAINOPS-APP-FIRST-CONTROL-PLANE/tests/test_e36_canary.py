from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from brainops_control_plane.canary import E36_CANARY_ID, CanaryGateContext, OneShotCanaryGate, select_canary_owner
from brainops_control_plane.models import (
    ActivationManifest,
    BoundCanaryApproval,
    CanaryEvent,
    CapabilitySet,
    CapabilityStatus,
    ExecutionOwner,
    Lease,
    RouteRef,
    RouteState,
    ShadowOutcome,
    ValidationError,
    find_secret_values,
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


TASK_ID = "CODEX-BRAINOPS-OBSERVABLE-ONE-SHOT-AUTOMATIC-TRIGGER-CANARY-0031-E36"
ROUTE = RouteRef("brainops.e36", "CODEX", 37)
NOW = "2026-08-02T00:00:00Z"
FUTURE = "2026-08-02T01:00:00Z"
ACTIVE_HASH = "a" * 64
COORDINATION_HASH = "b" * 64
REPOSITORY = "vxz2datoubo/second-brain-coordination"
ISSUE_NUMBER = 114
COMMENT_ID = 114038
ACTOR = "gpt"
APPROVAL_BODY = "synthetic E37 approval only"
MAIN_COMMIT = "d" * 40


def approval(
    *,
    canary_id: str = E36_CANARY_ID,
    task_id: str = TASK_ID,
    route_epoch: int = 37,
    scope: str = "public_safe_non_executing_trigger_receipt_only",
    expires_at: str = FUTURE,
    nonce: str = "nonce.e36.one",
) -> BoundCanaryApproval:
    return BoundCanaryApproval(
        canary_id,
        task_id,
        route_epoch,
        scope,
        expires_at,
        nonce,
        canonical_approval_ref(REPOSITORY, ISSUE_NUMBER, COMMENT_ID),
        REPOSITORY,
        ISSUE_NUMBER,
        COMMENT_ID,
        ACTOR,
        NOW,
        hashlib.sha256(APPROVAL_BODY.encode("utf-8")).hexdigest(),
    )


def activation(*, bound: BoundCanaryApproval | None | object = ..., automatic_key: str = "idem.e36.one") -> ActivationManifest:
    selected = approval() if bound is ... else bound
    return ActivationManifest(
        "activation.e36",
        ROUTE,
        37,
        automatic_key,
        E36_CANARY_ID,
        TASK_ID,
        "public_safe_non_executing_trigger_receipt_only",
        "nonce.e36.one",
        selected,  # type: ignore[arg-type]
    )


def event(*, event_id: str = "event.e36.one", route: RouteRef = ROUTE, canary_id: str = E36_CANARY_ID, key: str = "idem.e36.one", payload_hash: str = "c" * 64) -> CanaryEvent:
    return CanaryEvent(event_id, "GITHUB", route, canary_id, key, payload_hash)


def _blob_sha1(content: bytes) -> str:
    return hashlib.sha1(f"blob {len(content)}\0".encode("ascii") + content).hexdigest()


def route_evidence(route: RouteRef = ROUTE, active_content: bytes = b"active task", coordination_content: bytes = b"coordination") -> RouteStateEvidence:
    return RouteStateEvidence(
        route,
        REPOSITORY,
        "refs/heads/main",
        MAIN_COMMIT,
        RouteFileIdentity(CANONICAL_ACTIVE_TASK_PATH, _blob_sha1(active_content), hashlib.sha256(active_content).hexdigest()),
        RouteFileIdentity(CANONICAL_COORDINATION_PATH, _blob_sha1(coordination_content), hashlib.sha256(coordination_content).hexdigest()),
        NOW,
    )


def route_proof(route: RouteRef = ROUTE, active_content: bytes = b"active task", coordination_content: bytes = b"coordination") -> RouteProofVerification:
    evidence_value = route_evidence(route, active_content, coordination_content)
    return ReadOnlyRouteProofVerifier().verify(
        evidence_value,
        {CANONICAL_ACTIVE_TASK_PATH: active_content, CANONICAL_COORDINATION_PATH: coordination_content},
        REPOSITORY,
        MAIN_COMMIT,
        NOW,
    )


def approval_verification(bound: BoundCanaryApproval) -> ApprovalVerificationResult:
    document = ReadOnlyApprovalDocument(REPOSITORY, ISSUE_NUMBER, COMMENT_ID, ACTOR, NOW, APPROVAL_BODY)
    return ReadOnlyApprovalVerifier().verify(bound, document, NOW)


def context(**overrides: object) -> CanaryGateContext:
    default_activation = activation()
    values: dict[str, object] = {
        "activation": default_activation,
        "route_state": RouteState.READY,
        "observed_epoch": 37,
        "capabilities": CapabilitySet(CapabilityStatus.SUPPORTED, CapabilityStatus.SUPPORTED, CapabilityStatus.SUPPORTED),
        "remote_available": True,
        "automatic_dispatch_allowed": True,
        "cli_fallback_permitted": False,
        "approval_verification": approval_verification(default_activation.approval),
        "route_proof": route_proof(),
        "checked_at": NOW,
    }
    values.update(overrides)
    selected_activation = values["activation"]
    assert isinstance(selected_activation, ActivationManifest)
    if "approval_verification" not in overrides:
        if selected_activation.approval is None:
            values["approval_verification"] = ApprovalVerificationResult.unknown(NOW, "bound_approval_missing")
        else:
            values["approval_verification"] = approval_verification(selected_activation.approval)
    if "route_proof" not in overrides:
        values["route_proof"] = route_proof(selected_activation.route)
    return CanaryGateContext(**values)  # type: ignore[arg-type]


class E36ContractTests(unittest.TestCase):
    def test_payload_hash_accepts_exact_lowercase_sha256(self) -> None:
        self.assertEqual(event().payload_hash, "c" * 64)

    def test_payload_hash_rejects_short_value(self) -> None:
        with self.assertRaises(ValidationError):
            event(payload_hash="c" * 63)

    def test_payload_hash_rejects_uppercase_value(self) -> None:
        with self.assertRaises(ValidationError):
            event(payload_hash="C" * 64)

    def test_event_rejects_non_github_source(self) -> None:
        with self.assertRaises(ValidationError):
            CanaryEvent("event.e36.one", "LOCAL", ROUTE, E36_CANARY_ID, "idem.e36.one", "c" * 64)

    def test_approval_canary_binding_is_checked(self) -> None:
        self.assertEqual(approval(canary_id="BRAINOPS-E36-CANARY-OTHER").validates(activation(), NOW), "approval_canary_mismatch")

    def test_approval_task_binding_is_checked(self) -> None:
        self.assertEqual(approval(task_id="CODEX-OTHER-TASK").validates(activation(), NOW), "approval_task_mismatch")

    def test_approval_epoch_binding_is_checked(self) -> None:
        self.assertEqual(approval(route_epoch=38).validates(activation(), NOW), "approval_epoch_mismatch")

    def test_approval_scope_binding_is_checked(self) -> None:
        self.assertEqual(approval(scope="other_scope").validates(activation(), NOW), "approval_scope_mismatch")

    def test_approval_expiry_is_checked(self) -> None:
        self.assertEqual(approval(expires_at=NOW).validates(activation(), NOW), "approval_expired")

    def test_approval_nonce_binding_is_checked(self) -> None:
        self.assertEqual(approval(nonce="nonce.e36.other").validates(activation(), NOW), "approval_nonce_mismatch")

    def test_manual_app_is_excluded_from_automatic_owner_selection(self) -> None:
        owner = select_canary_owner(CapabilitySet(CapabilityStatus.UNKNOWN, CapabilityStatus.UNKNOWN, CapabilityStatus.SUPPORTED), False)
        self.assertEqual(owner, ExecutionOwner.NONE)

    def test_cli_requires_explicit_route_permission(self) -> None:
        caps = CapabilitySet(CapabilityStatus.UNKNOWN, CapabilityStatus.SUPPORTED, CapabilityStatus.SUPPORTED)
        self.assertEqual(select_canary_owner(caps, False), ExecutionOwner.NONE)
        self.assertEqual(select_canary_owner(caps, True), ExecutionOwner.CLI_FALLBACK)

    def test_app_is_preferred_to_cli(self) -> None:
        self.assertEqual(select_canary_owner(CapabilitySet(CapabilityStatus.SUPPORTED, CapabilityStatus.SUPPORTED), True), ExecutionOwner.APP_AUTOMATION)

    def test_route_state_evidence_rejects_non_blob_hash(self) -> None:
        with self.assertRaises(ValidationError):
            RouteFileIdentity(CANONICAL_ACTIVE_TASK_PATH, "not-a-hash", ACTIVE_HASH)

    def test_context_rejects_unbound_state_evidence(self) -> None:
        other_route = RouteRef("brainops.other", "CODEX", 37)
        with self.assertRaises(ValidationError):
            context(route_proof=route_proof(other_route))

    def test_value_scanner_reports_category_not_secret_contents(self) -> None:
        fixture = "ghp_" + ("x" * 36)
        findings = find_secret_values({"opaque": fixture})
        self.assertEqual(findings[0].category, "github_token")
        self.assertNotIn(fixture, repr(findings))


class E36GateTests(unittest.TestCase):
    def run_gate(self, event_value: CanaryEvent | None = None, context_value: CanaryGateContext | None = None) -> tuple[object, MetadataStore]:
        self.temp = TemporaryDirectory()
        store = MetadataStore(Path(self.temp.name))
        decision = OneShotCanaryGate().evaluate(store, event_value or event(), context_value or context())
        return decision, store

    def tearDown(self) -> None:
        if hasattr(self, "temp"):
            self.temp.cleanup()

    def test_missing_bound_approval_blocks_before_reservation(self) -> None:
        decision, store = self.run_gate(context_value=context(activation=activation(bound=None)))
        try:
            self.assertEqual(decision.reason_code, "bound_approval_missing")
            self.assertEqual(store.list_canary_events(), [])
        finally:
            store.close()

    def test_automation_disabled_blocks_before_reservation(self) -> None:
        decision, store = self.run_gate(context_value=context(automatic_dispatch_allowed=False))
        try:
            self.assertEqual(decision.reason_code, "automation_disabled")
            self.assertEqual(store.list_canary_events(), [])
        finally:
            store.close()

    def test_stale_epoch_blocks_before_reservation(self) -> None:
        decision, store = self.run_gate(context_value=context(observed_epoch=36))
        try:
            self.assertEqual(decision.reason_code, "stale_epoch")
            self.assertEqual(store.list_canary_events(), [])
        finally:
            store.close()

    def test_paused_route_blocks_before_reservation(self) -> None:
        decision, store = self.run_gate(context_value=context(route_state=RouteState.PAUSED))
        try:
            self.assertEqual(decision.reason_code, "route_paused")
            self.assertEqual(store.list_canary_events(), [])
        finally:
            store.close()

    def test_offline_route_blocks_before_reservation(self) -> None:
        decision, store = self.run_gate(context_value=context(remote_available=False))
        try:
            self.assertEqual(decision.reason_code, "github_offline")
            self.assertEqual(store.list_canary_events(), [])
        finally:
            store.close()

    def test_manual_only_capability_cannot_automatically_progress(self) -> None:
        caps = CapabilitySet(CapabilityStatus.UNKNOWN, CapabilityStatus.UNKNOWN, CapabilityStatus.SUPPORTED)
        decision, store = self.run_gate(context_value=context(capabilities=caps))
        try:
            self.assertEqual(decision.reason_code, "no_supported_automatic_owner")
            self.assertEqual(store.list_canary_events(), [])
        finally:
            store.close()

    def test_unallowlisted_canary_is_rejected(self) -> None:
        invalid = event(canary_id="BRAINOPS-E36-CANARY-OTHER")
        decision, store = self.run_gate(event_value=invalid)
        try:
            self.assertEqual(decision.reason_code, "canary_id_not_allowlisted")
            self.assertEqual(store.list_canary_events(), [])
        finally:
            store.close()

    def test_event_route_mismatch_is_rejected(self) -> None:
        other_route = RouteRef("brainops.other", "CODEX", 37)
        decision, store = self.run_gate(event_value=event(route=other_route))
        try:
            self.assertEqual(decision.reason_code, "event_route_mismatch")
            self.assertEqual(store.list_canary_events(), [])
        finally:
            store.close()

    def test_valid_canary_is_shadow_eligible_and_never_dispatches(self) -> None:
        decision, store = self.run_gate()
        try:
            self.assertEqual(decision.outcome, ShadowOutcome.CANARY_ELIGIBLE_SHADOW_ONLY)
            self.assertFalse(decision.actual_dispatch_performed)
            self.assertEqual(len(store.list_canary_events()), 1)
            self.assertEqual(len(store.list_approval_consumptions()), 1)
            self.assertEqual(len(store.list_verified_route_state_evidence()), 1)
        finally:
            store.close()

    def test_duplicate_same_event_is_persistently_suppressed_without_second_effect(self) -> None:
        self.temp = TemporaryDirectory()
        store = MetadataStore(Path(self.temp.name))
        try:
            gate = OneShotCanaryGate()
            first = gate.evaluate(store, event(), context())
            second = gate.evaluate(store, event(), context())
            self.assertEqual(first.outcome, ShadowOutcome.CANARY_ELIGIBLE_SHADOW_ONLY)
            self.assertEqual(second.outcome, ShadowOutcome.DUPLICATE_SUPPRESSED)
            self.assertEqual(len(store.list_canary_events()), 1)
            self.assertEqual(len(store.list_approval_consumptions()), 1)
            self.assertEqual(len(store.list_verified_route_state_evidence()), 1)
        finally:
            store.close()

    def test_duplicate_idempotency_key_with_new_event_is_suppressed(self) -> None:
        self.temp = TemporaryDirectory()
        store = MetadataStore(Path(self.temp.name))
        try:
            gate = OneShotCanaryGate()
            gate.evaluate(store, event(), context())
            duplicate = gate.evaluate(store, event(event_id="event.e36.two"), context())
            self.assertEqual(duplicate.outcome, ShadowOutcome.DUPLICATE_SUPPRESSED)
            self.assertEqual(len(store.list_canary_events()), 1)
        finally:
            store.close()

    def test_changed_route_proof_cannot_add_a_second_effect_for_duplicate(self) -> None:
        self.temp = TemporaryDirectory()
        store = MetadataStore(Path(self.temp.name))
        try:
            gate = OneShotCanaryGate()
            gate.evaluate(store, event(), context())
            changed = context(route_proof=route_proof(coordination_content=b"changed coordination"))
            duplicate = gate.evaluate(store, event(), changed)
            self.assertEqual(duplicate.outcome, ShadowOutcome.DUPLICATE_SUPPRESSED)
            self.assertEqual(len(store.list_verified_route_state_evidence()), 1)
        finally:
            store.close()


class E36StoreTests(unittest.TestCase):
    def test_unknown_key_secret_value_is_redacted_before_persistence(self) -> None:
        fixture = "ghp_" + ("x" * 36)
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                store.record_audit("public_event", {"opaque": fixture}, NOW)
                stored = store.list_audit()[0]["payload"]
                self.assertEqual(stored["opaque"], "[REDACTED]")
                self.assertNotIn(fixture, str(stored))
                self.assertEqual(stored["_value_secret_findings"][0]["category"], "github_token")
            finally:
                store.close()

    def test_expired_lease_is_deterministically_released(self) -> None:
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                stale = Lease("lease.e36.stale", ROUTE, ExecutionOwner.APP_AUTOMATION, 1, NOW, "2026-08-02T00:05:00Z")
                self.assertTrue(store.acquire_lease(stale, NOW))
                self.assertTrue(store.active_lease_exists(ROUTE.route_id, ROUTE.route_epoch, "2026-08-02T00:04:59Z"))
                self.assertFalse(store.active_lease_exists(ROUTE.route_id, ROUTE.route_epoch, "2026-08-02T00:05:00Z"))
            finally:
                store.close()

    def test_fencing_generation_cannot_regress_after_release(self) -> None:
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                first = Lease("lease.e36.one", ROUTE, ExecutionOwner.APP_AUTOMATION, 2, NOW, FUTURE)
                lower = Lease("lease.e36.lower", ROUTE, ExecutionOwner.APP_AUTOMATION, 1, NOW, FUTURE)
                newer = Lease("lease.e36.newer", ROUTE, ExecutionOwner.APP_AUTOMATION, 3, NOW, FUTURE)
                self.assertTrue(store.acquire_lease(first, NOW))
                self.assertTrue(store.release_lease(first.lease_id, NOW))
                self.assertFalse(store.acquire_lease(lower, NOW))
                self.assertTrue(store.acquire_lease(newer, NOW))
            finally:
                store.close()

    def test_route_evidence_and_event_are_atomic(self) -> None:
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                selected_activation = activation()
                assert selected_activation.approval is not None
                verification = approval_verification(selected_activation.approval)
                self.assertTrue(store.reserve_canary_event(event(), selected_activation, verification, route_proof(), NOW))
                self.assertFalse(store.reserve_canary_event(event(), selected_activation, verification, route_proof(coordination_content=b"changed"), NOW))
                self.assertEqual(len(store.list_canary_events()), 1)
                self.assertEqual(len(store.list_approval_consumptions()), 1)
                self.assertEqual(len(store.list_verified_route_state_evidence()), 1)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
