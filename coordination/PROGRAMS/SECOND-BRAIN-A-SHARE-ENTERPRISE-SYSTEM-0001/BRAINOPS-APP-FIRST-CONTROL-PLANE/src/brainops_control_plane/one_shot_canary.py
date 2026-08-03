"""E40R1's bounded, terminal one-shot engineering Canary.

The module deliberately models only the route-claim state transition.  It has
no subprocess, shell, service, account, credential, order, or trading API.
An external owner is selected and recorded as public metadata, while the
single persisted reservation prevents a second App or CLI attempt.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import (
    ActivationManifest,
    BoundCanaryApproval,
    CanaryEvent,
    RouteRef,
    ValidationError,
    canonical_hash,
    parse_rfc3339_utc,
    require_identifier,
)
from .proofs import (
    ApprovalVerificationResult,
    ExecutableCanaryRouteProofVerifier,
    ReadOnlyApprovalVerifier,
    RouteProofVerification,
    VerificationStatus,
    canonical_approval_ref,
)
from .store import MetadataStore


E40R1_TASK_ID = "CODEX-BRAINOPS-ONE-SHOT-BOUNDED-ENGINEERING-CANARY-0036-E40R1"
E40R1_ROUTE_EPOCH = 42
E40R1_ROUTE = RouteRef("brainops.e40r1", "CODEX", E40R1_ROUTE_EPOCH)
E40R1_CANARY_ID = "BRAINOPS-E40R1-ONE-SHOT-ENGINEERING-0001"
E40R1_SCOPE = "brainops_one_shot_engineering_canary_app_first_cli_fallback_no_trade"
E40R1_ISSUE = 126
E40R1_COMMENT = 5155930613
E40R1_NONCE = "e40r1-20260802-1425-c7a93f1b6d2e4a80"
E40R1_EXPIRES_AT = "2026-08-02T18:25:00Z"


class OneShotOwner(str, Enum):
    CODEX_APP = "CODEX_APP"
    CODEX_CLI = "CODEX_CLI"


class OneShotResultCode(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    DUPLICATE_SUPPRESSED = "DUPLICATE_SUPPRESSED"
    WOULD_BLOCK = "WOULD_BLOCK"


@dataclass(frozen=True)
class OwnerPreflight:
    """A non-secret availability result; it never probes a CLI session."""

    app_available: bool
    cli_available: bool


@dataclass(frozen=True)
class OneShotExecutionRequest:
    activation: ActivationManifest
    event: CanaryEvent
    selected_owner: OneShotOwner
    preflight: OwnerPreflight

    def __post_init__(self) -> None:
        if self.activation.route != E40R1_ROUTE:
            raise ValidationError("one-shot execution route is not E40R1")
        if self.activation.task_id != E40R1_TASK_ID:
            raise ValidationError("one-shot execution task is not E40R1")
        if self.activation.canary_id != E40R1_CANARY_ID:
            raise ValidationError("one-shot execution canary is not allowlisted")
        if self.event.route != self.activation.route or self.event.canary_id != self.activation.canary_id:
            raise ValidationError("one-shot event must bind the E40R1 activation")

    @property
    def non_attempted_owner(self) -> OneShotOwner:
        return OneShotOwner.CODEX_CLI if self.selected_owner is OneShotOwner.CODEX_APP else OneShotOwner.CODEX_APP


@dataclass(frozen=True)
class OneShotExecutionResult:
    code: OneShotResultCode
    event_id: str
    selected_owner: OneShotOwner
    non_attempted_owner: OneShotOwner
    terminal_reason: str
    normal_dispatch_disabled: bool


def build_e40r1_request(
    transport: object,
    checked_at: str,
    *,
    selected_owner: OneShotOwner = OneShotOwner.CODEX_APP,
    preflight: OwnerPreflight = OwnerPreflight(app_available=True, cli_available=False),
) -> tuple[OneShotExecutionRequest, ApprovalVerificationResult, RouteProofVerification]:
    """Read the public route/comment once and build a bound in-memory request.

    The transport is intentionally duck-typed to keep the control surface
    limited to the existing public GitHub reader and its test fixture.
    """

    parse_rfc3339_utc(checked_at, "E40R1 checked_at")
    fetch_route = getattr(transport, "fetch_main_route_snapshot", None)
    fetch_comment = getattr(transport, "fetch_approval_comment", None)
    if not callable(fetch_route) or not callable(fetch_comment):
        raise ValidationError("E40R1 requires the bounded public GitHub transport")
    snapshot = fetch_route(checked_at)
    route_proof = ExecutableCanaryRouteProofVerifier().verify(E40R1_ROUTE, E40R1_TASK_ID, snapshot, checked_at)
    if route_proof.status is not VerificationStatus.READ_ONLY_FETCH_VERIFIED:
        raise ValidationError(route_proof.reason_code)
    document = fetch_comment(E40R1_ISSUE, E40R1_COMMENT)
    approval = BoundCanaryApproval(
        E40R1_CANARY_ID,
        E40R1_TASK_ID,
        E40R1_ROUTE_EPOCH,
        E40R1_SCOPE,
        E40R1_EXPIRES_AT,
        E40R1_NONCE,
        canonical_approval_ref(document.repository, E40R1_ISSUE, E40R1_COMMENT),
        document.repository,
        E40R1_ISSUE,
        E40R1_COMMENT,
        document.actor,
        document.issued_at,
        document.body_sha256,
    )
    approval_proof = ReadOnlyApprovalVerifier().verify(approval, document, route_proof, checked_at)
    if approval_proof.status is not VerificationStatus.READ_ONLY_FETCH_VERIFIED:
        raise ValidationError(approval_proof.reason_code)
    activation = ActivationManifest(
        activation_id="brainops.e40r1.activation",
        route=E40R1_ROUTE,
        expected_epoch=E40R1_ROUTE_EPOCH,
        idempotency_key="brainops.e40r1.route_claim",
        canary_id=E40R1_CANARY_ID,
        task_id=E40R1_TASK_ID,
        scope=E40R1_SCOPE,
        approval_nonce=E40R1_NONCE,
        approval=approval,
    )
    payload_hash = canonical_hash(
        {
            "task_id": activation.task_id,
            "route_epoch": activation.expected_epoch,
            "canary_id": activation.canary_id,
            "nonce": activation.approval_nonce,
            "owner": selected_owner.value,
            "main_commit": route_proof.evidence.main_commit_sha1,
            "main_tree": route_proof.evidence.main_tree_sha1,
            "active_task_hash": route_proof.evidence.active_task.content_sha256,
            "coordination_hash": route_proof.evidence.coordination.content_sha256,
            "approval_body_hash": approval.body_sha256,
        }
    )
    event = CanaryEvent(
        event_id="brainops.e40r1.route_claim",
        source="GITHUB",
        route=E40R1_ROUTE,
        canary_id=E40R1_CANARY_ID,
        idempotency_key=activation.idempotency_key,
        payload_hash=payload_hash,
    )
    return OneShotExecutionRequest(activation, event, selected_owner, preflight), approval_proof, route_proof


class OneShotCanaryExecutor:
    """Reserve one owner, then terminally close the engineering route claim."""

    def execute(
        self,
        store: MetadataStore,
        request: OneShotExecutionRequest,
        approval_proof: ApprovalVerificationResult,
        route_proof: RouteProofVerification,
        attempted_at: str,
        *,
        terminal_state: OneShotResultCode = OneShotResultCode.SUCCEEDED,
        terminal_reason: str = "engineering_canary_claim_completed",
    ) -> OneShotExecutionResult:
        parse_rfc3339_utc(attempted_at, "E40R1 attempted_at")
        require_identifier(terminal_reason, "E40R1 terminal reason")
        block = self._preflight_block(request)
        if block is not None:
            return OneShotExecutionResult(
                OneShotResultCode.WOULD_BLOCK,
                request.event.event_id,
                request.selected_owner,
                request.non_attempted_owner,
                block,
                True,
            )
        if terminal_state not in {OneShotResultCode.SUCCEEDED, OneShotResultCode.FAILED}:
            raise ValidationError("E40R1 terminal state must be SUCCEEDED or FAILED")
        reserved = store.reserve_canary_event(
            request.event,
            request.activation,
            approval_proof,
            route_proof,
            attempted_at,
            selected_owner=request.selected_owner.value,
            non_attempted_owner=request.non_attempted_owner.value,
            one_shot_execution=True,
        )
        if not reserved:
            return OneShotExecutionResult(
                OneShotResultCode.DUPLICATE_SUPPRESSED,
                request.event.event_id,
                request.selected_owner,
                request.non_attempted_owner,
                "nonce_or_idempotency_already_consumed",
                True,
            )
        finalized = store.finalize_one_shot_execution(
            request.event.event_id,
            terminal_state.value,
            terminal_reason,
            attempted_at,
        )
        if not finalized:
            raise ValidationError("one_shot_terminal_transition_failed")
        return OneShotExecutionResult(
            terminal_state,
            request.event.event_id,
            request.selected_owner,
            request.non_attempted_owner,
            terminal_reason,
            True,
        )

    @staticmethod
    def _preflight_block(request: OneShotExecutionRequest) -> str | None:
        if request.selected_owner is OneShotOwner.CODEX_APP:
            if not request.preflight.app_available:
                return "app_preflight_unavailable"
            return None
        if request.selected_owner is OneShotOwner.CODEX_CLI:
            if request.preflight.app_available:
                return "cli_fallback_forbidden_after_app_available"
            if not request.preflight.cli_available:
                return "cli_preflight_unavailable"
            return None
        return "unsupported_execution_owner"
