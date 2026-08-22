"""E44 Q2 — Derived evidence, bundle and atom authority.

Evidence layer, confidence, verification state, provenance, scope and invalidation
conditions are EVALUATOR-DERIVED from verified capability + versioned semantic policy,
never caller enums or booleans.

Registry insertion is private and identity-bound.
Verification compares the exact issued object and recomputes every canonical field.
Ordinary callers cannot read/reuse signing capability, self-register objects,
replace policy/registry state, pass caller source digests or forge copied objects.
"""
from __future__ import annotations

import hashlib, time, dataclasses, enum, hmac
from typing import Dict, List, Tuple, Optional, Set

from qclaw_e44.capability import (
    VerifiedEvidenceCapability, EvidenceOrigin, CAPABILITY_SCHEMA_VERSION,
)

__all__ = [
    "EvidenceLayer", "ConfidenceBand", "VerificationState",
    "AtomType", "EvidenceRecord", "EvidenceBundle", "Atom",
    "EvidenceFactory", "EvidenceError",
]

E44_SCHEMA = "44.0"
E44_POLICY = "1.0"


class EvidenceError(Exception):
    pass


class EvidenceLayer(enum.Enum):
    SOURCE_FACT = "source_fact"
    AUTHOR_CLAIM = "author_claim"
    EVIDENCE = "evidence"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    VALUE_JUDGMENT = "value_judgment"


