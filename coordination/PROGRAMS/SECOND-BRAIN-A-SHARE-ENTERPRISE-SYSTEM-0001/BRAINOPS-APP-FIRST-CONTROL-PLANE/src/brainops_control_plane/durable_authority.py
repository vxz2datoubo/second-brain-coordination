"""Trusted, revisioned durable claim authority for E42.

Persistent records are evidence bindings, not self-authenticating proof.  Every
state-changing API therefore requires the same verifier-minted provenance and
the same closed owner identity that won the compare-and-set operation.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import timedelta
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Iterator, Protocol

from .models import BoundCanaryApproval, ValidationError, canonical_hash, parse_rfc3339_utc, require_identifier, strict_json_loads
from .proofs import ApprovalVerificationResult, RouteProofVerification, VerificationStatus


_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_REVISION = re.compile(r"^[0-9a-f]{40,64}$")
_GIT_REF = re.compile(r"^refs/heads/[A-Za-z0-9_.-]+$")
_PROVENANCE_SEAL = object()
_PERMIT_SEAL = object()
_RECOVERY_SEAL = object()


class OwnerType(str, Enum):
    CURRENT_CODEX_APP_SESSION = "CURRENT_CODEX_APP_SESSION"
    APP_AUTOMATION_NEW_RUN = "APP_AUTOMATION_NEW_RUN"
    CODEX_CLI_PROCESS = "CODEX_CLI_PROCESS"


@dataclass(frozen=True)
class ClaimHolder:
    owner_type: OwnerType
    owner_instance_id: str
    claimant_correlation_id: str

    def __post_init__(self) -> None:
        require_identifier(self.owner_instance_id, "owner_instance_id")
        require_identifier(self.claimant_correlation_id, "claimant_correlation_id")


class RecoveryPrincipalType(str, Enum):
    """Closed identities permitted to reconcile an abandoned claim only."""

    GOVERNED_RECOVERY_COORDINATOR = "GOVERNED_RECOVERY_COORDINATOR"


@dataclass(frozen=True, init=False)
class RecoveryPrincipal:
    """A recovery identity deliberately distinct from a claim holder.

    It cannot be supplied to effect-permit, attach, or finalization APIs. The
    seal is an API boundary; a separately trusted process or signer remains
    necessary for a production trust root.
    """

    principal_type: RecoveryPrincipalType
    principal_instance_id: str

    def __init__(
        self,
        principal_type: RecoveryPrincipalType,
        principal_instance_id: str,
        *,
        _seal: object | None = None,
    ) -> None:
        if _seal is not _RECOVERY_SEAL:
            raise ValidationError("recovery principal must be minted by governance")
        require_identifier(principal_instance_id, "recovery principal_instance_id")
        object.__setattr__(self, "principal_type", principal_type)
        object.__setattr__(self, "principal_instance_id", principal_instance_id)


@dataclass(frozen=True, init=False)
class RecoveryAuthorization:
    """One bounded authorization for a single expired durable claim."""

    principal: RecoveryPrincipal
    claim_id: str
    original_holder: ClaimHolder
    not_before: str
    expires_at: str
    reason: str

    def __init__(
        self,
        principal: RecoveryPrincipal,
        claim_id: str,
        original_holder: ClaimHolder,
        not_before: str,
        expires_at: str,
        reason: str,
        *,
        _seal: object | None = None,
    ) -> None:
        if _seal is not _RECOVERY_SEAL:
            raise ValidationError("recovery authorization must be minted by governance")
        if not isinstance(principal, RecoveryPrincipal) or not isinstance(original_holder, ClaimHolder):
            raise ValidationError("recovery authorization principal or holder invalid")
        require_identifier(claim_id, "recovery claim_id")
        require_identifier(reason, "recovery reason")
        if parse_rfc3339_utc(expires_at, "recovery expires_at") <= parse_rfc3339_utc(not_before, "recovery not_before"):
            raise ValidationError("recovery authorization expiry must follow not_before")
        object.__setattr__(self, "principal", principal)
        object.__setattr__(self, "claim_id", claim_id)
        object.__setattr__(self, "original_holder", original_holder)
        object.__setattr__(self, "not_before", not_before)
        object.__setattr__(self, "expires_at", expires_at)
        object.__setattr__(self, "reason", reason)


def _governed_recovery_principal(principal_instance_id: str) -> RecoveryPrincipal:
    """Synthetic composition-root factory for E43 tests and future adapters."""

    return RecoveryPrincipal(
        RecoveryPrincipalType.GOVERNED_RECOVERY_COORDINATOR,
        principal_instance_id,
        _seal=_RECOVERY_SEAL,
    )


def _governed_recovery_authorization(
    principal: RecoveryPrincipal,
    claim_id: str,
    original_holder: ClaimHolder,
    not_before: str,
    expires_at: str,
    reason: str,
) -> RecoveryAuthorization:
    return RecoveryAuthorization(
        principal,
        claim_id,
        original_holder,
        not_before,
        expires_at,
        reason,
        _seal=_RECOVERY_SEAL,
    )


@dataclass(frozen=True)
class AuthorityProvenanceBinding:
    repository: str
    route_id: str
    route_target_agent: str
    route_epoch: int
    task_id: str
    canary_id: str
    nonce: str
    scope: str
    expires_at: str
    route_ref: str
    route_commit_sha1: str
    route_tree_sha1: str
    route_path: str
    route_blob_sha1: str
    route_content_sha256: str
    coordination_path: str
    coordination_blob_sha1: str
    coordination_content_sha256: str
    route_observed_at: str
    approval_repository: str
    approval_issue_number: int
    approval_comment_id: int
    approval_actor: str
    approval_issued_at: str
    approval_body_sha256: str
    approval_ref: str
    approval_binding_sha256: str
    verified_at: str

    @property
    def digest(self) -> str:
        return canonical_hash(self.document())

    def document(self) -> dict[str, object]:
        return dict(self.__dict__)


@dataclass(frozen=True, init=False)
class VerifiedAuthorityProvenance:
    """Verifier-minted route and approval identity used by claim APIs."""

    binding: AuthorityProvenanceBinding

    def __init__(self, binding: AuthorityProvenanceBinding, *, _seal: object | None = None) -> None:
        if _seal is not _PROVENANCE_SEAL:
            raise ValidationError("trusted authority provenance must come from the verifier")
        object.__setattr__(self, "binding", binding)


class AuthorityProvenanceVerifier:
    """Join sealed route and approval verifier outputs into one exact binding."""

    def verify(
        self,
        route_proof: RouteProofVerification,
        approval_result: ApprovalVerificationResult,
        approval: BoundCanaryApproval,
        checked_at: str,
    ) -> VerifiedAuthorityProvenance:
        checked = parse_rfc3339_utc(checked_at, "authority provenance checked_at")
        if not isinstance(route_proof, RouteProofVerification) or route_proof.status is not VerificationStatus.READ_ONLY_FETCH_VERIFIED:
            raise ValidationError("verified route proof required")
        if not isinstance(approval_result, ApprovalVerificationResult) or approval_result.status is not VerificationStatus.READ_ONLY_FETCH_VERIFIED:
            raise ValidationError("verified approval proof required")
        if route_proof.evidence is None or approval_result.evidence is None:
            raise ValidationError("verified provenance evidence missing")
        if route_proof.verified_at != checked_at or approval_result.verified_at != checked_at:
            raise ValidationError("route and approval verification must belong to this check")
        route = route_proof.evidence
        approval_evidence = approval_result.evidence
        if approval_result.validates(approval, checked_at) is not None:
            raise ValidationError("approval proof no longer validates")
        if route.repository != approval_evidence.repository or route.repository != approval.repository:
            raise ValidationError("route and approval repository mismatch")
        if route.authority.task_id != approval.task_id or route.authority.route_epoch != approval.route_epoch:
            raise ValidationError("route and approval task or epoch mismatch")
        if approval.comment_id is None or approval.issue_number is None:
            raise ValidationError("approval issue and comment identities required")
        if approval.actor != approval_evidence.actor or approval.issued_at != approval_evidence.issued_at:
            raise ValidationError("approval actor or time mismatch")
        if approval.body_sha256 != approval_evidence.body_sha256:
            raise ValidationError("approval body hash mismatch")
        issued = parse_rfc3339_utc(approval_evidence.issued_at, "approval issued_at")
        observed = parse_rfc3339_utc(route.observed_at, "route observed_at")
        if issued < observed or issued > checked:
            raise ValidationError("approval time is outside the verified route window")
        if checked >= parse_rfc3339_utc(approval.expires_at, "approval expires_at"):
            raise ValidationError("approval is expired at provenance verification")
        binding = AuthorityProvenanceBinding(
            repository=route.repository,
            route_id=route.route.route_id,
            route_target_agent=route.route.target_agent,
            route_epoch=route.route.route_epoch,
            task_id=approval.task_id,
            canary_id=approval.canary_id,
            nonce=approval.nonce,
            scope=approval.scope,
            expires_at=approval.expires_at,
            route_ref=route.ref,
            route_commit_sha1=route.main_commit_sha1,
            route_tree_sha1=route.main_tree_sha1,
            route_path=route.active_task.path,
            route_blob_sha1=route.active_task.blob_sha1,
            route_content_sha256=route.active_task.content_sha256,
            coordination_path=route.coordination.path,
            coordination_blob_sha1=route.coordination.blob_sha1,
            coordination_content_sha256=route.coordination.content_sha256,
            route_observed_at=route.observed_at,
            approval_repository=approval_evidence.repository,
            approval_issue_number=approval_evidence.issue_number,
            approval_comment_id=approval_evidence.comment_id,
            approval_actor=approval_evidence.actor,
            approval_issued_at=approval_evidence.issued_at,
            approval_body_sha256=approval_evidence.body_sha256,
            approval_ref=approval_evidence.approval_ref,
            approval_binding_sha256=approval_evidence.binding_payload_sha256,
            verified_at=checked_at,
        )
        return VerifiedAuthorityProvenance(binding, _seal=_PROVENANCE_SEAL)


class DurableClaimState(str, Enum):
    CLAIMED = "CLAIMED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"

    @property
    def terminal(self) -> bool:
        return self is not DurableClaimState.CLAIMED


class DurableClaimResultCode(str, Enum):
    CLAIMED = "CLAIMED"
    FINALIZED = "FINALIZED"
    INVOCATION_ATTACHED = "INVOCATION_ATTACHED"
    DUPLICATE_INVOCATION = "DUPLICATE_INVOCATION"
    INVOCATION_MISMATCH = "INVOCATION_MISMATCH"
    ALREADY_CLAIMED = "ALREADY_CLAIMED"
    TERMINAL_EXISTS = "TERMINAL_EXISTS"
    CAS_CONFLICT = "CAS_CONFLICT"
    AUTHORITY_UNAVAILABLE = "AUTHORITY_UNAVAILABLE"
    CLAIM_NOT_FOUND = "CLAIM_NOT_FOUND"
    CLAIM_OWNER_MISMATCH = "CLAIM_OWNER_MISMATCH"
    PROVENANCE_MISMATCH = "PROVENANCE_MISMATCH"
    STATE_INVALID = "STATE_INVALID"
    TIME_INVALID = "TIME_INVALID"
    TRANSPORT_INVALID = "TRANSPORT_INVALID"
    RECOVERY_UNAUTHORIZED = "RECOVERY_UNAUTHORIZED"
    RECOVERY_TIMEOUT_NOT_REACHED = "RECOVERY_TIMEOUT_NOT_REACHED"
    RECOVERY_RECONCILED = "RECOVERY_RECONCILED"
    EFFECT_BLOCKED = "EFFECT_BLOCKED"


class _DurableMutationError(ValidationError):
    def __init__(self, code: DurableClaimResultCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, init=False)
class DurableClaimKey:
    repository: str
    route_id: str
    route_epoch: int
    task_id: str
    canary_id: str
    nonce: str
    provenance_digest: str

    def __init__(self, provenance: VerifiedAuthorityProvenance) -> None:
        if not isinstance(provenance, VerifiedAuthorityProvenance):
            raise ValidationError("durable claim key requires verified provenance")
        binding = provenance.binding
        for key, value in (
            ("repository", binding.repository),
            ("route_id", binding.route_id),
            ("route_epoch", binding.route_epoch),
            ("task_id", binding.task_id),
            ("canary_id", binding.canary_id),
            ("nonce", binding.nonce),
            ("provenance_digest", binding.digest),
        ):
            object.__setattr__(self, key, value)

    @property
    def storage_id(self) -> str:
        # The one-shot identity must remain stable when an attacker substitutes
        # route or approval evidence.  Exact provenance stays in the record and
        # is compared on every read; it must not create a second storage slot.
        return canonical_hash(
            {
                "repository": self.repository,
                "route_id": self.route_id,
                "route_epoch": self.route_epoch,
                "task_id": self.task_id,
                "canary_id": self.canary_id,
                "nonce": self.nonce,
            }
        )


@dataclass(frozen=True)
class DurableClaimRecord:
    key: DurableClaimKey
    claim_id: str
    holder: ClaimHolder
    provenance: AuthorityProvenanceBinding
    state: DurableClaimState
    claimed_at: str
    terminal_at: str | None = None
    terminal_reason: str | None = None
    invocation_id: str | None = None

    def __post_init__(self) -> None:
        require_identifier(self.claim_id, "durable claim_id")
        parse_rfc3339_utc(self.claimed_at, "durable claimed_at")
        if self.key.provenance_digest != self.provenance.digest:
            raise ValidationError("durable provenance digest mismatch")
        if self.state.terminal:
            if self.terminal_at is None or self.terminal_reason is None:
                raise ValidationError("terminal durable record requires time and reason")
            if parse_rfc3339_utc(self.terminal_at, "durable terminal_at") < parse_rfc3339_utc(self.claimed_at, "durable claimed_at"):
                raise ValidationError("durable terminal precedes claim")
            require_identifier(self.terminal_reason, "durable terminal_reason")
        elif self.terminal_at is not None or self.terminal_reason is not None:
            raise ValidationError("claimed durable record cannot carry terminal fields")
        if self.invocation_id is not None:
            require_identifier(self.invocation_id, "durable invocation_id")

    def document(self) -> dict[str, object]:
        return {
            "schema_version": "2.0",
            "key": dict(self.key.__dict__),
            "claim_id": self.claim_id,
            "holder": {"owner_type": self.holder.owner_type.value, "owner_instance_id": self.holder.owner_instance_id, "claimant_correlation_id": self.holder.claimant_correlation_id},
            "provenance": self.provenance.document(),
            "state": self.state.value,
            "claimed_at": self.claimed_at,
            "terminal_at": self.terminal_at,
            "terminal_reason": self.terminal_reason,
            "invocation_id": self.invocation_id,
        }

    @property
    def document_bytes(self) -> bytes:
        return json.dumps(self.document(), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_document_bytes(cls, payload: bytes, provenance: VerifiedAuthorityProvenance) -> "DurableClaimRecord":
        try:
            value = strict_json_loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, ValidationError) as exc:
            raise ValidationError("durable claim document invalid") from exc
        if not isinstance(value, dict) or value.get("schema_version") != "2.0":
            raise ValidationError("durable claim document schema unsupported")
        if not isinstance(value.get("key"), dict) or not isinstance(value.get("holder"), dict) or not isinstance(value.get("provenance"), dict):
            raise ValidationError("durable claim document binding missing")
        try:
            key = DurableClaimKey(provenance)
            if value["key"] != key.__dict__ or value["provenance"] != provenance.binding.document():
                raise ValidationError("durable claim document provenance substitution")
            holder = value["holder"]
            return cls(
                key=key,
                claim_id=value["claim_id"],
                holder=ClaimHolder(OwnerType(holder["owner_type"]), holder["owner_instance_id"], holder["claimant_correlation_id"]),
                provenance=provenance.binding,
                state=DurableClaimState(value["state"]),
                claimed_at=value["claimed_at"],
                terminal_at=value.get("terminal_at"),
                terminal_reason=value.get("terminal_reason"),
                invocation_id=value.get("invocation_id"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("durable claim document field invalid") from exc


@dataclass(frozen=True)
class RevisionedObject:
    revision: str | None
    payload: bytes | None
    payload_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.revision is None:
            if self.payload is not None or self.payload_sha256 is not None:
                raise ValidationError("missing durable revision cannot carry payload")
        else:
            if _REVISION.fullmatch(self.revision) is None or self.payload is None:
                raise ValidationError("durable object revision/payload mismatch")
            digest = hashlib.sha256(self.payload).hexdigest()
            if self.payload_sha256 is not None and self.payload_sha256 != digest:
                raise ValidationError("durable object payload digest mismatch")
            object.__setattr__(self, "payload_sha256", digest)


@dataclass(frozen=True)
class CasWriteResult:
    applied: bool
    revision: str | None


class RevisionedObjectGateway(Protocol):
    def read(self, object_id: str) -> RevisionedObject: ...
    def compare_and_set(self, object_id: str, expected_revision: str | None, payload: bytes) -> CasWriteResult: ...


class FixedRepositoryContentCasClient(Protocol):
    def read_content(self, repository: str, ref: str, path: str) -> RevisionedObject: ...
    def compare_and_set_content(self, repository: str, ref: str, path: str, expected_revision: str | None, payload: bytes) -> CasWriteResult: ...


class FixedRepositoryGitHubCasGateway:
    def __init__(self, repository: str, ref: str, path_prefix: str, client: FixedRepositoryContentCasClient) -> None:
        if _REPOSITORY.fullmatch(repository) is None or _GIT_REF.fullmatch(ref) is None:
            raise ValidationError("fixed GitHub CAS repository or ref invalid")
        if not path_prefix or path_prefix.startswith("/") or ".." in path_prefix.split("/"):
            raise ValidationError("fixed GitHub CAS path prefix invalid")
        self._repository = repository
        self._ref = ref
        self._path_prefix = path_prefix.rstrip("/")
        self._client = client

    def _path(self, object_id: str) -> str:
        require_identifier(object_id, "durable object_id")
        return f"{self._path_prefix}/{object_id}.json"

    def read(self, object_id: str) -> RevisionedObject:
        return self._client.read_content(self._repository, self._ref, self._path(object_id))

    def compare_and_set(self, object_id: str, expected_revision: str | None, payload: bytes) -> CasWriteResult:
        return self._client.compare_and_set_content(self._repository, self._ref, self._path(object_id), expected_revision, payload)


@dataclass(frozen=True)
class DurableClaimResult:
    code: DurableClaimResultCode
    record: DurableClaimRecord | None


@dataclass(frozen=True, init=False)
class DurableEffectPermit:
    permit_type: str
    claim_id: str
    holder: ClaimHolder
    storage_id: str
    route_commit_sha1: str
    route_tree_sha1: str
    approval_comment_id: int
    issued_at: str

    def __init__(self, record: DurableClaimRecord, issued_at: str, *, _seal: object | None = None) -> None:
        if _seal is not _PERMIT_SEAL:
            raise ValidationError("effect permits are authority-internal")
        if record.state is not DurableClaimState.CLAIMED:
            raise ValidationError("only an active durable claim may receive a permit")
        parse_rfc3339_utc(issued_at, "effect permit issued_at")
        object.__setattr__(self, "permit_type", "DURABLE_CLAIM_ACQUIRED_EFFECT_MAY_PROCEED")
        object.__setattr__(self, "claim_id", record.claim_id)
        object.__setattr__(self, "holder", record.holder)
        object.__setattr__(self, "storage_id", record.key.storage_id)
        object.__setattr__(self, "route_commit_sha1", record.provenance.route_commit_sha1)
        object.__setattr__(self, "route_tree_sha1", record.provenance.route_tree_sha1)
        object.__setattr__(self, "approval_comment_id", record.provenance.approval_comment_id)
        object.__setattr__(self, "issued_at", issued_at)


class DurableClaimAuthority:
    def __init__(self, repository: str, namespace: str, gateway: RevisionedObjectGateway) -> None:
        if _REPOSITORY.fullmatch(repository) is None:
            raise ValidationError("durable authority repository must be owner/name")
        require_identifier(namespace, "durable authority namespace")
        self._repository = repository
        self._namespace = namespace
        self._gateway = gateway

    def _key(self, provenance: VerifiedAuthorityProvenance) -> DurableClaimKey:
        if provenance.binding.repository != self._repository:
            raise ValidationError("durable provenance repository mismatch")
        return DurableClaimKey(provenance)

    def _object_id(self, key: DurableClaimKey) -> str:
        return f"{self._namespace}.{key.storage_id}"

    def _read_snapshot(
        self, provenance: VerifiedAuthorityProvenance
    ) -> tuple[RevisionedObject | None, DurableClaimRecord | None, DurableClaimResultCode | None]:
        key = self._key(provenance)
        try:
            snapshot = self._gateway.read(self._object_id(key))
            record = None if snapshot.payload is None else DurableClaimRecord.from_document_bytes(snapshot.payload, provenance)
            return snapshot, record, None
        except ValidationError:
            return None, None, DurableClaimResultCode.PROVENANCE_MISMATCH
        except Exception:
            return None, None, DurableClaimResultCode.AUTHORITY_UNAVAILABLE

    def read(self, provenance: VerifiedAuthorityProvenance) -> DurableClaimResult:
        snapshot, record, error = self._read_snapshot(provenance)
        if error is not None:
            return DurableClaimResult(error, None)
        if snapshot is None:
            return DurableClaimResult(DurableClaimResultCode.AUTHORITY_UNAVAILABLE, None)
        if record is None:
            return DurableClaimResult(DurableClaimResultCode.CLAIM_NOT_FOUND, None)
        return DurableClaimResult(DurableClaimResultCode.TERMINAL_EXISTS if record.state.terminal else DurableClaimResultCode.ALREADY_CLAIMED, record)

    @staticmethod
    def _same_holder(record: DurableClaimRecord, claim_id: str, holder: ClaimHolder) -> bool:
        return record.claim_id == claim_id and record.holder == holder

    def claim(self, provenance: VerifiedAuthorityProvenance, claim_id: str, holder: ClaimHolder, claimed_at: str) -> DurableClaimResult:
        claimed = parse_rfc3339_utc(claimed_at, "durable claimed_at")
        if claimed < parse_rfc3339_utc(provenance.binding.verified_at, "provenance verified_at"):
            raise ValidationError("durable claim precedes provenance verification")
        if claimed >= parse_rfc3339_utc(provenance.binding.expires_at, "approval expires_at"):
            raise ValidationError("durable claim occurs after approval expiry")
        key = self._key(provenance)
        proposed = DurableClaimRecord(key, claim_id, holder, provenance.binding, DurableClaimState.CLAIMED, claimed_at)
        object_id = self._object_id(key)
        try:
            snapshot = self._gateway.read(object_id)
            if snapshot.payload is not None:
                existing = DurableClaimRecord.from_document_bytes(snapshot.payload, provenance)
                return DurableClaimResult(DurableClaimResultCode.TERMINAL_EXISTS if existing.state.terminal else DurableClaimResultCode.ALREADY_CLAIMED, existing)
            result = self._gateway.compare_and_set(object_id, None, proposed.document_bytes)
            if result.applied:
                return DurableClaimResult(DurableClaimResultCode.CLAIMED, proposed)
        except ValidationError:
            return DurableClaimResult(DurableClaimResultCode.PROVENANCE_MISMATCH, None)
        except Exception:
            return DurableClaimResult(DurableClaimResultCode.AUTHORITY_UNAVAILABLE, None)
        observed = self.read(provenance)
        if observed.code is DurableClaimResultCode.CLAIM_NOT_FOUND:
            return DurableClaimResult(DurableClaimResultCode.CAS_CONFLICT, None)
        return observed

    def acquire_effect_permit(self, provenance: VerifiedAuthorityProvenance, claim_id: str, holder: ClaimHolder, issued_at: str) -> DurableEffectPermit | None:
        """Legacy effect issuance is permanently fail closed in E46.

        A positive permit can only be minted by the durable execution lease
        transition from CAPABILITY_ATTESTED to EFFECT_AUTHORIZED.
        """

        return None

    def _mutate(
        self,
        provenance: VerifiedAuthorityProvenance,
        claim_id: str,
        holder: ClaimHolder,
        transform,
        success_code: DurableClaimResultCode,
        validation_code: DurableClaimResultCode = DurableClaimResultCode.STATE_INVALID,
    ) -> DurableClaimResult:
        key = self._key(provenance)
        object_id = self._object_id(key)
        try:
            snapshot = self._gateway.read(object_id)
            if snapshot.payload is None:
                return DurableClaimResult(DurableClaimResultCode.CLAIM_NOT_FOUND, None)
            current = DurableClaimRecord.from_document_bytes(snapshot.payload, provenance)
        except ValidationError:
            return DurableClaimResult(DurableClaimResultCode.PROVENANCE_MISMATCH, None)
        except Exception:
            return DurableClaimResult(DurableClaimResultCode.AUTHORITY_UNAVAILABLE, None)
        if not self._same_holder(current, claim_id, holder):
            return DurableClaimResult(DurableClaimResultCode.CLAIM_OWNER_MISMATCH, current)
        if current.state.terminal:
            return DurableClaimResult(DurableClaimResultCode.TERMINAL_EXISTS, current)
        try:
            updated = transform(current)
        except _DurableMutationError as exc:
            return DurableClaimResult(exc.code, current)
        except ValidationError:
            return DurableClaimResult(validation_code, current)
        try:
            result = self._gateway.compare_and_set(object_id, snapshot.revision, updated.document_bytes)
            if result.applied:
                return DurableClaimResult(success_code, updated)
        except Exception:
            return DurableClaimResult(DurableClaimResultCode.AUTHORITY_UNAVAILABLE, current)
        reread = self.read(provenance)
        if reread.record is None:
            return DurableClaimResult(DurableClaimResultCode.CAS_CONFLICT, None)
        return DurableClaimResult(DurableClaimResultCode.CAS_CONFLICT, reread.record)

    def attach_invocation(self, provenance: VerifiedAuthorityProvenance, claim_id: str, holder: ClaimHolder, invocation_id: str) -> DurableClaimResult:
        """Legacy direct attachment is blocked; an E46 lease permit is mandatory."""

        current = self.read(provenance)
        return DurableClaimResult(DurableClaimResultCode.EFFECT_BLOCKED, current.record)

    def attach_invocation_with_effect_permit(
        self,
        provenance: VerifiedAuthorityProvenance,
        effect_permit: object,
        invocation_id: str,
    ) -> DurableClaimResult:
        """Attach exactly one invocation using a lease-minted permit."""

        from .execution_lease import LeaseEffectPermit

        try:
            require_identifier(invocation_id, "durable invocation_id")
        except ValidationError:
            return DurableClaimResult(DurableClaimResultCode.INVOCATION_MISMATCH, None)
        if not isinstance(effect_permit, LeaseEffectPermit):
            return DurableClaimResult(DurableClaimResultCode.EFFECT_BLOCKED, None)
        current = self.read(provenance)
        record = current.record
        if record is None:
            return DurableClaimResult(current.code, None)
        if (
            record.state is not DurableClaimState.CLAIMED
            or effect_permit.provenance_digest != provenance.binding.digest
            or effect_permit.storage_id != record.key.storage_id
            or effect_permit.claim_id != record.claim_id
            or effect_permit.holder != record.holder
            or effect_permit.lease_version != 2
        ):
            return DurableClaimResult(DurableClaimResultCode.EFFECT_BLOCKED, record)
        if record.invocation_id is not None:
            return DurableClaimResult(
                DurableClaimResultCode.DUPLICATE_INVOCATION if record.invocation_id == invocation_id else DurableClaimResultCode.INVOCATION_MISMATCH,
                record,
            )
        return self._mutate(
            provenance,
            record.claim_id,
            record.holder,
            lambda active: replace(active, invocation_id=invocation_id),
            DurableClaimResultCode.INVOCATION_ATTACHED,
        )

    def finalize(
        self,
        provenance: VerifiedAuthorityProvenance,
        claim_id: str,
        holder: ClaimHolder,
        state: DurableClaimState,
        terminal_reason: str,
        terminal_at: str,
        *,
        invocation_id: str | None = None,
    ) -> DurableClaimResult:
        """Legacy direct finalization is permanently fail closed in E46."""

        current = self.read(provenance)
        return DurableClaimResult(DurableClaimResultCode.EFFECT_BLOCKED, current.record)

    def finalize_with_attested_terminal(
        self,
        provenance: VerifiedAuthorityProvenance,
        terminal_authorization: object,
    ) -> DurableClaimResult:
        """The only positive E46 terminal mutation boundary.

        The authorization is sealed and minted only after the durable lease has
        reached TERMINAL_ATTESTED.  Journal and lease commit orchestration live
        in `DurableExecutionLeaseAuthority`.
        """

        from .execution_lease import JournaledTerminalMutationPermit

        if not isinstance(terminal_authorization, JournaledTerminalMutationPermit):
            return DurableClaimResult(DurableClaimResultCode.EFFECT_BLOCKED, None)
        mutation_permit = terminal_authorization
        terminal_authorization = mutation_permit.authorization
        current = self.read(provenance)
        record = current.record
        if record is None:
            return DurableClaimResult(current.code, None)
        authorization = terminal_authorization
        if (
            authorization.provenance_digest != provenance.binding.digest
            or authorization.storage_id != record.key.storage_id
            or authorization.claim_id != record.claim_id
            or authorization.holder != record.holder
            or authorization.invocation_id != record.invocation_id
            or authorization.lease_version != 4
            or not authorization.terminal_state.terminal
        ):
            return DurableClaimResult(DurableClaimResultCode.EFFECT_BLOCKED, record)

        def transform(active: DurableClaimRecord) -> DurableClaimRecord:
            if active.invocation_id != authorization.invocation_id:
                raise _DurableMutationError(DurableClaimResultCode.INVOCATION_MISMATCH, "attested invocation differs from durable claim")
            return replace(
                active,
                state=authorization.terminal_state,
                terminal_reason=authorization.terminal_reason,
                terminal_at=authorization.terminal_at,
            )

        return self._mutate(
            provenance,
            authorization.claim_id,
            authorization.holder,
            transform,
            DurableClaimResultCode.FINALIZED,
            DurableClaimResultCode.TIME_INVALID,
        )

    def recover_expired_claim(
        self,
        provenance: VerifiedAuthorityProvenance,
        claim_id: str,
        holder: ClaimHolder,
        observed_at: str,
        timeout_seconds: int,
    ) -> DurableClaimResult:
        """Legacy holder recovery path retained only as a fail-closed diagnostic.

        E45 removes this mutation path.  Recovery now requires a separately
        issued and durably consumed `RecoveryAuthorizationGrant` at the exact
        governed mutation boundary.
        """

        current = self.read(provenance)
        return DurableClaimResult(DurableClaimResultCode.RECOVERY_UNAUTHORIZED, current.record)

    def governed_recover_expired_claim(
        self,
        provenance: VerifiedAuthorityProvenance,
        recovery_grant: object,
        recovery_ledger: object,
        observed_at: str,
    ) -> DurableClaimResult:
        """Mark a timed-out claim for reconciliation without holder powers.

        The recovery grant is bound to one original claim and holder and is
        consumed before this method mutates the durable claim.  A consumed,
        unavailable, stale, or mismatched grant never reports recovery success.
        """

        # Local import avoids a module cycle while making the integration
        # explicit: the durable recovery mutation is downstream of the E45
        # ledger, rather than merely adjacent to it.
        from .durable_challenge import LedgerCode, RecoveryAuthorizationGrant, RecoveryAuthorizationLedger

        if not isinstance(recovery_grant, RecoveryAuthorizationGrant) or not isinstance(recovery_ledger, RecoveryAuthorizationLedger):
            return DurableClaimResult(DurableClaimResultCode.RECOVERY_UNAUTHORIZED, None)
        observed = parse_rfc3339_utc(observed_at, "governed recovery observed_at")
        if observed < parse_rfc3339_utc(recovery_grant.not_before, "recovery not_before"):
            return DurableClaimResult(DurableClaimResultCode.RECOVERY_TIMEOUT_NOT_REACHED, None)
        if observed >= parse_rfc3339_utc(recovery_grant.expires_at, "recovery expires_at"):
            return DurableClaimResult(DurableClaimResultCode.RECOVERY_UNAUTHORIZED, None)
        key = self._key(provenance)
        object_id = self._object_id(key)
        try:
            snapshot = self._gateway.read(object_id)
            if snapshot.payload is None:
                return DurableClaimResult(DurableClaimResultCode.CLAIM_NOT_FOUND, None)
            current = DurableClaimRecord.from_document_bytes(snapshot.payload, provenance)
        except ValidationError:
            return DurableClaimResult(DurableClaimResultCode.PROVENANCE_MISMATCH, None)
        except Exception:
            return DurableClaimResult(DurableClaimResultCode.AUTHORITY_UNAVAILABLE, None)
        if current.claim_id != recovery_grant.claim_id or current.holder != recovery_grant.original_holder:
            return DurableClaimResult(DurableClaimResultCode.RECOVERY_UNAUTHORIZED, current)
        if current.state.terminal:
            return DurableClaimResult(DurableClaimResultCode.TERMINAL_EXISTS, current)
        if observed < parse_rfc3339_utc(current.claimed_at, "durable claimed_at"):
            return DurableClaimResult(DurableClaimResultCode.TIME_INVALID, current)
        consumed = recovery_ledger.consume(recovery_grant, current, observed_at)
        if consumed.code is LedgerCode.UNAVAILABLE:
            return DurableClaimResult(DurableClaimResultCode.AUTHORITY_UNAVAILABLE, current)
        if consumed.code is not LedgerCode.CONSUMED:
            return DurableClaimResult(DurableClaimResultCode.RECOVERY_UNAUTHORIZED, current)
        updated = replace(
            current,
            state=DurableClaimState.RECOVERY_REQUIRED,
            terminal_reason=recovery_grant.reason,
            terminal_at=observed_at,
        )
        try:
            result = self._gateway.compare_and_set(object_id, snapshot.revision, updated.document_bytes)
            if result.applied:
                return DurableClaimResult(DurableClaimResultCode.RECOVERY_RECONCILED, updated)
        except Exception:
            return DurableClaimResult(DurableClaimResultCode.AUTHORITY_UNAVAILABLE, current)
        reread = self.read(provenance)
        return DurableClaimResult(DurableClaimResultCode.CAS_CONFLICT, reread.record)


class SyntheticFileCasGateway:
    """Atomic file CAS used only by deterministic tests."""

    def __init__(self, root: Path, *, lock_timeout_seconds: float = 3.0) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        if not isinstance(lock_timeout_seconds, (int, float)) or lock_timeout_seconds <= 0:
            raise ValidationError("synthetic CAS lock timeout must be positive")
        self._lock_timeout_seconds = float(lock_timeout_seconds)

    def _path(self, object_id: str) -> Path:
        require_identifier(object_id, "durable object_id")
        return self._root / f"{object_id}.json"

    def read(self, object_id: str) -> RevisionedObject:
        path = self._path(object_id)
        if not path.exists():
            return RevisionedObject(None, None)
        payload = path.read_bytes()
        return RevisionedObject(hashlib.sha256(payload).hexdigest(), payload)

    @contextmanager
    def _lock(self, object_id: str) -> Iterator[None]:
        lock_path = self._root / f"{object_id}.lock"
        deadline = time.monotonic() + self._lock_timeout_seconds
        descriptor: int | None = None
        while descriptor is None:
            try:
                descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise OSError("synthetic_cas_lock_timeout")
                time.sleep(0.005)
        try:
            yield
        finally:
            os.close(descriptor)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    def compare_and_set(self, object_id: str, expected_revision: str | None, payload: bytes) -> CasWriteResult:
        if not isinstance(payload, bytes) or not payload:
            raise ValidationError("durable CAS payload must be nonempty bytes")
        if expected_revision is not None and _REVISION.fullmatch(expected_revision) is None:
            raise ValidationError("durable CAS expected revision invalid")
        path = self._path(object_id)
        with self._lock(object_id):
            current = self.read(object_id)
            if current.revision != expected_revision:
                return CasWriteResult(False, current.revision)
            descriptor, temporary = tempfile.mkstemp(prefix=f"{object_id}.", suffix=".tmp", dir=self._root)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            return CasWriteResult(True, hashlib.sha256(payload).hexdigest())
