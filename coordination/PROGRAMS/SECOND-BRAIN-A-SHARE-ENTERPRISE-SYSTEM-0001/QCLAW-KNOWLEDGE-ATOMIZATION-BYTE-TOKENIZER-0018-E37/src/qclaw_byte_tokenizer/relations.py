"""E37 S3 — Relations: explicit-link-only semantic relations.

Only 6 legal relation types, each REQUIRES explicit evidence source.
Adjacency/proximity/type-pairing NEVER generates a relation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, FrozenSet
import hashlib
from .atoms import Atom


# ── legal relation types ─────────────────────────────────────────────
LEGAL_TYPES = frozenset({
    "SUPPORTS",
    "DEPENDS_ON",
    "REFINES",
    "CONTRADICTS",
    "RAISES_UNKNOWN",
    "VERIFIED_BY",
})

# Legal evidence sources
LEGAL_SOURCES = frozenset({
    "explicit_link_syntax",     # e.g., [[ref]] in markdown
    "verifiable_rule_id",       # e.g., schema $id reference
    "human_confirmation",       # explicit human annotation
    "verified_parser_structure",  # structural postcondition proven by parser
})


# ── Relation ─────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Relation:
    relation_id: str
    rel_type: str            # one of LEGAL_TYPES
    source_atom_id: str      # atom_id
    target_atom_id: str      # atom_id
    evidence_source: str     # one of LEGAL_SOURCES
    evidence_detail: str     # human-readable evidence
    confidence: float = 1.0  # 0.0-1.0

    def __post_init__(self):
        if self.rel_type not in LEGAL_TYPES:
            raise ValueError(f"Illegal relation type: {self.rel_type}")
        if self.evidence_source not in LEGAL_SOURCES:
            raise ValueError(f"Illegal evidence source: {self.evidence_source}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be [0,1]: {self.confidence}")


# ── relation builder ─────────────────────────────────────────────────
def build_relation_id(source_id: str, target_id: str, rel_type: str) -> str:
    return hashlib.sha256(
        f"{source_id}|{rel_type}|{target_id}".encode("utf-8")
    ).hexdigest()


def relate(
    source: Atom,
    target: Atom,
    rel_type: str,
    evidence_source: str,
    evidence_detail: str,
    confidence: float = 1.0,
) -> Relation:
    return Relation(
        relation_id=build_relation_id(source.atom_id, target.atom_id, rel_type),
        rel_type=rel_type,
        source_atom_id=source.atom_id,
        target_atom_id=target.atom_id,
        evidence_source=evidence_source,
        evidence_detail=evidence_detail,
        confidence=confidence,
    )


# ── forbidden adjacency detector (for tests) ────────────────────────
def adjacency_based_relations(atoms: List[Atom]) -> List[Relation]:
    """Return NO relations — adjacency never generates relations."""
    return []  # Explicitly empty; adjacency is NEVER a valid source


def type_pairing_relations(atoms: List[Atom]) -> List[Relation]:
    """Return NO relations — type pairing never generates relations."""
    return []  # Explicitly empty
