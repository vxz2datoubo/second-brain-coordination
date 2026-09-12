"""Ingestion: turn raw statements into provenance-carrying knowledge atoms."""

from __future__ import annotations

from datetime import datetime, timezone

from .atom import KnowledgeAtom, Provenance
from .store import ShadowStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ingest(
    store: ShadowStore,
    *,
    content: str,
    subject: str,
    topic: str,
    nature: str = "fact",
    confidence: float = 1.0,
    source_type: str = "user_statement",
    retriever: str = "workbuddy",
    time_valid_from: str | None = None,
    time_valid_to: str | None = None,
    url: str | None = None,
    raw_ref: str | None = None,
    revision: str | None = None,
    evidence_refs: tuple[str, ...] = (),
) -> KnowledgeAtom:
    """Create and persist one atom with mandatory provenance."""

    timestamp = _now()
    atom = KnowledgeAtom(
        content=content,
        subject=subject,
        topic=topic,
        nature=nature,
        confidence=confidence,
        provenance=Provenance(
            source_type=source_type,
            retriever=retriever,
            retrieved_at=timestamp,
            url=url,
            raw_ref=raw_ref,
            revision=revision,
        ),
        time_valid_from=time_valid_from or timestamp,
        time_valid_to=time_valid_to,
        evidence_refs=evidence_refs,
        created_at=timestamp,
        updated_at=timestamp,
    )
    store.upsert_atom(atom)
    return atom
