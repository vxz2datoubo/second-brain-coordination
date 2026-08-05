"""E44 durable challenge and owner-specific terminal evidence contracts.

All records are synthetic test contracts.  The ledger is deliberately backed by
the existing revisioned CAS interface so one-shot consumption survives a new
ledger instance, restart, and cooperating test process.  It is not a live
runtime identity or authority root.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
import json
from typing import Callable

from .durable_authority import (
    ClaimHolder,
    DurableClaimRecord,
    DurableClaimState,
    RevisionedObjectGateway,
    OwnerType,
)
from .execution_evidence import CapabilityPreflightDecision, CapabilityTarget
from .models import CapabilityStatus, ValidationError, canonical_hash, parse_rfc3339_utc, require_identifier, require_sha256, strict_json_loads


_CHALLENGE_SEAL = object()
_DECISION_SEAL = object()
_RECOVERY_SEAL = object()


class LedgerCode(str, Enum):
    ISSUED = "ISSUED"
    CONSUMED = "CONSUMED"
    ALREADY_CONSUMED = "ALREADY_CONSUMED"
    NOT_FOUND = "NOT_FOUND"
    BINDING_MISMATCH = "BINDING_MISMATCH"
    EXPIRED = "EXPIRED"
    STALE = "STALE"
    CAS_CONFLICT = "CAS_CONFLICT"
    UNAVAILABLE = "UNAVAILABLE"


class TerminalEvidenceKind(str, Enum):
    MANUAL_APP = "MANUAL_APP"
    APP_AUTOMATION = "APP_AUTOMATION"
    CLI_PROCESS = "CLI_PROCESS"


@dataclass(frozen=True)
class DurableChallenge:
    challenge_id: str
    target: CapabilityTarget
    holder: ClaimHolder
    task_id: str
    route_epoch: int
    canary_id: str
    nonce: str
    issued_at: str
    expires_at: str
    max_age_seconds: int

    def __post_init__(self) -> None:
        for value, label in ((self.challenge_id, "challenge_id"), (self.task_id, "challenge task_id"), (self.canary_id, "challenge canary_id"), (self.nonce, "challenge nonce")):
            require_identifier(value, label)
        if not isinstance(self.holder, ClaimHolder) or not isinstance(self.route_epoch, int) or self.route_epoch < 1:
            raise ValidationError("challenge holder or epoch invalid")
        issued = parse_rfc3339_utc(self.issued_at, "challenge issued_at")
        if parse_rfc3339_utc(self.expires_at, "challenge expires_at") <= issued:
            raise ValidationError("challenge expiry must follow issue time")
        if not isinstance(self.max_age_seconds, int) or self.max_age_seconds < 1:
            raise ValidationError("challenge max age must be positive")

    @property
    def storage_id(self) -> str:
        return canonical_hash({"challenge_id": self.challenge_id, "task_id": self.task_id, "route_epoch": self.route_epoch, "canary_id": self.canary_id, "nonce": self.nonce})

    def document(self, state: str = "ACTIVE") -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "state": state,
            "challenge_id": self.challenge_id,
            "target": self.target.value,
            "holder": {"owner_type": self.holder.owner_type.value, "owner_instance_id": self.holder.owner_instance_id, "claimant_correlation_id": self.holder.claimant_correlation_id},
            "task_id": self.task_id,
            "route_epoch": self.route_epoch,
            "canary_id": self.canary_id,
            "nonce": self.nonce,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "max_age_seconds": self.max_age_seconds,
        }

    @property
    def document_bytes(self) -> bytes:
        return json.dumps(self.document(), sort_keys=True, separators=(",", ":")).encode("utf-8")


def _mint_challenge(
    challenge_id: str,
    target: CapabilityTarget,
    holder: ClaimHolder,
    task_id: str,
    route_epoch: int,
    canary_id: str,
    nonce: str,
    issued_at: str,
    expires_at: str,
    max_age_seconds: int,
) -> DurableChallenge:
    return DurableChallenge(challenge_id, target, holder, task_id, route_epoch, canary_id, nonce, issued_at, expires_at, max_age_seconds)


@dataclass(frozen=True)
class CapabilityWitness:
    challenge_id: str
    target: CapabilityTarget
    holder: ClaimHolder
    task_id: str
    route_epoch: int
    canary_id: str
    nonce: str
    observed_at: str
    status: CapabilityStatus
    evidence_hash: str
    transport_id: str

    def __post_init__(self) -> None:
        for value, label in ((self.challenge_id, "witness challenge_id"), (self.task_id, "witness task_id"), (self.canary_id, "witness canary_id"), (self.nonce, "witness nonce"), (self.transport_id, "witness transport_id")):
            require_identifier(value, label)
        if not isinstance(self.holder, ClaimHolder) or not isinstance(self.route_epoch, int) or self.route_epoch < 1:
            raise ValidationError("witness holder or epoch invalid")
        parse_rfc3339_utc(self.observed_at, "witness observed_at")
        require_sha256(self.evidence_hash, "witness evidence_hash")


@dataclass(frozen=True, init=False)
class ChallengeCapabilityDecision:
    challenge: DurableChallenge
    witness: CapabilityWitness
    consumed_at: str

    def __init__(self, challenge: DurableChallenge, witness: CapabilityWitness, consumed_at: str, *, _seal: object | None = None) -> None:
        if _seal is not _DECISION_SEAL:
            raise ValidationError("challenge capability decision must be ledger minted")
        object.__setattr__(self, "challenge", challenge)
        object.__setattr__(self, "witness", witness)
        object.__setattr__(self, "consumed_at", consumed_at)


@dataclass(frozen=True)
class ChallengeLedgerResult:
    code: LedgerCode
    decision: ChallengeCapabilityDecision | None = None


class DurableChallengeLedger:
    def __init__(self, namespace: str, gateway: RevisionedObjectGateway) -> None:
        require_identifier(namespace, "challenge ledger namespace")
        self._namespace = namespace
        self._gateway = gateway

    def _object_id(self, challenge: DurableChallenge) -> str:
        return f"{self._namespace}.challenge.{challenge.storage_id}"

    @staticmethod
    def _matches(challenge: DurableChallenge, witness: CapabilityWitness) -> bool:
        return (
            challenge.challenge_id == witness.challenge_id
            and challenge.target is witness.target
            and challenge.holder == witness.holder
            and challenge.task_id == witness.task_id
            and challenge.route_epoch == witness.route_epoch
            and challenge.canary_id == witness.canary_id
            and challenge.nonce == witness.nonce
        )

    def issue(self, challenge: DurableChallenge) -> ChallengeLedgerResult:
        try:
            object_id = self._object_id(challenge)
            snapshot = self._gateway.read(object_id)
            if snapshot.payload is not None:
                return ChallengeLedgerResult(LedgerCode.BINDING_MISMATCH)
            write = self._gateway.compare_and_set(object_id, None, challenge.document_bytes)
            return ChallengeLedgerResult(LedgerCode.ISSUED if write.applied else LedgerCode.CAS_CONFLICT)
        except Exception:
            return ChallengeLedgerResult(LedgerCode.UNAVAILABLE)

    def consume(self, challenge: DurableChallenge, witness: CapabilityWitness, checked_at: str) -> ChallengeLedgerResult:
        if not self._matches(challenge, witness):
            return ChallengeLedgerResult(LedgerCode.BINDING_MISMATCH)
        checked = parse_rfc3339_utc(checked_at, "challenge checked_at")
        observed = parse_rfc3339_utc(witness.observed_at, "challenge witness observed_at")
        issued = parse_rfc3339_utc(challenge.issued_at, "challenge issued_at")
        expires = parse_rfc3339_utc(challenge.expires_at, "challenge expires_at")
        if checked >= expires or observed >= expires or observed < issued:
            return ChallengeLedgerResult(LedgerCode.EXPIRED)
        if observed > checked or checked - observed > timedelta(seconds=challenge.max_age_seconds):
            return ChallengeLedgerResult(LedgerCode.STALE)
        try:
            object_id = self._object_id(challenge)
            snapshot = self._gateway.read(object_id)
            if snapshot.payload is None:
                return ChallengeLedgerResult(LedgerCode.NOT_FOUND)
            value = strict_json_loads(snapshot.payload.decode("utf-8"))
            if not isinstance(value, dict) or value.get("schema_version") != "1.0":
                return ChallengeLedgerResult(LedgerCode.BINDING_MISMATCH)
            if value != challenge.document(value.get("state", "ACTIVE")):
                return ChallengeLedgerResult(LedgerCode.BINDING_MISMATCH)
            if value.get("state") != "ACTIVE":
                return ChallengeLedgerResult(LedgerCode.ALREADY_CONSUMED)
            payload = json.dumps(challenge.document("CONSUMED"), sort_keys=True, separators=(",", ":")).encode("utf-8")
            write = self._gateway.compare_and_set(object_id, snapshot.revision, payload)
            if not write.applied:
                return ChallengeLedgerResult(LedgerCode.CAS_CONFLICT)
        except Exception:
            return ChallengeLedgerResult(LedgerCode.UNAVAILABLE)
        return ChallengeLedgerResult(LedgerCode.CONSUMED, ChallengeCapabilityDecision(challenge, witness, checked_at, _seal=_DECISION_SEAL))


def evaluate_challenge_capability(target: CapabilityTarget, decision: object | None) -> CapabilityPreflightDecision:
    if not isinstance(decision, ChallengeCapabilityDecision):
        return CapabilityPreflightDecision(target, CapabilityStatus.BLOCKED, "challenge_attested_capability_required", None)
    if decision.challenge.target is not target:
        return CapabilityPreflightDecision(target, CapabilityStatus.BLOCKED, "challenge_target_mismatch", None)
    if decision.witness.status is not CapabilityStatus.SUPPORTED:
        return CapabilityPreflightDecision(target, decision.witness.status, "challenge_attested_nonpositive_capability", None)
    return CapabilityPreflightDecision(target, CapabilityStatus.SUPPORTED, "durable_challenge_attested_capability", None)


@dataclass(frozen=True)
class RecoveryAuthorizationGrant:
    authorization_id: str
    provenance_digest: str
    storage_id: str
    task_id: str
    route_epoch: int
    canary_id: str
    nonce: str
    claim_id: str
    original_holder: ClaimHolder
    not_before: str
    expires_at: str
    reason: str

    def __post_init__(self) -> None:
        for value, label in ((self.authorization_id, "recovery authorization_id"), (self.task_id, "recovery task_id"), (self.canary_id, "recovery canary_id"), (self.nonce, "recovery nonce"), (self.claim_id, "recovery claim_id"), (self.reason, "recovery reason")):
            require_identifier(value, label)
        require_sha256(self.provenance_digest, "recovery provenance_digest")
        require_sha256(self.storage_id, "recovery storage_id")
        if not isinstance(self.original_holder, ClaimHolder) or not isinstance(self.route_epoch, int) or self.route_epoch < 1:
            raise ValidationError("recovery holder or epoch invalid")
        if parse_rfc3339_utc(self.expires_at, "recovery expires_at") <= parse_rfc3339_utc(self.not_before, "recovery not_before"):
            raise ValidationError("recovery expiry must follow not_before")

    @property
    def storage_key(self) -> str:
        return canonical_hash({"authorization_id": self.authorization_id, "provenance_digest": self.provenance_digest, "storage_id": self.storage_id, "claim_id": self.claim_id, "nonce": self.nonce})

    def document(self, state: str = "ACTIVE") -> dict[str, object]:
        return {
            "schema_version": "1.0", "state": state, "authorization_id": self.authorization_id,
            "provenance_digest": self.provenance_digest, "storage_id": self.storage_id,
            "task_id": self.task_id, "route_epoch": self.route_epoch, "canary_id": self.canary_id,
            "nonce": self.nonce, "claim_id": self.claim_id,
            "original_holder": {"owner_type": self.original_holder.owner_type.value, "owner_instance_id": self.original_holder.owner_instance_id, "claimant_correlation_id": self.original_holder.claimant_correlation_id},
            "not_before": self.not_before, "expires_at": self.expires_at, "reason": self.reason,
        }


def recovery_grant_from_claim(authorization_id: str, claim: DurableClaimRecord, not_before: str, expires_at: str, reason: str) -> RecoveryAuthorizationGrant:
    return RecoveryAuthorizationGrant(authorization_id, claim.provenance.digest, claim.key.storage_id, claim.provenance.task_id, claim.provenance.route_epoch, claim.provenance.canary_id, claim.provenance.nonce, claim.claim_id, claim.holder, not_before, expires_at, reason)


@dataclass(frozen=True)
class RecoveryLedgerResult:
    code: LedgerCode
    grant: RecoveryAuthorizationGrant | None = None


class RecoveryAuthorizationLedger:
    def __init__(self, namespace: str, gateway: RevisionedObjectGateway) -> None:
        require_identifier(namespace, "recovery ledger namespace")
        self._namespace = namespace
        self._gateway = gateway

    def _object_id(self, grant: RecoveryAuthorizationGrant) -> str:
        return f"{self._namespace}.recovery.{grant.storage_key}"

    def issue(self, grant: RecoveryAuthorizationGrant) -> RecoveryLedgerResult:
        try:
            object_id = self._object_id(grant)
            snapshot = self._gateway.read(object_id)
            if snapshot.payload is not None:
                return RecoveryLedgerResult(LedgerCode.BINDING_MISMATCH)
            payload = json.dumps(grant.document(), sort_keys=True, separators=(",", ":")).encode("utf-8")
            write = self._gateway.compare_and_set(object_id, None, payload)
            return RecoveryLedgerResult(LedgerCode.ISSUED if write.applied else LedgerCode.CAS_CONFLICT)
        except Exception:
            return RecoveryLedgerResult(LedgerCode.UNAVAILABLE)

    def consume(self, grant: RecoveryAuthorizationGrant, claim: DurableClaimRecord, observed_at: str) -> RecoveryLedgerResult:
        observed = parse_rfc3339_utc(observed_at, "recovery observed_at")
        if (grant.provenance_digest != claim.provenance.digest or grant.storage_id != claim.key.storage_id or grant.task_id != claim.provenance.task_id or grant.route_epoch != claim.provenance.route_epoch or grant.canary_id != claim.provenance.canary_id or grant.nonce != claim.provenance.nonce or grant.claim_id != claim.claim_id or grant.original_holder != claim.holder):
            return RecoveryLedgerResult(LedgerCode.BINDING_MISMATCH)
        if observed < parse_rfc3339_utc(grant.not_before, "recovery not_before") or observed >= parse_rfc3339_utc(grant.expires_at, "recovery expires_at"):
            return RecoveryLedgerResult(LedgerCode.EXPIRED)
        try:
            object_id = self._object_id(grant)
            snapshot = self._gateway.read(object_id)
            if snapshot.payload is None:
                return RecoveryLedgerResult(LedgerCode.NOT_FOUND)
            value = strict_json_loads(snapshot.payload.decode("utf-8"))
            if not isinstance(value, dict) or value != grant.document(value.get("state", "ACTIVE")):
                return RecoveryLedgerResult(LedgerCode.BINDING_MISMATCH)
            if value.get("state") != "ACTIVE":
                return RecoveryLedgerResult(LedgerCode.ALREADY_CONSUMED)
            payload = json.dumps(grant.document("CONSUMED"), sort_keys=True, separators=(",", ":")).encode("utf-8")
            write = self._gateway.compare_and_set(object_id, snapshot.revision, payload)
            return RecoveryLedgerResult(LedgerCode.CONSUMED, grant) if write.applied else RecoveryLedgerResult(LedgerCode.CAS_CONFLICT)
        except Exception:
            return RecoveryLedgerResult(LedgerCode.UNAVAILABLE)


@dataclass(frozen=True)
class ManualAppTerminalEvidence:
    claim_id: str
    invocation_id: str
    holder: ClaimHolder
    target: CapabilityTarget
    terminal_status: str
    terminal_at: str
    session_id: str
    interaction_hash: str
    log_hash: str
    cleanup_hash: str


@dataclass(frozen=True)
class AutomationTerminalEvidence:
    claim_id: str
    invocation_id: str
    holder: ClaimHolder
    target: CapabilityTarget
    terminal_status: str
    terminal_at: str
    dispatch_id: str
    run_id: str
    callback_id: str
    callback_identity: str
    callback_hash: str
    log_hash: str
    cleanup_hash: str


@dataclass(frozen=True)
class CliTerminalEvidence:
    claim_id: str
    invocation_id: str
    holder: ClaimHolder
    target: CapabilityTarget
    terminal_status: str
    terminal_at: str
    launcher_id: str
    process_id: int
    process_start_token: str
    exit_code: int | None
    cleanup_state: str
    log_hash: str
    cleanup_hash: str


TerminalEvidence = ManualAppTerminalEvidence | AutomationTerminalEvidence | CliTerminalEvidence


@dataclass(frozen=True, init=False)
class OwnerTerminalDecision:
    claim_id: str
    invocation_id: str
    holder: ClaimHolder
    target: CapabilityTarget
    terminal_status: str
    terminal_at: str
    evidence_type: str
    log_hash: str
    exit_code: int | None

    def __init__(self, evidence: TerminalEvidence, *, _seal: object | None = None) -> None:
        if _seal is not _DECISION_SEAL:
            raise ValidationError("owner terminal decision must be gate minted")
        object.__setattr__(self, "claim_id", evidence.claim_id)
        object.__setattr__(self, "invocation_id", evidence.invocation_id)
        object.__setattr__(self, "holder", evidence.holder)
        object.__setattr__(self, "target", evidence.target)
        object.__setattr__(self, "terminal_status", evidence.terminal_status)
        object.__setattr__(self, "terminal_at", evidence.terminal_at)
        object.__setattr__(self, "evidence_type", type(evidence).__name__)
        object.__setattr__(self, "log_hash", evidence.log_hash)
        object.__setattr__(self, "exit_code", evidence.exit_code if isinstance(evidence, CliTerminalEvidence) else None)


def _require_evidence_fields(evidence: TerminalEvidence) -> None:
    for value, label in ((evidence.claim_id, "terminal claim_id"), (evidence.invocation_id, "terminal invocation_id"), (evidence.terminal_status, "terminal status")):
        require_identifier(value, label)
    if not isinstance(evidence.holder, ClaimHolder):
        raise ValidationError("terminal evidence holder invalid")
    parse_rfc3339_utc(evidence.terminal_at, "terminal evidence time")
    require_sha256(evidence.log_hash, "terminal log_hash")
    require_sha256(evidence.cleanup_hash, "terminal cleanup_hash")


def validate_owner_terminal_evidence(claim: DurableClaimRecord, capability: object, evidence: TerminalEvidence) -> OwnerTerminalDecision:
    """Return a sealed decision only after capability, owner and terminal truth agree."""

    _require_evidence_fields(evidence)
    if not isinstance(capability, ChallengeCapabilityDecision) or capability.witness.status is not CapabilityStatus.SUPPORTED:
        raise ValidationError("fresh positive challenge capability required")
    if claim.claim_id != evidence.claim_id or claim.invocation_id != evidence.invocation_id or claim.holder != evidence.holder:
        raise ValidationError("terminal evidence claim, invocation, or owner mismatch")
    if capability.challenge.holder != claim.holder or capability.challenge.target is not evidence.target:
        raise ValidationError("challenge and terminal evidence binding mismatch")
    if evidence.terminal_at != claim.terminal_at:
        raise ValidationError("terminal evidence time differs from durable claim")
    expected = {
        DurableClaimState.SUCCEEDED: "completed",
        DurableClaimState.FAILED: "failed",
        DurableClaimState.TIMED_OUT: "timed_out",
        DurableClaimState.RECOVERY_REQUIRED: "recovery_required",
    }.get(claim.state)
    if expected is None or evidence.terminal_status != expected:
        raise ValidationError("terminal status contradicts durable state")
    if isinstance(evidence, ManualAppTerminalEvidence):
        if evidence.holder.owner_type is not OwnerType.CURRENT_CODEX_APP_SESSION or evidence.target is not CapabilityTarget.CODEX_APP:
            raise ValidationError("manual evidence owner or target mismatch")
        for value, label in ((evidence.session_id, "manual session_id"),):
            require_identifier(value, label)
        require_sha256(evidence.interaction_hash, "manual interaction_hash")
    elif isinstance(evidence, AutomationTerminalEvidence):
        if evidence.holder.owner_type is not OwnerType.APP_AUTOMATION_NEW_RUN or evidence.target is not CapabilityTarget.CODEX_APP:
            raise ValidationError("automation evidence owner or target mismatch")
        for value, label in ((evidence.dispatch_id, "automation dispatch_id"), (evidence.run_id, "automation run_id"), (evidence.callback_id, "automation callback_id"), (evidence.callback_identity, "automation callback_identity")):
            require_identifier(value, label)
        require_sha256(evidence.callback_hash, "automation callback_hash")
    elif isinstance(evidence, CliTerminalEvidence):
        if evidence.holder.owner_type is not OwnerType.CODEX_CLI_PROCESS or evidence.target is not CapabilityTarget.CODEX_CLI:
            raise ValidationError("CLI evidence owner or target mismatch")
        require_identifier(evidence.launcher_id, "CLI launcher_id")
        require_sha256(evidence.process_start_token, "CLI process_start_token")
        if not isinstance(evidence.process_id, int) or evidence.process_id < 1 or evidence.cleanup_state != "CLEAN":
            raise ValidationError("CLI process identity or cleanup invalid")
        if claim.state is DurableClaimState.SUCCEEDED and evidence.exit_code != 0:
            raise ValidationError("successful CLI terminal requires exit code zero")
        if claim.state is DurableClaimState.FAILED and (not isinstance(evidence.exit_code, int) or evidence.exit_code == 0):
            raise ValidationError("failed CLI terminal requires nonzero exit code")
        if claim.state in {DurableClaimState.TIMED_OUT, DurableClaimState.RECOVERY_REQUIRED} and evidence.exit_code is not None:
            raise ValidationError("timed-out or recovery CLI terminal cannot assert an exit code")
    else:
        raise ValidationError("unknown terminal evidence schema")
    return OwnerTerminalDecision(evidence, _seal=_DECISION_SEAL)
