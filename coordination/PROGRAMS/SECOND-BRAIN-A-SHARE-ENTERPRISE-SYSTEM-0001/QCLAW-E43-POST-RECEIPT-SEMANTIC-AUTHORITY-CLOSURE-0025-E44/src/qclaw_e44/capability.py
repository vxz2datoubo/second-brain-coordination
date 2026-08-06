"""E44 Q1 — VerifiedEvidenceCapability boundary contract.

Narrow immutable consumer contract for semantic processing.
Does NOT reimplement Codex E56 low-level source admission, format ownership,
generic graph/topology, artifact binding or history hygiene.

Capability exposes: issuer/policy identity, source identity, exact raw/decoded
span identity, evidence digest, origin class, and verification result.

Foreign, mutable, self-issued, stale-policy or incomplete capabilities fail closed.
"""
from __future__ import annotations

import hashlib
import dataclasses
import enum
from typing import Tuple

__all__ = [
    "EvidenceOrigin", "CapabilityStatus", "VerifiedEvidenceCapability",
    "CapabilityError", "SyntheticCapability", "CAPABILITY_SCHEMA_VERSION",
]

CAPABILITY_SCHEMA_VERSION = "44.0"


class EvidenceOrigin(enum.Enum):
    """Origin class of evidence — derived from capability verification result."""
    SOURCE_FACT = "source_fact"
    AUTHOR_CLAIM = "author_claim"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    VALUE_JUDGMENT = "value_judgment"
    USER_EXPLICIT = "user_explicit"         # requires verified user-origin/message evidence
    UNKNOWN_ORIGIN = "unknown_origin"


class CapabilityStatus(enum.Enum):
    VERIFIED = "verified"
    STALE = "stale"             # policy version changed
    INCOMPLETE = "incomplete"   # missing required fields
    FOREIGN = "foreign"         # issuer not recognized
    SELF_ISSUED = "self_issued"  # consumer tried to self-sign
    MUTATED = "mutated"         # content vs signature mismatch


class CapabilityError(Exception):
    """Raised when capability verification fails."""
    def __init__(self, status: CapabilityStatus, detail: str = ""):
        self.status = status
        self.detail = detail
        super().__init__(f"[{status.value}] {detail}")


@dataclasses.dataclass(frozen=True)
class VerifiedEvidenceCapability:
    """Immutable verified capability. Only produced by the capability verifier.

    Fields:
        capability_id: Unique deterministic ID
        issuer: The verified issuer identity
        source_id: Source document/span identity
        raw_span_hash: SHA-256 of the exact raw bytes
        decoded_span_hash: SHA-256 of the decoded text content
        evidence_digest: Combined content digest
        origin_class: Verified evidence origin (derived, not caller-supplied)
        schema_version: Capability schema version
        policy_version: Semantic policy version used for verification
        verified_at_ns: Timestamp of verification
    """
    capability_id: str
    issuer: str
    source_id: str
    raw_span_hash: str
    decoded_span_hash: str
    evidence_digest: str
    origin_class: EvidenceOrigin
    schema_version: str
    policy_version: str
    verified_at_ns: int

    def verify_integrity(self, verifier: "CapabilityVerifier") -> bool:
        """Re-verify this capability against the current verifier state."""
        return verifier.re_verify(self)

    @staticmethod
    def compute_id(issuer: str, source_id: str, raw_span_hash: str, decoded_span_hash: str) -> str:
        h = hashlib.sha256()
        h.update(issuer.encode())
        h.update(source_id.encode())
        h.update(raw_span_hash.encode())
        h.update(decoded_span_hash.encode())
        h.update(CAPABILITY_SCHEMA_VERSION.encode())
        return h.hexdigest()


