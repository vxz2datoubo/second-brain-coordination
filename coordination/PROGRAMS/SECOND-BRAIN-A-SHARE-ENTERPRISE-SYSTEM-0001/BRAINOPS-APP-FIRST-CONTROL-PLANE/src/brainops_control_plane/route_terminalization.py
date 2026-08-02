"""Fail-closed interpretation of durable authority versus route content."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .durable_authority import DurableClaimRecord, DurableClaimState
from .models import RouteState, ValidationError, parse_rfc3339_utc, require_identifier


class RouteExecutionDisposition(str, Enum):
    READY_REQUIRES_DURABLE_CLAIM = "READY_REQUIRES_DURABLE_CLAIM"
    BLOCKED_BY_DURABLE_CLAIM = "BLOCKED_BY_DURABLE_CLAIM"
    BLOCKED_BY_DURABLE_TERMINAL = "BLOCKED_BY_DURABLE_TERMINAL"
    ROUTE_TERMINALIZED = "ROUTE_TERMINALIZED"
    ROUTE_STATE_BLOCKED = "ROUTE_STATE_BLOCKED"


class CanonicalTerminalState(str, Enum):
    """Published route outcome, intentionally narrower than a claim label."""

    CONSUMED = "CONSUMED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True)
class CanonicalRouteTerminalization:
    """Route-publisher evidence that names the exact durable outcome.

    A generic ``BLOCKED`` route does not prove terminalization.  It must bind
    the durable claim ID, the final state, and the publication time.  The
    route publisher owns construction from a verified canonical route; E41
    only verifies the structural correspondence and never writes that route.
    """

    route_state: RouteState
    claim_id: str
    terminal_state: CanonicalTerminalState
    terminalized_at: str

    def __post_init__(self) -> None:
        if self.route_state not in {RouteState.BLOCKED, RouteState.DISABLED}:
            raise ValidationError("canonical terminal route must be blocked or disabled")
        require_identifier(self.claim_id, "canonical terminal claim_id")
        parse_rfc3339_utc(self.terminalized_at, "canonical terminalized_at")

    def matches(self, route_state: RouteState, durable: DurableClaimRecord) -> bool:
        expected = {
            DurableClaimState.SUCCEEDED: CanonicalTerminalState.CONSUMED,
            DurableClaimState.FAILED: CanonicalTerminalState.FAILED,
            DurableClaimState.TIMED_OUT: CanonicalTerminalState.TIMED_OUT,
            DurableClaimState.RECOVERY_REQUIRED: CanonicalTerminalState.RECOVERY_REQUIRED,
        }
        return (
            durable.state.terminal
            and self.route_state is route_state
            and self.claim_id == durable.claim_id
            and self.terminal_state is expected[durable.state]
        )


@dataclass(frozen=True)
class RouteTerminalDecision:
    route_state: RouteState
    durable_state: DurableClaimState | None
    disposition: RouteExecutionDisposition
    execution_permitted: bool
    canonical_terminalization_verified: bool

    def __post_init__(self) -> None:
        if self.execution_permitted and self.durable_state is not None:
            raise ValidationError("durable authority can never permit replay")
        if self.canonical_terminalization_verified and self.route_state is RouteState.READY:
            raise ValidationError("ready route cannot be terminalization verified")


def evaluate_route_terminalization(
    route_state: RouteState,
    durable: DurableClaimRecord | None,
    canonical_terminal: CanonicalRouteTerminalization | None = None,
) -> RouteTerminalDecision:
    """Treat durable consumption as stronger than a stale route document."""

    if durable is not None:
        if durable.state is DurableClaimState.CLAIMED:
            return RouteTerminalDecision(
                route_state,
                durable.state,
                RouteExecutionDisposition.BLOCKED_BY_DURABLE_CLAIM,
                False,
                False,
            )
        if route_state is RouteState.READY:
            return RouteTerminalDecision(
                route_state,
                durable.state,
                RouteExecutionDisposition.BLOCKED_BY_DURABLE_TERMINAL,
                False,
                False,
            )
        if canonical_terminal is not None and canonical_terminal.matches(route_state, durable):
            return RouteTerminalDecision(
                route_state,
                durable.state,
                RouteExecutionDisposition.ROUTE_TERMINALIZED,
                False,
                True,
            )
        return RouteTerminalDecision(
            route_state,
            durable.state,
            RouteExecutionDisposition.BLOCKED_BY_DURABLE_TERMINAL,
            False,
            False,
        )
    if route_state is RouteState.READY:
        return RouteTerminalDecision(
            route_state,
            None,
            RouteExecutionDisposition.READY_REQUIRES_DURABLE_CLAIM,
            False,
            False,
        )
    return RouteTerminalDecision(
        route_state,
        None,
        RouteExecutionDisposition.ROUTE_STATE_BLOCKED,
        False,
        False,
    )
