"""E41 Q1 — Knowledge Atom Taxonomy

12 atomic knowledge types with 6 evidence-layer distinctions.
Every atom carries provenance, confidence, scope, verification state
and invalidation conditions. No externally supplied authority label
is trusted without evaluator evidence.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import hashlib


class AtomType(str, Enum):
    """Twelve irreducible knowledge categories."""
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


class EvidenceLayer(str, Enum):
    """Six layers separating source truth from interpretation."""
    SOURCE_FACT = "source_fact"
    AUTHOR_CLAIM = "author_claim"
    EVIDENCE = "evidence"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    VALUE_JUDGMENT = "value_judgment"


class VerificationState(str, Enum):
    UNVERIFIED = "unverified"
    PARTIALLY_VERIFIED = "partially_verified"
    VERIFIED = "verified"
    FALSIFIED = "falsified"
    NOT_VERIFIABLE = "not_verifiable"


class ConfidenceBand(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNKNOWN = "unknown"


class MemoryDestination(str, Enum):
    GLOBAL = "global"
    PROJECT = "project"
    CANDIDATE = "candidate"
    UNPERSISTED = "unpersisted"


@dataclass(frozen=True)
class Atom:
    """An irreducible knowledge atom with full provenance."""
    atom_id: str
    atom_type: AtomType
    evidence_layer: EvidenceLayer
    text: str  # the content string
    source_reference: str  # exact source ref
    is_quoted_source: bool  # True = direct quote, False = system interpretation
    provenance: str  # origin description
    confidence: ConfidenceBand
    scope: str  # scope qualifier
    verification_state: VerificationState
    invalidation_conditions: List[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        atom_type: AtomType,
        evidence_layer: EvidenceLayer,
        text: str,
        source_reference: str,
        is_quoted_source: bool,
        provenance: str,
        confidence: ConfidenceBand = ConfidenceBand.UNKNOWN,
        scope: str = "unspecified",
        verification_state: VerificationState = VerificationState.UNVERIFIED,
        invalidation_conditions: Optional[List[str]] = None,
    ) -> Atom:
        """Create an atom with deterministic ID."""
        id_input = f"{atom_type.value}|{evidence_layer.value}|{text}|{source_reference}|{provenance}"
        atom_id = hashlib.sha256(id_input.encode("utf-8")).hexdigest()[:16]
        return cls(
            atom_id=atom_id,
            atom_type=atom_type,
            evidence_layer=evidence_layer,
            text=text,
            source_reference=source_reference,
            is_quoted_source=is_quoted_source,
            provenance=provenance,
            confidence=confidence,
            scope=scope,
            verification_state=verification_state,
            invalidation_conditions=list(invalidation_conditions or []),
        )


# Taxonomy validators
VALID_ATOM_TYPES = frozenset(at.value for at in AtomType)
VALID_EVIDENCE_LAYERS = frozenset(el.value for el in EvidenceLayer)
VALID_VERIFICATION_STATES = frozenset(vs.value for vs in VerificationState)
VALID_CONFIDENCE_BANDS = frozenset(cb.value for cb in ConfidenceBand)
VALID_MEMORY_DESTINATIONS = frozenset(md.value for md in MemoryDestination)


def classify_atom_type(text: str, context: Dict[str, str] = None) -> Tuple[AtomType, str]:
    """Classify an atom's type based on content and context.
    
    Returns (type, reasoning).
    Never auto-promotes to DEFINITION without explicit definition syntax.
    Never auto-promotes to FACT — all atoms are author/source claims by default.
    """
    ctx = context or {}
    if ctx.get("explicit_type"):
        try:
            return AtomType(ctx["explicit_type"]), "explicitly provided"
        except ValueError:
            pass

    # Conservative classification — default to CONCEPT
    return AtomType.CONCEPT, "default conservative classification"


def separate_evidence_layer(text: str, author: str = "source") -> EvidenceLayer:
    """Determine the evidence layer. Default to AUTHOR_CLAIM.
    
    Never auto-promotes to SOURCE_FACT without explicit source-fact markers.
    Never auto-promotes to EVIDENCE without verifiable supporting data.
    """
    return EvidenceLayer.AUTHOR_CLAIM


def validate_atom(atom: Atom) -> List[str]:
    """Validate an atom against taxonomy invariants. Returns list of violations."""
    violations = []
    if atom.atom_type.value not in VALID_ATOM_TYPES:
        violations.append(f"invalid atom_type: {atom.atom_type}")
    if atom.evidence_layer.value not in VALID_EVIDENCE_LAYERS:
        violations.append(f"invalid evidence_layer: {atom.evidence_layer}")
    if atom.confidence.value not in VALID_CONFIDENCE_BANDS:
        violations.append(f"invalid confidence: {atom.confidence}")
    if atom.verification_state.value not in VALID_VERIFICATION_STATES:
        violations.append(f"invalid verification_state: {atom.verification_state}")
    if not atom.text.strip():
        violations.append("empty text")
    if not atom.source_reference.strip():
        violations.append("empty source_reference")
    return violations
