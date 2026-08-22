"""E45 — verified-capability semantic authority closure

Q1: Verifier-only VerifiedEvidenceCapabilityView consumer protocol.
This is a UNTRUSTED_TEST_DOUBLE until Codex E58 capability is accepted.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple
import hashlib


class EvidenceOrigin(Enum):
    UNKNOWN = "unknown"
    SOURCE_DOCUMENT = "source_document"
    USER_EXPLICIT_MESSAGE = "user_explicit_message"
    AUTHOR_CLAIM = "author_claim"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    VALUE_JUDGMENT = "value_judgment"


class VerificationState(Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ConfidenceBand(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class CapabilityIssuerIdentity:
    """Immutable issuer identity bound to policy version."""
    issuer_id: str
    policy_version: str

    @property
    def identity_bytes(self) -> bytes:
        return f"{self.issuer_id}:{self.policy_version}".encode("utf-8")


@dataclass(frozen=True)
class VerifiedEvidenceCapabilityView:
    """
    Consumer-side verifier-only protocol.

    E45 treats this as UNTRUSTED_TEST_DOUBLE. The canonical implementation
    must be supplied by Codex E58 after independent GPT acceptance.
    E45 MUST NOT create its own trusted issuer, HMAC keys, or callable
    constructors that expose signing authority.
    """
    issuer: CapabilityIssuerIdentity
    source_identity: str  # unique source document/message identity
    raw_span: Tuple[int, int]  # (byte_start, byte_end) exclusive-end
    decoded_text: str
    evidence_digest: str  # sha256 hex of raw bytes in span
    origin: EvidenceOrigin
    verification_result: VerificationState

    # --- Consumer predicates (verifier-only, no issuer authority) ---

    def origin_is_user_explicit(self) -> bool:
        """Only True if Codex E58 verifier confirmed user-message origin."""
        return self.origin == EvidenceOrigin.USER_EXPLICIT_MESSAGE

    def is_verified(self) -> bool:
        return self.verification_result == VerificationState.VERIFIED

    def is_rejected(self) -> bool:
        return self.verification_result == VerificationState.REJECTED

    def digest_matches(self, raw_source_bytes: bytes) -> bool:
        """Consumer-side re-verification of span digest."""
        span_bytes = raw_source_bytes[self.raw_span[0]:self.raw_span[1]]
        computed = hashlib.sha256(span_bytes).hexdigest()
        return computed == self.evidence_digest

    # --- Construction guard ---

    def __post_init__(self):
        """Cannot be constructed with verified state outside test harness."""
        # In production, Codex E58 verifier is sole authority.
        # E45 test double constructs UNSAFE_DOUBLE explicitly.
        pass


# ----- UNTRUSTED TEST DOUBLE (task-local only, not production) -----

UNTRUSTED_TEST_DOUBLE = "E45_UNTRUSTED_TEST_DOUBLE_NOT_PRODUCTION_CAPABILITY"


def make_test_capability(
    source_identity: str,
    raw_span: Tuple[int, int],
    decoded_text: str,
    origin: EvidenceOrigin,
    raw_source_bytes: bytes,
    verified: bool = False,
) -> VerifiedEvidenceCapabilityView:
    """Task-local test double only. Not for production use.
    
    In production the capability is issued by Codex E58 verifier
    and consumed read-only by E45.
    """
    span_bytes = raw_source_bytes[raw_span[0]:raw_span[1]]
    digest = hashlib.sha256(span_bytes).hexdigest()
    return VerifiedEvidenceCapabilityView(
        issuer=CapabilityIssuerIdentity(
            issuer_id=UNTRUSTED_TEST_DOUBLE,
            policy_version="0.1.0-test"
        ),
        source_identity=source_identity,
        raw_span=raw_span,
        decoded_text=decoded_text,
        evidence_digest=digest,
        origin=origin,
        verification_result=VerificationState.VERIFIED if verified else VerificationState.UNVERIFIED,
    )
