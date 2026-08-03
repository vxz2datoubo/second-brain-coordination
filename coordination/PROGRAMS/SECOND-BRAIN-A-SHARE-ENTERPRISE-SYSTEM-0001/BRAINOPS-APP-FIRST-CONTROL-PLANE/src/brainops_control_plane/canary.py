"""E36 one-shot canary gate.  It has no dispatch implementation."""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    ActivationManifest,
    CanaryEvent,
    CapabilitySet,
    CapabilityStatus,
    ExecutionOwner,
    RouteState,
    RouteStateEvidence,
    ShadowDecision,
    ShadowOutcome,
    ValidationError,
    parse_rfc3339_utc,
)
from .store import MetadataStore


E36_CANARY_ID = "BRAINOPS-E36-CANARY-0001"


@dataclass(frozen=True)
class CanaryGateContext:
    activation: ActivationManifest
    route_state: RouteState
    observed_epoch: int
    capabilities: CapabilitySet
    remote_available: bool
    automatic_dispatch_allowed: bool
    cli_fallback_permitted: bool
    route_state_evidence: RouteStateEvidence
    checked_at: str

    def __post_init__(self) -> None:
        parse_rfc3339_utc(self.checked_at, "canary checked_at")
        if self.activation.route != self.route_state_evidence.route:
            raise ValidationError("activation and synchronized route-state evidence must bind the same route")


def select_canary_owner(capabilities: CapabilitySet, cli_fallback_permitted: bool) -> ExecutionOwner:
    """Manual App is intentionally never an automatic canary owner."""
    if capabilities.app_automation is CapabilityStatus.SUPPORTED:
        return ExecutionOwner.APP_AUTOMATION
    if capabilities.cli_fallback is CapabilityStatus.SUPPORTED and cli_fallback_permitted:
        return ExecutionOwner.CLI_FALLBACK
    return ExecutionOwner.NONE


class OneShotCanaryGate:
    """Evaluate and reserve a single public-safe canary without dispatching it."""

    def evaluate(
        self,
        store: MetadataStore,
        event: CanaryEvent,
        context: CanaryGateContext,
    ) -> ShadowDecision:
        activation = context.activation
        owner = select_canary_owner(context.capabilities, context.cli_fallback_permitted)
        evidence = {
            "canary_id": event.canary_id,
            "shadow_only": True,
            "automatic_dispatch_performed": False,
            "route_state_hashes_bound": True,
        }
        if event.canary_id != E36_CANARY_ID:
            return self._block("canary_id_not_allowlisted", owner, context, evidence)
        if event.route != activation.route:
            return self._block("event_route_mismatch", owner, context, evidence)
        if event.canary_id != activation.canary_id:
            return self._block("event_activation_canary_mismatch", owner, context, evidence)
        if event.idempotency_key != activation.idempotency_key:
            return self._block("event_idempotency_mismatch", owner, context, evidence)
        if not context.remote_available:
            return self._block("github_offline", owner, context, evidence)
        if context.route_state is not RouteState.READY:
            return self._block(f"route_{context.route_state.value.lower()}", owner, context, evidence)
        if context.observed_epoch != activation.expected_epoch:
            return self._block("stale_epoch", owner, context, evidence)
        if activation.approval is None:
            return self._block("bound_approval_missing", owner, context, evidence)
        approval_error = activation.approval.validates(activation, context.checked_at)
        if approval_error is not None:
            return self._block(approval_error, owner, context, evidence)
        if not context.automatic_dispatch_allowed:
            return self._block("automation_disabled", owner, context, evidence)
        if owner is ExecutionOwner.NONE:
            return self._block("no_supported_automatic_owner", owner, context, evidence)
        if not store.reserve_canary_event(event, context.route_state_evidence, context.checked_at):
            return ShadowDecision(
                outcome=ShadowOutcome.DUPLICATE_SUPPRESSED,
                reason_code="persistent_idempotency_duplicate",
                selected_owner=owner,
                route=activation.route,
                evidence=evidence,
            )
        evidence["idempotency_reservation"] = "persisted"
        evidence["external_effect"] = "none"
        return ShadowDecision(
            outcome=ShadowOutcome.CANARY_ELIGIBLE_SHADOW_ONLY,
            reason_code="all_bound_canary_gates_passed_no_executor_invoked",
            selected_owner=owner,
            route=activation.route,
            evidence=evidence,
        )

    @staticmethod
    def _block(
        reason_code: str,
        owner: ExecutionOwner,
        context: CanaryGateContext,
        evidence: dict[str, object],
    ) -> ShadowDecision:
        return ShadowDecision(
            outcome=ShadowOutcome.WOULD_BLOCK,
            reason_code=reason_code,
            selected_owner=owner,
            route=context.activation.route,
            evidence=evidence,
        )