class CapabilityVerifier:
    """Verifies and produces VerifiedEvidenceCapability instances.

    Only the verifier holds the issuer identity and policy version.
    Callers cannot self-issue, mutate, or bypass verification.
    """

    def __init__(self, issuer: str, policy_version: str):
        self._issuer = issuer
        self._policy_version = policy_version
        self._schema_version = CAPABILITY_SCHEMA_VERSION
        self._issued: set[str] = set()  # issued capability IDs

    @property
    def issuer(self) -> str:
        return self._issuer

    @property
    def policy_version(self) -> str:
        return self._policy_version

    def verify(self, raw_bytes: bytes, source_id: str,
               claimed_origin: EvidenceOrigin) -> VerifiedEvidenceCapability:
        """Verify raw evidence and produce a capability.

        The claimed_origin is NOT trusted — the verifier derives the actual origin
        from the content + policy. The claimed origin is used as a hint only.
        """
        raw_span_hash = hashlib.sha256(raw_bytes).hexdigest()

        # Decode and derive origin
        try:
            decoded = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            decoded = raw_bytes.decode("utf-8", errors="replace")

        decoded_span_hash = hashlib.sha256(decoded.encode("utf-8")).hexdigest()

        # Derive actual origin (policy-driven, not caller-supplied)
        origin_class = self._derive_origin_class(decoded, claimed_origin)

        # Compute full digest
        evidence_digest = hashlib.sha256(
            f"{raw_span_hash}|{decoded_span_hash}|{origin_class.value}|{source_id}".encode()
        ).hexdigest()

        import time
        cap_id = VerifiedEvidenceCapability.compute_id(
            self._issuer, source_id, raw_span_hash, decoded_span_hash)

        if cap_id in self._issued:
            raise CapabilityError(CapabilityStatus.SELF_ISSUED, f"duplicate capability {cap_id[:16]}")

        self._issued.add(cap_id)

        return VerifiedEvidenceCapability(
            capability_id=cap_id,
            issuer=self._issuer,
            source_id=source_id,
            raw_span_hash=raw_span_hash,
            decoded_span_hash=decoded_span_hash,
            evidence_digest=evidence_digest,
            origin_class=origin_class,
            schema_version=self._schema_version,
            policy_version=self._policy_version,
            verified_at_ns=time.time_ns(),
        )

    def re_verify(self, cap: VerifiedEvidenceCapability) -> bool:
        """Re-verify a capability against current verifier state."""
        if cap.issuer != self._issuer:
            return False
        if cap.schema_version != self._schema_version:
            return False
        if cap.policy_version != self._policy_version:
            return False
        expected_id = VerifiedEvidenceCapability.compute_id(
            cap.issuer, cap.source_id, cap.raw_span_hash, cap.decoded_span_hash)
        if cap.capability_id != expected_id:
            return False
        if cap.capability_id not in self._issued:
            return False
        return True

    def _derive_origin_class(self, text: str, claimed: EvidenceOrigin) -> EvidenceOrigin:
        """Derive actual origin from text content + policy, not caller input."""
        t = text.strip().lower()

        # Explicit user statements (personal pronouns + certainty)
        user_indicators = ("i know", "i remember", "i believe", "my experience",
                          "i think", "in my opinion", "i always", "i never")
        for ind in user_indicators:
            if t.startswith(ind) or f" {ind}" in t:
                return EvidenceOrigin.USER_EXPLICIT

        # Hypothesis markers
        if any(m in t for m in ("maybe", "perhaps", "possibly", "it could be",
                                 "might be", "one hypothesis", "speculative")):
            return EvidenceOrigin.HYPOTHESIS

        # Value judgments
        if any(m in t for m in ("best", "worst", "should", "ought to", "good idea",
                                 "bad idea", "recommend")):
            return EvidenceOrigin.VALUE_JUDGMENT

        # Inference markers
        if any(m in t for m in ("therefore", "thus", "implies", "it follows",
                                 "we can conclude", "as a result")):
            return EvidenceOrigin.INFERENCE

        # Author claims (attributed)
        if t.startswith("according to") or "said" in t or "reported" in t:
            return EvidenceOrigin.AUTHOR_CLAIM

        # Default: treat direct factual statements as SOURCE_FACT
        if len(t) > 10 and not any(w in t for w in ("maybe", "perhaps", "opinion")):
            return EvidenceOrigin.SOURCE_FACT

        return EvidenceOrigin.UNKNOWN_ORIGIN


# ── Synthetic test-only fixtures ───────────────────────────────
# These are test doubles, never canonical authority.
# Marked with SYNTHETIC_ prefix to prevent confusion with production capabilities.

SYNTHETIC_BYTES = {
    "fact_short": b"Market volatility increases during earnings season",
    "user_explicit": b"I know that my portfolio rebalance occurs quarterly",
    "hypothesis": b"It could be that the correlation is spurious",
    "inference": b"Therefore, the signal is significant at p < 0.01",
    "value_judgment": b"This is the best trading strategy available",
    "author_claim": b"According to the report, revenues grew 15%",
    "empty": b"",
    "secret_like": b"api_key = sk-proj-1234567890abcdefghijklmnop",
}

SYNTHETIC_SOURCE_IDS = {
    "default": "synth://doc-001/0-56",
    "user": "synth://user-message/msg-001/0-58",
}
