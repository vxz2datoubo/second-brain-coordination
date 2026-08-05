"""E43 lifecycle, freshness, and bounded-transport execution attestation.

This module deliberately does not claim a live runtime trust root.  It turns a
synthetic or future external transport into a narrow, verifier-minted envelope
and requires a matching durable terminal record before a positive execution
classification can be returned.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum

from .durable_authority import ClaimHolder, DurableClaimRecord, DurableClaimState
from .execution_evidence import CapabilityTarget, ExecutionEvidenceType
from .models import CapabilityStatus, ValidationError, parse_rfc3339_utc, require_identifier, require_sha256


_CHALLENGE_SEAL = object()
_ENVELOPE_SEAL = object()
_RECONCILIATION_SEAL = object()


class InvocationLifecycleState(str, Enum):
    INVOCATION_STARTED = "INVOCATION_STARTED"
    INVOCATION_TERMINAL_OBSERVED = "INVOCATION_TERMINAL_OBSERVED"
    DURABLE_TERMINAL_RECONCILED = "DURABLE_TERMINAL_RECONCILED"


class AttestationCode(str, Enum):
    STARTED = "STARTED"
    TERMINAL_OBSERVED = "TERMINAL_OBSERVED"
    DURABLE_TERMINAL_RECONCILED = "DURABLE_TERMINAL_RECONCILED"
    EXECUTION_IN_PROGRESS_OR_UNRECONCILED = "EXECUTION_IN_PROGRESS_OR_UNRECONCILED"
    DURABLE_RECONCILIATION_MISSING = "DURABLE_RECONCILIATION_MISSING"
    CHALLENGE_EXPIRED = "CHALLENGE_EXPIRED"
    CHALLENGE_REPLAYED = "CHALLENGE_REPLAYED"
    CHALLENGE_BINDING_MISMATCH = "CHALLENGE_BINDING_MISMATCH"
    OBSERVATION_STALE = "OBSERVATION_STALE"
    OBSERVATION_IN_FUTURE = "OBSERVATION_IN_FUTURE"
    TRANSPORT_UNATTESTED = "TRANSPORT_UNATTESTED"
    TRANSPORT_MISMATCH = "TRANSPORT_MISMATCH"
    OWNER_MISMATCH = "OWNER_MISMATCH"
    INVOCATION_MISMATCH = "INVOCATION_MISMATCH"
    TERMINAL_MISMATCH = "TERMINAL_MISMATCH"
    TIME_ORDER_INVALID = "TIME_ORDER_INVALID"
    DURABLE_STATE_INVALID = "DURABLE_STATE_INVALID"


class AttestationError(ValidationError):
    def __init__(self, code: AttestationCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, init=False)
class OneShotChallenge:
    challenge_id: str
    target: CapabilityTarget
    owner: ClaimHolder
    task_id: str
    route_epoch: int
    canary_id: str
    nonce: str
    issued_at: str
    expires_at: str
    max_observation_age_seconds: int

    def __init__(
        self,
        challenge_id: str,
        target: CapabilityTarget,
        owner: ClaimHolder,
        task_id: str,
        route_epoch: int,
        canary_id: str,
        nonce: str,
        issued_at: str,
        expires_at: str,
        max_observation_age_seconds: int,
        *,
        _seal: object | None = None,
    ) -> None:
        if _seal is not _CHALLENGE_SEAL:
            raise ValidationError("one-shot challenge must be minted by a bounded issuer")
        for value, label in (
            (challenge_id, "challenge_id"),
            (task_id, "challenge task_id"),
            (canary_id, "challenge canary_id"),
            (nonce, "challenge nonce"),
        ):
            require_identifier(value, label)
        if not isinstance(owner, ClaimHolder) or not isinstance(route_epoch, int) or route_epoch < 1:
            raise ValidationError("challenge owner or route_epoch invalid")
        issued = parse_rfc3339_utc(issued_at, "challenge issued_at")
        if parse_rfc3339_utc(expires_at, "challenge expires_at") <= issued:
            raise ValidationError("challenge expiry must follow issue time")
        if not isinstance(max_observation_age_seconds, int) or max_observation_age_seconds < 1:
            raise ValidationError("challenge maximum age must be positive")
        object.__setattr__(self, "challenge_id", challenge_id)
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "owner", owner)
        object.__setattr__(self, "task_id", task_id)
        object.__setattr__(self, "route_epoch", route_epoch)
        object.__setattr__(self, "canary_id", canary_id)
        object.__setattr__(self, "nonce", nonce)
        object.__setattr__(self, "issued_at", issued_at)
        object.__setattr__(self, "expires_at", expires_at)
        object.__setattr__(self, "max_observation_age_seconds", max_observation_age_seconds)


@dataclass(frozen=True)
class RawCapabilityTransportObservation:
    challenge_id: str
    target: CapabilityTarget
    owner: ClaimHolder
    task_id: str
    route_epoch: int
    canary_id: str
    nonce: str
    observed_at: str
    status: CapabilityStatus
    evidence_hash: str
    transport_identity: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.challenge_id, "capability challenge_id"),
            (self.task_id, "capability task_id"),
            (self.canary_id, "capability canary_id"),
            (self.nonce, "capability nonce"),
            (self.transport_identity, "capability transport_identity"),
        ):
            require_identifier(value, label)
        if not isinstance(self.owner, ClaimHolder) or not isinstance(self.route_epoch, int) or self.route_epoch < 1:
            raise ValidationError("capability owner or route_epoch invalid")
        parse_rfc3339_utc(self.observed_at, "capability observed_at")
        require_sha256(self.evidence_hash, "capability evidence_hash")


@dataclass(frozen=True)
class RawInvocationTransportObservation:
    challenge_id: str
    target: CapabilityTarget
    claim_id: str
    invocation_id: str
    owner: ClaimHolder
    evidence_type: ExecutionEvidenceType
    task_id: str
    route_epoch: int
    canary_id: str
    nonce: str
    started_at: str
    terminal_at: str
    terminal_status: str
    exit_code: int | None
    log_hash: str
    transport_identity: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.challenge_id, "invocation challenge_id"),
            (self.claim_id, "invocation claim_id"),
            (self.invocation_id, "invocation_id"),
            (self.task_id, "invocation task_id"),
            (self.canary_id, "invocation canary_id"),
            (self.nonce, "invocation nonce"),
            (self.terminal_status, "invocation terminal_status"),
            (self.transport_identity, "invocation transport_identity"),
        ):
            require_identifier(value, label)
        if not isinstance(self.owner, ClaimHolder) or not isinstance(self.route_epoch, int) or self.route_epoch < 1:
            raise ValidationError("invocation owner or route_epoch invalid")
        if self.evidence_type is ExecutionEvidenceType.CONTROL_PLANE_CLAIM_ONLY:
            raise ValidationError("claim-only cannot be an execution observation")
        if parse_rfc3339_utc(self.terminal_at, "invocation terminal_at") < parse_rfc3339_utc(self.started_at, "invocation started_at"):
            raise ValidationError("invocation terminal precedes start")
        require_sha256(self.log_hash, "invocation log_hash")


@dataclass(frozen=True, init=False)
class BoundedTransportEnvelope:
    """Verifier-minted observation binding, not a caller-owned identity string."""

    challenge: OneShotChallenge
    raw: RawCapabilityTransportObservation | RawInvocationTransportObservation
    attested_at: str
    transport_identity: str

    def __init__(
        self,
        challenge: OneShotChallenge,
        raw: RawCapabilityTransportObservation | RawInvocationTransportObservation,
        attested_at: str,
        transport_identity: str,
        *,
        _seal: object | None = None,
    ) -> None:
        if _seal is not _ENVELOPE_SEAL:
            raise ValidationError("transport envelope must come from a bounded attestor")
        parse_rfc3339_utc(attested_at, "transport attested_at")
        require_identifier(transport_identity, "attested transport_identity")
        object.__setattr__(self, "challenge", challenge)
        object.__setattr__(self, "raw", raw)
        object.__setattr__(self, "attested_at", attested_at)
        object.__setattr__(self, "transport_identity", transport_identity)


class BoundedTransportAttestor:
    """One composition-root transport identity with one-use challenge consumption."""

    def __init__(self, transport_identity: str, *, _seal: object | None = None) -> None:
        if _seal is not _ENVELOPE_SEAL:
            raise ValidationError("bounded transport attestor is composition-root only")
        require_identifier(transport_identity, "bounded transport_identity")
        self._transport_identity = transport_identity
        self._consumed_challenges: set[str] = set()

    @staticmethod
    def _raw_observed_at(raw: RawCapabilityTransportObservation | RawInvocationTransportObservation) -> str:
        return raw.observed_at if isinstance(raw, RawCapabilityTransportObservation) else raw.terminal_at

    @staticmethod
    def _challenge_matches(
        challenge: OneShotChallenge,
        raw: RawCapabilityTransportObservation | RawInvocationTransportObservation,
    ) -> bool:
        return (
            raw.challenge_id == challenge.challenge_id
            and raw.target is challenge.target
            and raw.owner == challenge.owner
            and raw.task_id == challenge.task_id
            and raw.route_epoch == challenge.route_epoch
            and raw.canary_id == challenge.canary_id
            and raw.nonce == challenge.nonce
        )

    def attest(
        self,
        challenge: OneShotChallenge,
        raw: RawCapabilityTransportObservation | RawInvocationTransportObservation,
        checked_at: str,
    ) -> BoundedTransportEnvelope:
        if not isinstance(challenge, OneShotChallenge):
            raise AttestationError(AttestationCode.CHALLENGE_BINDING_MISMATCH, "trusted challenge required")
        if raw.transport_identity != self._transport_identity:
            raise AttestationError(AttestationCode.TRANSPORT_MISMATCH, "raw transport identity does not match bounded transport")
        if not self._challenge_matches(challenge, raw):
            raise AttestationError(AttestationCode.CHALLENGE_BINDING_MISMATCH, "challenge binding mismatch")
        if raw.challenge_id in self._consumed_challenges:
            raise AttestationError(AttestationCode.CHALLENGE_REPLAYED, "one-shot challenge was already consumed")
        checked = parse_rfc3339_utc(checked_at, "transport checked_at")
        observed = parse_rfc3339_utc(self._raw_observed_at(raw), "transport observation time")
        issued = parse_rfc3339_utc(challenge.issued_at, "challenge issued_at")
        expires = parse_rfc3339_utc(challenge.expires_at, "challenge expires_at")
        if observed > checked:
            raise AttestationError(AttestationCode.OBSERVATION_IN_FUTURE, "transport observation is in the future")
        if checked >= expires:
            raise AttestationError(AttestationCode.CHALLENGE_EXPIRED, "challenge expired before attestation")
        if observed < issued or observed >= expires:
            raise AttestationError(AttestationCode.CHALLENGE_BINDING_MISMATCH, "observation is outside challenge window")
        if checked - observed > timedelta(seconds=challenge.max_observation_age_seconds):
            raise AttestationError(AttestationCode.OBSERVATION_STALE, "observation exceeds maximum age")
        self._consumed_challenges.add(raw.challenge_id)
        return BoundedTransportEnvelope(challenge, raw, checked_at, self._transport_identity, _seal=_ENVELOPE_SEAL)


def _bounded_transport_attestor(transport_identity: str) -> BoundedTransportAttestor:
    return BoundedTransportAttestor(transport_identity, _seal=_ENVELOPE_SEAL)


def _one_shot_challenge(
    challenge_id: str,
    target: CapabilityTarget,
    owner: ClaimHolder,
    task_id: str,
    route_epoch: int,
    canary_id: str,
    nonce: str,
    issued_at: str,
    expires_at: str,
    max_observation_age_seconds: int,
) -> OneShotChallenge:
    return OneShotChallenge(
        challenge_id,
        target,
        owner,
        task_id,
        route_epoch,
        canary_id,
        nonce,
        issued_at,
        expires_at,
        max_observation_age_seconds,
        _seal=_CHALLENGE_SEAL,
    )


@dataclass(frozen=True)
class InvocationStarted:
    claim_id: str
    invocation_id: str
    holder: ClaimHolder
    challenge: OneShotChallenge
    started_at: str
    state: InvocationLifecycleState = InvocationLifecycleState.INVOCATION_STARTED


@dataclass(frozen=True)
class InvocationTerminalObserved:
    started: InvocationStarted
    envelope: BoundedTransportEnvelope
    state: InvocationLifecycleState = InvocationLifecycleState.INVOCATION_TERMINAL_OBSERVED

    @property
    def raw(self) -> RawInvocationTransportObservation:
        if not isinstance(self.envelope.raw, RawInvocationTransportObservation):
            raise AttestationError(AttestationCode.TRANSPORT_UNATTESTED, "terminal observation envelope type invalid")
        return self.envelope.raw


@dataclass(frozen=True, init=False)
class DurableTerminalReconciliation:
    observed: InvocationTerminalObserved
    durable_claim: DurableClaimRecord
    reconciled_at: str
    state: InvocationLifecycleState

    def __init__(
        self,
        observed: InvocationTerminalObserved,
        durable_claim: DurableClaimRecord,
        reconciled_at: str,
        *,
        _seal: object | None = None,
    ) -> None:
        if _seal is not _RECONCILIATION_SEAL:
            raise ValidationError("durable terminal reconciliation must come from the reconciliation verifier")
        parse_rfc3339_utc(reconciled_at, "durable reconciled_at")
        object.__setattr__(self, "observed", observed)
        object.__setattr__(self, "durable_claim", durable_claim)
        object.__setattr__(self, "reconciled_at", reconciled_at)
        object.__setattr__(self, "state", InvocationLifecycleState.DURABLE_TERMINAL_RECONCILED)


@dataclass(frozen=True)
class TerminalExecutionClassification:
    code: AttestationCode
    lifecycle_state: InvocationLifecycleState | None
    evidence_type: ExecutionEvidenceType | None


class TerminalExecutionReconciler:
    @staticmethod
    def begin(claim: DurableClaimRecord, challenge: OneShotChallenge, invocation_id: str, started_at: str) -> InvocationStarted:
        if claim.state is not DurableClaimState.CLAIMED:
            raise AttestationError(AttestationCode.DURABLE_STATE_INVALID, "only a claimed durable record may start invocation")
        if claim.holder != challenge.owner:
            raise AttestationError(AttestationCode.OWNER_MISMATCH, "challenge owner does not match durable holder")
        if claim.provenance.task_id != challenge.task_id or claim.provenance.route_epoch != challenge.route_epoch:
            raise AttestationError(AttestationCode.CHALLENGE_BINDING_MISMATCH, "challenge task or epoch mismatches durable claim")
        if claim.provenance.canary_id != challenge.canary_id or claim.provenance.nonce != challenge.nonce:
            raise AttestationError(AttestationCode.CHALLENGE_BINDING_MISMATCH, "challenge canary or nonce mismatches durable claim")
        if claim.invocation_id != invocation_id:
            raise AttestationError(AttestationCode.INVOCATION_MISMATCH, "invocation is not durably attached")
        started = parse_rfc3339_utc(started_at, "invocation started_at")
        if started < parse_rfc3339_utc(claim.claimed_at, "durable claimed_at"):
            raise AttestationError(AttestationCode.TIME_ORDER_INVALID, "invocation starts before durable claim")
        if started < parse_rfc3339_utc(challenge.issued_at, "challenge issued_at") or started >= parse_rfc3339_utc(challenge.expires_at, "challenge expires_at"):
            raise AttestationError(AttestationCode.CHALLENGE_EXPIRED, "invocation start is outside challenge lifetime")
        return InvocationStarted(claim.claim_id, invocation_id, claim.holder, challenge, started_at)

    @staticmethod
    def observe_terminal(started: InvocationStarted, envelope: object) -> InvocationTerminalObserved:
        if not isinstance(envelope, BoundedTransportEnvelope) or not isinstance(envelope.raw, RawInvocationTransportObservation):
            raise AttestationError(AttestationCode.TRANSPORT_UNATTESTED, "bounded invocation envelope required")
        raw = envelope.raw
        if raw.claim_id != started.claim_id or raw.invocation_id != started.invocation_id:
            raise AttestationError(AttestationCode.INVOCATION_MISMATCH, "terminal observation claim or invocation mismatch")
        if raw.owner != started.holder or envelope.challenge != started.challenge:
            raise AttestationError(AttestationCode.OWNER_MISMATCH, "terminal observation owner or challenge mismatch")
        if raw.started_at != started.started_at:
            raise AttestationError(AttestationCode.TIME_ORDER_INVALID, "terminal observation start time mismatch")
        if parse_rfc3339_utc(raw.terminal_at, "terminal observation terminal_at") < parse_rfc3339_utc(started.started_at, "started_at"):
            raise AttestationError(AttestationCode.TIME_ORDER_INVALID, "terminal observation precedes start")
        return InvocationTerminalObserved(started, envelope)

    @staticmethod
    def reconcile(
        observed: InvocationTerminalObserved,
        durable_claim: DurableClaimRecord,
        reconciled_at: str,
        owner_terminal: object | None = None,
    ) -> DurableTerminalReconciliation:
        # Import locally to keep E43 primitive imports acyclic.  E44 makes an
        # owner-specific, challenge-bound terminal decision mandatory here.
        from .durable_challenge import OwnerTerminalDecision

        raw = observed.raw
        if durable_claim.state is DurableClaimState.CLAIMED or not durable_claim.state.terminal:
            raise AttestationError(AttestationCode.DURABLE_STATE_INVALID, "durable claim is not terminally reconciled")
        if durable_claim.claim_id != raw.claim_id or durable_claim.invocation_id != raw.invocation_id:
            raise AttestationError(AttestationCode.INVOCATION_MISMATCH, "durable invocation mismatch")
        if durable_claim.holder != raw.owner:
            raise AttestationError(AttestationCode.OWNER_MISMATCH, "durable holder mismatch")
        if not isinstance(owner_terminal, OwnerTerminalDecision):
            raise AttestationError(AttestationCode.TERMINAL_MISMATCH, "E44 owner terminal decision required")
        if (
            owner_terminal.claim_id != raw.claim_id
            or owner_terminal.invocation_id != raw.invocation_id
            or owner_terminal.holder != raw.owner
            or owner_terminal.target is not raw.target
            or owner_terminal.terminal_status != raw.terminal_status
            or owner_terminal.terminal_at != raw.terminal_at
            or owner_terminal.log_hash != raw.log_hash
        ):
            raise AttestationError(AttestationCode.TERMINAL_MISMATCH, "E44 owner terminal decision mismatch")
        expected_evidence_type = {
            "ManualAppTerminalEvidence": ExecutionEvidenceType.CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION,
            "AutomationTerminalEvidence": ExecutionEvidenceType.APP_AUTOMATION_DISPATCHED_NEW_RUN,
            "CliTerminalEvidence": ExecutionEvidenceType.CODEX_CLI_PROCESS_INVOKED,
        }.get(owner_terminal.evidence_type)
        if expected_evidence_type is None or raw.evidence_type is not expected_evidence_type:
            raise AttestationError(AttestationCode.TERMINAL_MISMATCH, "E44 owner evidence type mismatch")
        if raw.exit_code != owner_terminal.exit_code:
            raise AttestationError(AttestationCode.TERMINAL_MISMATCH, "E44 terminal exit semantics mismatch")
        expected = {
            DurableClaimState.SUCCEEDED: "completed",
            DurableClaimState.FAILED: "failed",
            DurableClaimState.TIMED_OUT: "timed_out",
            DurableClaimState.RECOVERY_REQUIRED: "recovery_required",
        }[durable_claim.state]
        if raw.terminal_status != expected:
            raise AttestationError(AttestationCode.TERMINAL_MISMATCH, "durable state and observed terminal status differ")
        if durable_claim.terminal_at != raw.terminal_at:
            raise AttestationError(AttestationCode.TERMINAL_MISMATCH, "durable terminal time differs from observed terminal time")
        reconciled = parse_rfc3339_utc(reconciled_at, "reconciled_at")
        if reconciled < parse_rfc3339_utc(raw.terminal_at, "observed terminal_at"):
            raise AttestationError(AttestationCode.TIME_ORDER_INVALID, "reconciliation precedes observed terminal")
        return DurableTerminalReconciliation(observed, durable_claim, reconciled_at, _seal=_RECONCILIATION_SEAL)

    @staticmethod
    def classify(
        durable_claim: DurableClaimRecord,
        reconciliation: object | None,
    ) -> TerminalExecutionClassification:
        if durable_claim.state is DurableClaimState.CLAIMED:
            return TerminalExecutionClassification(
                AttestationCode.EXECUTION_IN_PROGRESS_OR_UNRECONCILED,
                InvocationLifecycleState.INVOCATION_STARTED,
                None,
            )
        if not isinstance(reconciliation, DurableTerminalReconciliation):
            return TerminalExecutionClassification(AttestationCode.DURABLE_RECONCILIATION_MISSING, None, None)
        if reconciliation.durable_claim != durable_claim:
            return TerminalExecutionClassification(AttestationCode.DURABLE_RECONCILIATION_MISSING, None, None)
        return TerminalExecutionClassification(
            AttestationCode.DURABLE_TERMINAL_RECONCILED,
            InvocationLifecycleState.DURABLE_TERMINAL_RECONCILED,
            reconciliation.observed.raw.evidence_type,
        )
