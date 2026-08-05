"""E35 S5 — PacketBuilder: SHA-256 of complete semantic content."""
from dataclasses import dataclass, field
from typing import List, Optional
import hashlib
import json


@dataclass
class KnowledgePacket:
    """Complete atomization output with deterministic hash."""
    schema_version: str
    packet_id: str
    source_hash: str
    atoms: list
    relations: list
    unknowns: list
    conflicts: list
    lineage: dict
    byte_coverage: float

    def compute_packet_hash(self) -> str:
        """Deterministic packet hash from semantic content only (not packet_id)."""
        h = hashlib.sha256()
        h.update(self.schema_version.encode())
        h.update(self.source_hash.encode())
        h.update(json.dumps(self.atoms, sort_keys=True, ensure_ascii=False).encode())
        h.update(json.dumps(self.relations, sort_keys=True, ensure_ascii=False).encode())
        h.update(json.dumps(self.unknowns, sort_keys=True, ensure_ascii=False).encode())
        h.update(json.dumps(self.conflicts, sort_keys=True, ensure_ascii=False).encode())
        h.update(json.dumps(self.lineage, sort_keys=True, ensure_ascii=False).encode())
        return h.hexdigest()

    def to_dict(self):
        self.packet_id = self.compute_packet_hash()
        return {
            "schema_version": self.schema_version,
            "packet_id": self.packet_id,
            "source_hash": self.source_hash,
            "atoms": self.atoms,
            "relations": self.relations,
            "unknowns": self.unknowns,
            "conflicts": self.conflicts,
            "lineage": self.lineage,
            "byte_coverage": self.byte_coverage
        }


class PacketBuilder:
    """Build deterministic knowledge packets from atomization results."""

    def __init__(self, schema_version: str = "1.0.0-e35"):
        self.schema_version = schema_version

    def build(self, source: str, atoms: list, relations: list,
              source_hash: str = "", lineage: dict = None,
              unknowns: list = None, conflicts: list = None) -> KnowledgePacket:
        source_hash = source_hash or hashlib.sha256(source.encode()).hexdigest()
        return KnowledgePacket(
            schema_version=self.schema_version,
            packet_id="",
            source_hash=source_hash,
            atoms=atoms,
            relations=relations,
            unknowns=unknowns or [],
            conflicts=conflicts or [],
            lineage=lineage or {},
            byte_coverage=0.0
        )
