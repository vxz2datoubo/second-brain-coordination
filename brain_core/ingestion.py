"""Input ingestion pipeline."""

from __future__ import annotations

from typing import Any

from .contracts import EpisodicMemory, SourceRecord
from .knowledge import atomize_text
from .storage import BrainStore


class TextIngestor:
    def __init__(self, store: BrainStore):
        self.store = store

    def ingest_text(
        self,
        text: str,
        title: str = "",
        source_type: str = "manual",
        uri: str = "",
        reliability: float = 0.6,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        text = (text or "").strip()
        if not text:
            raise ValueError("text is required")
        source = SourceRecord(
            source_type=source_type,
            title=title or text[:48],
            uri=uri,
            reliability=reliability,
            metadata=metadata or {},
        )
        evidence, atoms, edges = atomize_text(source, text)
        episode = EpisodicMemory(
            event_type="ingest_text",
            title=source.title,
            source_ids=[source.id],
            evidence_ids=[e.id for e in evidence],
            atom_ids=[a.id for a in atoms],
            context={"source_type": source.source_type, "uri": source.uri},
        )
        self.store.save("sources", source)
        self.store.save_many("evidence", evidence)
        self.store.save_many("atoms", atoms)
        self.store.save_many("relations", edges)
        self.store.save("episodes", episode)
        return {
            "source": source,
            "evidence": evidence,
            "atoms": atoms,
            "relations": edges,
            "episode": episode,
        }
