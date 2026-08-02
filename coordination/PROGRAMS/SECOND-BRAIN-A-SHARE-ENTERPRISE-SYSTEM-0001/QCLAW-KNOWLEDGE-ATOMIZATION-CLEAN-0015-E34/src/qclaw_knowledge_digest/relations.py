"""
QCLAW E34 — Relation Extractor
6 relation types: SUPPORTS, DEPENDS_ON, REFINES, CONTRADICTS, RAISES_UNKNOWN, VERIFIED_BY
Adapted from E28 relations_v2 design.
"""
import hashlib
from typing import List, Optional
from .atomizer import KnowledgeAtom, Relation


# Known relation types
RELATION_TYPES = [
    "SUPPORTS",
    "DEPENDS_ON",
    "REFINES",
    "CONTRADICTS",
    "RAISES_UNKNOWN",
    "VERIFIED_BY",
    "CONDITIONS",
    "EXCEPTED_BY",
]


def extract_proximity_relations(atoms: List[KnowledgeAtom]) -> List[Relation]:
    """Extract relations based on proximity and content type."""
    relations = []
    
    for i in range(len(atoms) - 1):
        a = atoms[i]
        b = atoms[i + 1]
        
        rtype = "SUPPORTS"  # default
        
        if a.content_type.value == "CONDITION":
            rtype = "CONDITIONS"
        elif a.content_type.value == "EXCEPTION":
            rtype = "EXCEPTED_BY"
        elif b.content_type.value == "EXCEPTION":
            rtype = "EXCEPTED_BY"
        elif a.content_type.value == "CONFLICT":
            rtype = "CONTRADICTS"
        elif b.content_type.value == "CONFLICT":
            rtype = "CONTRADICTS"
        elif b.content_type.value in ("UNKNOWN",):
            rtype = "RAISES_UNKNOWN"
        elif b.content_type.value == "NEGATION":
            rtype = "CONTRADICTS"
        elif a.content_type.value == "DEFINITION":
            rtype = "REFINES"
        
        relations.append(Relation(
            source_atom_id=a.deterministic_id,
            target_atom_id=b.deterministic_id,
            relation_type=rtype,
        ))
    
    return relations


def compute_relation_id(r: Relation) -> str:
    """Deterministic relation ID."""
    canonical = f"{r.source_atom_id}|{r.relation_type}|{r.target_atom_id}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
