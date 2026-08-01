"""Read-only approval and remote-route proof contracts for E37.

The module accepts transient document bytes from a separately controlled
read-only fetcher. It does not contain an HTTP client, webhook handler, or
executor. Persistent callers receive only hashes and public metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
import hashlib
from typing import Mapping

from .models import (
    BoundCanaryApproval,
    RouteRef,
    ValidationError,
    parse_rfc3339_utc,
    require_identifier,
    require_sha1,
    require_sha256,
)


CANONICAL_ACTIVE_TASK_PATH = "coordination/ACTIVE-CODEX-TASK.yaml"
CANONICAL_COORDINATION_PATH = "coordination/ACTIVE-THREE-AGENT-COORDINATION.yaml"
CANONICAL_MAIN_REF = "refs/heads/main"
DEFAULT_MAX_ROUTE_PROOF_AGE_SECONDS = 300
_APPROVAL_VERIFIER_SEAL = object()
_ROUTE_VERIFIER_SEAL = object()


class VerificationStatus(str, Enum):
    READ_ONLY_FETCH_VERIFIED = "READ_ONLY_FETCH_VERIFIED"
    UNKNOWN = "UNKNOWN"
    REJECTED = "REJECTED"


def canonical_approval_ref(repository: str, issue_number: int, comment_id: int) -> str:
    return f"github://{repository}/issues/{issue_number}/comments/{comment_id}"


def _require_repository(value: str) -> str:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValidationError("repository must be an owner/name identifier")
    owner, name = value.split("/")
    require_identifier(owner, "repository owner")
    require_identifier(name, "repository name")
    return value


def _require_positive(value: int, label: str) -> int:
    if not isinstance(value, int) or value < 1:
        raise ValidationError(f"{label} must be a positive integer")
    return value


@dataclass(frozen=True)
class ReadOnlyApprovalDocument:
    """Transient GitHub comment data supplied by an external read-only reader."""

    repository: str
    issue_number: int
    comment_id: int
    actor: str
    issued_at: str
    body: str

    def __post_init__(self) -> None:
        _require_repository(self.repository)
        _require_positive(self.issue_number, "issue_number")
        _require_positive(self.comment_id, "comment_id")
        require_identifier(self.actor, "approval actor")
        parse_rfc3339_utc(self.issued_at, "approval issued_at")
        if not isinstance(self.body, str):
            raise ValidationError("approval body must be text")

    @property
    def approval_ref(self) -> str:
        return canonical_approval_ref(self.repository, self.issue_number, self.comment_id)

    @property
    def body_sha256(self) -> str:
        return hashlib.sha256(self.body.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ApprovalEvidence:
    repository: str
    issue_number: int
    comment_id: int
    actor: str
    issued_at: str
    body_sha256: str
    approval_ref: str
    binding_payload_sha256: str

    def __post_init__(self) -> None:
        _require_repository(self.repository)
        _require_positive(self.issue_number, "issue_number")
        _require_positive(self.comment_id, "comment_id")
        require_identifier(self.actor, "approval actor")
        parse_rfc3339_utc(self.issued_at, "approval issued_at")
        require_sha256(self.body_sha256, "approval body_sha256")
        require_sha256(self.binding_payload_sha256, "approval binding_payload_sha256")
        if self.approval_ref != canonical_approval_ref(self.repository, self.issue_number, self.comment_id):
            raise ValidationError("approval_ref must bind the exact repository issue and comment")

    @classmethod
    def from_document(cls, approval: BoundCanaryApproval, document: ReadOnlyApprovalDocument) -> "ApprovalEvidence":
        return cls(
            repository=document.repository,
            issue_number=document.issue_number,
            comment_id=document.comment_id,
            actor=document.actor,
            issued_at=document.issued_at,
            body_sha256=document.body_sha256,
            approval_ref=document.approval_ref,
            binding_payload_sha256=approval.binding_payload_hash(),
        )

    def validates(self, approval: BoundCanaryApproval, checked_at: str) -> str | None:
        checked = parse_rfc3339_utc(checked_at, "approval checked_at")
        if approval.repository != self.repository:
            return "approval_repository_mismatch"
        if approval.issue_number != self.issue_number or approval.comment_id != self.comment_id:
            return "approval_comment_mismatch"
        if approval.actor != self.actor:
            return "approval_actor_mismatch"
        if approval.issued_at != self.issued_at:
            return "approval_issued_at_mismatch"
        if approval.body_sha256 != self.body_sha256:
            return "approval_body_hash_mismatch"
        if approval.approval_ref != self.approval_ref:
            return "approval_ref_mismatch"
        if self.binding_payload_sha256 != approval.binding_payload_hash():
            return "approval_binding_payload_mismatch"
        if parse_rfc3339_utc(self.issued_at, "approval issued_at") > checked:
            return "approval_issued_in_future"
        return None


@dataclass(frozen=True, init=False)
class ApprovalVerificationResult:
    status: VerificationStatus
    evidence: ApprovalEvidence | None
    verified_at: str
    reason_code: str

    def __init__(
        self,
        status: VerificationStatus,
        evidence: ApprovalEvidence | None,
        verified_at: str,
        reason_code: str,
        *,
        _seal: object | None = None,
    ) -> None:
        if _seal is not _APPROVAL_VERIFIER_SEAL:
            raise ValidationError("approval verification results must come from the read-only verifier")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "verified_at", verified_at)
        object.__setattr__(self, "reason_code", reason_code)
        parse_rfc3339_utc(self.verified_at, "approval verified_at")
        require_identifier(self.reason_code, "approval verification reason")
        if self.status is VerificationStatus.READ_ONLY_FETCH_VERIFIED and self.evidence is None:
            raise ValidationError("verified approval result requires immutable evidence")
        if self.status is not VerificationStatus.READ_ONLY_FETCH_VERIFIED and self.evidence is not None:
            raise ValidationError("unverified approval result must not carry trusted evidence")

    @classmethod
    def verified(cls, evidence: ApprovalEvidence, verified_at: str, reason_code: str) -> "ApprovalVerificationResult":
        return cls(VerificationStatus.READ_ONLY_FETCH_VERIFIED, evidence, verified_at, reason_code, _seal=_APPROVAL_VERIFIER_SEAL)

    @classmethod
    def rejected(cls, verified_at: str, reason_code: str) -> "ApprovalVerificationResult":
        return cls(VerificationStatus.REJECTED, None, verified_at, reason_code, _seal=_APPROVAL_VERIFIER_SEAL)

    @classmethod
    def unknown(cls, verified_at: str, reason_code: str) -> "ApprovalVerificationResult":
        return cls(VerificationStatus.UNKNOWN, None, verified_at, reason_code, _seal=_APPROVAL_VERIFIER_SEAL)

    def validates(self, approval: BoundCanaryApproval, checked_at: str) -> str | None:
        if self.status is not VerificationStatus.READ_ONLY_FETCH_VERIFIED:
            return "approval_read_only_verification_required"
        assert self.evidence is not None
        return self.evidence.validates(approval, checked_at)


class ReadOnlyApprovalVerifier:
    """Derive an approval result from fetched comment metadata without persistence."""

    def verify(
        self,
        approval: BoundCanaryApproval,
        document: ReadOnlyApprovalDocument,
        checked_at: str,
    ) -> ApprovalVerificationResult:
        parse_rfc3339_utc(checked_at, "approval checked_at")
        evidence = ApprovalEvidence.from_document(approval, document)
        error = evidence.validates(approval, checked_at)
        if error is not None:
            return ApprovalVerificationResult.rejected(checked_at, error)
        return ApprovalVerificationResult.verified(
            evidence,
            checked_at,
            "read_only_comment_identity_and_hash_verified",
        )


@dataclass(frozen=True)
class RouteFileIdentity:
    path: str
    blob_sha1: str
    content_sha256: str

    def __post_init__(self) -> None:
        if self.path not in {CANONICAL_ACTIVE_TASK_PATH, CANONICAL_COORDINATION_PATH}:
            raise ValidationError("route proof path is not one of the two canonical route files")
        require_sha1(self.blob_sha1, "route blob_sha1")
        require_sha256(self.content_sha256, "route content_sha256")


@dataclass(frozen=True)
class RouteStateEvidence:
    """Caller-supplied route identity. It is insufficient until independently verified."""

    route: RouteRef
    repository: str
    ref: str
    main_commit_sha1: str
    active_task: RouteFileIdentity
    coordination: RouteFileIdentity
    observed_at: str

    def __post_init__(self) -> None:
        _require_repository(self.repository)
        if self.ref != CANONICAL_MAIN_REF:
            raise ValidationError("route proof ref must be refs/heads/main")
        require_sha1(self.main_commit_sha1, "route main_commit_sha1")
        if self.active_task.path != CANONICAL_ACTIVE_TASK_PATH:
            raise ValidationError("active task route path mismatch")
        if self.coordination.path != CANONICAL_COORDINATION_PATH:
            raise ValidationError("coordination route path mismatch")
        parse_rfc3339_utc(self.observed_at, "route state observed_at")


@dataclass(frozen=True, init=False)
class RouteProofVerification:
    status: VerificationStatus
    evidence: RouteStateEvidence | None
    verified_at: str
    reason_code: str

    def __init__(
        self,
        status: VerificationStatus,
        evidence: RouteStateEvidence | None,
        verified_at: str,
        reason_code: str,
        *,
        _seal: object | None = None,
    ) -> None:
        if _seal is not _ROUTE_VERIFIER_SEAL:
            raise ValidationError("route proof results must come from the read-only verifier")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "verified_at", verified_at)
        object.__setattr__(self, "reason_code", reason_code)
        parse_rfc3339_utc(self.verified_at, "route proof verified_at")
        require_identifier(self.reason_code, "route proof reason")
        if self.status is VerificationStatus.READ_ONLY_FETCH_VERIFIED and self.evidence is None:
            raise ValidationError("verified route proof requires evidence")
        if self.status is not VerificationStatus.READ_ONLY_FETCH_VERIFIED and self.evidence is not None:
            raise ValidationError("unverified route proof must not carry trusted evidence")

    @classmethod
    def verified(cls, evidence: RouteStateEvidence, verified_at: str, reason_code: str) -> "RouteProofVerification":
        return cls(VerificationStatus.READ_ONLY_FETCH_VERIFIED, evidence, verified_at, reason_code, _seal=_ROUTE_VERIFIER_SEAL)

    @classmethod
    def rejected(cls, verified_at: str, reason_code: str) -> "RouteProofVerification":
        return cls(VerificationStatus.REJECTED, None, verified_at, reason_code, _seal=_ROUTE_VERIFIER_SEAL)

    @classmethod
    def unknown(cls, verified_at: str, reason_code: str) -> "RouteProofVerification":
        return cls(VerificationStatus.UNKNOWN, None, verified_at, reason_code, _seal=_ROUTE_VERIFIER_SEAL)

    def validates(self, route: RouteRef) -> str | None:
        if self.status is not VerificationStatus.READ_ONLY_FETCH_VERIFIED:
            return "route_read_only_verification_required"
        assert self.evidence is not None
        if self.evidence.route != route:
            return "route_proof_route_mismatch"
        return None


def _git_blob_sha1(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


class ReadOnlyRouteProofVerifier:
    """Recompute both file identities from transient, exact-commit document bytes."""

    def verify(
        self,
        evidence: RouteStateEvidence,
        documents: Mapping[str, bytes],
        expected_repository: str,
        expected_main_commit_sha1: str,
        checked_at: str,
        max_age_seconds: int = DEFAULT_MAX_ROUTE_PROOF_AGE_SECONDS,
    ) -> RouteProofVerification:
        checked = parse_rfc3339_utc(checked_at, "route proof checked_at")
        _require_repository(expected_repository)
        require_sha1(expected_main_commit_sha1, "expected main_commit_sha1")
        if not isinstance(max_age_seconds, int) or max_age_seconds < 0:
            raise ValidationError("max route proof age must be a non-negative integer")
        if evidence.repository != expected_repository:
            return self._reject(checked_at, "route_repository_mismatch")
        if evidence.ref != CANONICAL_MAIN_REF:
            return self._reject(checked_at, "route_ref_mismatch")
        if evidence.main_commit_sha1 != expected_main_commit_sha1:
            return self._reject(checked_at, "route_main_commit_mismatch")
        observed = parse_rfc3339_utc(evidence.observed_at, "route state observed_at")
        if observed > checked:
            return self._reject(checked_at, "route_observation_in_future")
        if checked - observed > timedelta(seconds=max_age_seconds):
            return self._reject(checked_at, "route_proof_stale")
        for identity in (evidence.active_task, evidence.coordination):
            content = documents.get(identity.path)
            if not isinstance(content, bytes):
                return self._reject(checked_at, "route_document_missing")
            if _git_blob_sha1(content) != identity.blob_sha1:
                return self._reject(checked_at, "route_blob_hash_mismatch")
            if hashlib.sha256(content).hexdigest() != identity.content_sha256:
                return self._reject(checked_at, "route_content_hash_mismatch")
        return RouteProofVerification.verified(
            evidence,
            checked_at,
            "read_only_main_commit_blob_and_content_verified",
        )

    @staticmethod
    def _reject(checked_at: str, reason_code: str) -> RouteProofVerification:
        return RouteProofVerification.rejected(checked_at, reason_code)
