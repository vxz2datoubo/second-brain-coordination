"""Evidence contracts that prevent claim labels from becoming execution claims."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .durable_authority import DurableClaimRecord
from .models import CapabilityStatus, ValidationError, parse_rfc3339_utc, require_identifier, require_sha256


class ExecutionEvidenceType(str, Enum):
    CONTROL_PLANE_CLAIM_ONLY = "CONTROL_PLANE_CLAIM_ONLY"
    CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION = "CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION"
    APP_AUTOMATION_DISPATCHED_NEW_RUN = "APP_AUTOMATION_DISPATCHED_NEW_RUN"
    CODEX_CLI_PROCESS_INVOKED = "CODEX_CLI_PROCESS_INVOKED"


class CapabilityTarget(str, Enum):
    CODEX_APP = "CODEX_APP"
    CODEX_CLI = "CODEX_CLI"


@dataclass(frozen=True)
class CapabilityObservation:
    target: CapabilityTarget
    status: CapabilityStatus
    observed_at: str
    evidence_hash: str
    evidence_source: str

    def __post_init__(self) -> None:
        parse_rfc3339_utc(self.observed_at, "capability observed_at")
        require_sha256(self.evidence_hash, "capability evidence_hash")
        require_identifier(self.evidence_source, "capability evidence_source")


@dataclass(frozen=True)
class CapabilityPreflightDecision:
    target: CapabilityTarget
    status: CapabilityStatus
    reason_code: str
    observation: CapabilityObservation | None


def evaluate_capability(target: CapabilityTarget, observation: CapabilityObservation | None) -> CapabilityPreflightDecision:
    """No observation means UNKNOWN; there is intentionally no default-true path."""

    if observation is None:
        return CapabilityPreflightDecision(target, CapabilityStatus.UNKNOWN, "capability_evidence_missing", None)
    if observation.target is not target:
        return CapabilityPreflightDecision(target, CapabilityStatus.BLOCKED, "capability_target_mismatch", observation)
    return CapabilityPreflightDecision(target, observation.status, "capability_evidence_observed", observation)


@dataclass(frozen=True)
class InvocationReceipt:
    invocation_id: str
    parent_correlation_id: str
    evidence_type: ExecutionEvidenceType
    owner_type: str
    started_at: str
    ended_at: str
    terminal_status: str
    log_hash: str
    non_attempted_owner: str
    cleanup_proof_hash: str
    callback_proof_hash: str | None = None
    exit_code: int | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.invocation_id, "invocation_id"),
            (self.parent_correlation_id, "parent_correlation_id"),
            (self.owner_type, "invocation owner_type"),
            (self.terminal_status, "invocation terminal_status"),
            (self.non_attempted_owner, "invocation non_attempted_owner"),
        ):
            require_identifier(value, label)
        if parse_rfc3339_utc(self.ended_at, "invocation ended_at") < parse_rfc3339_utc(self.started_at, "invocation started_at"):
            raise ValidationError("invocation ended_at precedes started_at")
        require_sha256(self.log_hash, "invocation log_hash")
        require_sha256(self.cleanup_proof_hash, "invocation cleanup_proof_hash")
        if self.evidence_type is ExecutionEvidenceType.APP_AUTOMATION_DISPATCHED_NEW_RUN:
            if self.callback_proof_hash is None:
                raise ValidationError("app automation receipt requires callback proof")
            require_sha256(self.callback_proof_hash, "app callback_proof_hash")
        elif self.callback_proof_hash is not None:
            raise ValidationError("callback proof is limited to app automation evidence")
        if self.evidence_type is ExecutionEvidenceType.CODEX_CLI_PROCESS_INVOKED:
            if not isinstance(self.exit_code, int):
                raise ValidationError("CLI receipt requires integer exit_code")
        elif self.exit_code is not None:
            raise ValidationError("exit_code is limited to CLI execution evidence")


@dataclass(frozen=True)
class ExecutionEvidenceAssessment:
    evidence_type: ExecutionEvidenceType
    claim_id: str
    invocation_id: str | None
    reason_code: str


def classify_execution(claim: DurableClaimRecord, receipt: InvocationReceipt | None) -> ExecutionEvidenceAssessment:
    """Return the least-powerful truthful classification supported by evidence."""

    if receipt is None:
        return ExecutionEvidenceAssessment(
            ExecutionEvidenceType.CONTROL_PLANE_CLAIM_ONLY,
            claim.claim_id,
            None,
            "invocation_receipt_missing",
        )
    if receipt.parent_correlation_id != claim.parent_correlation_id:
        raise ValidationError("invocation receipt parent correlation mismatch")
    if claim.invocation_id != receipt.invocation_id:
        raise ValidationError("invocation receipt is not durably attached to claim")
    return ExecutionEvidenceAssessment(receipt.evidence_type, claim.claim_id, receipt.invocation_id, "receipt_contract_complete")
