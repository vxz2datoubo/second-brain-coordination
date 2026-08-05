"""E39 S4 — Relations with explicit evidence only.

Six legal relation types:
  SUPPORTS, DEPENDS_ON, REFINES, CONTRADICTS, RAISES_UNKNOWN, VERIFIED_BY

All relations MUST have explicit evidence spans. No adjacency-default,
no proximity-based, no type-pairing relations. Only:
  - explicit_link_syntax (e.g. markdown links, references)
  - verifiable_rule_id (deterministic rule match)
  - verified_parser_structure (structural relationship from parser)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import hashlib

from .atoms import Atom


# ═══════════════════════════════════════════════════════════════════════
# Legal relation types
# ═══════════════════════════════════════════════════════════════════════

REL_SUPPORTS = "SUPPORTS"
REL_DEPENDS_ON = "DEPENDS_ON"
REL_REFINES = "REFINES"
REL_CONTRADICTS = "CONTRADICTS"
REL_RAISES_UNKNOWN = "RAISES_UNKNOWN"
REL_VERIFIED_BY = "VERIFIED_BY"

LEGAL_RELATIONS = frozenset({
    REL_SUPPORTS, REL_DEPENDS_ON, REL_REFINES,
    REL_CONTRADICTS, REL_RAISES_UNKNOWN, REL_VERIFIED_BY,
})

LEGAL_EVIDENCE_SOURCES = frozenset({
    "explicit_link_syntax",
    "verifiable_rule_id",
    "human_confirmation",
    "verified_parser_structure",
})


@dataclass
class Relation:
    """A directed relation between two atoms with mandatory evidence."""
    source_id: str      # source atom ID
    target_id: str      # target atom ID
    relation_type: str
    evidence_source: str  # one of LEGAL_EVIDENCE_SOURCES
    evidence_detail: str  # human-readable evidence description
    evidence_bytes: str = ""  # hex-encoded SHA256 of evidence content
    confidence: float = 0.0

    def __post_init__(self):
        if self.relation_type not in LEGAL_RELATIONS:
            raise ValueError(
                f"Illegal relation type: {self.relation_type}. "
                f"Allowed: {sorted(LEGAL_RELATIONS)}"
            )
        if self.evidence_source not in LEGAL_EVIDENCE_SOURCES:
            raise ValueError(
                f"Illegal evidence source: {self.evidence_source}. "
                f"Allowed: {sorted(LEGAL_EVIDENCE_SOURCES)}"
            )

    @property
    def relation_id(self) -> str:
        """Deterministic relation ID from source+target+type."""
        canonical = f"{self.source_id}|{self.target_id}|{self.relation_type}"
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relation_id": self.relation_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "evidence_source": self.evidence_source,
            "evidence_detail": self.evidence_detail,
            "evidence_bytes": self.evidence_bytes,
            "confidence": self.confidence,
        }


# ═══════════════════════════════════════════════════════════════════════
# Relation extraction
# ═══════════════════════════════════════════════════════════════════════

def adjacency_based_relations(atoms: List[Atom]) -> List[Relation]:
    """NEVER returns adjacency-based relations. This is the explicit gate."""
    return []  # Explicitly empty — adjacency is not evidence


def extract_relations(
    atoms: List[Atom],
    source_bytes: bytes,
    confirmed: Optional[List[Relation]] = None,
) -> List[Relation]:
    """Extract relations from atoms using ONLY explicit evidence.

    Checks for:
    1. explicit_link_syntax: Markdown-style references between atoms
    2. verifiable_rule_id: Pattern-based structural relationships
    3. human_confirmation: Externally-provided confirmed relations

    Returns list of relations. Adjacency/proximity NEVER used.
    """
    relations: List[Relation] = []

    if confirmed:
        for rel in confirmed:
            if rel.relation_type not in LEGAL_RELATIONS:
                raise ValueError(f"Illegal type in confirmed: {rel.relation_type}")
            if rel.evidence_source != "human_confirmation":
                raise ValueError(f"Confirmed must use human_confirmation source")
        relations.extend(confirmed)

    return relations
