"""
E43 Q1 — Controlled Evidence and Atom Authority

All EvidenceRecord, EvidenceBundle, and Atom instances are factory/registry-issued.
Direct construction is rejected by verifier. No caller-supplied IDs, labels, or
verification enums bypass the registry.

Evidence records are bound to immutable admitted sources via SourceSpan references
(without duplicating Codex E55 authority).
"""
from __future__ import annotations

import hashlib, hmac, json, secrets, enum, functools, dataclasses
from typing import Dict, List, Optional, Tuple, Any

__all__ = [
    "AtomType", "VerificationState", "ConfidenceBand", "EvidenceLayer",
    "EvidenceRecord", "EvidenceBundle", "Atom",
    "AtomFactory", "EvidenceFactory", "AuthorityRegistry",
    "FACTORY_REJECTED", "REGISTRY_REJECTED",
]

# ── Security tokens ────────────────────────────────────────────
class _FactorySecret:
    """Cryptographic secret held only by factory. Never exposed."""
    def __init__(self):
        self._key = secrets.token_bytes(32)
    def sign(self, payload: bytes) -> bytes:
        return hmac.digest(self._key, payload, "sha256")
    def verify(self, payload: bytes, signature: bytes) -> bool:
        return hmac.compare_digest(signature, hmac.digest(self._key, payload, "sha256"))

# ── Enumerations ────────────────────────────────────────────────
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

class VerificationState(enum.Enum):
    UNVERIFIED = "unverified"
    PARTIALLY_VERIFIED = "partially_verified"
    VERIFIED = "verified"
    FALSIFIED = "falsified"
    DISPUTED = "disputed"

