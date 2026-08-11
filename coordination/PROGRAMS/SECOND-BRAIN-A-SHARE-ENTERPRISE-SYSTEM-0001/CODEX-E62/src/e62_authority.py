"""PUBLIC_SAFE E62 authority-state-machine candidate.

This module intentionally models contracts only.  ``SyntheticTestSigner`` is
not an AWS KMS replacement and no class here can activate a real authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import hmac
import json
import re
from typing import Dict, Optional


SHA256 = re.compile(r"^[0-9a-f]{64}$")
LEGACY_HASH = re.compile(r"^[0-9a-f]{16}$")


class AuthorityError(ValueError):
    """A request failed closed before a capability could be consumed."""


class GrantState(str, Enum):
    APPROVED = "APPROVED"
    CLAIMED = "CLAIMED"
    SIGNED = "SIGNED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    WRITE_CONSUMED = "WRITE_CONSUMED"


@dataclass(frozen=True)
class DigestBundle:
    raw_artifact_sha256: str
    canonical_semantic_sha256: str
    l0_provenance_sha256: str
    legacy_short_content_hash: Optional[str] = None

    def __post_init__(self) -> None:
        for value in (
            self.raw_artifact_sha256,
            self.canonical_semantic_sha256,
            self.l0_provenance_sha256,
        ):
            if not SHA256.fullmatch(value):
                raise AuthorityError("all production digest fields must be lowercase SHA-256")
        if self.legacy_short_content_hash and not LEGACY_HASH.fullmatch(self.legacy_short_content_hash):
            raise AuthorityError("legacy content hash is compatibility-only 16 lowercase hex")


@dataclass(frozen=True)
class RequesterContext:
    repository: str
    workflow_ref: str
    ref: str
    audience: str
    route_epoch: int
    task_id: str


@dataclass(frozen=True)
class AuthorityPolicy:
    repository: str
    workflow_ref: str
    ref: str = "refs/heads/main"
    audience: str = "aws-a1-certification-issuer"
    route_epoch: int = 69
    task_id: str = "CODEX-AWS-A1-PRODUCTION-CERTIFICATION-AUTHORITY-AND-PRIVATE-GIT-WRITE-GATE-0058-E62"
    key_id: str = "AWS_KMS_ASYMMETRIC_PLACEHOLDER"
    key_version: str = "v1"

    def validate_requester(self, context: RequesterContext) -> None:
        if context != RequesterContext(
            self.repository, self.workflow_ref, self.ref, self.audience, self.route_epoch, self.task_id
        ):
            raise AuthorityError("requester context does not satisfy the exact OIDC policy")


@dataclass
class ApprovalRecord:
    grant_id: str
    bundle: DigestBundle
    scope: str
    target: str
    approval_ref: str
    approval_identity_ref: str
    expires_at: datetime
    nonce: str
    state: GrantState = GrantState.APPROVED
    claim_token: Optional[str] = None
    signed_grant: Optional["ProductionCertificationGrant"] = None
    reconciliation_ref: Optional[str] = None


@dataclass(frozen=True)
class ProductionCertificationGrant:
    grant_id: str
    bundle: DigestBundle
    scope: str
    target: str
    approval_ref: str
    approval_identity_ref: str
    requester: RequesterContext
    key_id: str
    key_version: str
    issued_at: datetime
    expires_at: datetime
    nonce: str
    signature: str

    def payload_bytes(self) -> bytes:
        payload = {
            "approval_identity_ref": self.approval_identity_ref,
            "approval_ref": self.approval_ref,
            "bundle": self.bundle.__dict__,
            "expires_at": self.expires_at.isoformat(),
            "grant_id": self.grant_id,
            "issued_at": self.issued_at.isoformat(),
            "key_id": self.key_id,
            "key_version": self.key_version,
            "nonce": self.nonce,
            "requester": self.requester.__dict__,
            "scope": self.scope,
            "target": self.target,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class SyntheticTestSigner:
    """Deterministic test-only signer; it must never be used as production KMS."""

    test_only = True

    def __init__(self, fixture_key: bytes = b"PUBLIC_SAFE_E62_TEST_VECTOR_ONLY") -> None:
        self._fixture_key = fixture_key

    def sign(self, payload: bytes) -> str:
        return hmac.new(self._fixture_key, payload, hashlib.sha256).hexdigest()

    def verify(self, payload: bytes, signature: str) -> bool:
        return hmac.compare_digest(self.sign(payload), signature)


class ApprovalGrantLedger:
    """In-memory model of conditional DynamoDB transitions, not a real ledger."""

    def __init__(self, policy: AuthorityPolicy, signer: SyntheticTestSigner) -> None:
        if not signer.test_only:
            raise AuthorityError("E62 local model accepts only an explicitly synthetic signer")
        self.policy, self.signer, self.records = policy, signer, {}

    def load_external_preapproval(self, record: ApprovalRecord) -> None:
        """Load a record created outside requester authority; duplicates are denied."""
        if record.grant_id in self.records:
            raise AuthorityError("grant_id already exists")
        if record.state is not GrantState.APPROVED:
            raise AuthorityError("only an external APPROVED record may enter the issuer ledger")
        self.records[record.grant_id] = record

    def _get_live(self, grant_id: str, now: datetime) -> ApprovalRecord:
        record = self.records.get(grant_id)
        if not record:
            raise AuthorityError("unknown approval")
        if record.state is GrantState.REVOKED:
            raise AuthorityError("approval revoked")
        if now >= record.expires_at:
            record.state = GrantState.EXPIRED
            raise AuthorityError("approval expired")
        return record

    def claim(self, grant_id: str, context: RequesterContext, claim_token: str, now: datetime) -> ApprovalRecord:
        self.policy.validate_requester(context)
        record = self._get_live(grant_id, now)
        if record.state is GrantState.APPROVED:
            record.state, record.claim_token = GrantState.CLAIMED, claim_token
            return record
        if record.state in (GrantState.CLAIMED, GrantState.FAILED_RETRYABLE) and record.claim_token == claim_token:
            return record
        if record.state is GrantState.SIGNED and record.claim_token == claim_token:
            return record
        raise AuthorityError("approval cannot be concurrently or repeatedly claimed")

    def mark_kms_outcome_unknown(self, grant_id: str, claim_token: str, reconciliation_ref: str) -> None:
        record = self.records[grant_id]
        if record.state is not GrantState.CLAIMED or record.claim_token != claim_token:
            raise AuthorityError("only the current claim may enter outcome-unknown")
        record.state, record.reconciliation_ref = GrantState.OUTCOME_UNKNOWN, reconciliation_ref

    def mark_retryable_before_sign(self, grant_id: str, claim_token: str) -> None:
        record = self.records[grant_id]
        if record.state is not GrantState.CLAIMED or record.claim_token != claim_token:
            raise AuthorityError("only the current pre-sign claim may retry")
        record.state = GrantState.FAILED_RETRYABLE

    def reconcile_unknown_as_not_signed(self, grant_id: str, reconciliation_ref: str) -> None:
        record = self.records[grant_id]
        if record.state is not GrantState.OUTCOME_UNKNOWN or record.reconciliation_ref != reconciliation_ref:
            raise AuthorityError("unknown KMS outcome requires matching reconciliation evidence")
        record.state = GrantState.FAILED_RETRYABLE

    def sign_claim(self, grant_id: str, context: RequesterContext, claim_token: str, now: datetime) -> ProductionCertificationGrant:
        self.policy.validate_requester(context)
        record = self._get_live(grant_id, now)
        if record.state is GrantState.SIGNED and record.claim_token == claim_token and record.signed_grant:
            return record.signed_grant
        if record.state not in (GrantState.CLAIMED, GrantState.FAILED_RETRYABLE) or record.claim_token != claim_token:
            raise AuthorityError("sign requires the current claimed approval")
        unsigned = ProductionCertificationGrant(
            record.grant_id, record.bundle, record.scope, record.target,
            record.approval_ref, record.approval_identity_ref, context,
            self.policy.key_id, self.policy.key_version, now, record.expires_at,
            record.nonce, "",
        )
        signature = self.signer.sign(unsigned.payload_bytes())
        grant = ProductionCertificationGrant(**{**unsigned.__dict__, "signature": signature})
        record.signed_grant, record.state = grant, GrantState.SIGNED
        return grant

    def revoke(self, grant_id: str) -> None:
        record = self.records.get(grant_id)
        if not record or record.state is GrantState.WRITE_CONSUMED:
            raise AuthorityError("cannot revoke unknown or already-consumed approval")
        record.state = GrantState.REVOKED


class GrantVerifier:
    def __init__(self, policy: AuthorityPolicy, signer: SyntheticTestSigner) -> None:
        self.policy, self.signer = policy, signer

    def verify(self, grant: ProductionCertificationGrant, now: datetime) -> None:
        if grant.key_id != self.policy.key_id or grant.key_version != self.policy.key_version:
            raise AuthorityError("untrusted authority key")
        self.policy.validate_requester(grant.requester)
        if now >= grant.expires_at:
            raise AuthorityError("grant expired")
        unsigned = ProductionCertificationGrant(**{**grant.__dict__, "signature": ""})
        if not self.signer.verify(unsigned.payload_bytes(), grant.signature):
            raise AuthorityError("invalid canonical signing payload or signature")


@dataclass(frozen=True)
class FormalWriteReceipt:
    grant_id: str
    target: str
    expected_parent: str
    formal_record_digest: str


class PrivateGitWriteGate:
    """Second, independent one-time consumption gate for a future private Git SOR."""

    def __init__(self, ledger: ApprovalGrantLedger, verifier: GrantVerifier) -> None:
        self.ledger, self.verifier = ledger, verifier

    def consume(
        self, grant: ProductionCertificationGrant, expected_parent: str, current_parent: str,
        formal_record_digest: str, now: datetime,
    ) -> FormalWriteReceipt:
        self.verifier.verify(grant, now)
        record = self.ledger.records.get(grant.grant_id)
        if not record or record.state is not GrantState.SIGNED or record.signed_grant != grant:
            raise AuthorityError("grant is not an active ledger-issued capability")
        if grant.target != "future-private-git-knowledge":
            raise AuthorityError("wrong formal knowledge target")
        if expected_parent != current_parent:
            raise AuthorityError("stale private-Git expected-parent CAS")
        if not SHA256.fullmatch(formal_record_digest):
            raise AuthorityError("formal record digest must be SHA-256")
        record.state = GrantState.WRITE_CONSUMED
        return FormalWriteReceipt(grant.grant_id, grant.target, expected_parent, formal_record_digest)
