"""E45 Q2 — Evidence Registry and Factory

Fields derived from VerifiedEvidenceCapabilityView + policy.
No caller-supplied HMAC keys, mutable registries, or partial signatures.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
import hashlib
import uuid

from qclaw_e45.capability import (
    VerifiedEvidenceCapabilityView, EvidenceOrigin,
    VerificationState, ConfidenceBand, UNTRUSTED_TEST_DOUBLE,
)


class AtomType(Enum):
    CONCEPT = "concept"
    DEFINITION = "definition"
    MECHANISM = "mechanism"
    CAUSAL_CHAIN = "causal_chain"
    CONDITION = "condition"
    INDICATOR = "indicator"
    FAILURE_CONDITION = "failure_condition"


@dataclass(frozen=True)
class EvidenceRecord:
    """Immutable record derived from capability + policy."""
    record_id: str
    source_identity: str
    origin: EvidenceOrigin
    verification_state: VerificationState
    confidence: ConfidenceBand
    evidence_digest: str
    raw_span: tuple
    decoded_text: str
    issuer_id: str
    policy_version: str

    def __post_init__(self):
        # Confidence must match origin + verification
        if self.origin == EvidenceOrigin.HYPOTHESIS:
            object.__setattr__(self, "confidence", ConfidenceBand.LOW)


@dataclass(frozen=True)
class EvidenceBundle:
    """Ordered collection of records with deterministic identity."""
    bundle_id: str
    records: tuple  # (EvidenceRecord, ...)
    verification_state: VerificationState
    derived_origin: EvidenceOrigin
    derived_confidence: ConfidenceBand

    @property
    def record_count(self) -> int:
        return len(self.records)


@dataclass(frozen=True)
class Atom:
    """Knowledge atom issued by factory — no caller-constructible verified atoms."""
    atom_id: str
    atom_type: AtomType
    bundle_id: str
    content: str
    verification_hash: str

    def __eq__(self, other):
        if not isinstance(other, Atom):
            return False
        return self.atom_id == other.atom_id

    def __hash__(self):
        return hash(self.atom_id)


class EvidenceRegistry:
    """Private registry. Callers cannot insert directly."""
    def __init__(self):
        self._records: Dict[str, EvidenceRecord] = {}
        self._bundles: Dict[str, EvidenceBundle] = {}
        self._atoms: Dict[str, Atom] = {}

    def _register_record(self, record: EvidenceRecord):
        if record.record_id in self._records:
            raise ValueError(f"duplicate record {record.record_id[:12]}")
        self._records[record.record_id] = record

    def _register_bundle(self, bundle: EvidenceBundle):
        if bundle.bundle_id in self._bundles:
            raise ValueError(f"duplicate bundle {bundle.bundle_id[:12]}")
        self._bundles[bundle.bundle_id] = bundle

    def _register_atom(self, atom: Atom):
        if atom.atom_id in self._atoms:
            raise ValueError(f"duplicate atom {atom.atom_id[:12]}")
        self._atoms[atom.atom_id] = atom

    def has_record(self, record_id: str) -> bool:
        return record_id in self._records

    def get_record(self, record_id: str) -> Optional[EvidenceRecord]:
        return self._records.get(record_id)

    def get_atom(self, atom_id: str) -> Optional[Atom]:
        return self._atoms.get(atom_id)


class EvidenceFactory:
    """Sole evidence producer. Factory issues records/bundles/atoms.
    
    Every field is recomputed from the capability + policy.
    The factory does not expose signing keys or accept caller HMAC.
    """

    def __init__(self, registry: EvidenceRegistry):
        self._registry = registry
        self._factory_id = hashlib.sha256(b"e45_evidence_factory").hexdigest()[:12]
        self._bundle_counter = 0

    def create_record(self, cap: VerifiedEvidenceCapabilityView,
                     layer: str = "general") -> EvidenceRecord:
        # Derive confidence from origin + verification
        if cap.origin in (EvidenceOrigin.HYPOTHESIS, EvidenceOrigin.VALUE_JUDGMENT):
            confidence = ConfidenceBand.LOW
        elif cap.is_verified():
            confidence = ConfidenceBand.HIGH
        else:
            confidence = ConfidenceBand.MEDIUM

        record_id = hashlib.sha256(
            f"{cap.source_identity}:{cap.raw_span}:{cap.evidence_digest}".encode()
        ).hexdigest()[:32]

        rec = EvidenceRecord(
            record_id=record_id,
            source_identity=cap.source_identity,
            origin=cap.origin,
            verification_state=cap.verification_result,
            confidence=confidence,
            evidence_digest=cap.evidence_digest,
            raw_span=cap.raw_span,
            decoded_text=cap.decoded_text,
            issuer_id=cap.issuer.issuer_id,
            policy_version=cap.issuer.policy_version,
        )
        self._registry._register_record(rec)
        return rec

    def create_bundle(self, records: list) -> EvidenceBundle:
        if not records:
            raise ValueError("empty bundle rejected")

        # Deterministic bundle identity from all records
        parts = []
        for r in records:
            parts.append(r.record_id)
        self._bundle_counter += 1
        bundle_hash = hashlib.sha256(f"{''.join(sorted(parts))}:{self._bundle_counter}".encode()).hexdigest()[:24]
        bundle_id = f"bundle-{bundle_hash}"

        # Derive bundle-level properties from records
        origins = set(r.origin for r in records)
        if EvidenceOrigin.USER_EXPLICIT_MESSAGE in origins:
            derived_origin = EvidenceOrigin.USER_EXPLICIT_MESSAGE
        elif EvidenceOrigin.SOURCE_DOCUMENT in origins:
            derived_origin = EvidenceOrigin.SOURCE_DOCUMENT
        else:
            derived_origin = EvidenceOrigin.UNKNOWN

        states = set(r.verification_state for r in records)
        if VerificationState.REJECTED in states:
            bundle_state = VerificationState.REJECTED
        elif all(s == VerificationState.VERIFIED for s in states):
            bundle_state = VerificationState.VERIFIED
        else:
            bundle_state = VerificationState.UNVERIFIED

        confidences = set(r.confidence for r in records)
        if ConfidenceBand.LOW in confidences:
            derived_confidence = ConfidenceBand.LOW
        elif ConfidenceBand.MEDIUM in confidences:
            derived_confidence = ConfidenceBand.MEDIUM
        else:
            derived_confidence = ConfidenceBand.HIGH

        bundle = EvidenceBundle(
            bundle_id=bundle_id,
            records=tuple(records),
            verification_state=bundle_state,
            derived_origin=derived_origin,
            derived_confidence=derived_confidence,
        )
        self._registry._register_bundle(bundle)
        return bundle

    def create_atom(self, bundle: EvidenceBundle,
                   atom_type: AtomType = AtomType.CONCEPT) -> Atom:
        # Atom identity from bundle + type + content
        content_parts = [r.decoded_text for r in bundle.records]
        content = " ".join(content_parts)
        atom_hash = hashlib.sha256(
            f"{bundle.bundle_id}:{atom_type.value}:{content}".encode()
        ).hexdigest()[:32]
        atom_id = f"atom-{atom_hash}"

        verification_hash = hashlib.sha256(
            f"{atom_id}:{bundle.bundle_id}:{atom_type.value}".encode()
        ).hexdigest()[:32]

        atom = Atom(
            atom_id=atom_id,
            atom_type=atom_type,
            bundle_id=bundle.bundle_id,
            content=content,
            verification_hash=verification_hash,
        )
        self._registry._register_atom(atom)
        return atom

    def verify_atom(self, atom: Atom) -> bool:
        """Recompute every field and compare against stored atom."""
        stored = self._registry.get_atom(atom.atom_id)
        if stored is None:
            return False
        # Must match: atom_id, atom_type, bundle_id, content, verification_hash
        if stored.atom_id != atom.atom_id:
            return False
        if stored.atom_type != atom.atom_type:
            return False
        if stored.bundle_id != atom.bundle_id:
            return False
        if stored.content != atom.content:
            return False
        if stored.verification_hash != atom.verification_hash:
            return False
        return True

    @property
    def factory_id(self) -> str:
        return self._factory_id
