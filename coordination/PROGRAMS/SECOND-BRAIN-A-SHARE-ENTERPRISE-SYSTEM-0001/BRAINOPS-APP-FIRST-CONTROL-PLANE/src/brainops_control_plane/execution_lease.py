"""Mandatory durable execution lease for the E46 control plane.

This module is an offline executable contract.  Its sealed constructors model
composition-root ownership for tests; they are not a production cryptographic
trust root.  Positive effect and terminal mutation paths are nevertheless
forced through one revisioned, monotonic lease and one durable operation
journal.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import json
from typing import TypeAlias

from .durable_authority import (
    ClaimHolder,
    DurableClaimAuthority,
    DurableClaimRecord,
    DurableClaimResultCode,
    DurableClaimState,
    DurableClaimKey,
    OwnerType,
    RevisionedObjectGateway,
    VerifiedAuthorityProvenance,
)
from .durable_challenge import ChallengeCapabilityDecision
from .execution_evidence import CapabilityTarget, ExecutionEvidenceType
from .models import (
    CapabilityStatus,
    ValidationError,
    canonical_hash,
    parse_rfc3339_utc,
    require_identifier,
    require_sha256,
    strict_json_loads,
)


_EFFECT_PERMIT_SEAL = object()
_CAPTURE_SEAL = object()
_TRANSPORT_SEAL = object()
_IDENTITY_SEAL = object()
_IDENTITY_VERIFIER_SEAL = object()
_TERMINAL_EVIDENCE_SEAL = object()
_TERMINAL_AUTHORIZATION_SEAL = object()
_JOURNALED_MUTATION_SEAL = object()
_TERMINAL_RECEIPT_SEAL = object()


class ExecutionLeaseState(str, Enum):
    CAPABILITY_ATTESTED = "CAPABILITY_ATTESTED"
    EFFECT_AUTHORIZED = "EFFECT_AUTHORIZED"
    INVOCATION_ATTACHED = "INVOCATION_ATTACHED"
    TERMINAL_ATTESTED = "TERMINAL_ATTESTED"
    TERMINAL_COMMITTED = "TERMINAL_COMMITTED"

    @property
    def version(self) -> int:
        return {
            ExecutionLeaseState.CAPABILITY_ATTESTED: 1,
            ExecutionLeaseState.EFFECT_AUTHORIZED: 2,
            ExecutionLeaseState.INVOCATION_ATTACHED: 3,
            ExecutionLeaseState.TERMINAL_ATTESTED: 4,
            ExecutionLeaseState.TERMINAL_COMMITTED: 5,
        }[self]


class ExecutionLeaseCode(str, Enum):
    CAPABILITY_ATTESTED = "CAPABILITY_ATTESTED"
    EFFECT_AUTHORIZED = "EFFECT_AUTHORIZED"
    INVOCATION_ATTACHED = "INVOCATION_ATTACHED"
    TERMINAL_ATTESTED = "TERMINAL_ATTESTED"
    TERMINAL_COMMITTED = "TERMINAL_COMMITTED"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    ALREADY_COMMITTED = "ALREADY_COMMITTED"
    CLAIM_NOT_FOUND = "CLAIM_NOT_FOUND"
    BINDING_MISMATCH = "BINDING_MISMATCH"
    CAPABILITY_REQUIRED = "CAPABILITY_REQUIRED"
    LEASE_NOT_FOUND = "LEASE_NOT_FOUND"
    LEASE_EXPIRED = "LEASE_EXPIRED"
    ILLEGAL_TRANSITION = "ILLEGAL_TRANSITION"
    INVOCATION_INVALID = "INVOCATION_INVALID"
    INVOCATION_MISMATCH = "INVOCATION_MISMATCH"
    IDENTITY_UNATTESTED = "IDENTITY_UNATTESTED"
    TERMINAL_EVIDENCE_REQUIRED = "TERMINAL_EVIDENCE_REQUIRED"
    CLAIM_NOT_APPLIED = "CLAIM_NOT_APPLIED"
    CAS_CONFLICT = "CAS_CONFLICT"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    AUTHORITY_UNAVAILABLE = "AUTHORITY_UNAVAILABLE"
    TAMPERED = "TAMPERED"


class ExecutionIdentityKind(str, Enum):
    MANUAL_APP = "MANUAL_APP"
    AUTOMATION = "AUTOMATION"
    CLI = "CLI"


class OperationPhase(str, Enum):
    REQUESTED = "REQUESTED"
    CLAIM_NOT_APPLIED = "CLAIM_NOT_APPLIED"
    CLAIM_APPLIED = "CLAIM_APPLIED"
    RESPONSE_LOST_UNKNOWN = "RESPONSE_LOST_UNKNOWN"
    CLAIM_APPLIED_RESPONSE_LOST = "CLAIM_APPLIED_RESPONSE_LOST"
    LEASE_COMMITTED_RESPONSE_LOST = "LEASE_COMMITTED_RESPONSE_LOST"
    CAS_CONFLICT = "CAS_CONFLICT"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    RECONCILED = "RECONCILED"
    TERMINAL_COMMITTED = "TERMINAL_COMMITTED"


_JOURNAL_TRANSITIONS = {
    OperationPhase.REQUESTED: {
        OperationPhase.CLAIM_NOT_APPLIED,
        OperationPhase.CLAIM_APPLIED,
        OperationPhase.RESPONSE_LOST_UNKNOWN,
        OperationPhase.CAS_CONFLICT,
    },
    OperationPhase.RESPONSE_LOST_UNKNOWN: {OperationPhase.RECONCILIATION_REQUIRED},
    OperationPhase.RECONCILIATION_REQUIRED: {
        OperationPhase.CLAIM_APPLIED_RESPONSE_LOST,
        OperationPhase.LEASE_COMMITTED_RESPONSE_LOST,
        OperationPhase.CLAIM_NOT_APPLIED,
        OperationPhase.CAS_CONFLICT,
    },
    OperationPhase.CLAIM_APPLIED_RESPONSE_LOST: {OperationPhase.RECONCILED},
    OperationPhase.LEASE_COMMITTED_RESPONSE_LOST: {OperationPhase.RECONCILED},
    OperationPhase.RECONCILED: {OperationPhase.TERMINAL_COMMITTED},
    OperationPhase.CLAIM_APPLIED: {OperationPhase.RECONCILIATION_REQUIRED, OperationPhase.TERMINAL_COMMITTED},
}


def _holder_document(holder: ClaimHolder) -> dict[str, str]:
    return {
        "owner_type": holder.owner_type.value,
        "owner_instance_id": holder.owner_instance_id,
        "claimant_correlation_id": holder.claimant_correlation_id,
    }


def _holder_from_document(value: object) -> ClaimHolder:
    if not isinstance(value, dict):
        raise ValidationError("execution lease holder document invalid")
    try:
        return ClaimHolder(
            OwnerType(value["owner_type"]),
            value["owner_instance_id"],
            value["claimant_correlation_id"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError("execution lease holder fields invalid") from exc


def _decision_digest(decision: ChallengeCapabilityDecision) -> str:
    challenge = decision.challenge
    witness = decision.witness
    return canonical_hash(
        {
            "challenge_id": challenge.challenge_id,
            "target": challenge.target.value,
            "holder": _holder_document(challenge.holder),
            "task_id": challenge.task_id,
            "route_epoch": challenge.route_epoch,
            "canary_id": challenge.canary_id,
            "nonce": challenge.nonce,
            "expires_at": challenge.expires_at,
            "attestation_hash": witness.attestation_hash,
            "consumed_at": decision.consumed_at,
        }
    )


@dataclass(frozen=True)
class ExecutionLeaseRecord:
    lease_id: str
    provenance_digest: str
    storage_id: str
    claim_id: str
    holder: ClaimHolder
    target: CapabilityTarget
    task_id: str
    route_epoch: int
    canary_id: str
    nonce: str
    state: ExecutionLeaseState
    version: int
    capability_decision_digest: str
    capability_attestation_hash: str
    capability_transport_id: str
    created_at: str
    expires_at: str
    effect_authorized_at: str | None = None
    invocation_id: str | None = None
    invocation_attached_at: str | None = None
    terminal_identity_digest: str | None = None
    terminal_evidence_digest: str | None = None
    terminal_status: str | None = None
    terminal_reason: str | None = None
    terminal_at: str | None = None
    terminal_attested_at: str | None = None
    terminal_commit_receipt_digest: str | None = None
    terminal_committed_at: str | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.lease_id, "execution lease_id"),
            (self.provenance_digest, "execution provenance_digest"),
            (self.storage_id, "execution storage_id"),
            (self.capability_decision_digest, "capability decision digest"),
            (self.capability_attestation_hash, "capability attestation hash"),
        ):
            require_sha256(value, label)
        for value, label in (
            (self.claim_id, "execution claim_id"),
            (self.task_id, "execution task_id"),
            (self.canary_id, "execution canary_id"),
            (self.nonce, "execution nonce"),
            (self.capability_transport_id, "capability transport_id"),
        ):
            require_identifier(value, label)
        if not isinstance(self.holder, ClaimHolder) or not isinstance(self.target, CapabilityTarget):
            raise ValidationError("execution lease holder or target invalid")
        if not isinstance(self.route_epoch, int) or self.route_epoch < 1:
            raise ValidationError("execution route_epoch invalid")
        if self.version != self.state.version:
            raise ValidationError("execution lease version/state mismatch")
        created = parse_rfc3339_utc(self.created_at, "execution lease created_at")
        expires = parse_rfc3339_utc(self.expires_at, "execution lease expires_at")
        if expires <= created:
            raise ValidationError("execution lease lifetime invalid")
        self._validate_stage_fields()

    def _validate_stage_fields(self) -> None:
        stage = self.state.version
        if stage >= 2:
            if self.effect_authorized_at is None:
                raise ValidationError("effect-authorized lease requires time")
            parse_rfc3339_utc(self.effect_authorized_at, "effect authorized_at")
        elif self.effect_authorized_at is not None:
            raise ValidationError("capability-only lease cannot carry effect time")
        if stage >= 3:
            if self.invocation_id is None or self.invocation_attached_at is None:
                raise ValidationError("invocation-attached lease requires identity and time")
            require_identifier(self.invocation_id, "lease invocation_id")
            parse_rfc3339_utc(self.invocation_attached_at, "invocation attached_at")
        elif self.invocation_id is not None or self.invocation_attached_at is not None:
            raise ValidationError("pre-invocation lease cannot carry invocation")
        terminal_fields = (
            self.terminal_identity_digest,
            self.terminal_evidence_digest,
            self.terminal_status,
            self.terminal_reason,
            self.terminal_at,
            self.terminal_attested_at,
        )
        if stage >= 4:
            if any(value is None for value in terminal_fields):
                raise ValidationError("terminal-attested lease fields incomplete")
            require_sha256(self.terminal_identity_digest, "terminal identity digest")
            require_sha256(self.terminal_evidence_digest, "terminal evidence digest")
            require_identifier(self.terminal_status, "terminal status")
            require_identifier(self.terminal_reason, "terminal reason")
            parse_rfc3339_utc(self.terminal_at, "terminal_at")
            parse_rfc3339_utc(self.terminal_attested_at, "terminal attested_at")
        elif any(value is not None for value in terminal_fields):
            raise ValidationError("pre-terminal lease cannot carry terminal evidence")
        if stage >= 5:
            if self.terminal_commit_receipt_digest is None or self.terminal_committed_at is None:
                raise ValidationError("committed lease requires receipt and time")
            require_sha256(self.terminal_commit_receipt_digest, "terminal commit receipt digest")
            parse_rfc3339_utc(self.terminal_committed_at, "terminal committed_at")
        elif self.terminal_commit_receipt_digest is not None or self.terminal_committed_at is not None:
            raise ValidationError("uncommitted lease cannot carry commit receipt")

    def _payload_document(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "lease_id": self.lease_id,
            "provenance_digest": self.provenance_digest,
            "storage_id": self.storage_id,
            "claim_id": self.claim_id,
            "holder": _holder_document(self.holder),
            "target": self.target.value,
            "task_id": self.task_id,
            "route_epoch": self.route_epoch,
            "canary_id": self.canary_id,
            "nonce": self.nonce,
            "state": self.state.value,
            "version": self.version,
            "capability_decision_digest": self.capability_decision_digest,
            "capability_attestation_hash": self.capability_attestation_hash,
            "capability_transport_id": self.capability_transport_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "effect_authorized_at": self.effect_authorized_at,
            "invocation_id": self.invocation_id,
            "invocation_attached_at": self.invocation_attached_at,
            "terminal_identity_digest": self.terminal_identity_digest,
            "terminal_evidence_digest": self.terminal_evidence_digest,
            "terminal_status": self.terminal_status,
            "terminal_reason": self.terminal_reason,
            "terminal_at": self.terminal_at,
            "terminal_attested_at": self.terminal_attested_at,
            "terminal_commit_receipt_digest": self.terminal_commit_receipt_digest,
            "terminal_committed_at": self.terminal_committed_at,
        }

    def document(self) -> dict[str, object]:
        payload = self._payload_document()
        return {**payload, "record_hash": canonical_hash(payload)}

    @property
    def document_bytes(self) -> bytes:
        return json.dumps(self.document(), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_document_bytes(cls, payload: bytes, provenance: VerifiedAuthorityProvenance) -> "ExecutionLeaseRecord":
        try:
            value = strict_json_loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, ValidationError) as exc:
            raise ValidationError("execution lease document invalid") from exc
        if not isinstance(value, dict) or value.get("schema_version") != "1.0":
            raise ValidationError("execution lease schema unsupported")
        record_hash = value.pop("record_hash", None)
        if not isinstance(record_hash, str) or canonical_hash(value) != record_hash:
            raise ValidationError("execution lease record hash mismatch")
        try:
            record = cls(
                lease_id=value["lease_id"],
                provenance_digest=value["provenance_digest"],
                storage_id=value["storage_id"],
                claim_id=value["claim_id"],
                holder=_holder_from_document(value["holder"]),
                target=CapabilityTarget(value["target"]),
                task_id=value["task_id"],
                route_epoch=value["route_epoch"],
                canary_id=value["canary_id"],
                nonce=value["nonce"],
                state=ExecutionLeaseState(value["state"]),
                version=value["version"],
                capability_decision_digest=value["capability_decision_digest"],
                capability_attestation_hash=value["capability_attestation_hash"],
                capability_transport_id=value["capability_transport_id"],
                created_at=value["created_at"],
                expires_at=value["expires_at"],
                effect_authorized_at=value.get("effect_authorized_at"),
                invocation_id=value.get("invocation_id"),
                invocation_attached_at=value.get("invocation_attached_at"),
                terminal_identity_digest=value.get("terminal_identity_digest"),
                terminal_evidence_digest=value.get("terminal_evidence_digest"),
                terminal_status=value.get("terminal_status"),
                terminal_reason=value.get("terminal_reason"),
                terminal_at=value.get("terminal_at"),
                terminal_attested_at=value.get("terminal_attested_at"),
                terminal_commit_receipt_digest=value.get("terminal_commit_receipt_digest"),
                terminal_committed_at=value.get("terminal_committed_at"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("execution lease document fields invalid") from exc
        expected_key = DurableClaimKey(provenance)
        if record.provenance_digest != provenance.binding.digest or record.storage_id != expected_key.storage_id:
            raise ValidationError("execution lease provenance substitution")
        return record


@dataclass(frozen=True)
class ExecutionLeaseResult:
    code: ExecutionLeaseCode
    record: ExecutionLeaseRecord | None = None
    effect_permit: "LeaseEffectPermit | None" = None
    terminal_authorization: "TerminalMutationAuthorization | None" = None
    terminal_receipt: "TerminalCommitReceipt | None" = None


@dataclass(frozen=True, init=False)
class LeaseEffectPermit:
    permit_id: str
    lease_id: str
    lease_version: int
    provenance_digest: str
    storage_id: str
    claim_id: str
    holder: ClaimHolder
    target: CapabilityTarget
    issued_at: str

    def __init__(self, record: ExecutionLeaseRecord, *, _seal: object | None = None) -> None:
        if _seal is not _EFFECT_PERMIT_SEAL or record.state is not ExecutionLeaseState.EFFECT_AUTHORIZED:
            raise ValidationError("effect permit must be minted by the durable lease transition")
        for key, value in (
            ("lease_id", record.lease_id),
            ("lease_version", record.version),
            ("provenance_digest", record.provenance_digest),
            ("storage_id", record.storage_id),
            ("claim_id", record.claim_id),
            ("holder", record.holder),
            ("target", record.target),
            ("issued_at", record.effect_authorized_at),
        ):
            object.__setattr__(self, key, value)
        object.__setattr__(self, "permit_id", canonical_hash({
            "lease_id": record.lease_id,
            "lease_version": record.version,
            "claim_id": record.claim_id,
            "holder": _holder_document(record.holder),
            "target": record.target.value,
            "issued_at": record.effect_authorized_at,
        }))


@dataclass(frozen=True)
class RawManualExecutionIdentity:
    session_id: str
    owner_instance_id: str
    correlation_id: str
    transport_id: str
    observed_at: str

    def __post_init__(self) -> None:
        for value, label in ((self.session_id, "manual session_id"), (self.owner_instance_id, "manual owner"), (self.correlation_id, "manual correlation"), (self.transport_id, "manual transport")):
            require_identifier(value, label)
        parse_rfc3339_utc(self.observed_at, "manual observed_at")


@dataclass(frozen=True)
class RawAutomationExecutionIdentity:
    dispatch_id: str
    run_id: str
    callback_id: str
    callback_identity: str
    owner_instance_id: str
    correlation_id: str
    transport_id: str
    observed_at: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.dispatch_id, "automation dispatch_id"),
            (self.run_id, "automation run_id"),
            (self.callback_id, "automation callback_id"),
            (self.callback_identity, "automation callback_identity"),
            (self.owner_instance_id, "automation owner"),
            (self.correlation_id, "automation correlation"),
            (self.transport_id, "automation transport"),
        ):
            require_identifier(value, label)
        parse_rfc3339_utc(self.observed_at, "automation observed_at")


@dataclass(frozen=True)
class RawCliExecutionIdentity:
    launcher_id: str
    process_id: int
    process_start_token: str
    process_identity: str
    owner_instance_id: str
    correlation_id: str
    transport_id: str
    observed_at: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.launcher_id, "CLI launcher_id"),
            (self.process_identity, "CLI process_identity"),
            (self.owner_instance_id, "CLI owner"),
            (self.correlation_id, "CLI correlation"),
            (self.transport_id, "CLI transport"),
        ):
            require_identifier(value, label)
        require_sha256(self.process_start_token, "CLI process_start_token")
        if not isinstance(self.process_id, int) or self.process_id < 1:
            raise ValidationError("CLI process_id invalid")
        parse_rfc3339_utc(self.observed_at, "CLI observed_at")


RawExecutionIdentity: TypeAlias = RawManualExecutionIdentity | RawAutomationExecutionIdentity | RawCliExecutionIdentity


def _raw_identity_document(raw: RawExecutionIdentity) -> tuple[ExecutionIdentityKind, dict[str, object]]:
    if isinstance(raw, RawManualExecutionIdentity):
        return ExecutionIdentityKind.MANUAL_APP, {
            "session_id": raw.session_id,
            "owner_instance_id": raw.owner_instance_id,
            "correlation_id": raw.correlation_id,
            "transport_id": raw.transport_id,
            "observed_at": raw.observed_at,
        }
    if isinstance(raw, RawAutomationExecutionIdentity):
        return ExecutionIdentityKind.AUTOMATION, {
            "dispatch_id": raw.dispatch_id,
            "run_id": raw.run_id,
            "callback_id": raw.callback_id,
            "callback_identity": raw.callback_identity,
            "owner_instance_id": raw.owner_instance_id,
            "correlation_id": raw.correlation_id,
            "transport_id": raw.transport_id,
            "observed_at": raw.observed_at,
        }
    if isinstance(raw, RawCliExecutionIdentity):
        return ExecutionIdentityKind.CLI, {
            "launcher_id": raw.launcher_id,
            "process_id": raw.process_id,
            "process_start_token": raw.process_start_token,
            "process_identity": raw.process_identity,
            "owner_instance_id": raw.owner_instance_id,
            "correlation_id": raw.correlation_id,
            "transport_id": raw.transport_id,
            "observed_at": raw.observed_at,
        }
    raise ValidationError("unsupported raw execution identity")


@dataclass(frozen=True)
class RawTerminalObservation:
    lease_id: str
    claim_id: str
    invocation_id: str
    identity_digest: str
    terminal_status: str
    terminal_reason: str
    terminal_at: str
    log_hash: str
    cleanup_hash: str
    transport_id: str
    exit_code: int | None = None

    def __post_init__(self) -> None:
        require_sha256(self.lease_id, "terminal lease_id")
        require_sha256(self.identity_digest, "terminal identity_digest")
        require_sha256(self.log_hash, "terminal log_hash")
        require_sha256(self.cleanup_hash, "terminal cleanup_hash")
        for value, label in (
            (self.claim_id, "terminal claim_id"),
            (self.invocation_id, "terminal invocation_id"),
            (self.terminal_status, "terminal status"),
            (self.terminal_reason, "terminal reason"),
            (self.transport_id, "terminal transport_id"),
        ):
            require_identifier(value, label)
        parse_rfc3339_utc(self.terminal_at, "terminal_at")
        if self.exit_code is not None and not isinstance(self.exit_code, int):
            raise ValidationError("terminal exit_code invalid")

    def document(self) -> dict[str, object]:
        return dict(self.__dict__)


@dataclass(frozen=True, init=False)
class TransportCapturedIdentity:
    kind: ExecutionIdentityKind
    raw: RawExecutionIdentity
    source_id: str
    captured_at: str
    capture_digest: str

    def __init__(self, raw: RawExecutionIdentity, source_id: str, captured_at: str, *, _seal: object | None = None) -> None:
        if _seal is not _CAPTURE_SEAL:
            raise ValidationError("identity capture must be transport minted")
        kind, document = _raw_identity_document(raw)
        require_identifier(source_id, "identity source_id")
        parse_rfc3339_utc(captured_at, "identity captured_at")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "raw", raw)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "captured_at", captured_at)
        object.__setattr__(self, "capture_digest", canonical_hash({"kind": kind.value, "raw": document, "source_id": source_id, "captured_at": captured_at}))


@dataclass(frozen=True, init=False)
class TransportCapturedTerminal:
    raw: RawTerminalObservation
    source_id: str
    captured_at: str
    capture_digest: str

    def __init__(self, raw: RawTerminalObservation, source_id: str, captured_at: str, *, _seal: object | None = None) -> None:
        if _seal is not _CAPTURE_SEAL or not isinstance(raw, RawTerminalObservation):
            raise ValidationError("terminal capture must be transport minted")
        require_identifier(source_id, "terminal source_id")
        parse_rfc3339_utc(captured_at, "terminal captured_at")
        object.__setattr__(self, "raw", raw)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "captured_at", captured_at)
        object.__setattr__(self, "capture_digest", canonical_hash({"raw": raw.document(), "source_id": source_id, "captured_at": captured_at}))


class SyntheticExecutionTransport:
    """Synthetic capture source for deterministic tests only."""

    def __init__(self, transport_id: str, source_id: str, *, _seal: object | None = None) -> None:
        if _seal is not _TRANSPORT_SEAL:
            raise ValidationError("execution transport is composition-root only")
        require_identifier(transport_id, "execution transport_id")
        require_identifier(source_id, "execution source_id")
        self._transport_id = transport_id
        self._source_id = source_id

    def capture_identity(self, raw: RawExecutionIdentity, captured_at: str) -> TransportCapturedIdentity:
        _kind, document = _raw_identity_document(raw)
        if document["transport_id"] != self._transport_id:
            raise ValidationError("identity transport mismatch")
        return TransportCapturedIdentity(raw, self._source_id, captured_at, _seal=_CAPTURE_SEAL)

    def capture_terminal(self, raw: RawTerminalObservation, captured_at: str) -> TransportCapturedTerminal:
        if not isinstance(raw, RawTerminalObservation) or raw.transport_id != self._transport_id:
            raise ValidationError("terminal transport mismatch")
        return TransportCapturedTerminal(raw, self._source_id, captured_at, _seal=_CAPTURE_SEAL)


def _synthetic_execution_transport(transport_id: str, source_id: str) -> SyntheticExecutionTransport:
    return SyntheticExecutionTransport(transport_id, source_id, _seal=_TRANSPORT_SEAL)


@dataclass(frozen=True, init=False)
class AttestedExecutionIdentity:
    lease_id: str
    claim_id: str
    invocation_id: str
    holder: ClaimHolder
    target: CapabilityTarget
    kind: ExecutionIdentityKind
    transport_id: str
    source_id: str
    verifier_id: str
    native_identity: tuple[tuple[str, object], ...]
    capture_digest: str
    attested_at: str
    identity_digest: str

    def __init__(self, lease: ExecutionLeaseRecord, capture: TransportCapturedIdentity, verifier_id: str, attested_at: str, *, _seal: object | None = None) -> None:
        if _seal is not _IDENTITY_SEAL:
            raise ValidationError("execution identity must be verifier minted")
        if lease.state is not ExecutionLeaseState.INVOCATION_ATTACHED or lease.invocation_id is None:
            raise ValidationError("execution identity requires attached invocation lease")
        kind, document = _raw_identity_document(capture.raw)
        native = tuple(sorted(document.items()))
        for key, value in (
            ("lease_id", lease.lease_id),
            ("claim_id", lease.claim_id),
            ("invocation_id", lease.invocation_id),
            ("holder", lease.holder),
            ("target", lease.target),
            ("kind", kind),
            ("transport_id", document["transport_id"]),
            ("source_id", capture.source_id),
            ("verifier_id", verifier_id),
            ("native_identity", native),
            ("capture_digest", capture.capture_digest),
            ("attested_at", attested_at),
        ):
            object.__setattr__(self, key, value)
        object.__setattr__(self, "identity_digest", canonical_hash({
            "lease_id": lease.lease_id,
            "claim_id": lease.claim_id,
            "invocation_id": lease.invocation_id,
            "holder": _holder_document(lease.holder),
            "target": lease.target.value,
            "kind": kind.value,
            "transport_id": document["transport_id"],
            "source_id": capture.source_id,
            "verifier_id": verifier_id,
            "native_identity": dict(native),
            "capture_digest": capture.capture_digest,
            "attested_at": attested_at,
        }))


@dataclass(frozen=True, init=False)
class AttestedTerminalEvidence:
    lease_id: str
    claim_id: str
    invocation_id: str
    holder: ClaimHolder
    target: CapabilityTarget
    identity_kind: ExecutionIdentityKind
    identity_digest: str
    terminal_status: str
    terminal_reason: str
    terminal_at: str
    log_hash: str
    cleanup_hash: str
    exit_code: int | None
    transport_id: str
    source_id: str
    capture_digest: str
    attested_at: str
    evidence_digest: str

    def __init__(self, lease: ExecutionLeaseRecord, identity: AttestedExecutionIdentity, capture: TransportCapturedTerminal, attested_at: str, *, _seal: object | None = None) -> None:
        if _seal is not _TERMINAL_EVIDENCE_SEAL:
            raise ValidationError("terminal evidence must be verifier minted")
        raw = capture.raw
        for key, value in (
            ("lease_id", lease.lease_id),
            ("claim_id", lease.claim_id),
            ("invocation_id", lease.invocation_id),
            ("holder", lease.holder),
            ("target", lease.target),
            ("identity_kind", identity.kind),
            ("identity_digest", identity.identity_digest),
            ("terminal_status", raw.terminal_status),
            ("terminal_reason", raw.terminal_reason),
            ("terminal_at", raw.terminal_at),
            ("log_hash", raw.log_hash),
            ("cleanup_hash", raw.cleanup_hash),
            ("exit_code", raw.exit_code),
            ("transport_id", raw.transport_id),
            ("source_id", capture.source_id),
            ("capture_digest", capture.capture_digest),
            ("attested_at", attested_at),
        ):
            object.__setattr__(self, key, value)
        object.__setattr__(self, "evidence_digest", canonical_hash({
            "lease_id": lease.lease_id,
            "claim_id": lease.claim_id,
            "invocation_id": lease.invocation_id,
            "identity_digest": identity.identity_digest,
            "terminal": raw.document(),
            "source_id": capture.source_id,
            "capture_digest": capture.capture_digest,
            "attested_at": attested_at,
        }))


class ExecutionIdentityVerifier:
    """Synthetic verifier boundary; production must replace its trust root."""

    def __init__(self, verifier_id: str, trusted_source_id: str, *, _seal: object | None = None) -> None:
        if _seal is not _IDENTITY_VERIFIER_SEAL:
            raise ValidationError("execution identity verifier is composition-root only")
        require_identifier(verifier_id, "execution verifier_id")
        require_identifier(trusted_source_id, "trusted source_id")
        self._verifier_id = verifier_id
        self._trusted_source_id = trusted_source_id

    @staticmethod
    def _expected(kind: ExecutionIdentityKind) -> tuple[OwnerType, CapabilityTarget]:
        return {
            ExecutionIdentityKind.MANUAL_APP: (OwnerType.CURRENT_CODEX_APP_SESSION, CapabilityTarget.CODEX_APP),
            ExecutionIdentityKind.AUTOMATION: (OwnerType.APP_AUTOMATION_NEW_RUN, CapabilityTarget.CODEX_APP),
            ExecutionIdentityKind.CLI: (OwnerType.CODEX_CLI_PROCESS, CapabilityTarget.CODEX_CLI),
        }[kind]

    def attest_identity(self, lease: ExecutionLeaseRecord, capture: object, checked_at: str) -> AttestedExecutionIdentity:
        if not isinstance(capture, TransportCapturedIdentity) or capture.source_id != self._trusted_source_id:
            raise ValidationError("transport-captured execution identity required")
        if lease.state is not ExecutionLeaseState.INVOCATION_ATTACHED:
            raise ValidationError("identity attestation requires invocation-attached lease")
        kind, document = _raw_identity_document(capture.raw)
        expected_owner, expected_target = self._expected(kind)
        if lease.holder.owner_type is not expected_owner or lease.target is not expected_target:
            raise ValidationError("identity kind does not match lease owner or target")
        if document["owner_instance_id"] != lease.holder.owner_instance_id or document["correlation_id"] != lease.holder.claimant_correlation_id:
            raise ValidationError("identity is not cross-bound to claim holder")
        if document["transport_id"] != lease.capability_transport_id:
            raise ValidationError("identity transport differs from capability transport")
        checked = parse_rfc3339_utc(checked_at, "identity checked_at")
        observed = parse_rfc3339_utc(document["observed_at"], "identity observed_at")
        captured = parse_rfc3339_utc(capture.captured_at, "identity captured_at")
        if observed > captured or captured > checked:
            raise ValidationError("identity observation, capture, or verification order invalid")
        return AttestedExecutionIdentity(lease, capture, self._verifier_id, checked_at, _seal=_IDENTITY_SEAL)

    def attest_terminal(self, lease: ExecutionLeaseRecord, identity: object, capture: object, checked_at: str) -> AttestedTerminalEvidence:
        if not isinstance(identity, AttestedExecutionIdentity) or not isinstance(capture, TransportCapturedTerminal):
            raise ValidationError("attested identity and transport terminal capture required")
        if capture.source_id != self._trusted_source_id or identity.source_id != self._trusted_source_id or identity.verifier_id != self._verifier_id:
            raise ValidationError("terminal evidence source or verifier mismatch")
        raw = capture.raw
        if (
            identity.lease_id != lease.lease_id
            or identity.claim_id != lease.claim_id
            or identity.invocation_id != lease.invocation_id
            or identity.holder != lease.holder
            or identity.target is not lease.target
            or raw.lease_id != lease.lease_id
            or raw.claim_id != lease.claim_id
            or raw.invocation_id != lease.invocation_id
            or raw.identity_digest != identity.identity_digest
        ):
            raise ValidationError("terminal identity or lease binding mismatch")
        if raw.transport_id != identity.transport_id or raw.transport_id != lease.capability_transport_id:
            raise ValidationError("terminal transport binding mismatch")
        checked = parse_rfc3339_utc(checked_at, "terminal checked_at")
        terminal = parse_rfc3339_utc(raw.terminal_at, "terminal_at")
        captured = parse_rfc3339_utc(capture.captured_at, "terminal captured_at")
        if terminal > captured or captured > checked or checked >= parse_rfc3339_utc(lease.expires_at, "lease expires_at"):
            raise ValidationError("terminal observation or attestation outside lease lifetime")
        expected_status = {"completed", "failed", "timed_out"}
        if raw.terminal_status not in expected_status:
            raise ValidationError("terminal status unsupported")
        if identity.kind is ExecutionIdentityKind.CLI:
            if raw.terminal_status == "completed" and raw.exit_code != 0:
                raise ValidationError("successful CLI terminal requires zero exit code")
            if raw.terminal_status == "failed" and (raw.exit_code is None or raw.exit_code == 0):
                raise ValidationError("failed CLI terminal requires nonzero exit code")
            if raw.terminal_status == "timed_out" and raw.exit_code is not None:
                raise ValidationError("timed-out CLI terminal cannot assert exit code")
        elif raw.exit_code is not None:
            raise ValidationError("non-CLI terminal cannot assert process exit code")
        return AttestedTerminalEvidence(lease, identity, capture, checked_at, _seal=_TERMINAL_EVIDENCE_SEAL)


def _execution_identity_verifier(verifier_id: str, trusted_source_id: str) -> ExecutionIdentityVerifier:
    return ExecutionIdentityVerifier(verifier_id, trusted_source_id, _seal=_IDENTITY_VERIFIER_SEAL)


@dataclass(frozen=True, init=False)
class TerminalMutationAuthorization:
    authorization_id: str
    lease_id: str
    lease_version: int
    provenance_digest: str
    storage_id: str
    claim_id: str
    holder: ClaimHolder
    target: CapabilityTarget
    invocation_id: str
    identity_kind: ExecutionIdentityKind
    identity_digest: str
    evidence_digest: str
    terminal_state: DurableClaimState
    terminal_status: str
    terminal_reason: str
    terminal_at: str
    log_hash: str
    exit_code: int | None

    def __init__(self, record: ExecutionLeaseRecord, evidence: AttestedTerminalEvidence, *, _seal: object | None = None) -> None:
        if _seal is not _TERMINAL_AUTHORIZATION_SEAL or record.state is not ExecutionLeaseState.TERMINAL_ATTESTED:
            raise ValidationError("terminal authorization must be lease minted")
        state = {
            "completed": DurableClaimState.SUCCEEDED,
            "failed": DurableClaimState.FAILED,
            "timed_out": DurableClaimState.TIMED_OUT,
        }.get(evidence.terminal_status)
        if state is None:
            raise ValidationError("terminal status has no durable state")
        for key, value in (
            ("lease_id", record.lease_id),
            ("lease_version", record.version),
            ("provenance_digest", record.provenance_digest),
            ("storage_id", record.storage_id),
            ("claim_id", record.claim_id),
            ("holder", record.holder),
            ("target", record.target),
            ("invocation_id", record.invocation_id),
            ("identity_kind", evidence.identity_kind),
            ("identity_digest", evidence.identity_digest),
            ("evidence_digest", evidence.evidence_digest),
            ("terminal_state", state),
            ("terminal_status", evidence.terminal_status),
            ("terminal_reason", evidence.terminal_reason),
            ("terminal_at", evidence.terminal_at),
            ("log_hash", evidence.log_hash),
            ("exit_code", evidence.exit_code),
        ):
            object.__setattr__(self, key, value)
        object.__setattr__(self, "authorization_id", canonical_hash({
            "lease_id": record.lease_id,
            "lease_version": record.version,
            "claim_id": record.claim_id,
            "invocation_id": record.invocation_id,
            "identity_digest": evidence.identity_digest,
            "evidence_digest": evidence.evidence_digest,
            "terminal_state": state.value,
            "terminal_at": evidence.terminal_at,
        }))


@dataclass(frozen=True, init=False)
class TerminalCommitReceipt:
    receipt_digest: str
    lease_id: str
    claim_id: str
    invocation_id: str
    holder: ClaimHolder
    target: CapabilityTarget
    terminal_state: DurableClaimState
    terminal_status: str
    terminal_at: str
    terminal_reason: str
    identity_kind: ExecutionIdentityKind
    identity_digest: str
    evidence_digest: str
    evidence_type: ExecutionEvidenceType
    log_hash: str
    exit_code: int | None
    committed_at: str

    def __init__(self, record: ExecutionLeaseRecord, claim: DurableClaimRecord, authorization: TerminalMutationAuthorization, committed_at: str, *, _seal: object | None = None) -> None:
        if _seal is not _TERMINAL_RECEIPT_SEAL or record.state is not ExecutionLeaseState.TERMINAL_COMMITTED:
            raise ValidationError("terminal receipt must be committed-lease minted")
        evidence_type = {
            ExecutionIdentityKind.MANUAL_APP: ExecutionEvidenceType.CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION,
            ExecutionIdentityKind.AUTOMATION: ExecutionEvidenceType.APP_AUTOMATION_DISPATCHED_NEW_RUN,
            ExecutionIdentityKind.CLI: ExecutionEvidenceType.CODEX_CLI_PROCESS_INVOKED,
        }[authorization.identity_kind]
        digest = _terminal_receipt_digest(record, claim, authorization, committed_at)
        if record.terminal_commit_receipt_digest != digest:
            raise ValidationError("terminal receipt differs from committed lease")
        for key, value in (
            ("receipt_digest", digest),
            ("lease_id", record.lease_id),
            ("claim_id", claim.claim_id),
            ("invocation_id", claim.invocation_id),
            ("holder", claim.holder),
            ("target", record.target),
            ("terminal_state", claim.state),
            ("terminal_status", authorization.terminal_status),
            ("terminal_at", claim.terminal_at),
            ("terminal_reason", claim.terminal_reason),
            ("identity_kind", authorization.identity_kind),
            ("identity_digest", authorization.identity_digest),
            ("evidence_digest", authorization.evidence_digest),
            ("evidence_type", evidence_type),
            ("log_hash", authorization.log_hash),
            ("exit_code", authorization.exit_code),
            ("committed_at", committed_at),
        ):
            object.__setattr__(self, key, value)


def _terminal_receipt_digest(record: ExecutionLeaseRecord, claim: DurableClaimRecord, authorization: TerminalMutationAuthorization, committed_at: str) -> str:
    return canonical_hash({
        "lease_id": record.lease_id,
        "claim_id": claim.claim_id,
        "claim_state": claim.state.value,
        "invocation_id": claim.invocation_id,
        "terminal_at": claim.terminal_at,
        "terminal_reason": claim.terminal_reason,
        "identity_digest": authorization.identity_digest,
        "evidence_digest": authorization.evidence_digest,
        "committed_at": committed_at,
    })


@dataclass(frozen=True)
class OperationJournalEvent:
    phase: OperationPhase
    at: str
    detail_hash: str
    previous_hash: str | None
    event_hash: str

    @classmethod
    def mint(cls, phase: OperationPhase, at: str, detail_hash: str, previous_hash: str | None) -> "OperationJournalEvent":
        parse_rfc3339_utc(at, "operation event at")
        require_sha256(detail_hash, "operation detail hash")
        if previous_hash is not None:
            require_sha256(previous_hash, "operation previous hash")
        event_hash = canonical_hash({"phase": phase.value, "at": at, "detail_hash": detail_hash, "previous_hash": previous_hash})
        return cls(phase, at, detail_hash, previous_hash, event_hash)

    def validate(self, expected_previous: str | None) -> None:
        if self.previous_hash != expected_previous:
            raise ValidationError("operation journal chain mismatch")
        expected = canonical_hash({"phase": self.phase.value, "at": self.at, "detail_hash": self.detail_hash, "previous_hash": self.previous_hash})
        if expected != self.event_hash:
            raise ValidationError("operation journal event hash mismatch")


@dataclass(frozen=True)
class OperationJournalRecord:
    operation_id: str
    lease_id: str
    claim_id: str
    authorization_id: str
    events: tuple[OperationJournalEvent, ...]

    def __post_init__(self) -> None:
        for value, label in ((self.operation_id, "operation_id"), (self.lease_id, "operation lease_id"), (self.authorization_id, "operation authorization_id")):
            require_sha256(value, label)
        require_identifier(self.claim_id, "operation claim_id")
        if not self.events or self.events[0].phase is not OperationPhase.REQUESTED:
            raise ValidationError("operation journal must start with REQUESTED")
        previous = None
        for index, event in enumerate(self.events):
            event.validate(previous)
            if index > 0 and event.phase not in _JOURNAL_TRANSITIONS.get(self.events[index - 1].phase, set()):
                raise ValidationError("operation journal transition invalid")
            previous = event.event_hash

    @property
    def phase(self) -> OperationPhase:
        return self.events[-1].phase

    def document(self) -> dict[str, object]:
        payload = {
            "schema_version": "1.0",
            "operation_id": self.operation_id,
            "lease_id": self.lease_id,
            "claim_id": self.claim_id,
            "authorization_id": self.authorization_id,
            "events": [
                {"phase": event.phase.value, "at": event.at, "detail_hash": event.detail_hash, "previous_hash": event.previous_hash, "event_hash": event.event_hash}
                for event in self.events
            ],
        }
        return {**payload, "record_hash": canonical_hash(payload)}

    @property
    def document_bytes(self) -> bytes:
        return json.dumps(self.document(), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_document_bytes(cls, payload: bytes) -> "OperationJournalRecord":
        try:
            value = strict_json_loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, ValidationError) as exc:
            raise ValidationError("operation journal document invalid") from exc
        if not isinstance(value, dict) or value.get("schema_version") != "1.0":
            raise ValidationError("operation journal schema unsupported")
        record_hash = value.pop("record_hash", None)
        if not isinstance(record_hash, str) or canonical_hash(value) != record_hash:
            raise ValidationError("operation journal record hash mismatch")
        try:
            events = tuple(
                OperationJournalEvent(OperationPhase(item["phase"]), item["at"], item["detail_hash"], item.get("previous_hash"), item["event_hash"])
                for item in value["events"]
            )
            return cls(value["operation_id"], value["lease_id"], value["claim_id"], value["authorization_id"], events)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("operation journal fields invalid") from exc


@dataclass(frozen=True, init=False)
class JournaledTerminalMutationPermit:
    """One terminal mutation permit minted only after journal REQUESTED."""

    authorization: TerminalMutationAuthorization
    operation_id: str
    requested_event_hash: str
    minted_at: str
    permit_digest: str

    def __init__(
        self,
        authorization: TerminalMutationAuthorization,
        journal: OperationJournalRecord,
        minted_at: str,
        *,
        _seal: object | None = None,
    ) -> None:
        if _seal is not _JOURNALED_MUTATION_SEAL:
            raise ValidationError("journaled terminal mutation permit must be lease-manager minted")
        if journal.phase is not OperationPhase.REQUESTED or journal.authorization_id != authorization.authorization_id or journal.lease_id != authorization.lease_id:
            raise ValidationError("journaled terminal mutation permit binding invalid")
        parse_rfc3339_utc(minted_at, "journaled mutation minted_at")
        object.__setattr__(self, "authorization", authorization)
        object.__setattr__(self, "operation_id", journal.operation_id)
        object.__setattr__(self, "requested_event_hash", journal.events[-1].event_hash)
        object.__setattr__(self, "minted_at", minted_at)
        object.__setattr__(self, "permit_digest", canonical_hash({
            "authorization_id": authorization.authorization_id,
            "operation_id": journal.operation_id,
            "requested_event_hash": journal.events[-1].event_hash,
            "minted_at": minted_at,
        }))


class DurableOperationJournal:
    def __init__(self, namespace: str, gateway: RevisionedObjectGateway) -> None:
        require_identifier(namespace, "operation journal namespace")
        self._namespace = namespace
        self._gateway = gateway

    def _object_id(self, operation_id: str) -> str:
        require_sha256(operation_id, "operation_id")
        return f"{self._namespace}.operation.{operation_id}"

    def read(self, operation_id: str) -> OperationJournalRecord | None:
        snapshot = self._gateway.read(self._object_id(operation_id))
        return None if snapshot.payload is None else OperationJournalRecord.from_document_bytes(snapshot.payload)

    def begin(self, authorization: TerminalMutationAuthorization, at: str) -> OperationJournalRecord:
        operation_id = canonical_hash({"lease_id": authorization.lease_id, "authorization_id": authorization.authorization_id})
        detail_hash = canonical_hash({"event": "terminal_mutation_requested", "authorization_id": authorization.authorization_id})
        record = OperationJournalRecord(operation_id, authorization.lease_id, authorization.claim_id, authorization.authorization_id, (OperationJournalEvent.mint(OperationPhase.REQUESTED, at, detail_hash, None),))
        object_id = self._object_id(operation_id)
        snapshot = self._gateway.read(object_id)
        if snapshot.payload is not None:
            existing = OperationJournalRecord.from_document_bytes(snapshot.payload)
            if existing.lease_id != authorization.lease_id or existing.authorization_id != authorization.authorization_id:
                raise ValidationError("operation journal binding mismatch")
            return existing
        write = self._gateway.compare_and_set(object_id, None, record.document_bytes)
        if not write.applied:
            existing = self.read(operation_id)
            if existing is None:
                raise ValidationError("operation journal create conflict")
            return existing
        return record

    def advance(self, operation_id: str, phase: OperationPhase, at: str, detail: str) -> OperationJournalRecord:
        require_identifier(detail, "operation journal detail")
        object_id = self._object_id(operation_id)
        snapshot = self._gateway.read(object_id)
        if snapshot.payload is None:
            raise ValidationError("operation journal not found")
        current = OperationJournalRecord.from_document_bytes(snapshot.payload)
        if current.phase is phase:
            return current
        if phase not in _JOURNAL_TRANSITIONS.get(current.phase, set()):
            raise ValidationError("operation journal illegal transition")
        event = OperationJournalEvent.mint(phase, at, canonical_hash({"detail": detail}), current.events[-1].event_hash)
        updated = replace(current, events=current.events + (event,))
        write = self._gateway.compare_and_set(object_id, snapshot.revision, updated.document_bytes)
        if not write.applied:
            raise ValidationError("operation journal CAS conflict")
        return updated


class DurableExecutionLeaseAuthority:
    def __init__(self, namespace: str, gateway: RevisionedObjectGateway, claim_authority: DurableClaimAuthority) -> None:
        require_identifier(namespace, "execution lease namespace")
        if not isinstance(claim_authority, DurableClaimAuthority):
            raise ValidationError("execution lease requires durable claim authority")
        self._namespace = namespace
        self._gateway = gateway
        self._claim_authority = claim_authority
        self._journal = DurableOperationJournal(namespace, gateway)

    def _object_id(self, storage_id: str) -> str:
        require_sha256(storage_id, "lease storage_id")
        return f"{self._namespace}.lease.{storage_id}"

    def _read_snapshot(self, provenance: VerifiedAuthorityProvenance) -> tuple[object, ExecutionLeaseRecord | None]:
        storage_id = DurableClaimKey(provenance).storage_id
        snapshot = self._gateway.read(self._object_id(storage_id))
        record = None if snapshot.payload is None else ExecutionLeaseRecord.from_document_bytes(snapshot.payload, provenance)
        return snapshot, record

    def read(self, provenance: VerifiedAuthorityProvenance, lease_id: str) -> ExecutionLeaseResult:
        try:
            _snapshot, record = self._read_snapshot(provenance)
        except ValidationError:
            return ExecutionLeaseResult(ExecutionLeaseCode.TAMPERED)
        except Exception:
            return ExecutionLeaseResult(ExecutionLeaseCode.AUTHORITY_UNAVAILABLE)
        if record is None:
            return ExecutionLeaseResult(ExecutionLeaseCode.LEASE_NOT_FOUND)
        if record.lease_id != lease_id:
            return ExecutionLeaseResult(ExecutionLeaseCode.BINDING_MISMATCH, record)
        code = ExecutionLeaseCode.ALREADY_COMMITTED if record.state is ExecutionLeaseState.TERMINAL_COMMITTED else ExecutionLeaseCode.ALREADY_EXISTS
        return ExecutionLeaseResult(code, record)

    @staticmethod
    def _matches_claim(record: ExecutionLeaseRecord, claim: DurableClaimRecord) -> bool:
        return (
            record.provenance_digest == claim.provenance.digest
            and record.storage_id == claim.key.storage_id
            and record.claim_id == claim.claim_id
            and record.holder == claim.holder
            and record.task_id == claim.provenance.task_id
            and record.route_epoch == claim.provenance.route_epoch
            and record.canary_id == claim.provenance.canary_id
            and record.nonce == claim.provenance.nonce
        )

    def attest_capability(
        self,
        provenance: VerifiedAuthorityProvenance,
        claim_id: str,
        holder: ClaimHolder,
        target: CapabilityTarget,
        capability: object,
        attested_at: str,
    ) -> ExecutionLeaseResult:
        if not isinstance(capability, ChallengeCapabilityDecision) or capability.witness.status is not CapabilityStatus.SUPPORTED:
            return ExecutionLeaseResult(ExecutionLeaseCode.CAPABILITY_REQUIRED)
        claim_result = self._claim_authority.read(provenance)
        claim = claim_result.record
        if claim is None:
            return ExecutionLeaseResult(ExecutionLeaseCode.CLAIM_NOT_FOUND)
        challenge = capability.challenge
        witness = capability.witness
        if (
            claim.state is not DurableClaimState.CLAIMED
            or claim.invocation_id is not None
            or claim.claim_id != claim_id
            or claim.holder != holder
            or challenge.holder != holder
            or challenge.target is not target
            or witness.target is not target
            or challenge.task_id != claim.provenance.task_id
            or challenge.route_epoch != claim.provenance.route_epoch
            or challenge.canary_id != claim.provenance.canary_id
            or challenge.nonce != claim.provenance.nonce
        ):
            return ExecutionLeaseResult(ExecutionLeaseCode.BINDING_MISMATCH)
        checked = parse_rfc3339_utc(attested_at, "capability attested_at")
        if checked < parse_rfc3339_utc(capability.consumed_at, "capability consumed_at") or checked >= parse_rfc3339_utc(challenge.expires_at, "challenge expires_at"):
            return ExecutionLeaseResult(ExecutionLeaseCode.LEASE_EXPIRED)
        approval_expiry = parse_rfc3339_utc(provenance.binding.expires_at, "approval expires_at")
        challenge_expiry = parse_rfc3339_utc(challenge.expires_at, "challenge expires_at")
        expires_at = challenge.expires_at if challenge_expiry <= approval_expiry else provenance.binding.expires_at
        decision_digest = _decision_digest(capability)
        lease_id = canonical_hash({
            "provenance_digest": claim.provenance.digest,
            "storage_id": claim.key.storage_id,
            "claim_id": claim.claim_id,
            "holder": _holder_document(holder),
            "target": target.value,
            "decision_digest": decision_digest,
        })
        record = ExecutionLeaseRecord(
            lease_id=lease_id,
            provenance_digest=claim.provenance.digest,
            storage_id=claim.key.storage_id,
            claim_id=claim.claim_id,
            holder=holder,
            target=target,
            task_id=claim.provenance.task_id,
            route_epoch=claim.provenance.route_epoch,
            canary_id=claim.provenance.canary_id,
            nonce=claim.provenance.nonce,
            state=ExecutionLeaseState.CAPABILITY_ATTESTED,
            version=1,
            capability_decision_digest=decision_digest,
            capability_attestation_hash=witness.attestation_hash,
            capability_transport_id=witness.transport_id,
            created_at=attested_at,
            expires_at=expires_at,
        )
        try:
            object_id = self._object_id(record.storage_id)
            snapshot = self._gateway.read(object_id)
            if snapshot.payload is not None:
                existing = ExecutionLeaseRecord.from_document_bytes(snapshot.payload, provenance)
                return ExecutionLeaseResult(ExecutionLeaseCode.ALREADY_EXISTS, existing)
            write = self._gateway.compare_and_set(object_id, None, record.document_bytes)
            return ExecutionLeaseResult(ExecutionLeaseCode.CAPABILITY_ATTESTED if write.applied else ExecutionLeaseCode.CAS_CONFLICT, record if write.applied else None)
        except ValidationError:
            return ExecutionLeaseResult(ExecutionLeaseCode.TAMPERED)
        except Exception:
            return ExecutionLeaseResult(ExecutionLeaseCode.AUTHORITY_UNAVAILABLE)

    def _transition(
        self,
        provenance: VerifiedAuthorityProvenance,
        lease_id: str,
        expected: ExecutionLeaseState,
        new_state: ExecutionLeaseState,
        checked_at: str,
        **changes: object,
    ) -> ExecutionLeaseResult:
        try:
            snapshot, current = self._read_snapshot(provenance)
        except ValidationError:
            return ExecutionLeaseResult(ExecutionLeaseCode.TAMPERED)
        except Exception:
            return ExecutionLeaseResult(ExecutionLeaseCode.AUTHORITY_UNAVAILABLE)
        if current is None:
            return ExecutionLeaseResult(ExecutionLeaseCode.LEASE_NOT_FOUND)
        if current.lease_id != lease_id:
            return ExecutionLeaseResult(ExecutionLeaseCode.BINDING_MISMATCH, current)
        if current.state is not expected or new_state.version != expected.version + 1:
            return ExecutionLeaseResult(ExecutionLeaseCode.ILLEGAL_TRANSITION, current)
        checked = parse_rfc3339_utc(checked_at, "lease transition checked_at")
        if expected.version < ExecutionLeaseState.TERMINAL_ATTESTED.version and checked >= parse_rfc3339_utc(current.expires_at, "lease expires_at"):
            return ExecutionLeaseResult(ExecutionLeaseCode.LEASE_EXPIRED, current)
        updated = replace(current, state=new_state, version=new_state.version, **changes)
        try:
            write = self._gateway.compare_and_set(self._object_id(current.storage_id), snapshot.revision, updated.document_bytes)
        except Exception:
            return ExecutionLeaseResult(ExecutionLeaseCode.AUTHORITY_UNAVAILABLE, current)
        if not write.applied:
            return ExecutionLeaseResult(ExecutionLeaseCode.CAS_CONFLICT, current)
        code = {
            ExecutionLeaseState.EFFECT_AUTHORIZED: ExecutionLeaseCode.EFFECT_AUTHORIZED,
            ExecutionLeaseState.INVOCATION_ATTACHED: ExecutionLeaseCode.INVOCATION_ATTACHED,
            ExecutionLeaseState.TERMINAL_ATTESTED: ExecutionLeaseCode.TERMINAL_ATTESTED,
            ExecutionLeaseState.TERMINAL_COMMITTED: ExecutionLeaseCode.TERMINAL_COMMITTED,
        }[new_state]
        return ExecutionLeaseResult(code, updated)

    def authorize_effect(self, provenance: VerifiedAuthorityProvenance, lease_id: str, holder: ClaimHolder, target: CapabilityTarget, authorized_at: str) -> ExecutionLeaseResult:
        current = self.read(provenance, lease_id)
        record = current.record
        if record is None:
            return current
        claim = self._claim_authority.read(provenance).record
        if claim is None or not self._matches_claim(record, claim) or holder != record.holder or target is not record.target or claim.state is not DurableClaimState.CLAIMED or claim.invocation_id is not None:
            return ExecutionLeaseResult(ExecutionLeaseCode.BINDING_MISMATCH, record)
        transitioned = self._transition(provenance, lease_id, ExecutionLeaseState.CAPABILITY_ATTESTED, ExecutionLeaseState.EFFECT_AUTHORIZED, authorized_at, effect_authorized_at=authorized_at)
        if transitioned.code is ExecutionLeaseCode.EFFECT_AUTHORIZED:
            permit = LeaseEffectPermit(transitioned.record, _seal=_EFFECT_PERMIT_SEAL)
            return replace(transitioned, effect_permit=permit)
        return transitioned

    def attach_invocation(self, provenance: VerifiedAuthorityProvenance, permit: object, invocation_id: str, attached_at: str) -> ExecutionLeaseResult:
        try:
            require_identifier(invocation_id, "execution invocation_id")
        except ValidationError:
            return ExecutionLeaseResult(ExecutionLeaseCode.INVOCATION_INVALID)
        if not isinstance(permit, LeaseEffectPermit):
            return ExecutionLeaseResult(ExecutionLeaseCode.BINDING_MISMATCH)
        current = self.read(provenance, permit.lease_id)
        record = current.record
        if record is None:
            return current
        if (
            record.state is not ExecutionLeaseState.EFFECT_AUTHORIZED
            or permit.lease_version != record.version
            or permit.provenance_digest != record.provenance_digest
            or permit.storage_id != record.storage_id
            or permit.claim_id != record.claim_id
            or permit.holder != record.holder
            or permit.target is not record.target
        ):
            return ExecutionLeaseResult(ExecutionLeaseCode.BINDING_MISMATCH, record)
        attached = self._claim_authority.attach_invocation_with_effect_permit(provenance, permit, invocation_id)
        if attached.code not in {DurableClaimResultCode.INVOCATION_ATTACHED, DurableClaimResultCode.DUPLICATE_INVOCATION}:
            code = ExecutionLeaseCode.INVOCATION_MISMATCH if attached.code is DurableClaimResultCode.INVOCATION_MISMATCH else ExecutionLeaseCode.CLAIM_NOT_APPLIED
            return ExecutionLeaseResult(code, record)
        transitioned = self._transition(provenance, permit.lease_id, ExecutionLeaseState.EFFECT_AUTHORIZED, ExecutionLeaseState.INVOCATION_ATTACHED, attached_at, invocation_id=invocation_id, invocation_attached_at=attached_at)
        return transitioned

    def attest_terminal(self, provenance: VerifiedAuthorityProvenance, evidence: object, attested_at: str) -> ExecutionLeaseResult:
        if not isinstance(evidence, AttestedTerminalEvidence):
            return ExecutionLeaseResult(ExecutionLeaseCode.TERMINAL_EVIDENCE_REQUIRED)
        current = self.read(provenance, evidence.lease_id)
        record = current.record
        if record is None:
            return current
        claim = self._claim_authority.read(provenance).record
        if claim is None:
            return ExecutionLeaseResult(ExecutionLeaseCode.CLAIM_NOT_FOUND, record)
        from .durable_challenge import validate_owner_terminal_evidence
        try:
            validate_owner_terminal_evidence(claim, record, evidence)
        except ValidationError:
            return ExecutionLeaseResult(ExecutionLeaseCode.BINDING_MISMATCH, record)
        if (
            record.state is not ExecutionLeaseState.INVOCATION_ATTACHED
            or evidence.claim_id != record.claim_id
            or evidence.invocation_id != record.invocation_id
            or evidence.holder != record.holder
            or evidence.target is not record.target
            or evidence.transport_id != record.capability_transport_id
        ):
            return ExecutionLeaseResult(ExecutionLeaseCode.BINDING_MISMATCH, record)
        transitioned = self._transition(
            provenance,
            record.lease_id,
            ExecutionLeaseState.INVOCATION_ATTACHED,
            ExecutionLeaseState.TERMINAL_ATTESTED,
            attested_at,
            terminal_identity_digest=evidence.identity_digest,
            terminal_evidence_digest=evidence.evidence_digest,
            terminal_status=evidence.terminal_status,
            terminal_reason=evidence.terminal_reason,
            terminal_at=evidence.terminal_at,
            terminal_attested_at=attested_at,
        )
        if transitioned.code is ExecutionLeaseCode.TERMINAL_ATTESTED:
            authorization = TerminalMutationAuthorization(transitioned.record, evidence, _seal=_TERMINAL_AUTHORIZATION_SEAL)
            return replace(transitioned, terminal_authorization=authorization)
        return transitioned

    @staticmethod
    def _claim_matches_authorization(claim: DurableClaimRecord, authorization: TerminalMutationAuthorization) -> bool:
        return (
            claim.claim_id == authorization.claim_id
            and claim.holder == authorization.holder
            and claim.invocation_id == authorization.invocation_id
            and claim.state is authorization.terminal_state
            and claim.terminal_at == authorization.terminal_at
            and claim.terminal_reason == authorization.terminal_reason
        )

    def _commit_lease(self, provenance: VerifiedAuthorityProvenance, authorization: TerminalMutationAuthorization, claim: DurableClaimRecord, committed_at: str) -> ExecutionLeaseResult:
        current = self.read(provenance, authorization.lease_id)
        if current.record is None:
            return current
        if current.record.state is ExecutionLeaseState.TERMINAL_COMMITTED:
            receipt = TerminalCommitReceipt(current.record, claim, authorization, current.record.terminal_committed_at, _seal=_TERMINAL_RECEIPT_SEAL)
            return ExecutionLeaseResult(ExecutionLeaseCode.ALREADY_COMMITTED, current.record, terminal_receipt=receipt)
        if current.record.state is not ExecutionLeaseState.TERMINAL_ATTESTED:
            return ExecutionLeaseResult(ExecutionLeaseCode.ILLEGAL_TRANSITION, current.record)
        receipt_digest = _terminal_receipt_digest(current.record, claim, authorization, committed_at)
        transitioned = self._transition(
            provenance,
            authorization.lease_id,
            ExecutionLeaseState.TERMINAL_ATTESTED,
            ExecutionLeaseState.TERMINAL_COMMITTED,
            committed_at,
            terminal_commit_receipt_digest=receipt_digest,
            terminal_committed_at=committed_at,
        )
        if transitioned.code is not ExecutionLeaseCode.TERMINAL_COMMITTED:
            return transitioned
        receipt = TerminalCommitReceipt(transitioned.record, claim, authorization, committed_at, _seal=_TERMINAL_RECEIPT_SEAL)
        return replace(transitioned, terminal_receipt=receipt)

    def finalize_with_attested_terminal(self, provenance: VerifiedAuthorityProvenance, authorization: object, committed_at: str) -> ExecutionLeaseResult:
        if not isinstance(authorization, TerminalMutationAuthorization):
            return ExecutionLeaseResult(ExecutionLeaseCode.TERMINAL_EVIDENCE_REQUIRED)
        current = self.read(provenance, authorization.lease_id)
        record = current.record
        if record is None:
            return current
        binding_matches = (
            authorization.lease_version == ExecutionLeaseState.TERMINAL_ATTESTED.version
            and authorization.provenance_digest == record.provenance_digest
            and authorization.storage_id == record.storage_id
            and authorization.claim_id == record.claim_id
            and authorization.holder == record.holder
            and authorization.target is record.target
            and authorization.invocation_id == record.invocation_id
            and authorization.identity_digest == record.terminal_identity_digest
            and authorization.evidence_digest == record.terminal_evidence_digest
            and authorization.terminal_status == record.terminal_status
            and authorization.terminal_reason == record.terminal_reason
            and authorization.terminal_at == record.terminal_at
        )
        if not binding_matches:
            return ExecutionLeaseResult(ExecutionLeaseCode.BINDING_MISMATCH, record)
        if record.state is ExecutionLeaseState.TERMINAL_COMMITTED:
            claim = self._claim_authority.read(provenance).record
            if claim is None or not self._claim_matches_authorization(claim, authorization):
                return ExecutionLeaseResult(ExecutionLeaseCode.RECONCILIATION_REQUIRED, record)
            receipt = TerminalCommitReceipt(record, claim, authorization, record.terminal_committed_at, _seal=_TERMINAL_RECEIPT_SEAL)
            return ExecutionLeaseResult(ExecutionLeaseCode.ALREADY_COMMITTED, record, terminal_receipt=receipt)
        if record.state is not ExecutionLeaseState.TERMINAL_ATTESTED:
            return ExecutionLeaseResult(ExecutionLeaseCode.ILLEGAL_TRANSITION, record)
        journal = self._journal.begin(authorization, committed_at)
        if journal.phase is not OperationPhase.REQUESTED:
            return self.reconcile_terminal(provenance, authorization, committed_at)
        mutation_permit = JournaledTerminalMutationPermit(authorization, journal, committed_at, _seal=_JOURNALED_MUTATION_SEAL)
        result = self._claim_authority.finalize_with_attested_terminal(provenance, mutation_permit)
        if result.record is not None and self._claim_matches_authorization(result.record, authorization):
            self._journal.advance(journal.operation_id, OperationPhase.CLAIM_APPLIED, committed_at, "claim_terminal_confirmed")
            committed = self._commit_lease(provenance, authorization, result.record, committed_at)
            if committed.code in {ExecutionLeaseCode.TERMINAL_COMMITTED, ExecutionLeaseCode.ALREADY_COMMITTED}:
                self._journal.advance(journal.operation_id, OperationPhase.TERMINAL_COMMITTED, committed_at, "lease_terminal_committed")
                return committed
            if committed.code in {ExecutionLeaseCode.AUTHORITY_UNAVAILABLE, ExecutionLeaseCode.CAS_CONFLICT}:
                self._journal.advance(journal.operation_id, OperationPhase.RECONCILIATION_REQUIRED, committed_at, "lease_commit_response_or_cas_requires_reread")
                return ExecutionLeaseResult(ExecutionLeaseCode.RECONCILIATION_REQUIRED, record)
            return committed
        if result.code is DurableClaimResultCode.AUTHORITY_UNAVAILABLE:
            self._journal.advance(journal.operation_id, OperationPhase.RESPONSE_LOST_UNKNOWN, committed_at, "claim_response_unavailable")
            self._journal.advance(journal.operation_id, OperationPhase.RECONCILIATION_REQUIRED, committed_at, "durable_reread_required")
            return ExecutionLeaseResult(ExecutionLeaseCode.RECONCILIATION_REQUIRED, record)
        if result.code is DurableClaimResultCode.CAS_CONFLICT:
            self._journal.advance(journal.operation_id, OperationPhase.CAS_CONFLICT, committed_at, "claim_cas_conflict")
            return ExecutionLeaseResult(ExecutionLeaseCode.CAS_CONFLICT, record)
        self._journal.advance(journal.operation_id, OperationPhase.CLAIM_NOT_APPLIED, committed_at, "claim_terminal_not_applied")
        return ExecutionLeaseResult(ExecutionLeaseCode.CLAIM_NOT_APPLIED, record)

    def reconcile_terminal(self, provenance: VerifiedAuthorityProvenance, authorization: object, reconciled_at: str) -> ExecutionLeaseResult:
        if not isinstance(authorization, TerminalMutationAuthorization):
            return ExecutionLeaseResult(ExecutionLeaseCode.TERMINAL_EVIDENCE_REQUIRED)
        journal = self._journal.begin(authorization, reconciled_at)
        lease_result = self.read(provenance, authorization.lease_id)
        record = lease_result.record
        claim = self._claim_authority.read(provenance).record
        if record is None or claim is None:
            return ExecutionLeaseResult(ExecutionLeaseCode.RECONCILIATION_REQUIRED, record)
        if record.state is ExecutionLeaseState.TERMINAL_COMMITTED and self._claim_matches_authorization(claim, authorization):
            if journal.phase is OperationPhase.RECONCILIATION_REQUIRED:
                journal = self._journal.advance(journal.operation_id, OperationPhase.LEASE_COMMITTED_RESPONSE_LOST, reconciled_at, "lease_commit_found_after_response_loss")
                journal = self._journal.advance(journal.operation_id, OperationPhase.RECONCILED, reconciled_at, "claim_and_committed_lease_reconciled")
                self._journal.advance(journal.operation_id, OperationPhase.TERMINAL_COMMITTED, reconciled_at, "terminal_commit_receipt_recovered")
            receipt = TerminalCommitReceipt(record, claim, authorization, record.terminal_committed_at, _seal=_TERMINAL_RECEIPT_SEAL)
            return ExecutionLeaseResult(ExecutionLeaseCode.ALREADY_COMMITTED, record, terminal_receipt=receipt)
        if journal.phase is OperationPhase.CLAIM_APPLIED:
            journal = self._journal.advance(journal.operation_id, OperationPhase.RECONCILIATION_REQUIRED, reconciled_at, "lease_commit_reconciliation_required")
        if journal.phase is not OperationPhase.RECONCILIATION_REQUIRED:
            return ExecutionLeaseResult(ExecutionLeaseCode.ILLEGAL_TRANSITION, record)
        if not self._claim_matches_authorization(claim, authorization):
            self._journal.advance(journal.operation_id, OperationPhase.CLAIM_NOT_APPLIED, reconciled_at, "durable_claim_not_terminal")
            return ExecutionLeaseResult(ExecutionLeaseCode.CLAIM_NOT_APPLIED, record)
        self._journal.advance(journal.operation_id, OperationPhase.CLAIM_APPLIED_RESPONSE_LOST, reconciled_at, "claim_terminal_found_after_restart")
        self._journal.advance(journal.operation_id, OperationPhase.RECONCILED, reconciled_at, "claim_and_lease_reconciled")
        committed = self._commit_lease(provenance, authorization, claim, reconciled_at)
        if committed.code in {ExecutionLeaseCode.TERMINAL_COMMITTED, ExecutionLeaseCode.ALREADY_COMMITTED}:
            self._journal.advance(journal.operation_id, OperationPhase.TERMINAL_COMMITTED, reconciled_at, "lease_terminal_committed_after_recovery")
        return committed
