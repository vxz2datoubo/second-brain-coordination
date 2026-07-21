"""Candidate-only fusion wrapper based on PR #46 lifecycle behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .memory_store import MemoryStore


@dataclass(frozen=True)
class FusionResult:
    status: str
    packet_id: str
    revision_id: str
    atoms_inserted: int
    authority_write: bool = False


class FusionEngine:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def ingest_candidate(self, packet: dict[str, Any]) -> FusionResult:
        if packet.get("status") != "candidate" or packet.get("authority_write") is not False:
            raise ValueError("fusion_candidate_boundary_violation")
        result = self.store.import_learning_packet(packet)
        return FusionResult(
            status=result["status"],
            packet_id=result["packet_id"],
            revision_id=result.get("revision_id") or self.store.latest_revision_id(),
            atoms_inserted=int(result["atoms_inserted"]),
        )
