"""E39 S4 — Deterministic packet with full semantic hash.

Packet includes:
- Full coverage ledger state
- Atoms + relations + unknowns + conflicts
- Redaction mapping (if any)
- Safe lineage + config
- packet_id does NOT self-reference
- All semantic fields participate in hash
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import hashlib
import json

from .atoms import Atom
from .relations import Relation
from .ledger import ByteLedger
from .redact import RedactionMapping


@dataclass
class LearningPacket:
    """Complete knowledge packet with deterministic identity."""
    packet_id: str
    atoms: List[Atom] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    redaction_map: List[Dict[str, Any]] = field(default_factory=list)
    coverage_data: Dict[str, Any] = field(default_factory=dict)
    source_hash: str = ""
    source_commit: str = ""
    policy_version: str = "1.0.0"
    config_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "atoms_count": len(self.atoms),
            "relations_count": len(self.relations),
            "unknowns_count": len(self.unknowns),
            "conflicts_count": len(self.conflicts),
            "redaction_count": len(self.redaction_map),
            "coverage": self.coverage_data,
            "source_hash": self.source_hash,
            "source_commit": self.source_commit,
            "policy_version": self.policy_version,
            "config_hash": self.config_hash,
        }


def _compute_atom_hash(atoms: List[Atom]) -> str:
    """Hash of all atoms (sorted by ID for determinism)."""
    sorted_atoms = sorted(atoms, key=lambda a: a.atom_id)
    combined = json.dumps([a.to_dict() for a in sorted_atoms], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _compute_relation_hash(relations: List[Relation]) -> str:
    """Hash of all relations (sorted by ID for determinism)."""
    sorted_rels = sorted(relations, key=lambda r: r.relation_id)
    combined = json.dumps([r.to_dict() for r in sorted_rels], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def build_packet(
    atoms: List[Atom],
    relations: List[Relation],
    ledger: ByteLedger,
    redaction_map: Optional[List[Dict[str, Any]]] = None,
    unknowns: Optional[List[str]] = None,
    conflicts: Optional[List[str]] = None,
    source_hash: str = "",
    source_commit: str = "",
    config_hash: str = "",
) -> LearningPacket:
    """Build a LearningPacket with deterministic packet_id.

    packet_id = sha256(atoms_hash + relations_hash + coverage_hash +
                        unknowns_hash + conflicts_hash + source_hash +
                        config_hash + policy_version)

    Does NOT self-reference.
    """
    atoms_hash = _compute_atom_hash(atoms)
    relations_hash = _compute_relation_hash(relations)

    coverage = ledger.check()
    coverage_str = json.dumps({
        "total_bytes": coverage["total_bytes"],
        "covered": coverage["covered"],
        "spans": coverage["spans"],
        "gaps": coverage["gaps"],
        "gap_count": coverage["gap_count"],
        "overlap_count": coverage["overlap_count"],
        "complete": coverage["complete"],
    }, sort_keys=True)
    coverage_hash = hashlib.sha256(coverage_str.encode("utf-8")).hexdigest()

    unknowns_sorted = sorted(unknowns or [])
    unknowns_hash = hashlib.sha256(
        json.dumps(unknowns_sorted, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    conflicts_sorted = sorted(conflicts or [])
    conflicts_hash = hashlib.sha256(
        json.dumps(conflicts_sorted, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    redact = redaction_map or []
    redact_hash = hashlib.sha256(
        json.dumps(redact, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    # Packet ID: all semantic components (no self-reference)
    packet_id_input = json.dumps({
        "atoms_hash": atoms_hash,
        "relations_hash": relations_hash,
        "coverage_hash": coverage_hash,
        "unknowns_hash": unknowns_hash,
        "conflicts_hash": conflicts_hash,
        "redact_hash": redact_hash,
        "source_hash": source_hash,
        "config_hash": config_hash,
        "policy_version": "1.0.0",
    }, sort_keys=True, ensure_ascii=False)

    packet_id = hashlib.sha256(packet_id_input.encode("utf-8")).hexdigest()

    return LearningPacket(
        packet_id=packet_id,
        atoms=atoms,
        relations=relations,
        unknowns=unknowns or [],
        conflicts=conflicts or [],
        redaction_map=redact,
        coverage_data=coverage,
        source_hash=source_hash,
        source_commit=source_commit,
        config_hash=config_hash,
    )
