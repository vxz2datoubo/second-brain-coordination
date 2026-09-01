"""E46 Capability — Verifier-only consumer contract.

Until E59 is accepted by GPT, all local capability implementations are UNTRUSTED_TEST_DOUBLE.
No ordinary caller can construct an object that passes accepted authority gates.

Design:
- VerifiedEvidenceCapabilityView: consumer-side frozen view, never locally constructed
- CapabilityVerifier: only path to accept a capability — always fails closed pre-E59
- UntrustedTestCapability: test-only, structurally marked, never passes production gates
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import hashlib


class EvidenceOrigin(str, Enum):
    UNKNOWN = "UNKNOWN"
    EXTERNAL_SOURCE_DOCUMENT = "EXTERNAL_SOURCE_DOCUMENT"
    USER_EXPLICIT_MESSAGE = "USER_EXPLICIT_MESSAGE"
    AUTHOR_CLAIM = "AUTHOR_CLAIM"
    INFERENCE = "INFERENCE"
    HYPOTHESIS = "HYPOTHESIS"
    VALUE_JUDGMENT = "VALUE_JUDGMENT"


class VerificationResult(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    UNTRUSTED_DOUBLE = "UNTRUSTED_DOUBLE"


@dataclass(frozen=True)
class VerifiedEvidenceCapabilityView:
    """Consumer-side frozen view. Never locally constructed.
    
    Until E59 acceptance, all production instances come from CapabilityVerifier.accept()
    which always returns UNTRUSTED_DOUBLE. Test doubles use UntrustedTestCapability.
    """
    capability_id: str
    issuer_identity: str
    source_identity: str  # Opaque — no prose heuristic parsing
    raw_span: tuple  # (byte_start, byte_end) — from accepted E59 source
    decoded_text: str
    evidence_digest: str  # SHA-256 of canonical evidence bytes
    origin: EvidenceOrigin
    verification_result: VerificationResult = VerificationResult.UNVERIFIED
    
    # Anti-forgery: _factory_seal prevents direct construction bypass
    _factory_seal: object = None
    
    def __post_init__(self):
        if self._factory_seal is not _FACTORY_SEAL_SENTINEL:
            raise CapabilityAccessError(
                "Cannot construct VerifiedEvidenceCapabilityView directly. "
                "Use CapabilityVerifier.accept() or UntrustedTestCapability."
            )
    
    def is_verified(self) -> bool:
        return self.verification_result == VerificationResult.VERIFIED
    
    def is_rejected(self) -> bool:
        return self.verification_result == VerificationResult.REJECTED
    
    def is_untrusted_double(self) -> bool:
        return self.verification_result == VerificationResult.UNTRUSTED_DOUBLE
    
    def digest_matches(self, other: "VerifiedEvidenceCapabilityView") -> bool:
        """Compare evidence digests — caller cannot bypass."""
        return self.evidence_digest == other.evidence_digest
    
    def raw_span_bytes(self, source_bytes: bytes) -> bytes:
        """Slice exact bytes from source."""
        return source_bytes[self.raw_span[0]:self.raw_span[1]]
    
    def origin_is_user_explicit(self) -> bool:
        """Only true if VERIFIED + USER_EXPLICIT_MESSAGE origin."""
        return (self.is_verified() and 
                self.origin == EvidenceOrigin.USER_EXPLICIT_MESSAGE)
    
    def origin_is_source_document(self) -> bool:
        return (self.is_verified() and 
                self.origin == EvidenceOrigin.EXTERNAL_SOURCE_DOCUMENT)


_FACTORY_SEAL_SENTINEL = object()


class CapabilityAccessError(Exception):
    """Raised when caller attempts forbidden capability construction."""
    pass


class CapabilityVerifier:
    """Only path to accept capabilities. Pre-E59: always fails closed.
    
    After E59 is accepted, this verifier will consume the canonical E59 interface.
    Until then, every input is UNTRUSTED_DOUBLE and no authority gate passes.
    """
    
    def __init__(self):
        self._e59_accepted = False  # GPT must set this after E59 acceptance
    
    def accept(self, raw_capability: dict) -> VerifiedEvidenceCapabilityView:
        """Accept a capability from an external verifier.
        
        Pre-E59: ALL capabilities are UNTRUSTED_DOUBLE.
        Post-E59: validates issuer, source identity, span boundaries, digest.
        """
        if not self._e59_accepted:
            # Pre-E59: never produce accepted authority
            return self._untrusted_view(raw_capability)
        
        # Post-E59 path (not yet implemented — requires E59 interface)
        cap_id = raw_capability.get("capability_id", "")
        issuer = raw_capability.get("issuer_identity", "")
        
        # E59 canonical verifier identity check (placeholder)
        if issuer != "E59_CANONICAL_VERIFIER":
            return self._untrusted_view(raw_capability)
        
        # Full E59 validation TBD after acceptance
        return self._verified_view(raw_capability)
    
    def _untrusted_view(self, raw: dict) -> VerifiedEvidenceCapabilityView:
        """Create an UNTRUSTED_DOUBLE view — never passes authority gates."""
        cap_id = raw.get("capability_id", f"UNTRUSTED-{hash(str(raw))}")
        return _make_capability(
            capability_id=cap_id,
            issuer_identity=raw.get("issuer_identity", "UNKNOWN"),
            source_identity=raw.get("source_identity", "UNTRUSTED_SOURCE"),
            raw_span=raw.get("raw_span", (0, 0)),
            decoded_text=raw.get("decoded_text", ""),
            evidence_digest=raw.get("evidence_digest", ""),
            origin=EvidenceOrigin(raw.get("origin", "UNKNOWN")),
            verification_result=VerificationResult.UNTRUSTED_DOUBLE,
        )
    
    def _verified_view(self, raw: dict) -> VerifiedEvidenceCapabilityView:
        """Create a VERIFIED view — only post-E59 acceptance."""
        return _make_capability(
            capability_id=raw["capability_id"],
            issuer_identity=raw["issuer_identity"],
            source_identity=raw["source_identity"],
            raw_span=tuple(raw["raw_span"]),
            decoded_text=raw["decoded_text"],
            evidence_digest=raw["evidence_digest"],
            origin=EvidenceOrigin(raw["origin"]),
            verification_result=VerificationResult.VERIFIED,
        )


def _make_capability(**kwargs) -> VerifiedEvidenceCapabilityView:
    """Internal factory — bypasses frozen dataclass __init__ for seal."""
    kwargs["_factory_seal"] = _FACTORY_SEAL_SENTINEL
    return VerifiedEvidenceCapabilityView(**kwargs)


class UntrustedTestCapability:
    """Test double factory. Explicitly marked, structurally UNTRUSTED.
    
    All capabilities from this factory carry UNTRUSTED_DOUBLE status
    and cannot pass production authority gates.
    """
    
    @staticmethod
    def make(
        source_identity: str = "UNTRUSTED_TEST_SOURCE",
        decoded_text: str = "",
        origin: EvidenceOrigin = EvidenceOrigin.UNKNOWN,
    ) -> VerifiedEvidenceCapabilityView:
        """Create an explicitly untrusted test capability."""
        raw = f"{source_identity}:{decoded_text}:{origin.value}:UNTRUSTED"
        cap_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
        digest = hashlib.sha256(decoded_text.encode()).hexdigest()
        
        return _make_capability(
            capability_id=cap_id,
            issuer_identity="UNTRUSTED_TEST_DOUBLE",
            source_identity=source_identity,
            raw_span=(0, len(decoded_text.encode()) if decoded_text else 0),
            decoded_text=decoded_text,
            evidence_digest=digest,
            origin=origin,
            verification_result=VerificationResult.UNTRUSTED_DOUBLE,
        )
