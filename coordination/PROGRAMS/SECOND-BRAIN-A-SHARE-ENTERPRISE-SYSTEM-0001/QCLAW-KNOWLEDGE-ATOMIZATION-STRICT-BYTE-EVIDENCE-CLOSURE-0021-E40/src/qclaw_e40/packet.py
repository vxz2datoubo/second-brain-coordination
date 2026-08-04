"""E40 S4 — Canonical packet with full content serialization."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
import hashlib
import json as _json


@dataclass
class LearningPacket:
    """Canonical learning packet — full content, not counts-only."""
    packet_id: str = ""
    packet_content_hash: str = ""
    atoms_count: int = 0
    relations_count: int = 0
    unknowns_count: int = 0
    conflicts_count: int = 0
    coverage_bytes: int = 0
    total_source_bytes: int = 0
    line_count: int = 0
    has_bom: bool = False
    redaction_mapping_count: int = 0
    atom_hashes: List[str] = field(default_factory=list)
    relation_hashes: List[str] = field(default_factory=list)
    lineage: str = ""
    config_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> bytes:
        return _json.dumps(self.to_dict(), indent=2, sort_keys=True).encode("utf-8")

    def compute_hash(self) -> str:
        """Deterministic hash over all semantic fields."""
        h = hashlib.sha256()
        # Serialize with sorted keys for determinism
        d = self.to_dict()
        # Exclude self-referencing fields
        d.pop("packet_id", None)
        d.pop("packet_content_hash", None)
        h.update(_json.dumps(d, sort_keys=True).encode("utf-8"))
        return h.hexdigest()

    def finalize(self) -> str:
        """Compute hash and set packet_id."""
        h = self.compute_hash()
        self.packet_content_hash = h
        self.packet_id = f"pkt_{h[:16]}"
        return h
