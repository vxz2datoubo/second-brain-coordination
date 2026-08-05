"""Raw-versus-verified capability and invocation evidence for E42."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .durable_authority import ClaimHolder, DurableClaimRecord, DurableClaimState, OwnerType
from .models import CapabilityStatus, ValidationError, parse_rfc3339_utc, require_identifier, require_sha256


_VERIFIER_SEAL = object()
_CAPABILITY_SEAL = object()
_INVOCATION_SEAL = object()


class ExecutionEvidenceType(str, Enum):
    CONTROL_PLANE_CLAIM_ONLY = "CONTROL_PLANE_CLAIM_ONLY"
    CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION = "CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION"
    APP_AUTOMATION_DISPATCHED_NEW_RUN = "APP_AUTOMATION_DISPATCHED_NEW_RUN"
    CODEX_CLI_PROCESS_INVOKED = "CODEX_CLI_PROCESS_INVOKED"


class CapabilityTarget(str, Enum):
    CODEX_APP = "CODEX_APP"
    CODEX_CLI = "CODEX_CLI"


@dataclass(frozen=True)
class RawCapabilityObservation:
    target: CapabilityTarget
    status: CapabilityStatus
    observed_at: str
    evidence_hash: str
    evidence_source: str
    transport_identity: str

    def __post_init__(self) -> None:
        parse_rfc3339_utc(self.observed_at, "capability observed_at")
        require_sha256(self.evidence_hash, "capability evidence_hash")
        require_identifier(self.evidence_source, "capability evidence_source")
        require_identifier(self.transport_identity, "capability transport_identity")


CapabilityObservation = RawCapabilityObservation


@dataclass(frozen=True, init=False)
class VerifiedCapabilityObservation:
    target: CapabilityTarget
    status: CapabilityStatus
    observed_at: str
    evidence_hash: str
    evidence_source: str
    transport_identity: str
    verified_at: str

    def __init__(self, raw: RawCapabilityObservation, verified_at: str, *, _seal: object | None = None) -> None:
        if _seal is not _CAPABILITY_SEAL:
            raise ValidationError("verified capability must come from a trusted verifier")
        for key, value in raw.__dict__.items():
            object.__setattr__(self, key, value)
        parse_rfc3339_utc(verified_at, "capability verified_at")
        object.__setattr__(self, "verified_at", verified_at)


@dataclass(frozen=True)
class CapabilityPreflightDecision:
    target: CapabilityTarget
    status: CapabilityStatus
    reason_code: str
    observation: VerifiedCapabilityObservation | None


def evaluate_capability(target: CapabilityTarget, observation: object | None) -> CapabilityPreflightDecision:
    if observation is None:
        return CapabilityPreflightDecision(target, CapabilityStatus.UNKNOWN, "capability_evidence_missing", None)
    if not isinstance(observation, VerifiedCapabilityObservation):
        return CapabilityPreflightDecision(target, CapabilityStatus.BLOCKED, "capability_observation_unverified", None)
    if observation.target is not target:
        return CapabilityPreflightDecision(target, CapabilityStatus.BLOCKED, "capability_target_mismatch", observation)
    # E44: this legacy object has no durable challenge consumption.  It remains
    # useful context, but cannot itself grant a positive capability decision.
    return CapabilityPreflightDecision(target, CapabilityStatus.BLOCKED, "legacy_capability_observational_only", observation)


@dataclass(frozen=True)
class RawInvocationReceipt:
    claim_id: str
    invocation_id: str
    holder: ClaimHolder
    evidence_type: ExecutionEvidenceType
    started_at: str
    ended_at: str
    terminal_status: str
    log_hash: str
    cleanup_proof_hash: str
    transport_identity: str
    non_attempted_owners: tuple[OwnerType, ...]
    session_id: str | None = None
    dispatch_receipt_hash: str | None = None
    callback_transport_identity: str | None = None
    callback_proof_hash: str | None = None
    process_launcher_identity: str | None = None
    process_id: int | None = None
    process_token: str | None = None
    exit_code: int | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.claim_id, "invocation claim_id"),
            (self.invocation_id, "invocation_id"),
            (self.terminal_status, "invocation terminal_status"),
            (self.transport_identity, "invocation transport_identity"),
        ):
            require_identifier(value, label)
        if parse_rfc3339_utc(self.ended_at, "invocation ended_at") < parse_rfc3339_utc(self.started_at, "invocation started_at"):
            raise ValidationError("invocation ended_at precedes started_at")
        require_sha256(self.log_hash, "invocation log_hash")
        require_sha256(self.cleanup_proof_hash, "invocation cleanup_proof_hash")
        if len(set(self.non_attempted_owners)) != len(self.non_attempted_owners):
            raise ValidationError("non-attempted owners must be unique")


InvocationReceipt = RawInvocationReceipt


@dataclass(frozen=True, init=False)
class VerifiedInvocationReceipt:
    raw: RawInvocationReceipt
    verified_at: str

    def __init__(self, raw: RawInvocationReceipt, verified_at: str, *, _seal: object | None = None) -> None:
        if _seal is not _INVOCATION_SEAL:
            raise ValidationError("verified invocation receipt must come from a trusted verifier")
        parse_rfc3339_utc(verified_at, "invocation verified_at")
        object.__setattr__(self, "raw", raw)
        object.__setattr__(self, "verified_at", verified_at)


class TrustedEvidenceVerifier:
    """Process-local API boundary around a fixed transport identity.

    This is not cryptographic isolation from hostile code in the same Python
    process.  The outer runtime must keep the verifier and its transport private.
    """

    def __init__(self, transport_identity: str, *, _seal: object | None = None) -> None:
        if _seal is not _VERIFIER_SEAL:
            raise ValidationError("trusted evidence verifier is composition-root only")
        require_identifier(transport_identity, "trusted transport_identity")
        self._transport_identity = transport_identity

    def verify_capability(self, raw: RawCapabilityObservation, checked_at: str) -> VerifiedCapabilityObservation:
        checked = parse_rfc3339_utc(checked_at, "capability checked_at")
        if not isinstance(raw, RawCapabilityObservation) or raw.transport_identity != self._transport_identity:
            raise ValidationError("capability transport identity mismatch")
        if parse_rfc3339_utc(raw.observed_at, "capability observed_at") > checked:
            raise ValidationError("capability observation is in the future")
        return VerifiedCapabilityObservation(raw, checked_at, _seal=_CAPABILITY_SEAL)

    @staticmethod
    def _expected_owner(evidence_type: ExecutionEvidenceType) -> OwnerType:
        return {
            ExecutionEvidenceType.CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION: OwnerType.CURRENT_CODEX_APP_SESSION,
            ExecutionEvidenceType.APP_AUTOMATION_DISPATCHED_NEW_RUN: OwnerType.APP_AUTOMATION_NEW_RUN,
            ExecutionEvidenceType.CODEX_CLI_PROCESS_INVOKED: OwnerType.CODEX_CLI_PROCESS,
        }[evidence_type]

    def verify_invocation(self, claim: DurableClaimRecord, raw: RawInvocationReceipt, checked_at: str) -> VerifiedInvocationReceipt:
        checked = parse_rfc3339_utc(checked_at, "invocation checked_at")
        if not isinstance(raw, RawInvocationReceipt) or raw.transport_identity != self._transport_identity:
            raise ValidationError("invocation transport identity mismatch")
        if raw.evidence_type is ExecutionEvidenceType.CONTROL_PLANE_CLAIM_ONLY:
            raise ValidationError("claim-only is not an invocation receipt")
        if raw.claim_id != claim.claim_id or raw.holder != claim.holder:
            raise ValidationError("invocation owner or claim mismatch")
        if raw.holder.owner_type is not self._expected_owner(raw.evidence_type):
            raise ValidationError("invocation evidence type is incompatible with owner")
        if claim.invocation_id != raw.invocation_id:
            raise ValidationError("invocation is not durably attached")
        started = parse_rfc3339_utc(raw.started_at, "invocation started_at")
        ended = parse_rfc3339_utc(raw.ended_at, "invocation ended_at")
        claimed = parse_rfc3339_utc(claim.claimed_at, "durable claimed_at")
        if started < claimed or ended > checked:
            raise ValidationError("invocation time order invalid")
        if claim.terminal_at is not None and ended > parse_rfc3339_utc(claim.terminal_at, "durable terminal_at"):
            raise ValidationError("invocation ends after durable terminal")
        expected_non_attempted = set(OwnerType) - {raw.holder.owner_type}
        if set(raw.non_attempted_owners) != expected_non_attempted:
            raise ValidationError("non-attempted owner mutual exclusion incomplete")
        if raw.evidence_type is ExecutionEvidenceType.CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION:
            if raw.session_id is None:
                raise ValidationError("manual App receipt requires session identity")
            require_identifier(raw.session_id, "manual App session_id")
            forbidden = (raw.dispatch_receipt_hash, raw.callback_transport_identity, raw.callback_proof_hash, raw.process_launcher_identity, raw.process_id, raw.process_token, raw.exit_code)
            if any(value is not None for value in forbidden):
                raise ValidationError("manual App receipt contains another owner evidence")
        elif raw.evidence_type is ExecutionEvidenceType.APP_AUTOMATION_DISPATCHED_NEW_RUN:
            for value, label in (
                (raw.dispatch_receipt_hash, "dispatch_receipt_hash"),
                (raw.callback_proof_hash, "callback_proof_hash"),
            ):
                if value is None:
                    raise ValidationError(f"App Automation requires {label}")
                require_sha256(value, label)
            if raw.callback_transport_identity != self._transport_identity:
                raise ValidationError("App callback transport identity mismatch")
            if raw.session_id is not None or any(value is not None for value in (raw.process_launcher_identity, raw.process_id, raw.process_token, raw.exit_code)):
                raise ValidationError("App Automation receipt contains another owner evidence")
        else:
            if raw.process_launcher_identity != self._transport_identity:
                raise ValidationError("CLI process launcher identity mismatch")
            if not isinstance(raw.process_id, int) or raw.process_id < 1 or raw.process_token is None or not isinstance(raw.exit_code, int):
                raise ValidationError("CLI receipt requires PID, process token, and exit code")
            require_identifier(raw.process_token, "CLI process_token")
            if raw.session_id is not None or any(value is not None for value in (raw.dispatch_receipt_hash, raw.callback_transport_identity, raw.callback_proof_hash)):
                raise ValidationError("CLI receipt contains another owner evidence")
        expected_terminal = {
            DurableClaimState.SUCCEEDED: "completed",
            DurableClaimState.FAILED: "failed",
            DurableClaimState.TIMED_OUT: "timed_out",
            DurableClaimState.RECOVERY_REQUIRED: "recovery_required",
        }.get(claim.state)
        if expected_terminal is not None and raw.terminal_status != expected_terminal:
            raise ValidationError("invocation terminal status contradicts durable state")
        return VerifiedInvocationReceipt(raw, checked_at, _seal=_INVOCATION_SEAL)


def _trusted_evidence_verifier(transport_identity: str) -> TrustedEvidenceVerifier:
    """Composition-root factory; tests use it with synthetic transport IDs."""

    return TrustedEvidenceVerifier(transport_identity, _seal=_VERIFIER_SEAL)


@dataclass(frozen=True)
class ExecutionEvidenceAssessment:
    evidence_type: ExecutionEvidenceType
    claim_id: str
    invocation_id: str | None
    reason_code: str


def classify_execution(claim: DurableClaimRecord, receipt: object | None) -> ExecutionEvidenceAssessment:
    """Keep the E42 entrypoint observational; E43 owns positive terminals.

    A process-local verified receipt is useful evidence, but it cannot classify
    an App or CLI execution as terminal until E43 matches it to a durable
    terminal reconciliation. Returning a claim-only assessment here prevents
    legacy callers from bypassing the E43 lifecycle gate.
    """

    if receipt is None:
        return ExecutionEvidenceAssessment(ExecutionEvidenceType.CONTROL_PLANE_CLAIM_ONLY, claim.claim_id, None, "invocation_receipt_missing")
    if not isinstance(receipt, VerifiedInvocationReceipt):
        raise ValidationError("verified invocation receipt required")
    if receipt.raw.claim_id != claim.claim_id or receipt.raw.holder != claim.holder or receipt.raw.invocation_id != claim.invocation_id:
        raise ValidationError("verified invocation no longer matches durable claim")
    if claim.state is DurableClaimState.CLAIMED:
        return ExecutionEvidenceAssessment(
            ExecutionEvidenceType.CONTROL_PLANE_CLAIM_ONLY,
            claim.claim_id,
            receipt.raw.invocation_id,
            "execution_in_progress_or_unreconciled",
        )
    return ExecutionEvidenceAssessment(
        ExecutionEvidenceType.CONTROL_PLANE_CLAIM_ONLY,
        claim.claim_id,
        receipt.raw.invocation_id,
        "durable_terminal_requires_e43_reconciliation",
    )
