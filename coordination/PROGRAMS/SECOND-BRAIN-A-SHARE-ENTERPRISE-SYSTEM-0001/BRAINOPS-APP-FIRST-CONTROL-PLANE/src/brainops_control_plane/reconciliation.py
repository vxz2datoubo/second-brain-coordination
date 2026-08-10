"""Fail-closed, counterfactual route reconciliation.  There is no executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import (
    ActivationManifest,
    CapabilitySet,
    CapabilityStatus,
    ExecutionOwner,
    is_sha256_hex,
    RouteState,
    ShadowDecision,
    ShadowOutcome,
)


@dataclass(frozen=True)
class ReconciliationContext:
    activation: ActivationManifest
    observed_epoch: int
    route_state: RouteState
    capabilities: CapabilitySet
    remote_available: bool
    automatic_dispatch_allowed: bool
    approval_checked_at: str = "2026-08-02T00:00:00Z"
    active_lease: bool = False
    existing_owner: ExecutionOwner = ExecutionOwner.NONE


@dataclass(frozen=True)
class AntiEntropySchedule:
    interval_minutes: int = 30
    shadow_only: bool = True

    def __post_init__(self) -> None:
        if self.interval_minutes != 30 or not self.shadow_only:
            raise ValueError("E35 supports only the 30-minute shadow anti-entropy fixture")


@dataclass(frozen=True)
class ReviewRequestEvent:
    """A redacted GitHub event envelope supplied to the watcher by another reader."""

    event_id: str
    source: str
    route_id: str
    route_epoch: int
    state: RouteState
    payload_hash: str


@dataclass(frozen=True)
class WatchObservation:
    accepted: bool
    reason_code: str
    event_id: str


class ShadowReviewWatcher:
    """Accepts supplied GitHub event metadata; it never calls GitHub or dispatches work."""

    def observe(self, event: ReviewRequestEvent) -> WatchObservation:
        if event.source != "GITHUB":
            return WatchObservation(False, "unsupported_event_source", event.event_id)
        if event.route_epoch < 0:
            return WatchObservation(False, "invalid_event_epoch", event.event_id)
        if not event.payload_hash:
            return WatchObservation(False, "missing_event_payload_hash", event.event_id)
        if not is_sha256_hex(event.payload_hash):
            return WatchObservation(False, "invalid_event_payload_hash", event.event_id)
        return WatchObservation(True, "shadow_event_recorded", event.event_id)


def select_owner(capabilities: CapabilitySet) -> ExecutionOwner:
    if capabilities.app_automation is CapabilityStatus.SUPPORTED:
        return ExecutionOwner.APP_AUTOMATION
    if capabilities.cli_fallback is CapabilityStatus.SUPPORTED:
        return ExecutionOwner.CLI_FALLBACK
    if capabilities.manual_app is CapabilityStatus.SUPPORTED:
        return ExecutionOwner.MANUAL_APP
    return ExecutionOwner.NONE


def select_automatic_owner(capabilities: CapabilitySet) -> ExecutionOwner:
    """Select only a supported non-manual owner for an automatic route."""
    if capabilities.app_automation is CapabilityStatus.SUPPORTED:
        return ExecutionOwner.APP_AUTOMATION
    if capabilities.cli_fallback is CapabilityStatus.SUPPORTED:
        return ExecutionOwner.CLI_FALLBACK
    return ExecutionOwner.NONE


class ShadowReconciler:
    """Evaluates routes, records a reason, and explicitly never performs an action."""

    def reconcile(self, context: ReconciliationContext) -> ShadowDecision:
        route = context.activation.route
        owner = select_owner(context.capabilities)
        evidence: dict[str, Any] = {
            "shadow_only": True,
            "route_state": context.route_state.value,
            "observed_epoch": context.observed_epoch,
            "expected_epoch": context.activation.expected_epoch,
            "automatic_dispatch_allowed": context.automatic_dispatch_allowed,
        }
        if route.target_agent.upper() == "QQ":
            return self._block("qq_route_excluded", owner, context, evidence)
        if not context.remote_available:
            return self._block("github_offline", owner, context, evidence)
        if context.route_state is not RouteState.READY:
            return self._block(f"route_{context.route_state.value.lower()}", owner, context, evidence)
        if context.observed_epoch != context.activation.expected_epoch:
            return self._block("stale_epoch", owner, context, evidence)
        if context.active_lease:
            return self._block("active_lease", owner, context, evidence)
        if context.existing_owner is not ExecutionOwner.NONE and context.existing_owner is not owner:
            return self._block("ownership_fenced", owner, context, evidence)
        if context.activation.approval is None:
            return self._block("bound_approval_missing", owner, context, evidence)
        approval_error = context.activation.approval.validates(context.activation, context.approval_checked_at)
        if approval_error is not None:
            return self._block(approval_error, owner, context, evidence)
        if not context.automatic_dispatch_allowed:
            return self._block("automation_disabled", owner, context, evidence)
        if owner is ExecutionOwner.NONE:
            return self._block("no_supported_owner", owner, context, evidence)
        if owner is ExecutionOwner.MANUAL_APP:
            return ShadowDecision(
                outcome=ShadowOutcome.WOULD_REQUIRE_MANUAL,
                reason_code="manual_app_requires_operator",
                selected_owner=owner,
                route=route,
                evidence=evidence,
            )
        evidence["counterfactual_only"] = True
        return ShadowDecision(
            outcome=ShadowOutcome.WOULD_DISPATCH,
            reason_code="all_shadow_gates_passed",
            selected_owner=owner,
            route=route,
            evidence=evidence,
        )

    @staticmethod
    def _block(
        reason_code: str,
        owner: ExecutionOwner,
        context: ReconciliationContext,
        evidence: dict[str, Any],
    ) -> ShadowDecision:
        return ShadowDecision(
            outcome=ShadowOutcome.WOULD_BLOCK,
            reason_code=reason_code,
            selected_owner=owner,
            route=context.activation.route,
            evidence=evidence,
        )
