"""E45 Q2 — Authority: evidence/records/bundles/atoms factory-issued, registry-verified

All fields derived from verifier-only capability. Caller cannot set enums, confidence, or bypass registry.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import hashlib
import time

from qclaw_e45.capability import (
    VerifiedEvidenceCapabilityView, EvidenceOrigin, VerificationState, ConfidenceBand,
)


class AtomType(Enum):
    CONCEPT = "concept"
    DEFINITION = "definition"
    MECHANISM = "mechanism"
    CAUSAL_CHAIN = "causal_chain"
    CONDITION = "condition"
    COUNTEREXAMPLE = "counterexample"
    INDICATOR = "indicator"
    DATA_SOURCE = "data_source"
    SCOPE = "scope"
    FAILURE_CONDITION = "failure_condition"
    VERIFICATION_METHOD = "verification_method"
    EXECUTABLE_ACTION = "executable_action"
    CLAIM = "claim"


# ----- Evidence Record (immutable, factory-issued) -----

@dataclass(frozen=True)
class EvidenceRecord:
    """Immutable record created by EvidenceFactory only."""
    record_id: str
    decoded_text: str
    origin: EvidenceOrigin
    verification_state: VerificationState
    confidence: ConfidenceBand
    source_identity: str
    evidence_layer: str
    scope: str
    issuer: str
    policy_version: str = "1.0"


# ----- Evidence Bundle -----

@dataclass(frozen=True)
class EvidenceBundle:
    bundle_id: str
    records: tuple  # Tuple[EvidenceRecord, ...]
    verification_state: VerificationState
    derived_confidence: ConfidenceBand
    derived_origin: EvidenceOrigin
    issuer: str
    policy_version: str = "1.0"


# ----- Atom -----

@dataclass(frozen=True)
class Atom:
    atom_id: str
    atom_type: AtomType
    bundle_id: str
    content: str
    source_identity: str
    issuer: str
    provenance: str = "derived"
    policy_version: str = "1.0"


# ----- Registry (private insertion, identity-bound) -----

class EvidenceRegistry:
    """Private registry. Inserts from factory only."""
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

    def has_bundle(self, bundle_id: str) -> bool:
        return bundle_id in self._bundles


# ----- EvidenceFactory (sole authority) -----

class EvidenceFactory:
    """Sole authority for creating records, bundles, and atoms."""

    def __init__(self, registry: EvidenceRegistry):
        self._registry = registry
        self._factory_id = hashlib.sha256(b"e45_evidence_factory").hexdigest()[:12]
        self._bundle_counter = 0

    def create_record(self, cap: VerifiedEvidenceCapabilityView) -> EvidenceRecord:
        """Create record from capability. All fields derived from cap, not caller."""
        text = cap.decoded_text
        record_id = hashlib.sha256(
            f"{cap.source_identity}:{cap.raw_span[0]}:{cap.raw_span[1]}:{text[:128]}:{time.time()}".encode()
        ).hexdigest()[:32]

        # Derive confidence from origin + verification
        if cap.origin == EvidenceOrigin.USER_EXPLICIT_MESSAGE:
            confidence = ConfidenceBand.HIGH if cap.is_verified() else ConfidenceBand.MEDIUM
        elif cap.origin == EvidenceOrigin.SOURCE_DOCUMENT:
            confidence = ConfidenceBand.HIGH if cap.is_verified() else ConfidenceBand.MEDIUM
        elif cap.origin == EvidenceOrigin.AUTHOR_CLAIM:
            confidence = ConfidenceBand.MEDIUM
        elif cap.origin in (EvidenceOrigin.HYPOTHESIS, EvidenceOrigin.VALUE_JUDGMENT):
            confidence = ConfidenceBand.LOW
        else:
            confidence = ConfidenceBand.LOW

        layer = "direct_evidence" if cap.is_verified() else "unverified"
        scope = "explicit" if cap.origin == EvidenceOrigin.USER_EXPLICIT_MESSAGE else "derived"

        rec = EvidenceRecord(
            record_id=record_id,
            decoded_text=text,
            origin=cap.origin,
            verification_state=VerificationState.VERIFIED if cap.is_verified() else VerificationState.UNVERIFIED,
            confidence=confidence,
            source_identity=cap.source_identity,
            evidence_layer=layer,
            scope=scope,
            issuer=self._factory_id,
        )
        self._registry._register_record(rec)
        return rec

    def create_bundle(self, records: List[EvidenceRecord]) -> EvidenceBundle:
        if not records:
            raise ValueError("empty bundle rejected")

        parts = [r.record_id for r in records]
        self._bundle_counter += 1
        bundle_id = hashlib.sha256(
            f"{''.join(sorted(parts))}:{self._bundle_counter}".encode()
        ).hexdigest()[:24]

        # Derive from records
        states = {r.verification_state for r in records}
        if VerificationState.UNVERIFIED in states:
            bundle_state = VerificationState.UNVERIFIED
        else:
            bundle_state = VerificationState.VERIFIED

        confidences = [r.confidence for r in records]
        if all(c == ConfidenceBand.HIGH for c in confidences):
            bundle_confidence = ConfidenceBand.HIGH
        elif all(c == ConfidenceBand.LOW for c in confidences):
            bundle_confidence = ConfidenceBand.LOW
        else:
            bundle_confidence = ConfidenceBand.MEDIUM

        origins = [r.origin for r in records]
        if EvidenceOrigin.USER_EXPLICIT_MESSAGE in origins:
            bundle_origin = EvidenceOrigin.USER_EXPLICIT_MESSAGE
        else:
            bundle_origin = origins[0]

        bundle = EvidenceBundle(
            bundle_id=bundle_id,
            records=tuple(records),
            verification_state=bundle_state,
            derived_confidence=bundle_confidence,
            derived_origin=bundle_origin,
            issuer=self._factory_id,
        )
        self._registry._register_bundle(bundle)
        return bundle

    def create_atom(self, bundle: EvidenceBundle,
                    atom_type: AtomType = AtomType.CLAIM) -> Atom:
        content = " ".join(r.decoded_text for r in bundle.records)
        atom_id = hashlib.sha256(
            f"{bundle.bundle_id}:{content[:200]}:{atom_type.value}".encode()
        ).hexdigest()[:32]

        atom = Atom(
            atom_id=atom_id,
            atom_type=atom_type,
            bundle_id=bundle.bundle_id,
            content=content,
            source_identity=bundle.records[0].source_identity,
            issuer=self._factory_id,
        )
        self._registry._register_atom(atom)
        return atom

    def verify_atom(self, atom: Atom) -> bool:
        """Verify atom is in our registry."""
        return self._registry._atoms.get(atom.atom_id) is atom
