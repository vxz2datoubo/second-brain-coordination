"""Verified canonical route terminalization for E42."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .durable_authority import DurableClaimRecord, DurableClaimState
from .models import RouteState, ValidationError, parse_rfc3339_utc, require_identifier
from .proofs import FetchedRouteSnapshot, _parse_route_yaml


_VERIFIER_SEAL = object()
_TERMINAL_SEAL = object()
_RESULT_SEAL = object()


class RouteExecutionDisposition(str, Enum):
    READY_REQUIRES_DURABLE_CLAIM = "READY_REQUIRES_DURABLE_CLAIM"
    BLOCKED_BY_DURABLE_CLAIM = "BLOCKED_BY_DURABLE_CLAIM"
    BLOCKED_BY_DURABLE_TERMINAL = "BLOCKED_BY_DURABLE_TERMINAL"
    DURABLE_TERMINAL_ROUTE_PUBLICATION_PENDING = "DURABLE_TERMINAL_ROUTE_PUBLICATION_PENDING"
    ROUTE_TERMINALIZED = "ROUTE_TERMINALIZED"
    ROUTE_STATE_BLOCKED = "ROUTE_STATE_BLOCKED"


class CanonicalTerminalState(str, Enum):
    CONSUMED = "CONSUMED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class TerminalizationVerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class RawCanonicalRouteTerminalization:
    route_state: RouteState
    claim_id: str
    terminal_state: CanonicalTerminalState
    terminalized_at: str


@dataclass(frozen=True, init=False)
class VerifiedCanonicalRouteTerminalization:
    repository: str
    ref: str
    commit_sha1: str
    tree_sha1: str
    path: str
    blob_sha1: str
    content_sha256: str
    route_state: RouteState
    route_id: str
    route_epoch: int
    task_id: str
    canary_id: str
    nonce: str
    claim_id: str
    terminal_state: CanonicalTerminalState
    durable_terminal_at: str
    published_at: str

    def __init__(self, values: dict[str, object], *, _seal: object | None = None) -> None:
        if _seal is not _TERMINAL_SEAL:
            raise ValidationError("verified canonical terminalization must come from the route verifier")
        for key, value in values.items():
            object.__setattr__(self, key, value)


CanonicalRouteTerminalization = RawCanonicalRouteTerminalization


@dataclass(frozen=True, init=False)
class TerminalizationVerificationResult:
    status: TerminalizationVerificationStatus
    terminalization: VerifiedCanonicalRouteTerminalization | None
    reason_code: str
    checked_at: str

    def __init__(
        self,
        status: TerminalizationVerificationStatus,
        terminalization: VerifiedCanonicalRouteTerminalization | None,
        reason_code: str,
        checked_at: str,
        *,
        _seal: object | None = None,
    ) -> None:
        if _seal is not _RESULT_SEAL:
            raise ValidationError("terminalization result is verifier-internal")
        require_identifier(reason_code, "terminalization reason_code")
        parse_rfc3339_utc(checked_at, "terminalization checked_at")
        if (status is TerminalizationVerificationStatus.VERIFIED) != (terminalization is not None):
            raise ValidationError("terminalization verification payload mismatch")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "terminalization", terminalization)
        object.__setattr__(self, "reason_code", reason_code)
        object.__setattr__(self, "checked_at", checked_at)


class CanonicalRouteTerminalizationVerifier:
    """Verify a terminal route only from a sealed bounded-route snapshot."""

    def __init__(self, repository: str, ref: str, path: str, *, _seal: object | None = None) -> None:
        if _seal is not _VERIFIER_SEAL:
            raise ValidationError("canonical terminalization verifier is composition-root only")
        self._repository = repository
        self._ref = ref
        self._path = path

    @staticmethod
    def _result(status: TerminalizationVerificationStatus, checked_at: str, reason: str, terminal=None) -> TerminalizationVerificationResult:
        return TerminalizationVerificationResult(status, terminal, reason, checked_at, _seal=_RESULT_SEAL)

    def verify(self, snapshot: object, durable: DurableClaimRecord, checked_at: str) -> TerminalizationVerificationResult:
        checked = parse_rfc3339_utc(checked_at, "terminalization checked_at")
        if not durable.state.terminal or durable.terminal_at is None:
            return self._result(TerminalizationVerificationStatus.REJECTED, checked_at, "durable_terminal_missing")
        if not isinstance(snapshot, FetchedRouteSnapshot):
            return self._result(TerminalizationVerificationStatus.REJECTED, checked_at, "route_snapshot_not_transport_bound")
        if snapshot.repository != self._repository or snapshot.ref != self._ref or snapshot.active_task.path != self._path:
            return self._result(TerminalizationVerificationStatus.REJECTED, checked_at, "canonical_route_identity_mismatch")
        observed = parse_rfc3339_utc(snapshot.observed_at, "canonical route observed_at")
        if observed > checked:
            return self._result(TerminalizationVerificationStatus.REJECTED, checked_at, "canonical_route_observation_in_future")
        try:
            payload = _parse_route_yaml(snapshot.active_task_content, "canonical terminal route")
        except ValidationError:
            return self._result(TerminalizationVerificationStatus.REJECTED, checked_at, "canonical_route_parse_rejected")
        required = {
            "route_id",
            "route_epoch",
            "task_id",
            "canary_id",
            "nonce",
            "status",
            "durable_claim_id",
            "durable_terminal_state",
            "durable_terminal_at",
            "published_at",
        }
        if not required.issubset(payload):
            return self._result(TerminalizationVerificationStatus.PENDING, checked_at, "durable_terminal_route_publication_pending")
        expected_terminal = {
            DurableClaimState.SUCCEEDED: CanonicalTerminalState.CONSUMED,
            DurableClaimState.FAILED: CanonicalTerminalState.FAILED,
            DurableClaimState.TIMED_OUT: CanonicalTerminalState.TIMED_OUT,
            DurableClaimState.RECOVERY_REQUIRED: CanonicalTerminalState.RECOVERY_REQUIRED,
        }[durable.state]
        try:
            route_state = RouteState(str(payload["status"]))
            terminal_state = CanonicalTerminalState(str(payload["durable_terminal_state"]))
            published = parse_rfc3339_utc(str(payload["published_at"]), "canonical published_at")
            terminal_at = parse_rfc3339_utc(str(payload["durable_terminal_at"]), "canonical durable_terminal_at")
        except (ValueError, ValidationError):
            return self._result(TerminalizationVerificationStatus.REJECTED, checked_at, "canonical_terminal_fields_invalid")
        binding = durable.provenance
        if route_state not in {RouteState.BLOCKED, RouteState.DISABLED}:
            return self._result(TerminalizationVerificationStatus.REJECTED, checked_at, "canonical_route_not_terminal")
        if (
            payload["route_id"] != binding.route_id
            or payload["route_epoch"] != binding.route_epoch
            or payload["task_id"] != binding.task_id
            or payload["canary_id"] != binding.canary_id
            or payload["nonce"] != binding.nonce
            or payload["durable_claim_id"] != durable.claim_id
            or terminal_state is not expected_terminal
            or str(payload["durable_terminal_at"]) != durable.terminal_at
        ):
            return self._result(TerminalizationVerificationStatus.REJECTED, checked_at, "canonical_terminal_binding_mismatch")
        if published < terminal_at or published > observed or observed > checked:
            return self._result(TerminalizationVerificationStatus.REJECTED, checked_at, "canonical_publication_time_invalid")
        terminal = VerifiedCanonicalRouteTerminalization(
            {
                "repository": snapshot.repository,
                "ref": snapshot.ref,
                "commit_sha1": snapshot.main_commit_sha1,
                "tree_sha1": snapshot.main_tree_sha1,
                "path": snapshot.active_task.path,
                "blob_sha1": snapshot.active_task.blob_sha1,
                "content_sha256": snapshot.active_task.content_sha256,
                "route_state": route_state,
                "route_id": binding.route_id,
                "route_epoch": binding.route_epoch,
                "task_id": binding.task_id,
                "canary_id": binding.canary_id,
                "nonce": binding.nonce,
                "claim_id": durable.claim_id,
                "terminal_state": terminal_state,
                "durable_terminal_at": durable.terminal_at,
                "published_at": str(payload["published_at"]),
            },
            _seal=_TERMINAL_SEAL,
        )
        return self._result(TerminalizationVerificationStatus.VERIFIED, checked_at, "canonical_terminal_route_verified", terminal)


def _canonical_terminalization_verifier(repository: str, ref: str, path: str) -> CanonicalRouteTerminalizationVerifier:
    return CanonicalRouteTerminalizationVerifier(repository, ref, path, _seal=_VERIFIER_SEAL)


@dataclass(frozen=True)
class RouteTerminalDecision:
    route_state: RouteState
    durable_state: DurableClaimState | None
    disposition: RouteExecutionDisposition
    execution_permitted: bool
    canonical_terminalization_verified: bool


def evaluate_route_terminalization(
    route_state: RouteState,
    durable: DurableClaimRecord | None,
    verification: object | None = None,
) -> RouteTerminalDecision:
    if durable is not None:
        if durable.state is DurableClaimState.CLAIMED:
            return RouteTerminalDecision(route_state, durable.state, RouteExecutionDisposition.BLOCKED_BY_DURABLE_CLAIM, False, False)
        if route_state is RouteState.READY:
            return RouteTerminalDecision(route_state, durable.state, RouteExecutionDisposition.BLOCKED_BY_DURABLE_TERMINAL, False, False)
        if isinstance(verification, TerminalizationVerificationResult):
            if verification.status is TerminalizationVerificationStatus.VERIFIED and verification.terminalization is not None:
                return RouteTerminalDecision(route_state, durable.state, RouteExecutionDisposition.ROUTE_TERMINALIZED, False, True)
            if verification.status is TerminalizationVerificationStatus.PENDING:
                return RouteTerminalDecision(route_state, durable.state, RouteExecutionDisposition.DURABLE_TERMINAL_ROUTE_PUBLICATION_PENDING, False, False)
        return RouteTerminalDecision(route_state, durable.state, RouteExecutionDisposition.BLOCKED_BY_DURABLE_TERMINAL, False, False)
    if route_state is RouteState.READY:
        return RouteTerminalDecision(route_state, None, RouteExecutionDisposition.READY_REQUIRES_DURABLE_CLAIM, False, False)
    return RouteTerminalDecision(route_state, None, RouteExecutionDisposition.ROUTE_STATE_BLOCKED, False, False)
