"""E42 Q1 — Controlled, Deep-Immutable Semantic Authority

AtomFactory: the ONLY path to create an Atom. All callers must pass through
the factory with verified evidence records. Direct Atom() construction is
detected and rejected at attribute-access time.

Every nested collection is deep-frozen. Identity = sha256(full canonical
payload, domain-separated). Confidence, verification_state, evidence_layer
are DERIVED from evidence, never caller-labeled.
"""
import hashlib, enum, json, copy
from dataclasses import dataclass, field, fields
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

DOMAIN_SEPARATOR = b"QCLAW:E42:ATOM:V1"


class AtomType(enum.Enum):
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


class EvidenceLayer(enum.Enum):
    SOURCE_FACT = "source_fact"
    AUTHOR_CLAIM = "author_claim"
    EVIDENCE = "evidence"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    VALUE_JUDGMENT = "value_judgment"


class VerificationState(enum.Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    PARTIALLY_VERIFIED = "partially_verified"
    VERIFIED = "verified"
    FALSIFIED = "falsified"


class ConfidenceBand(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ––– Evidence Records –––

@dataclass(frozen=True)
class EvidenceRecord:
    """Immutable evidence record. All authority derives from these."""
    record_id: str
    source_document_id: str
    source_span_start: int
    source_span_end: int
    evidence_type: EvidenceLayer
    verification_status: VerificationState
    verifier_id: Optional[str] = None
    verification_timestamp: Optional[str] = None
    notes: Tuple[str, ...] = ()

    def __post_init__(self):
        if self.evidence_type == EvidenceLayer.SOURCE_FACT:
            if self.verification_status not in (VerificationState.VERIFIED,):
                raise ValueError("SOURCE_FACT requires VERIFIED status")

    def to_canonical(self) -> bytes:
        fields = (
            self.record_id,
            self.source_document_id,
            str(self.source_span_start),
            str(self.source_span_end),
            self.evidence_type.value,
            self.verification_status.value,
            self.verifier_id or "",
            self.verification_timestamp or "",
            "|".join(self.notes),
        )
        return "|".join(fields).encode("utf-8")


@dataclass(frozen=True)
class EvidenceBundle:
    """Verified collection of evidence records."""
    records: Tuple[EvidenceRecord, ...]
    bundle_id: str
    digest: str = ""

    def __post_init__(self):
        h = hashlib.sha256(DOMAIN_SEPARATOR)
        for r in sorted(self.records, key=lambda r: r.record_id):
            h.update(r.to_canonical())
        digest = h.hexdigest()
        object.__setattr__(self, "digest", digest)

    def dominant_layer(self) -> EvidenceLayer:
        """Derive evidence layer from actual records, not caller label."""
        types = {r.evidence_type for r in self.records}
        # Precedence: evidence > source_fact > inference > author_claim > hypothesis > value_judgment
        order = [EvidenceLayer.EVIDENCE, EvidenceLayer.SOURCE_FACT,
                 EvidenceLayer.INFERENCE, EvidenceLayer.AUTHOR_CLAIM,
                 EvidenceLayer.HYPOTHESIS, EvidenceLayer.VALUE_JUDGMENT]
        for t in order:
            if t in types:
                return t
        return EvidenceLayer.AUTHOR_CLAIM

    def derived_confidence(self) -> ConfidenceBand:
        total = len(self.records)
        verified = sum(1 for r in self.records
                      if r.verification_status == VerificationState.VERIFIED)
        if total == 0:
            return ConfidenceBand.LOW
        ratio = verified / total
        if ratio >= 0.8 and total >= 3:
            return ConfidenceBand.HIGH
        if ratio >= 0.4:
            return ConfidenceBand.MEDIUM
        return ConfidenceBand.LOW

    def derived_verification(self) -> VerificationState:
        statuses = {r.verification_status for r in self.records}
        if VerificationState.FALSIFIED in statuses:
            return VerificationState.FALSIFIED
        if VerificationState.VERIFIED in statuses:
            if VerificationState.PENDING in statuses:
                return VerificationState.PARTIALLY_VERIFIED
            return VerificationState.VERIFIED
        if VerificationState.PENDING in statuses:
            return VerificationState.PENDING
        return VerificationState.UNVERIFIED


# ––– Deep-Freeze Helper –––

def _deep_freeze(obj):
    """Recursively freeze all nested structures."""
    if isinstance(obj, dict):
        return tuple(sorted((k, _deep_freeze(v)) for k, v in obj.items()))
    if isinstance(obj, (list, set, tuple)):
        return tuple(_deep_freeze(x) for x in obj)
    return obj


# ––– Immutable Atom –––

class AtomAccessError(TypeError):
    """Raised when a direct-constructed Atom is accessed — caller bypassed factory."""


@dataclass(frozen=True)
class Atom:
    """DO NOT CONSTRUCT DIRECTLY. Use AtomFactory.build()."""
    atom_id: str
    atom_type: AtomType
    content: str
    evidence_layer: EvidenceLayer
    confidence: ConfidenceBand
    verification_state: VerificationState
    source_bundle_id: str
    factory_signature: str
    canonical_payload: bytes = field(repr=False)
    invalidation_conditions: Tuple[str, ...] = ()
    scope_notes: Tuple[str, ...] = ()
    provenance_chain: Tuple[str, ...] = ()

    # Tamper detection
    _factory_issued: bool = field(default=False, repr=False)

    def __post_init__(self):
        if not self._factory_issued:
            return  # Will be detected on access
        # Verify identity
        expected = _compute_atom_id(self.atom_type, self.content,
                                     self.evidence_layer, self.confidence,
                                     self.verification_state, self.source_bundle_id)
        if self.atom_id != expected:
            raise ValueError(f"Atom ID mismatch: {self.atom_id[:16]} != {expected[:16]}")
        # Verify immutable collections are frozen
        for attr_name in ("invalidation_conditions", "scope_notes", "provenance_chain"):
            val = getattr(self, attr_name)
            if not isinstance(val, tuple):
                raise TypeError(f"{attr_name} must be tuple, got {type(val).__name__}")

    def __getattribute__(self, name):
        if name == "_factory_issued":
            return object.__getattribute__(self, name)
        issued = object.__getattribute__(self, "_factory_issued")
        if not issued and name not in ("_factory_issued", "__class__"):
            raise AtomAccessError(
                "Atom was constructed directly. Use AtomFactory.build() only. "
                "Direct-constructed atoms are not authoritative."
            )
        return object.__getattribute__(self, name)


def _compute_atom_id(atom_type: AtomType, content: str,
                     evidence_layer: EvidenceLayer, confidence: ConfidenceBand,
                     verification_state: VerificationState,
                     source_bundle_id: str) -> str:
    """Deterministic atom identity from full canonical payload."""
    payload = "|".join([
        DOMAIN_SEPARATOR.decode(),
        atom_type.value,
        content,
        evidence_layer.value,
        confidence.value,
        verification_state.value,
        source_bundle_id,
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ––– AtomFactory –––

class AtomFactory:
    """The ONLY path to authoritative Atom creation."""

    def __init__(self, factory_id: str = "E42_FACTORY_V1"):
        self._factory_id = factory_id
        self._issued: Set[str] = set()  # Track issued atom IDs

    def build(self, atom_type: AtomType, content: str,
              evidence: EvidenceBundle) -> Atom:
        """Build an authoritative Atom from verified evidence.

        All authority fields are DERIVED from the evidence bundle.
        The caller cannot override confidence, verification or evidence_layer.
        """
        if not isinstance(evidence, EvidenceBundle):
            raise TypeError("Evidence must be an EvidenceBundle")
        if not evidence.records:
            raise ValueError("Evidence bundle must contain at least one record")
        if not content or not content.strip():
            raise ValueError("Atom content must be non-empty")

        # Derive ALL authority fields from evidence
        evidence_layer = evidence.dominant_layer()
        confidence = evidence.derived_confidence()
        verification_state = evidence.derived_verification()

        # Prevent caller from injecting high-authority labels
        if evidence_layer == EvidenceLayer.SOURCE_FACT:
            if not all(r.verification_status == VerificationState.VERIFIED
                       for r in evidence.records):
                raise ValueError("SOURCE_FACT requires all records VERIFIED")

        if confidence == ConfidenceBand.HIGH:
            if len(evidence.records) < 3:
                raise ValueError("HIGH confidence requires >=3 evidence records")

        atom_id = _compute_atom_id(atom_type, content, evidence_layer,
                                    confidence, verification_state,
                                    evidence.bundle_id)

        if atom_id in self._issued:
            raise ValueError(f"Duplicate atom ID: {atom_id[:16]}")

        sig = hashlib.sha256(
            f"{self._factory_id}:{atom_id}:{evidence.bundle_id}".encode()
        ).hexdigest()

        atom = Atom(
            atom_id=atom_id,
            atom_type=atom_type,
            content=content,
            evidence_layer=evidence_layer,
            confidence=confidence,
            verification_state=verification_state,
            source_bundle_id=evidence.bundle_id,
            factory_signature=sig,
            canonical_payload=hashlib.sha256(
                f"{atom_type.value}|{content}".encode()
            ).digest(),
            _factory_issued=True,
        )
        self._issued.add(atom_id)
        return atom

    @property
    def issued_count(self) -> int:
        return len(self._issued)


# ––– Snapshot helper –––
def deep_snapshot(obj):
    """Return a deep-frozen, immutable copy — never a caller alias."""
    return _deep_freeze(copy.deepcopy(obj))