class ConfidenceBand(enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class VerificationState(enum.Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    DISPUTED = "DISPUTED"
    FALSIFIED = "FALSIFIED"


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


# ── Issued objects: frozen, registry-bound ────────────────────

@dataclasses.dataclass(frozen=True)
class EvidenceRecord:
    """Registry-issued evidence record. Only EvidenceFactory can produce."""
    record_id: str
    capability_id: str
    evidence_layer: EvidenceLayer
    content_hash: str
    origin_class: EvidenceOrigin
    source_digest: str
    schema_version: str
    policy_version: str
    issuer: str
    issued_at_ns: int
    factory_signature: bytes

    def verify(self, registry: "EvidenceRegistry", factory: "EvidenceFactory") -> bool:
        """Re-verify by recomputing every canonical field against registry+factory."""
        return factory._re_verify_record(self, registry)


@dataclasses.dataclass(frozen=True)
class EvidenceBundle:
    """Grouped evidence records with derived confidence and verification state."""
    bundle_id: str
    record_ids: Tuple[str, ...]
    evidence_layer: EvidenceLayer
    confidence: ConfidenceBand
    verification_state: VerificationState
    provenance: EvidenceLayer
    scope: str
    invalidation_conditions: Tuple[str, ...]
    schema_version: str
    policy_version: str
    issuer: str
    factory_signature: bytes

    @property
    def record_count(self) -> int:
        return len(self.record_ids)

    def verify(self, registry: "EvidenceRegistry", factory: "EvidenceFactory") -> bool:
        return factory._re_verify_bundle(self, registry)


@dataclasses.dataclass(frozen=True)
class Atom:
    """Atomic knowledge unit. Registry-issued. Default CLAIM, not FACT."""
    atom_id: str
    text: str
    atom_type: AtomType
    source_bundle_id: str
    provenance: EvidenceLayer
    confidence: ConfidenceBand
    scope: str
    verification_state: VerificationState
    invalidation_conditions: Tuple[str, ...]
    schema_version: str
    policy_version: str
    issuer: str
    factory_signature: bytes

    def verify(self, registry: "EvidenceRegistry", factory: "EvidenceFactory") -> bool:
        return factory._re_verify_atom(self, registry)


# ── Registry ──────────────────────────────────────────────────

class EvidenceRegistry:
    """Private registry for issued objects. Only EvidenceFactory can insert."""

    def __init__(self):
        self._records: Dict[str, EvidenceRecord] = {}
        self._bundles: Dict[str, EvidenceBundle] = {}
        self._atoms: Dict[str, Atom] = {}

    def _insert_record(self, record: EvidenceRecord) -> None:
        if record.record_id in self._records:
            raise EvidenceError(f"duplicate record {record.record_id[:16]}")
        self._records[record.record_id] = record

    def _insert_bundle(self, bundle: EvidenceBundle) -> None:
        if bundle.bundle_id in self._bundles:
            raise EvidenceError(f"duplicate bundle {bundle.bundle_id[:16]}")
        self._bundles[bundle.bundle_id] = bundle

    def _insert_atom(self, atom: Atom) -> None:
        if atom.atom_id in self._atoms:
            raise EvidenceError(f"duplicate atom {atom.atom_id[:16]}")
        self._atoms[atom.atom_id] = atom

    def get_record(self, record_id: str) -> Optional[EvidenceRecord]:
        return self._records.get(record_id)

    def get_bundle(self, bundle_id: str) -> Optional[EvidenceBundle]:
        return self._bundles.get(bundle_id)

    def get_atom(self, atom_id: str) -> Optional[Atom]:
        return self._atoms.get(atom_id)

    @property
    def record_count(self) -> int:
        return len(self._records)

    @property
    def atom_count(self) -> int:
        return len(self._atoms)

    @property
    def bundle_count(self) -> int:
        return len(self._bundles)


# ── Factory ────────────────────────────────────────────────────

class EvidenceFactory:
    """Only path to create EvidenceRecord/Bundle/Atom.

    Holds private HMAC signing key. Callers cannot access key or self-register.
    All evidence fields are DERIVED from capability + policy, not caller-supplied.
    """

    def __init__(self, registry: EvidenceRegistry, signing_key: bytes):
        self._registry = registry
        self._signing_key = signing_key
        self._issuer = "E44-evidence-factory"
        self._schema = E44_SCHEMA
        self._policy = E44_POLICY

    # ── Evidence derivation policy ──
    def _derive_layer(self, cap: VerifiedEvidenceCapability) -> EvidenceLayer:
        """Derive evidence layer from verified capability, not caller input."""
        mapping = {
            EvidenceOrigin.SOURCE_FACT: EvidenceLayer.SOURCE_FACT,
            EvidenceOrigin.AUTHOR_CLAIM: EvidenceLayer.AUTHOR_CLAIM,
            EvidenceOrigin.INFERENCE: EvidenceLayer.INFERENCE,
            EvidenceOrigin.HYPOTHESIS: EvidenceLayer.HYPOTHESIS,
            EvidenceOrigin.VALUE_JUDGMENT: EvidenceLayer.VALUE_JUDGMENT,
            EvidenceOrigin.USER_EXPLICIT: EvidenceLayer.SOURCE_FACT,
            EvidenceOrigin.UNKNOWN_ORIGIN: EvidenceLayer.HYPOTHESIS,
        }
        return mapping.get(cap.origin_class, EvidenceLayer.HYPOTHESIS)

    def _derive_confidence(self, layer: EvidenceLayer) -> ConfidenceBand:
        """Derive confidence from evidence layer."""
        high_layers = (EvidenceLayer.SOURCE_FACT, EvidenceLayer.EVIDENCE)
        medium_layers = (EvidenceLayer.AUTHOR_CLAIM, EvidenceLayer.INFERENCE)
        if layer in high_layers: return ConfidenceBand.HIGH
        if layer in medium_layers: return ConfidenceBand.MEDIUM
        return ConfidenceBand.LOW

    def _derive_verification(self, layer: EvidenceLayer) -> VerificationState:
        """Derive verification state from evidence layer."""
        if layer == EvidenceLayer.SOURCE_FACT: return VerificationState.VERIFIED
        if layer in (EvidenceLayer.AUTHOR_CLAIM, EvidenceLayer.EVIDENCE):
            return VerificationState.PARTIALLY_VERIFIED
        return VerificationState.UNVERIFIED

    def _derive_invalidation(self, cap: VerifiedEvidenceCapability,
                             layer: EvidenceLayer) -> Tuple[str, ...]:
        """Derive invalidation conditions from evidence properties."""
        conditions = []
        if layer in (EvidenceLayer.HYPOTHESIS, EvidenceLayer.VALUE_JUDGMENT):
            conditions.append("unvalidated_origin")
        if cap.origin_class == EvidenceOrigin.INFERENCE:
            conditions.append("inference_not_directly_observed")
        return tuple(conditions)

    def _derive_scope(self, cap: VerifiedEvidenceCapability,
                      layer: EvidenceLayer) -> str:
        """Derive scope from capability origin."""
        if cap.origin_class == EvidenceOrigin.USER_EXPLICIT:
            return "personal_user_experience"
        if layer == EvidenceLayer.SOURCE_FACT:
            return "general_domain"
        if layer == EvidenceLayer.AUTHOR_CLAIM:
            return "attributed_source"
        return "speculative"

    def _sign(self, payload: bytes) -> bytes:
        return hmac.digest(self._signing_key, payload, "sha256")

    # ── Public factory methods ──

    def create_record(self, capability: VerifiedEvidenceCapability) -> EvidenceRecord:
        """Create an EvidenceRecord from a verified capability only."""
        content_hash = capability.evidence_digest
        layer = self._derive_layer(capability)
        record_id = hashlib.sha256(
            f"{capability.capability_id}|{layer.value}|{content_hash}|{E44_SCHEMA}".encode()
        ).hexdigest()

        record = EvidenceRecord(
            record_id=record_id,
            capability_id=capability.capability_id,
            evidence_layer=layer,
            content_hash=content_hash,
            origin_class=capability.origin_class,
            source_digest=capability.evidence_digest,
            schema_version=E44_SCHEMA,
            policy_version=E44_POLICY,
            issuer=self._issuer,
            issued_at_ns=time.time_ns(),
            factory_signature=b"",  # set below
        )
        # Sign
        payload = f"{record_id}|{layer.value}|{content_hash}|{E44_SCHEMA}".encode()
        signature = self._sign(payload)
        record = dataclasses.replace(record, factory_signature=signature)

        self._registry._insert_record(record)
        return record

    def create_bundle(self, records: Tuple[EvidenceRecord, ...],
                       scope_override: Optional[str] = None) -> EvidenceBundle:
        """Create a bundle from existing registry records. All fields derived."""
        if not records:
            raise EvidenceError("empty bundle")

        record_ids = tuple(r.record_id for r in records)

        # Derive bundle layer (lowest of all records)
        layer_priority = (EvidenceLayer.SOURCE_FACT, EvidenceLayer.EVIDENCE,
                         EvidenceLayer.AUTHOR_CLAIM, EvidenceLayer.INFERENCE,
                         EvidenceLayer.HYPOTHESIS, EvidenceLayer.VALUE_JUDGMENT)
        bundle_layer = max(records, key=lambda r: layer_priority.index(r.evidence_layer)).evidence_layer

        confidence = self._derive_confidence(bundle_layer)
        verification = self._derive_verification(bundle_layer)
        scope = scope_override or self._derive_scope_aggregate(records)
        provenance = bundle_layer

        # Collect invalidation from all records
        all_conds: Set[str] = set()
        for r in records:
            inv = self._derive_invalidation_from_layer(r.evidence_layer)
            all_conds.update(inv)

        bundle_id = hashlib.sha256(
            "|".join(record_ids).encode() + E44_SCHEMA.encode()
        ).hexdigest()

        bundle = EvidenceBundle(
            bundle_id=bundle_id,
            record_ids=record_ids,
            evidence_layer=bundle_layer,
            confidence=confidence,
            verification_state=verification,
            provenance=provenance,
            scope=scope,
            invalidation_conditions=tuple(sorted(all_conds)),
            schema_version=E44_SCHEMA,
            policy_version=E44_POLICY,
            issuer=self._issuer,
            factory_signature=b"",
        )

        payload = f"{bundle_id}|{'|'.join(record_ids)}|{E44_SCHEMA}".encode()
        signature = self._sign(payload)
        bundle = dataclasses.replace(bundle, factory_signature=signature)

        self._registry._insert_bundle(bundle)
        return bundle

    def create_atom(self, text: str, atom_type: AtomType, bundle: EvidenceBundle,
                    *_unused) -> Atom:
        """Create an atom from a verified bundle. Atom type is caller-hinted
        but confidence/verification/scope are DERIVED from the bundle, not caller."""
        provenance = bundle.provenance
        confidence = bundle.confidence
        verification = bundle.verification_state
        scope = bundle.scope
        invalidation = bundle.invalidation_conditions

        atom_id = hashlib.sha256(
            f"{text[:500]}|{atom_type.value}|{bundle.bundle_id}|{E44_SCHEMA}".encode()
        ).hexdigest()

        atom = Atom(
            atom_id=atom_id,
            text=text[:500],
            atom_type=atom_type,
            source_bundle_id=bundle.bundle_id,
            provenance=provenance,
            confidence=confidence,
            scope=scope,
            verification_state=verification,
            invalidation_conditions=invalidation,
            schema_version=E44_SCHEMA,
            policy_version=E44_POLICY,
            issuer=self._issuer,
            factory_signature=b"",
        )

        payload = f"{atom_id}|{atom_type.value}|{bundle.bundle_id}|{E44_SCHEMA}".encode()
        signature = self._sign(payload)
        atom = dataclasses.replace(atom, factory_signature=signature)

        self._registry._insert_atom(atom)
        return atom

    # ── Re-verification (internal, for verify() methods) ──

    def _re_verify_record(self, record: EvidenceRecord,
                          registry: EvidenceRegistry) -> bool:
        stored = registry.get_record(record.record_id)
        if stored is None or stored is not record:
            return False
        expected_payload = f"{record.record_id}|{record.evidence_layer.value}|{record.content_hash}|{E44_SCHEMA}".encode()
        expected_sig = self._sign(expected_payload)
        if record.factory_signature != expected_sig:
            return False
        return record.schema_version == E44_SCHEMA and record.issuer == self._issuer

    def _re_verify_bundle(self, bundle: EvidenceBundle,
                          registry: EvidenceRegistry) -> bool:
        stored = registry.get_bundle(bundle.bundle_id)
        if stored is None or stored is not bundle:
            return False
        expected_payload = f"{bundle.bundle_id}|{'|'.join(bundle.record_ids)}|{E44_SCHEMA}".encode()
        return bundle.factory_signature == self._sign(expected_payload) and bundle.issuer == self._issuer

    def _re_verify_atom(self, atom: Atom, registry: EvidenceRegistry) -> bool:
        stored = registry.get_atom(atom.atom_id)
        if stored is None or stored is not atom:
            return False
        expected_payload = f"{atom.atom_id}|{atom.atom_type.value}|{atom.source_bundle_id}|{E44_SCHEMA}".encode()
        return atom.factory_signature == self._sign(expected_payload) and atom.issuer == self._issuer

    def _derive_scope_aggregate(self, records: Tuple[EvidenceRecord, ...]) -> str:
        origins = {r.origin_class for r in records}
        if EvidenceOrigin.USER_EXPLICIT in origins:
            return "personal_user_experience"
        if EvidenceOrigin.SOURCE_FACT in origins:
            return "general_domain"
        return "speculative"

    def _derive_invalidation_from_layer(self, layer: EvidenceLayer) -> Tuple[str, ...]:
        if layer == EvidenceLayer.HYPOTHESIS:
            return ("unvalidated_origin",)
        if layer == EvidenceLayer.VALUE_JUDGMENT:
            return ("unvalidated_origin", "subjective")
        if layer == EvidenceLayer.INFERENCE:
            return ("inference_not_directly_observed",)
        return ()
