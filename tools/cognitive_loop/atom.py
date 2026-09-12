"""Shadow Cognitive Loop v0 — a minimal, fully-offline knowledge loop.

This is the first runnable slice of the "second brain" cognition core. It
implements the smallest loop that can actually think about stored knowledge:

    ingest -> atom -> retrieve -> reason -> feedback -> update

The whole package is intentionally dependency-free (Python stdlib + SQLite)
so it can run anywhere the second brain is cloned, and it is a *shadow*
implementation: it never writes to the production W3 capture surface.

Design constraints inherited from the R175 / second-brain governance:
- provenance first: every atom records where it came from and when;
- fact vs inference are never conflated;
- time-validity is a first-class retrieval axis;
- feedback is a closed loop, not a one-shot lookup.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from .contracts import canonical_json  # reuse the deterministic JSON renderer


SCHEMA = "ShadowCognitiveLoop/v0"

NATURES = ("fact", "inference", "user_opinion")
SOURCE_TYPES = ("user_statement", "document", "inference", "agent_report", "unknown")


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Provenance:
    """Where an atom came from and when it was captured."""

    source_type: str
    retriever: str
    retrieved_at: str
    url: str | None = None
    raw_ref: str | None = None
    revision: str | None = None

    def __post_init__(self) -> None:
        if self.source_type not in SOURCE_TYPES:
            raise ValueError(f"source_type must be one of {SOURCE_TYPES}")
        if not self.retriever.strip():
            raise ValueError("retriever is required for provenance")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "retriever": self.retriever,
            "retrieved_at": self.retrieved_at,
            "url": self.url,
            "raw_ref": self.raw_ref,
            "revision": self.revision,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Provenance":
        return cls(
            source_type=str(value["source_type"]),
            retriever=str(value["retriever"]),
            retrieved_at=str(value["retrieved_at"]),
            url=value.get("url"),
            raw_ref=value.get("raw_ref"),
            revision=value.get("revision"),
        )


@dataclass(frozen=True)
class KnowledgeAtom:
    """One self-contained, addressable unit of knowledge."""

    content: str
    subject: str
    topic: str
    nature: str
    confidence: float
    provenance: Provenance
    time_valid_from: str
    time_valid_to: str | None = None
    evidence_refs: tuple[str, ...] = ()
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("content is required")
        if not self.subject.strip():
            raise ValueError("subject is required")
        if not self.topic.strip():
            raise ValueError("topic is required")
        if self.nature not in NATURES:
            raise ValueError(f"nature must be one of {NATURES}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0, 1]")

    @property
    def atom_id(self) -> str:
        material = canonical_json(
            {
                "content": self.content,
                "subject": self.subject,
                "topic": self.topic,
                "nature": self.nature,
                "source_type": self.provenance.source_type,
                "retriever": self.provenance.retriever,
            }
        )
        return "atm_" + _sha256(material)[:20]

    def is_time_valid(self, now: str) -> bool:
        return now >= self.time_valid_from and (
            self.time_valid_to is None or now <= self.time_valid_to
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "atom_id": self.atom_id,
            "content": self.content,
            "subject": self.subject,
            "topic": self.topic,
            "nature": self.nature,
            "confidence": self.confidence,
            "provenance": self.provenance.to_dict(),
            "time_valid_from": self.time_valid_from,
            "time_valid_to": self.time_valid_to,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgeAtom":
        return cls(
            content=str(value["content"]),
            subject=str(value["subject"]),
            topic=str(value["topic"]),
            nature=str(value["nature"]),
            confidence=float(value["confidence"]),
            provenance=Provenance.from_dict(value["provenance"]),
            time_valid_from=str(value["time_valid_from"]),
            time_valid_to=value.get("time_valid_to"),
            evidence_refs=tuple(value.get("evidence_refs", ())),
            created_at=str(value.get("created_at", "")),
            updated_at=str(value.get("updated_at", "")),
        )

    def with_confidence(self, confidence: float) -> "KnowledgeAtom":
        return replace(self, confidence=confidence)


@dataclass(frozen=True)
class FeedbackRecord:
    """A past prediction and its later observed outcome."""

    question: str
    predicted_subject: str
    predicted_answer: str
    predicted_confidence: float
    observed_subject: str | None = None
    observed_answer: str | None = None
    resolved_at: str | None = None
    was_correct: bool | None = None

    def resolve(self, observed_subject: str, observed_answer: str, resolved_at: str) -> "FeedbackRecord":
        correct = (
            observed_subject == self.predicted_subject
            and observed_answer == self.predicted_answer
        )
        return replace(
            self,
            observed_subject=observed_subject,
            observed_answer=observed_answer,
            resolved_at=resolved_at,
            was_correct=correct,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "predicted_subject": self.predicted_subject,
            "predicted_answer": self.predicted_answer,
            "predicted_confidence": self.predicted_confidence,
            "observed_subject": self.observed_subject,
            "observed_answer": self.observed_answer,
            "resolved_at": self.resolved_at,
            "was_correct": self.was_correct,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FeedbackRecord":
        return cls(
            question=str(value["question"]),
            predicted_subject=str(value["predicted_subject"]),
            predicted_answer=str(value["predicted_answer"]),
            predicted_confidence=float(value["predicted_confidence"]),
            observed_subject=value.get("observed_subject"),
            observed_answer=value.get("observed_answer"),
            resolved_at=value.get("resolved_at"),
            was_correct=value.get("was_correct"),
        )