class ConfidenceBand(enum.Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class EvidenceLayer(enum.Enum):
    SOURCE_FACT = "source_fact"
    AUTHOR_CLAIM = "author_claim"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    VALUE_JUDGMENT = "value_judgment"

# ── Registry ────────────────────────────────────────────────────
class AuthorityRegistry:
    """Single source of truth for all issued evidence records, bundles, and atoms."""

    def __init__(self):
        self._records: Dict[str, EvidenceRecord] = {}
        self._bundles: Dict[str, EvidenceBundle] = {}
        self._atoms: Dict[str, Atom] = {}

    # ── registration ──
    def register_record(self, record: EvidenceRecord):
        if record.record_id in self._records:
            raise ValueError(f"REGISTRY_REJECTED: duplicate record {record.record_id}")
        self._records[record.record_id] = record

    def register_bundle(self, bundle: EvidenceBundle):
        if bundle.bundle_id in self._bundles:
            raise ValueError(f"REGISTRY_REJECTED: duplicate bundle {bundle.bundle_id}")
        self._bundles[bundle.bundle_id] = bundle

    def register_atom(self, atom: Atom):
        if atom.atom_id in self._atoms:
            raise ValueError(f"REGISTRY_REJECTED: duplicate atom {atom.atom_id}")
        self._atoms[atom.atom_id] = atom

    # ── verification ──
    def verify_record_id(self, record_id: str) -> bool:
        return record_id in self._records

    def verify_bundle_id(self, bundle_id: str) -> bool:
        return bundle_id in self._bundles

    def verify_atom_id(self, atom_id: str) -> bool:
        return atom_id in self._atoms

    def get_record(self, record_id: str) -> Optional[EvidenceRecord]:
        return self._records.get(record_id)

    def get_bundle(self, bundle_id: str) -> Optional[EvidenceBundle]:
        return self._bundles.get(bundle_id)

    def get_atom(self, atom_id: str) -> Optional[Atom]:
        return self._atoms.get(atom_id)

    @property
    def record_count(self) -> int: return len(self._records)
    @property
    def bundle_count(self) -> int: return len(self._bundles)
    @property
    def atom_count(self) -> int: return len(self._atoms)


# ── Evidence Record ─────────────────────────────────────────────
@dataclasses.dataclass(frozen=True)
class EvidenceRecord:
    """Immutable evidence record. Factory-issued and registry-verified."""
    record_id: str
    source_span_ref: Optional[str]  # Reference to SourceDocument+SourceSpan (Q2)
    evidence_layer: EvidenceLayer
    content: str
    source_digest: str  # SHA-256 of original source bytes
    factory_signature: bytes  # HMAC-SHA256(record_id + source_digest + content + evidence_layer)

    def verify(self, registry: AuthorityRegistry, factory: EvidenceFactory) -> bool:
        """Record is authoritative only if registry-verified and factory-signed."""
        if not registry.verify_record_id(self.record_id):
            return False
        if not factory.verify_record(self):
            return False
        return True


# ── Evidence Bundle ─────────────────────────────────────────────
@dataclasses.dataclass(frozen=True)
class EvidenceBundle:
    """Immutable evidence bundle. Factory-issued, identity from all records."""
    bundle_id: str
    records: Tuple[EvidenceRecord, ...]
    schema_version: str
    policy_version: str
    factory_signature: bytes

    @staticmethod
    def compute_identity(records: Tuple[EvidenceRecord, ...], schema_version: str, policy_version: str) -> str:
        h = hashlib.sha256()
        h.update(schema_version.encode())
        h.update(policy_version.encode())
        for r in sorted(records, key=lambda x: x.record_id):
            h.update(r.record_id.encode())
            h.update(r.source_digest.encode())
            h.update(r.content.encode())
            h.update(r.evidence_layer.value.encode())
        return h.hexdigest()

    def verify(self, registry: AuthorityRegistry, factory: EvidenceFactory) -> bool:
        if not registry.verify_bundle_id(self.bundle_id):
            return False
        # Recompute identity
        expected = self.compute_identity(self.records, self.schema_version, self.policy_version)
        if expected != self.bundle_id:
            return False
        if not factory.verify_bundle(self):
            return False
        # All records must verify
        for r in self.records:
            if not r.verify(registry, factory):
                return False
        return True

    def derived_confidence(self) -> ConfidenceBand:
        """Derive confidence from records, not caller-supplied."""
        layers = [r.evidence_layer for r in self.records]
        has_source = EvidenceLayer.SOURCE_FACT in layers
        has_claim = EvidenceLayer.AUTHOR_CLAIM in layers or EvidenceLayer.INFERENCE in layers
        n = len(self.records)
        if has_source and n >= 3 and EvidenceLayer.HYPOTHESIS not in layers:
            return ConfidenceBand.HIGH
        if has_source and n >= 2:
            return ConfidenceBand.MEDIUM
        if has_claim and n >= 1:
            return ConfidenceBand.LOW
        return ConfidenceBand.VERY_LOW


# ── Atom ────────────────────────────────────────────────────────
@dataclasses.dataclass(frozen=True)
class Atom:
    """Immutable knowledge atom. Factory-issued, registry-verified."""
    atom_id: str
    atom_type: AtomType
    text: str
    source_bundle_id: str
    provenance: EvidenceLayer
    confidence: ConfidenceBand
    scope: str
    verification_state: VerificationState
    invalidation_conditions: Tuple[str, ...]
    factory_signature: bytes

    def verify(self, registry: AuthorityRegistry, factory: AtomFactory) -> bool:
        if not registry.verify_atom_id(self.atom_id):
            return False
        # Recompute all canonical fields
        expected_id = self.compute_deterministic_id(
            self.text, self.atom_type, self.source_bundle_id,
            self.provenance, self.confidence, self.scope,
            self.verification_state, self.invalidation_conditions)
        if expected_id != self.atom_id:
            return False
        if not registry.verify_bundle_id(self.source_bundle_id):
            return False
        if not factory.verify_atom(self):
            return False
        return True

    @staticmethod
    def compute_deterministic_id(
        text: str, atom_type: AtomType, source_bundle_id: str,
        provenance: EvidenceLayer, confidence: ConfidenceBand,
        scope: str, verification_state: VerificationState,
        invalidation_conditions: Tuple[str, ...]) -> str:
        h = hashlib.sha256()
        h.update(text.encode("utf-8"))
        h.update(atom_type.value.encode())
        h.update(source_bundle_id.encode())
        h.update(provenance.value.encode())
        h.update(confidence.value.encode())
        h.update(scope.encode())
        h.update(verification_state.value.encode())
        for c in sorted(invalidation_conditions):
            h.update(c.encode())
        return h.hexdigest()


# ── Factories ───────────────────────────────────────────────────
class EvidenceFactory:
    """Only path to create EvidenceRecord and EvidenceBundle. Holds secret key."""

    def __init__(self, registry: AuthorityRegistry):
        self._registry = registry
        self._secret = _FactorySecret()
        self.SCHEMA_VERSION = "43.0"
        self.POLICY_VERSION = "1.0"

    def create_record(
        self, source_span_ref: Optional[str], evidence_layer: EvidenceLayer,
        content: str, source_digest: str) -> EvidenceRecord:
        """Create and register a new evidence record."""
        record_id = hashlib.sha256(
            f"{source_span_ref or ''}|{evidence_layer.value}|{content}|{source_digest}".encode()
        ).hexdigest()
        payload = f"{record_id}|{source_digest}|{content}|{evidence_layer.value}"
        signature = self._secret.sign(payload.encode())
        record = EvidenceRecord(
            record_id=record_id, source_span_ref=source_span_ref,
            evidence_layer=evidence_layer, content=content,
            source_digest=source_digest, factory_signature=signature)
        self._registry.register_record(record)
        return record

    def create_bundle(self, records: Tuple[EvidenceRecord, ...]) -> EvidenceBundle:
        """Create and register a new evidence bundle."""
        bundle_id = EvidenceBundle.compute_identity(records, self.SCHEMA_VERSION, self.POLICY_VERSION)
        payload = f"{bundle_id}|{self.SCHEMA_VERSION}|{self.POLICY_VERSION}"
        for r in sorted(records, key=lambda x: x.record_id):
            payload += f"|{r.record_id}"
        signature = self._secret.sign(payload.encode())
        bundle = EvidenceBundle(
            bundle_id=bundle_id, records=records,
            schema_version=self.SCHEMA_VERSION, policy_version=self.POLICY_VERSION,
            factory_signature=signature)
        self._registry.register_bundle(bundle)
        return bundle

    def verify_record(self, record: EvidenceRecord) -> bool:
        payload = f"{record.record_id}|{record.source_digest}|{record.content}|{record.evidence_layer.value}"
        return self._secret.verify(payload.encode(), record.factory_signature)

    def verify_bundle(self, bundle: EvidenceBundle) -> bool:
        payload = f"{bundle.bundle_id}|{bundle.schema_version}|{bundle.policy_version}"
        for r in sorted(bundle.records, key=lambda x: x.record_id):
            payload += f"|{r.record_id}"
        return self._secret.verify(payload.encode(), bundle.factory_signature)


class AtomFactory:
    """Only path to create Atom. Holds secret key."""

    def __init__(self, registry: AuthorityRegistry):
        self._registry = registry
        self._secret = _FactorySecret()

    def create(
        self, text: str, atom_type: AtomType, source_bundle_id: str,
        provenance: EvidenceLayer, confidence: ConfidenceBand,
        scope: str, verification_state: VerificationState,
        invalidation_conditions: Tuple[str, ...]) -> Atom:
        """Create and register a new atom. Bundle must exist in registry."""
        if not self._registry.verify_bundle_id(source_bundle_id):
            raise ValueError(f"REGISTRY_REJECTED: bundle {source_bundle_id} not in registry")
        atom_id = Atom.compute_deterministic_id(
            text, atom_type, source_bundle_id, provenance, confidence,
            scope, verification_state, invalidation_conditions)
        payload = f"{atom_id}|{text}|{atom_type.value}|{source_bundle_id}|{provenance.value}|{confidence.value}|{scope}|{verification_state.value}"
        for c in sorted(invalidation_conditions):
            payload += f"|{c}"
        signature = self._secret.sign(payload.encode())
        atom = Atom(
            atom_id=atom_id, atom_type=atom_type, text=text,
            source_bundle_id=source_bundle_id, provenance=provenance,
            confidence=confidence, scope=scope,
            verification_state=verification_state,
            invalidation_conditions=invalidation_conditions,
            factory_signature=signature)
        self._registry.register_atom(atom)
        return atom

    def verify_atom(self, atom: Atom) -> bool:
        payload = f"{atom.atom_id}|{atom.text}|{atom.atom_type.value}|{atom.source_bundle_id}|{atom.provenance.value}|{atom.confidence.value}|{atom.scope}|{atom.verification_state.value}"
        for c in sorted(atom.invalidation_conditions):
            payload += f"|{c}"
        return self._secret.verify(payload.encode(), atom.factory_signature)


# ── Rejection markers ───────────────────────────────────────────
FACTORY_REJECTED = "FACTORY_REJECTED"
REGISTRY_REJECTED = "REGISTRY_REJECTED"
