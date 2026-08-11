"""E40 S4 — Relations: only 6 types, evidence-backed, no adjacency-default."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum


class RelationType(str, Enum):
    SUPPORTS = "SUPPORTS"
    DEPENDS_ON = "DEPENDS_ON"
    REFINES = "REFINES"
    CONTRADICTS = "CONTRADICTS"
    RAISES_UNKNOWN = "RAISES_UNKNOWN"
    VERIFIED_BY = "VERIFIED_BY"


@dataclass
class Relation:
    """A semantic relation with verifiable evidence."""
    relation_type: RelationType
    source_atom_id: str
    target_atom_id: str
    evidence: str  # how verified: explicit_link_syntax/verifiable_rule_id/human_confirmation/verified_parser_structure
    confidence: float = 0.0

    def __post_init__(self):
        if not isinstance(self.relation_type, RelationType):
            raise ValueError(f"[illegal_relation_type] {self.relation_type!r}")

    def is_valid(self) -> bool:
        """A relation is valid only if both endpoints exist and evidence is provided."""
        return (bool(self.source_atom_id) and bool(self.target_atom_id)
                and bool(self.evidence) and self.confidence >= 0)


# Allowed relation sources
VALID_EVIDENCE_SOURCES = {
    "explicit_link_syntax",
    "verifiable_rule_id",
    "human_confirmation",
    "verified_parser_structure",
}


def adjacency_based_relations(atoms) -> List[Relation]:
    """Adjacency is NOT evidence. This always returns empty."""
    return []  # Explicitly empty — adjacency is not evidence
