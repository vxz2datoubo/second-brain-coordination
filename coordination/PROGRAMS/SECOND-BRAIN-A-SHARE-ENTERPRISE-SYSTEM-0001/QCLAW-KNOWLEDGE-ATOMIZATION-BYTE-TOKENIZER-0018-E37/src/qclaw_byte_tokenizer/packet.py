"""E37 S3 — Packet: semantic packet builder with full hash coverage.

Hashes: all atoms (deterministic IDs), all relations (with evidence/confidence),
all UNKNOWNs/gaps, conflicts, redaction mapping, source lineage, config snapshot.
No self-referencing packet_id.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, FrozenSet
import hashlib, json
from .atoms import Atom
from .relations import Relation
from .redact import RedactedView, RedactionMapping


# ── Packet ───────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Packet:
    packet_id: str               # NOT self-referenced in hash input
    packet_content_hash: str      # hash of all semantic content
    source_hash: str
    source_byte_len: int
    atom_count: int
    relation_count: int
    unknown_count: int
    conflict_count: int
    coverage_ratio: float
    gap_count: int
    redaction_mapping_hash: str   # hash of redaction mappings (NOT secret content)
    semantic_hash: str            # hash of all atoms+relations+unknowns+config
    config_snapshot: str = ""     # frozen config at build time


# ── builder ──────────────────────────────────────────────────────────
def build_packet(
    atoms: List[Atom],
    relations: List[Relation],
    unknowns: List[str],
    conflicts: List[str],
    gaps: List[Tuple[int, int]],
    source_bytes: bytes,
    total_bytes: int,
    redaction_view: Optional[RedactedView] = None,
) -> Packet:
    """Build a LearningPacket with full hash coverage.

    packet_id is NOT included in its own hash computation.
    """
    source_hash = hashlib.sha256(source_bytes).hexdigest()

    # Coverage
    covered = sum(a.byte_len for a in atoms)
    coverage = covered / total_bytes if total_bytes > 0 else 1.0

    # Redaction mapping hash (structure only, no secret content)
    rm_hash = "none"
    if redaction_view is not None:
        rm_parts = []
        for m in redaction_view.mappings:
            rm_parts.append(f"{m.original_span[0]},{m.original_span[1]}:{m.category}:{m.length_change}")
        rm_hash = hashlib.sha256("|".join(sorted(rm_parts)).encode("utf-8")).hexdigest()

    # Semantic hash: all atoms (sorted by ID), relations, unknowns, conflicts, config
    sem_parts = []
    for a in sorted(atoms, key=lambda x: x.atom_id):
        sem_parts.append(f"A:{a.atom_id}:{a.class_}:{a.role}:{a.byte_start}-{a.byte_end}")
    for r in sorted(relations, key=lambda x: x.relation_id):
        sem_parts.append(f"R:{r.relation_id}:{r.rel_type}:{r.source_atom_id[:12]}→{r.target_atom_id[:12]}:{r.evidence_source}:{r.confidence:.4f}")
    for u in sorted(unknowns):
        sem_parts.append(f"U:{hashlib.sha256(u.encode()).hexdigest()[:16]}")
    for c in sorted(conflicts):
        sem_parts.append(f"C:{hashlib.sha256(c.encode()).hexdigest()[:16]}")
    sem_parts.append(f"G:{len(gaps)}")
    semantic_hash = hashlib.sha256("\n".join(sem_parts).encode("utf-8")).hexdigest()

    # Packet content hash (everything except packet_id itself)
    content_input = (
        f"source={source_hash}|bytes={total_bytes}|atoms={len(atoms)}"
        f"|relations={len(relations)}|unknowns={len(unknowns)}"
        f"|conflicts={len(conflicts)}|coverage={coverage:.6f}"
        f"|gaps={len(gaps)}|redact={rm_hash}|semantic={semantic_hash}"
    )
    packet_content_hash = hashlib.sha256(content_input.encode("utf-8")).hexdigest()

    # packet_id computed from content_hash + source_hash (NOT self-referenced)
    packet_id = hashlib.sha256(
        f"packet:{packet_content_hash}:{source_hash}".encode("utf-8")
    ).hexdigest()

    return Packet(
        packet_id=packet_id,
        packet_content_hash=packet_content_hash,
        source_hash=source_hash,
        source_byte_len=total_bytes,
        atom_count=len(atoms),
        relation_count=len(relations),
        unknown_count=len(unknowns),
        conflict_count=len(conflicts),
        coverage_ratio=coverage,
        gap_count=len(gaps),
        redaction_mapping_hash=rm_hash,
        semantic_hash=semantic_hash,
        config_snapshot="",
    )
