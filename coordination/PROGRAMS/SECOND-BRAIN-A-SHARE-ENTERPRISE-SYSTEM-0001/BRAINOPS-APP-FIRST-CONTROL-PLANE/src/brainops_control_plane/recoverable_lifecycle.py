"""E47 restart-safe synthetic execution lifecycle.

The module deliberately models an offline control-plane contract.  It does not
claim a production trust root.  Its value is narrower and testable: every
positive durable transition stores a request-bound receipt before its result is
trusted, so a restart can distinguish an identical retry from a substituted
request without repeating an already-applied mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json

from .durable_authority import ClaimHolder, RevisionedObjectGateway
from .execution_evidence import CapabilityTarget
from .models import ValidationError, parse_rfc3339_utc, require_identifier, require_sha256, strict_json_loads


class LifecycleStage(str, Enum):
    CAPABILITY_ATTESTED = "CAPABILITY_ATTESTED"
    EFFECT_AUTHORIZED = "EFFECT_AUTHORIZED"
    CLAIM_INVOCATION_ATTACHED = "CLAIM_INVOCATION_ATTACHED"
    LEASE_INVOCATION_ATTACHED = "LEASE_INVOCATION_ATTACHED"
    TERMINAL_ATTESTED = "TERMINAL_ATTESTED"
    CLAIM_TERMINAL_COMMITTED = "CLAIM_TERMINAL_COMMITTED"
    LEASE_TERMINAL_COMMITTED = "LEASE_TERMINAL_COMMITTED"

    @property
    def order(self) -> int:
        return _STAGE_ORDER.index(self) + 1

    @property
    def purpose(self) -> str:
        return _STAGE_PURPOSES[self]


_STAGE_ORDER = (
    LifecycleStage.CAPABILITY_ATTESTED,
    LifecycleStage.EFFECT_AUTHORIZED,
    LifecycleStage.CLAIM_INVOCATION_ATTACHED,
    LifecycleStage.LEASE_INVOCATION_ATTACHED,
    LifecycleStage.TERMINAL_ATTESTED,
    LifecycleStage.CLAIM_TERMINAL_COMMITTED,
    LifecycleStage.LEASE_TERMINAL_COMMITTED,
)

_STAGE_PURPOSES = {
    LifecycleStage.CAPABILITY_ATTESTED: "capability_attestation",
    LifecycleStage.EFFECT_AUTHORIZED: "effect_authorization",
    LifecycleStage.CLAIM_INVOCATION_ATTACHED: "claim_invocation_attachment",
    LifecycleStage.LEASE_INVOCATION_ATTACHED: "lease_invocation_attachment",
    LifecycleStage.TERMINAL_ATTESTED: "terminal_attestation",
    LifecycleStage.CLAIM_TERMINAL_COMMITTED: "claim_terminal_commit",
    LifecycleStage.LEASE_TERMINAL_COMMITTED: "lease_terminal_commit",
}


class LifecycleCode(str, Enum):
    CAPABILITY_ATTESTED = "CAPABILITY_ATTESTED"
    EFFECT_AUTHORIZED = "EFFECT_AUTHORIZED"
    INVOCATION_ATTACHED = "INVOCATION_ATTACHED"
    TERMINAL_ATTESTED = "TERMINAL_ATTESTED"
    TERMINAL_COMMITTED = "TERMINAL_COMMITTED"
    ALREADY_CAPABILITY_ATTESTED = "ALREADY_CAPABILITY_ATTESTED"
    ALREADY_EFFECT_AUTHORIZED = "ALREADY_EFFECT_AUTHORIZED"
    ALREADY_INVOCATION_ATTACHED = "ALREADY_INVOCATION_ATTACHED"
    ALREADY_TERMINAL_ATTESTED = "ALREADY_TERMINAL_ATTESTED"
    ALREADY_TERMINAL_COMMITTED = "ALREADY_TERMINAL_COMMITTED"
    BINDING_MISMATCH = "BINDING_MISMATCH"
    ILLEGAL_TRANSITION = "ILLEGAL_TRANSITION"
    RESPONSE_LOST = "RESPONSE_LOST"
    CAS_CONFLICT = "CAS_CONFLICT"
    TAMPERED = "TAMPERED"
    NOT_FOUND = "NOT_FOUND"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class JournalPhase(str, Enum):
    REQUESTED = "REQUESTED"
    CLAIM_APPLIED = "CLAIM_APPLIED"
    LEASE_APPLIED = "LEASE_APPLIED"
    RESPONSE_LOST = "RESPONSE_LOST"
    RECONCILED = "RECONCILED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


_JOURNAL_TRANSITIONS: dict[JournalPhase, set[JournalPhase]] = {
    JournalPhase.REQUESTED: {JournalPhase.CLAIM_APPLIED, JournalPhase.LEASE_APPLIED, JournalPhase.RESPONSE_LOST, JournalPhase.REJECTED},
    JournalPhase.CLAIM_APPLIED: {JournalPhase.LEASE_APPLIED, JournalPhase.RESPONSE_LOST, JournalPhase.REJECTED},
    JournalPhase.LEASE_APPLIED: {JournalPhase.COMPLETED, JournalPhase.RESPONSE_LOST, JournalPhase.REJECTED},
    JournalPhase.RESPONSE_LOST: {JournalPhase.RECONCILED},
    JournalPhase.RECONCILED: {JournalPhase.CLAIM_APPLIED, JournalPhase.LEASE_APPLIED, JournalPhase.COMPLETED, JournalPhase.REJECTED},
    JournalPhase.COMPLETED: set(),
    JournalPhase.REJECTED: set(),
}


def _holder_document(holder: ClaimHolder) -> dict[str, str]:
    return {
        "owner_type": holder.owner_type.value,
        "owner_instance_id": holder.owner_instance_id,
        "claimant_correlation_id": holder.claimant_correlation_id,
    }


def _holder_from_document(value: object) -> ClaimHolder:
    from .durable_authority import OwnerType

    if not isinstance(value, dict):
        raise ValidationError("lifecycle holder document invalid")
    try:
        return ClaimHolder(OwnerType(value["owner_type"]), value["owner_instance_id"], value["claimant_correlation_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError("lifecycle holder fields invalid") from exc


def _binding_hash(value: object) -> str:
    """Hash durable internal bindings without public-log redaction.

    ``canonical_hash`` is deliberately public-safe: secret-shaped key names can
    redact their values.  That is correct for report output, but unsafe for a
    replay identity because two distinct authorization requests could otherwise
    share a digest.  This helper only stores structural commitments; records
    expose their digest, never their raw request body.
    """

    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LifecycleBinding:
    """The immutable cross-record binding for one synthetic lifecycle."""

    lease_id: str
    claim_id: str
    provenance_digest: str
    storage_id: str
    holder: ClaimHolder
    target: CapabilityTarget
    task_id: str
    route_epoch: int
    canary_id: str
    nonce: str
    expires_at: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.lease_id, "lifecycle lease_id"),
            (self.provenance_digest, "lifecycle provenance_digest"),
            (self.storage_id, "lifecycle storage_id"),
        ):
            require_sha256(value, label)
        for value, label in ((self.claim_id, "lifecycle claim_id"), (self.task_id, "lifecycle task_id"), (self.canary_id, "lifecycle canary_id"), (self.nonce, "lifecycle nonce")):
            require_identifier(value, label)
        if not isinstance(self.holder, ClaimHolder) or not isinstance(self.target, CapabilityTarget):
            raise ValidationError("lifecycle holder or target invalid")
        if not isinstance(self.route_epoch, int) or self.route_epoch < 1:
            raise ValidationError("lifecycle route_epoch invalid")
        parse_rfc3339_utc(self.expires_at, "lifecycle expires_at")

    def document(self) -> dict[str, object]:
        return {
            "lease_id": self.lease_id,
            "claim_id": self.claim_id,
            "provenance_digest": self.provenance_digest,
            "storage_id": self.storage_id,
            "holder": _holder_document(self.holder),
            "target": self.target.value,
            "task_id": self.task_id,
            "route_epoch": self.route_epoch,
            "canary_id": self.canary_id,
            "nonce": self.nonce,
            "expires_at": self.expires_at,
        }

    @property
    def digest(self) -> str:
        return _binding_hash(self.document())

    @classmethod
    def from_document(cls, value: object) -> "LifecycleBinding":
        if not isinstance(value, dict):
            raise ValidationError("lifecycle binding document invalid")
        try:
            return cls(
                lease_id=value["lease_id"],
                claim_id=value["claim_id"],
                provenance_digest=value["provenance_digest"],
                storage_id=value["storage_id"],
                holder=_holder_from_document(value["holder"]),
                target=CapabilityTarget(value["target"]),
                task_id=value["task_id"],
                route_epoch=value["route_epoch"],
                canary_id=value["canary_id"],
                nonce=value["nonce"],
                expires_at=value["expires_at"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("lifecycle binding fields invalid") from exc


@dataclass(frozen=True)
class TerminalEvidence:
    evidence_id: str
    terminal_status: str
    terminal_reason: str
    terminal_at: str

    def __post_init__(self) -> None:
        for value, label in ((self.evidence_id, "terminal evidence_id"), (self.terminal_status, "terminal status"), (self.terminal_reason, "terminal reason")):
            require_identifier(value, label)
        parse_rfc3339_utc(self.terminal_at, "terminal evidence time")

    def document(self) -> dict[str, str]:
        return {
            "evidence_id": self.evidence_id,
            "terminal_status": self.terminal_status,
            "terminal_reason": self.terminal_reason,
            "terminal_at": self.terminal_at,
        }

    @property
    def digest(self) -> str:
        return _binding_hash(self.document())

    @classmethod
    def from_document(cls, value: object) -> "TerminalEvidence":
        if not isinstance(value, dict):
            raise ValidationError("terminal evidence document invalid")
        try:
            return cls(value["evidence_id"], value["terminal_status"], value["terminal_reason"], value["terminal_at"])
        except (KeyError, TypeError) as exc:
            raise ValidationError("terminal evidence fields invalid") from exc


def _request_digest(binding: LifecycleBinding, stage: LifecycleStage, request: dict[str, object]) -> str:
    return _binding_hash({"binding_digest": binding.digest, "stage": stage.value, "request": request})


@dataclass(frozen=True)
class StageReceipt:
    stage: LifecycleStage
    purpose: str
    request_digest: str
    binding_digest: str
    target: str
    applied_at: str
    receipt_digest: str

    @classmethod
    def mint(cls, binding: LifecycleBinding, stage: LifecycleStage, request_digest: str, target: str, applied_at: str) -> "StageReceipt":
        require_sha256(request_digest, "stage request digest")
        require_identifier(target, "stage target")
        parse_rfc3339_utc(applied_at, "stage applied_at")
        value = {
            "stage": stage.value,
            "purpose": stage.purpose,
            "request_digest": request_digest,
            "binding_digest": binding.digest,
            "target": target,
            "applied_at": applied_at,
        }
        return cls(stage, stage.purpose, request_digest, binding.digest, target, applied_at, _binding_hash(value))

    def document(self) -> dict[str, str]:
        value = {
            "stage": self.stage.value,
            "purpose": self.purpose,
            "request_digest": self.request_digest,
            "binding_digest": self.binding_digest,
            "target": self.target,
            "applied_at": self.applied_at,
        }
        return {**value, "receipt_digest": self.receipt_digest}

    @classmethod
    def from_document(cls, value: object) -> "StageReceipt":
        if not isinstance(value, dict):
            raise ValidationError("stage receipt document invalid")
        try:
            stage = LifecycleStage(value["stage"])
            receipt = cls(stage, value["purpose"], value["request_digest"], value["binding_digest"], value["target"], value["applied_at"], value["receipt_digest"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("stage receipt fields invalid") from exc
        expected = _binding_hash({key: receipt.document()[key] for key in ("stage", "purpose", "request_digest", "binding_digest", "target", "applied_at")})
        if expected != receipt.receipt_digest:
            raise ValidationError("stage receipt hash mismatch")
        if receipt.purpose != stage.purpose:
            raise ValidationError("stage receipt purpose mismatch")
        require_sha256(receipt.request_digest, "stage request digest")
        require_sha256(receipt.binding_digest, "stage binding digest")
        require_identifier(receipt.target, "stage target")
        parse_rfc3339_utc(receipt.applied_at, "stage applied_at")
        return receipt


@dataclass(frozen=True)
class LifecycleRecord:
    binding: LifecycleBinding
    state: LifecycleStage
    receipts: tuple[StageReceipt, ...]

    def __post_init__(self) -> None:
        if not self.receipts or len(self.receipts) != self.state.order:
            raise ValidationError("lifecycle receipt count/state mismatch")
        for index, receipt in enumerate(self.receipts):
            if receipt.stage is not _STAGE_ORDER[index] or receipt.binding_digest != self.binding.digest:
                raise ValidationError("lifecycle receipt sequence or binding mismatch")
            if index and parse_rfc3339_utc(receipt.applied_at, "lifecycle receipt time") < parse_rfc3339_utc(self.receipts[index - 1].applied_at, "lifecycle prior receipt time"):
                raise ValidationError("lifecycle receipt time reversal")

    def receipt_for(self, stage: LifecycleStage) -> StageReceipt | None:
        return self.receipts[stage.order - 1] if stage.order <= len(self.receipts) else None

    def document(self) -> dict[str, object]:
        payload = {
            "schema_version": "1.0",
            "binding": self.binding.document(),
            "state": self.state.value,
            "receipts": [receipt.document() for receipt in self.receipts],
        }
        return {**payload, "record_hash": _binding_hash(payload)}

    @property
    def document_bytes(self) -> bytes:
        return json.dumps(self.document(), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_document_bytes(cls, payload: bytes, expected_binding: LifecycleBinding) -> "LifecycleRecord":
        try:
            value = strict_json_loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, ValidationError) as exc:
            raise ValidationError("lifecycle record document invalid") from exc
        if not isinstance(value, dict) or value.get("schema_version") != "1.0":
            raise ValidationError("lifecycle record schema unsupported")
        record_hash = value.pop("record_hash", None)
        if not isinstance(record_hash, str) or _binding_hash(value) != record_hash:
            raise ValidationError("lifecycle record hash mismatch")
        try:
            record = cls(LifecycleBinding.from_document(value["binding"]), LifecycleStage(value["state"]), tuple(StageReceipt.from_document(item) for item in value["receipts"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("lifecycle record fields invalid") from exc
        if record.binding != expected_binding:
            raise ValidationError("lifecycle binding substitution")
        return record


@dataclass(frozen=True)
class ClaimSideRecord:
    binding_digest: str
    claim_id: str
    invocation_receipt: StageReceipt | None = None
    terminal_receipt: StageReceipt | None = None

    def __post_init__(self) -> None:
        require_sha256(self.binding_digest, "claim-side binding digest")
        require_identifier(self.claim_id, "claim-side claim_id")
        if self.invocation_receipt is not None and self.invocation_receipt.stage is not LifecycleStage.CLAIM_INVOCATION_ATTACHED:
            raise ValidationError("claim-side invocation receipt stage invalid")
        if self.terminal_receipt is not None:
            if self.invocation_receipt is None or self.terminal_receipt.stage is not LifecycleStage.CLAIM_TERMINAL_COMMITTED:
                raise ValidationError("claim-side terminal receipt stage invalid")
        for receipt in (self.invocation_receipt, self.terminal_receipt):
            if receipt is not None and receipt.binding_digest != self.binding_digest:
                raise ValidationError("claim-side receipt binding mismatch")

    def receipt_for(self, stage: LifecycleStage) -> StageReceipt | None:
        if stage is LifecycleStage.CLAIM_INVOCATION_ATTACHED:
            return self.invocation_receipt
        if stage is LifecycleStage.CLAIM_TERMINAL_COMMITTED:
            return self.terminal_receipt
        raise ValidationError("claim-side stage invalid")

    def with_receipt(self, receipt: StageReceipt) -> "ClaimSideRecord":
        if receipt.stage is LifecycleStage.CLAIM_INVOCATION_ATTACHED:
            return replace(self, invocation_receipt=receipt)
        if receipt.stage is LifecycleStage.CLAIM_TERMINAL_COMMITTED:
            return replace(self, terminal_receipt=receipt)
        raise ValidationError("claim-side receipt stage invalid")

    def document(self) -> dict[str, object]:
        payload = {
            "schema_version": "1.0",
            "binding_digest": self.binding_digest,
            "claim_id": self.claim_id,
            "invocation_receipt": self.invocation_receipt.document() if self.invocation_receipt else None,
            "terminal_receipt": self.terminal_receipt.document() if self.terminal_receipt else None,
        }
        return {**payload, "record_hash": _binding_hash(payload)}

    @property
    def document_bytes(self) -> bytes:
        return json.dumps(self.document(), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_document_bytes(cls, payload: bytes, binding: LifecycleBinding) -> "ClaimSideRecord":
        try:
            value = strict_json_loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, ValidationError) as exc:
            raise ValidationError("claim-side document invalid") from exc
        if not isinstance(value, dict) or value.get("schema_version") != "1.0":
            raise ValidationError("claim-side schema unsupported")
        record_hash = value.pop("record_hash", None)
        if not isinstance(record_hash, str) or _binding_hash(value) != record_hash:
            raise ValidationError("claim-side record hash mismatch")
        try:
            record = cls(
                value["binding_digest"],
                value["claim_id"],
                StageReceipt.from_document(value["invocation_receipt"]) if value.get("invocation_receipt") else None,
                StageReceipt.from_document(value["terminal_receipt"]) if value.get("terminal_receipt") else None,
            )
        except (KeyError, TypeError) as exc:
            raise ValidationError("claim-side fields invalid") from exc
        if record.binding_digest != binding.digest or record.claim_id != binding.claim_id:
            raise ValidationError("claim-side binding substitution")
        return record


@dataclass(frozen=True)
class JournalEvent:
    phase: JournalPhase
    at: str
    detail_digest: str
    previous_hash: str | None
    event_hash: str

    @classmethod
    def mint(cls, phase: JournalPhase, at: str, detail: object, previous_hash: str | None) -> "JournalEvent":
        parse_rfc3339_utc(at, "journal event time")
        if previous_hash is not None:
            require_sha256(previous_hash, "journal previous hash")
        detail_digest = _binding_hash(detail)
        event_hash = _binding_hash({"phase": phase.value, "at": at, "detail_digest": detail_digest, "previous_hash": previous_hash})
        return cls(phase, at, detail_digest, previous_hash, event_hash)

    def document(self) -> dict[str, str | None]:
        return {
            "phase": self.phase.value,
            "at": self.at,
            "detail_digest": self.detail_digest,
            "previous_hash": self.previous_hash,
            "event_hash": self.event_hash,
        }

    @classmethod
    def from_document(cls, value: object, previous_hash: str | None) -> "JournalEvent":
        if not isinstance(value, dict):
            raise ValidationError("journal event document invalid")
        try:
            event = cls(JournalPhase(value["phase"]), value["at"], value["detail_digest"], value.get("previous_hash"), value["event_hash"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("journal event fields invalid") from exc
        if event.previous_hash != previous_hash:
            raise ValidationError("journal event chain mismatch")
        parse_rfc3339_utc(event.at, "journal event time")
        require_sha256(event.detail_digest, "journal detail digest")
        expected = _binding_hash({"phase": event.phase.value, "at": event.at, "detail_digest": event.detail_digest, "previous_hash": event.previous_hash})
        if expected != event.event_hash:
            raise ValidationError("journal event hash mismatch")
        return event


@dataclass(frozen=True)
class LifecycleJournal:
    operation_id: str
    binding_digest: str
    stage: LifecycleStage
    purpose: str
    request_digest: str
    target: str
    events: tuple[JournalEvent, ...]

    def __post_init__(self) -> None:
        for value, label in ((self.operation_id, "journal operation_id"), (self.binding_digest, "journal binding digest"), (self.request_digest, "journal request digest")):
            require_sha256(value, label)
        require_identifier(self.target, "journal target")
        if self.purpose != self.stage.purpose:
            raise ValidationError("journal purpose/stage mismatch")
        if not self.events or self.events[0].phase is not JournalPhase.REQUESTED:
            raise ValidationError("journal must begin requested")
        previous = None
        for index, event in enumerate(self.events):
            validated = JournalEvent.from_document(event.document(), previous)
            if validated != event:
                raise ValidationError("journal event serialization drift")
            if index and event.phase not in _JOURNAL_TRANSITIONS[self.events[index - 1].phase]:
                raise ValidationError("journal phase transition invalid")
            previous = event.event_hash

    @property
    def phase(self) -> JournalPhase:
        return self.events[-1].phase

    @classmethod
    def start(cls, binding: LifecycleBinding, stage: LifecycleStage, request_digest: str, target: str, at: str) -> "LifecycleJournal":
        operation_id = _binding_hash({"binding_digest": binding.digest, "stage": stage.value, "purpose": stage.purpose, "request_digest": request_digest, "target": target})
        event = JournalEvent.mint(JournalPhase.REQUESTED, at, {"stage": stage.value, "request_digest": request_digest, "target": target}, None)
        return cls(operation_id, binding.digest, stage, stage.purpose, request_digest, target, (event,))

    def advance(self, phase: JournalPhase, at: str, detail: object) -> "LifecycleJournal":
        if phase not in _JOURNAL_TRANSITIONS[self.phase]:
            raise ValidationError("journal phase cannot advance")
        return replace(self, events=(*self.events, JournalEvent.mint(phase, at, detail, self.events[-1].event_hash)))

    def document(self) -> dict[str, object]:
        payload = {
            "schema_version": "1.0",
            "operation_id": self.operation_id,
            "binding_digest": self.binding_digest,
            "stage": self.stage.value,
            "purpose": self.purpose,
            "request_digest": self.request_digest,
            "target": self.target,
            "events": [event.document() for event in self.events],
        }
        return {**payload, "record_hash": _binding_hash(payload)}

    @property
    def document_bytes(self) -> bytes:
        return json.dumps(self.document(), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_document_bytes(cls, payload: bytes, binding: LifecycleBinding, stage: LifecycleStage, request_digest: str, target: str) -> "LifecycleJournal":
        try:
            value = strict_json_loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, ValidationError) as exc:
            raise ValidationError("journal document invalid") from exc
        if not isinstance(value, dict) or value.get("schema_version") != "1.0":
            raise ValidationError("journal schema unsupported")
        record_hash = value.pop("record_hash", None)
        if not isinstance(record_hash, str) or _binding_hash(value) != record_hash:
            raise ValidationError("journal record hash mismatch")
        try:
            events: list[JournalEvent] = []
            previous = None
            for item in value["events"]:
                event = JournalEvent.from_document(item, previous)
                events.append(event)
                previous = event.event_hash
            record = cls(value["operation_id"], value["binding_digest"], LifecycleStage(value["stage"]), value["purpose"], value["request_digest"], value["target"], tuple(events))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("journal fields invalid") from exc
        expected = cls.start(binding, stage, request_digest, target, record.events[0].at).operation_id
        if (
            record.operation_id != expected
            or record.binding_digest != binding.digest
            or record.stage is not stage
            or record.request_digest != request_digest
            or record.target != target
        ):
            raise ValidationError("journal binding substitution")
        return record

    @classmethod
    def from_existing_document_bytes(cls, payload: bytes, expected: "LifecycleJournal") -> "LifecycleJournal":
        """Reload one journal by its already-known immutable identity."""

        try:
            value = strict_json_loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, ValidationError) as exc:
            raise ValidationError("journal document invalid") from exc
        if not isinstance(value, dict) or value.get("schema_version") != "1.0":
            raise ValidationError("journal schema unsupported")
        record_hash = value.pop("record_hash", None)
        if not isinstance(record_hash, str) or _binding_hash(value) != record_hash:
            raise ValidationError("journal record hash mismatch")
        try:
            events: list[JournalEvent] = []
            previous = None
            for item in value["events"]:
                event = JournalEvent.from_document(item, previous)
                events.append(event)
                previous = event.event_hash
            record = cls(
                value["operation_id"],
                value["binding_digest"],
                LifecycleStage(value["stage"]),
                value["purpose"],
                value["request_digest"],
                value["target"],
                tuple(events),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("journal fields invalid") from exc
        if (
            record.operation_id != expected.operation_id
            or record.binding_digest != expected.binding_digest
            or record.stage is not expected.stage
            or record.purpose != expected.purpose
            or record.request_digest != expected.request_digest
            or record.target != expected.target
        ):
            raise ValidationError("journal binding substitution")
        return record


@dataclass(frozen=True)
class LifecycleResult:
    code: LifecycleCode
    record: LifecycleRecord | None = None
    receipt: StageReceipt | None = None
    journal: LifecycleJournal | None = None


def _validation_failure_code(exc: ValidationError) -> LifecycleCode:
    """Keep a valid foreign binding distinct from corrupted durable state."""

    if "binding substitution" in str(exc):
        return LifecycleCode.BINDING_MISMATCH
    return LifecycleCode.TAMPERED


class RecoverableLifecycleAuthority:
    """One restart-safe lifecycle coordinated through three revisioned stores."""

    def __init__(
        self,
        namespace: str,
        lease_gateway: RevisionedObjectGateway,
        claim_gateway: RevisionedObjectGateway,
        journal_gateway: RevisionedObjectGateway,
    ) -> None:
        require_identifier(namespace, "lifecycle namespace")
        self._namespace = namespace
        self._lease_gateway = lease_gateway
        self._claim_gateway = claim_gateway
        self._journal_gateway = journal_gateway

    def _lease_id(self, binding: LifecycleBinding) -> str:
        return f"{self._namespace}.lease.{binding.lease_id}"

    def _claim_id(self, binding: LifecycleBinding) -> str:
        return f"{self._namespace}.claim.{binding.claim_id}.{binding.digest}"

    def _journal_id(self, operation_id: str) -> str:
        return f"{self._namespace}.journal.{operation_id}"

    @staticmethod
    def _applied_code(stage: LifecycleStage, *, already: bool) -> LifecycleCode:
        values = {
            LifecycleStage.CAPABILITY_ATTESTED: (LifecycleCode.CAPABILITY_ATTESTED, LifecycleCode.ALREADY_CAPABILITY_ATTESTED),
            LifecycleStage.EFFECT_AUTHORIZED: (LifecycleCode.EFFECT_AUTHORIZED, LifecycleCode.ALREADY_EFFECT_AUTHORIZED),
            LifecycleStage.CLAIM_INVOCATION_ATTACHED: (LifecycleCode.INVOCATION_ATTACHED, LifecycleCode.ALREADY_INVOCATION_ATTACHED),
            LifecycleStage.LEASE_INVOCATION_ATTACHED: (LifecycleCode.INVOCATION_ATTACHED, LifecycleCode.ALREADY_INVOCATION_ATTACHED),
            LifecycleStage.TERMINAL_ATTESTED: (LifecycleCode.TERMINAL_ATTESTED, LifecycleCode.ALREADY_TERMINAL_ATTESTED),
            LifecycleStage.CLAIM_TERMINAL_COMMITTED: (LifecycleCode.TERMINAL_COMMITTED, LifecycleCode.ALREADY_TERMINAL_COMMITTED),
            LifecycleStage.LEASE_TERMINAL_COMMITTED: (LifecycleCode.TERMINAL_COMMITTED, LifecycleCode.ALREADY_TERMINAL_COMMITTED),
        }
        return values[stage][1 if already else 0]

    def _read_lease(self, binding: LifecycleBinding) -> tuple[object, LifecycleRecord | None, LifecycleCode | None]:
        try:
            snapshot = self._lease_gateway.read(self._lease_id(binding))
            if snapshot.payload is None:
                return snapshot, None, None
            return snapshot, LifecycleRecord.from_document_bytes(snapshot.payload, binding), None
        except ValidationError as exc:
            return None, None, _validation_failure_code(exc)
        except Exception:
            return None, None, LifecycleCode.CAS_CONFLICT

    def _read_claim(self, binding: LifecycleBinding) -> tuple[object, ClaimSideRecord | None, LifecycleCode | None]:
        try:
            snapshot = self._claim_gateway.read(self._claim_id(binding))
            if snapshot.payload is None:
                return snapshot, None, None
            return snapshot, ClaimSideRecord.from_document_bytes(snapshot.payload, binding), None
        except ValidationError as exc:
            return None, None, _validation_failure_code(exc)
        except Exception:
            return None, None, LifecycleCode.CAS_CONFLICT

    def _journal(self, binding: LifecycleBinding, stage: LifecycleStage, request_digest: str, target: str, at: str) -> tuple[LifecycleJournal | None, LifecycleCode | None]:
        proposed = LifecycleJournal.start(binding, stage, request_digest, target, at)
        object_id = self._journal_id(proposed.operation_id)
        try:
            snapshot = self._journal_gateway.read(object_id)
            if snapshot.payload is None:
                write = self._journal_gateway.compare_and_set(object_id, None, proposed.document_bytes)
                if write.applied:
                    return proposed, None
                snapshot = self._journal_gateway.read(object_id)
            if snapshot.payload is None:
                return None, LifecycleCode.CAS_CONFLICT
            return LifecycleJournal.from_document_bytes(snapshot.payload, binding, stage, request_digest, target), None
        except ValidationError:
            return None, LifecycleCode.TAMPERED
        except Exception:
            return None, LifecycleCode.CAS_CONFLICT

    def _advance_journal(self, journal: LifecycleJournal, phase: JournalPhase, at: str, detail: object) -> LifecycleJournal:
        """CAS the journal phase or fail closed when its durable state drifts."""

        object_id = self._journal_id(journal.operation_id)
        snapshot = self._journal_gateway.read(object_id)
        if snapshot.payload is None or snapshot.revision is None:
            raise OSError("journal_missing")
        current = LifecycleJournal.from_existing_document_bytes(snapshot.payload, journal)
        if current.phase is phase or current.phase is JournalPhase.COMPLETED:
            return current
        if phase not in _JOURNAL_TRANSITIONS[current.phase]:
            raise ValidationError("journal phase cannot advance")
        updated = current.advance(phase, at, detail)
        write = self._journal_gateway.compare_and_set(object_id, snapshot.revision, updated.document_bytes)
        if write.applied:
            return updated
        reread = self._journal_gateway.read(object_id)
        if reread.payload is None:
            raise OSError("journal_cas_conflict")
        observed = LifecycleJournal.from_existing_document_bytes(reread.payload, journal)
        if observed.phase is phase or observed.phase is JournalPhase.COMPLETED:
            return observed
        raise OSError("journal_cas_conflict")

    def _record_response_loss(self, journal: LifecycleJournal, at: str, target: str) -> LifecycleJournal:
        try:
            return self._advance_journal(journal, JournalPhase.RESPONSE_LOST, at, {"target": target})
        except Exception:
            return journal

    def _write_lease(self, binding: LifecycleBinding, record: LifecycleRecord, proposed: LifecycleRecord, journal: LifecycleJournal, at: str) -> LifecycleResult:
        try:
            snapshot = self._lease_gateway.read(self._lease_id(binding))
            if snapshot.payload != record.document_bytes:
                return LifecycleResult(LifecycleCode.CAS_CONFLICT, record, journal=journal)
            write = self._lease_gateway.compare_and_set(self._lease_id(binding), snapshot.revision, proposed.document_bytes)
            if write.applied:
                journal = self._advance_journal(journal, JournalPhase.LEASE_APPLIED, at, {"stage": proposed.state.value})
                journal = self._advance_journal(journal, JournalPhase.COMPLETED, at, {"stage": proposed.state.value})
                return LifecycleResult(self._applied_code(proposed.state, already=False), proposed, proposed.receipt_for(proposed.state), journal)
        except Exception:
            journal = self._record_response_loss(journal, at, "LEASE")
            return LifecycleResult(LifecycleCode.RESPONSE_LOST, record, journal=journal)
        reread = self._read_lease(binding)
        if reread[2] is not None:
            return LifecycleResult(reread[2], journal=journal)
        return LifecycleResult(LifecycleCode.CAS_CONFLICT, reread[1], journal=journal)

    def _advance_lease(self, binding: LifecycleBinding, stage: LifecycleStage, request_digest: str, at: str, journal: LifecycleJournal) -> LifecycleResult:
        _, record, failure = self._read_lease(binding)
        if failure is not None:
            return LifecycleResult(failure, journal=journal)
        if record is None:
            return LifecycleResult(LifecycleCode.NOT_FOUND, journal=journal)
        existing = record.receipt_for(stage)
        if existing is not None:
            if existing.request_digest != request_digest:
                return LifecycleResult(LifecycleCode.BINDING_MISMATCH, record, existing, journal)
            try:
                journal = self._advance_journal(journal, JournalPhase.RECONCILED, at, {"stage": stage.value, "target": "LEASE"})
                journal = self._advance_journal(journal, JournalPhase.COMPLETED, at, {"stage": stage.value})
            except Exception:
                return LifecycleResult(LifecycleCode.RESPONSE_LOST, record, existing, self._record_response_loss(journal, at, "LEASE"))
            return LifecycleResult(self._applied_code(stage, already=True), record, existing, journal)
        if stage.order != record.state.order + 1:
            return LifecycleResult(LifecycleCode.ILLEGAL_TRANSITION, record, journal=journal)
        receipt = StageReceipt.mint(binding, stage, request_digest, "LEASE", at)
        proposed = replace(record, state=stage, receipts=(*record.receipts, receipt))
        return self._write_lease(binding, record, proposed, journal, at)

    def _advance_claim(self, binding: LifecycleBinding, stage: LifecycleStage, request_digest: str, at: str, journal: LifecycleJournal) -> LifecycleResult:
        _, lease, failure = self._read_lease(binding)
        if failure is not None:
            return LifecycleResult(failure, journal=journal)
        if lease is None:
            return LifecycleResult(LifecycleCode.NOT_FOUND, journal=journal)
        _, claim, failure = self._read_claim(binding)
        if failure is not None:
            return LifecycleResult(failure, lease, journal=journal)
        if claim is None:
            return LifecycleResult(LifecycleCode.NOT_FOUND, lease, journal=journal)
        existing = claim.receipt_for(stage)
        if existing is None:
            receipt = StageReceipt.mint(binding, stage, request_digest, "CLAIM", at)
            proposed = claim.with_receipt(receipt)
            try:
                snapshot = self._claim_gateway.read(self._claim_id(binding))
                if snapshot.payload != claim.document_bytes:
                    return LifecycleResult(LifecycleCode.CAS_CONFLICT, lease, journal=journal)
                write = self._claim_gateway.compare_and_set(self._claim_id(binding), snapshot.revision, proposed.document_bytes)
                if not write.applied:
                    return LifecycleResult(LifecycleCode.CAS_CONFLICT, lease, journal=journal)
                journal = self._advance_journal(journal, JournalPhase.CLAIM_APPLIED, at, {"stage": stage.value})
            except Exception:
                journal = self._record_response_loss(journal, at, "CLAIM")
                return LifecycleResult(LifecycleCode.RESPONSE_LOST, lease, journal=journal)
        elif existing.request_digest != request_digest:
            return LifecycleResult(LifecycleCode.BINDING_MISMATCH, lease, existing, journal)
        else:
            try:
                journal = self._advance_journal(journal, JournalPhase.RECONCILED, at, {"stage": stage.value, "target": "CLAIM"})
                journal = self._advance_journal(journal, JournalPhase.CLAIM_APPLIED, at, {"stage": stage.value, "recovered": True})
            except Exception:
                return LifecycleResult(LifecycleCode.RESPONSE_LOST, lease, existing, self._record_response_loss(journal, at, "CLAIM"))
        return self._advance_lease(binding, stage, request_digest, at, journal)

    def attest_capability(self, binding: LifecycleBinding, at: str) -> LifecycleResult:
        parse_rfc3339_utc(at, "capability attested_at")
        if parse_rfc3339_utc(at, "capability attested_at") >= parse_rfc3339_utc(binding.expires_at, "binding expiry"):
            return LifecycleResult(LifecycleCode.ILLEGAL_TRANSITION)
        request = _request_digest(binding, LifecycleStage.CAPABILITY_ATTESTED, {"capability": "synthetic_attested"})
        _, existing, failure = self._read_lease(binding)
        if failure is not None:
            return LifecycleResult(failure)
        if existing is not None:
            receipt = existing.receipt_for(LifecycleStage.CAPABILITY_ATTESTED)
            if receipt is None or receipt.request_digest != request:
                return LifecycleResult(LifecycleCode.BINDING_MISMATCH, existing)
            return LifecycleResult(LifecycleCode.ALREADY_CAPABILITY_ATTESTED, existing, receipt)
        receipt = StageReceipt.mint(binding, LifecycleStage.CAPABILITY_ATTESTED, request, "LEASE", at)
        record = LifecycleRecord(binding, LifecycleStage.CAPABILITY_ATTESTED, (receipt,))
        claim = ClaimSideRecord(binding.digest, binding.claim_id)
        try:
            claim_write = self._claim_gateway.compare_and_set(self._claim_id(binding), None, claim.document_bytes)
            if not claim_write.applied:
                return LifecycleResult(LifecycleCode.CAS_CONFLICT)
            lease_write = self._lease_gateway.compare_and_set(self._lease_id(binding), None, record.document_bytes)
            if lease_write.applied:
                return LifecycleResult(LifecycleCode.CAPABILITY_ATTESTED, record, receipt)
        except Exception:
            return LifecycleResult(LifecycleCode.RESPONSE_LOST)
        reread = self._read_lease(binding)
        if reread[1] is not None:
            return LifecycleResult(LifecycleCode.ALREADY_CAPABILITY_ATTESTED, reread[1], reread[1].receipt_for(LifecycleStage.CAPABILITY_ATTESTED))
        return LifecycleResult(LifecycleCode.CAS_CONFLICT)

    def authorize_effect(self, binding: LifecycleBinding, authorization_id: str, at: str) -> LifecycleResult:
        require_identifier(authorization_id, "effect authorization_id")
        request = _request_digest(binding, LifecycleStage.EFFECT_AUTHORIZED, {"authorization_id": authorization_id})
        journal, failure = self._journal(binding, LifecycleStage.EFFECT_AUTHORIZED, request, "LEASE", at)
        if failure is not None or journal is None:
            return LifecycleResult(failure or LifecycleCode.CAS_CONFLICT)
        return self._advance_lease(binding, LifecycleStage.EFFECT_AUTHORIZED, request, at, journal)

    def attach_invocation(self, binding: LifecycleBinding, invocation_id: str, at: str) -> LifecycleResult:
        require_identifier(invocation_id, "lifecycle invocation_id")
        request = _request_digest(binding, LifecycleStage.CLAIM_INVOCATION_ATTACHED, {"invocation_id": invocation_id})
        journal, failure = self._journal(binding, LifecycleStage.CLAIM_INVOCATION_ATTACHED, request, "CROSS_RECORD", at)
        if failure is not None or journal is None:
            return LifecycleResult(failure or LifecycleCode.CAS_CONFLICT)
        result = self._advance_claim(binding, LifecycleStage.CLAIM_INVOCATION_ATTACHED, request, at, journal)
        if result.code in {LifecycleCode.INVOCATION_ATTACHED, LifecycleCode.ALREADY_INVOCATION_ATTACHED}:
            receipt = result.record.receipt_for(LifecycleStage.CLAIM_INVOCATION_ATTACHED) if result.record else None
            if receipt is None or receipt.request_digest != request:
                return LifecycleResult(LifecycleCode.BINDING_MISMATCH, result.record, journal=result.journal)
            journal = result.journal or journal
            lease_request = _request_digest(binding, LifecycleStage.LEASE_INVOCATION_ATTACHED, {"invocation_id": invocation_id, "claim_receipt": receipt.receipt_digest})
            lease_journal, failure = self._journal(binding, LifecycleStage.LEASE_INVOCATION_ATTACHED, lease_request, "LEASE", at)
            if failure is not None or lease_journal is None:
                return LifecycleResult(failure or LifecycleCode.CAS_CONFLICT, result.record)
            return self._advance_lease(binding, LifecycleStage.LEASE_INVOCATION_ATTACHED, lease_request, at, lease_journal)
        return result

    def attest_terminal(self, binding: LifecycleBinding, evidence: TerminalEvidence, at: str) -> LifecycleResult:
        request = _request_digest(binding, LifecycleStage.TERMINAL_ATTESTED, {"terminal_evidence": evidence.document()})
        journal, failure = self._journal(binding, LifecycleStage.TERMINAL_ATTESTED, request, "LEASE", at)
        if failure is not None or journal is None:
            return LifecycleResult(failure or LifecycleCode.CAS_CONFLICT)
        return self._advance_lease(binding, LifecycleStage.TERMINAL_ATTESTED, request, at, journal)

    def commit_terminal(self, binding: LifecycleBinding, terminal_commit_id: str, at: str) -> LifecycleResult:
        require_identifier(terminal_commit_id, "terminal commit id")
        _, record, failure = self._read_lease(binding)
        if failure is not None:
            return LifecycleResult(failure)
        if record is None:
            return LifecycleResult(LifecycleCode.NOT_FOUND)
        evidence_receipt = record.receipt_for(LifecycleStage.TERMINAL_ATTESTED)
        if evidence_receipt is None:
            return LifecycleResult(LifecycleCode.ILLEGAL_TRANSITION, record)
        request = _request_digest(binding, LifecycleStage.CLAIM_TERMINAL_COMMITTED, {"terminal_commit_id": terminal_commit_id, "terminal_receipt": evidence_receipt.receipt_digest})
        journal, failure = self._journal(binding, LifecycleStage.CLAIM_TERMINAL_COMMITTED, request, "CROSS_RECORD", at)
        if failure is not None or journal is None:
            return LifecycleResult(failure or LifecycleCode.CAS_CONFLICT, record)
        result = self._advance_claim(binding, LifecycleStage.CLAIM_TERMINAL_COMMITTED, request, at, journal)
        if result.code not in {LifecycleCode.TERMINAL_COMMITTED, LifecycleCode.ALREADY_TERMINAL_COMMITTED}:
            return result
        claim_receipt = result.record.receipt_for(LifecycleStage.CLAIM_TERMINAL_COMMITTED) if result.record else None
        if claim_receipt is None or claim_receipt.request_digest != request:
            return LifecycleResult(LifecycleCode.BINDING_MISMATCH, result.record, journal=result.journal)
        lease_request = _request_digest(binding, LifecycleStage.LEASE_TERMINAL_COMMITTED, {"claim_receipt": claim_receipt.receipt_digest, "terminal_commit_id": terminal_commit_id})
        lease_journal, failure = self._journal(binding, LifecycleStage.LEASE_TERMINAL_COMMITTED, lease_request, "LEASE", at)
        if failure is not None or lease_journal is None:
            return LifecycleResult(failure or LifecycleCode.CAS_CONFLICT, result.record)
        return self._advance_lease(binding, LifecycleStage.LEASE_TERMINAL_COMMITTED, lease_request, at, lease_journal)

    def read(self, binding: LifecycleBinding) -> LifecycleResult:
        _, record, failure = self._read_lease(binding)
        if failure is not None:
            return LifecycleResult(failure)
        return LifecycleResult(LifecycleCode.NOT_FOUND if record is None else self._applied_code(record.state, already=True), record)
