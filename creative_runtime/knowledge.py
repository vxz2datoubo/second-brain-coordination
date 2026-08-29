"""Review-only creative knowledge candidates; no canonical knowledge authority."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Iterable, Mapping

from .contracts import canonical_json


class KnowledgeBridgeViolation(ValueError):
    """Raised when a candidate lacks provenance or attempts an unsafe promotion."""


@dataclass(frozen=True)
class KnowledgeCandidate:
    candidate_id: str
    assertion: str
    source_event_ids: tuple[str, ...]
    source_artifact_ids: tuple[str, ...]
    status: str
    reviewer: str | None = None
    reviewer_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "assertion": self.assertion,
            "source_event_ids": list(self.source_event_ids),
            "source_artifact_ids": list(self.source_artifact_ids),
            "status": self.status,
            "reviewer": self.reviewer,
            "reviewer_note": self.reviewer_note,
        }

    @classmethod
    def from_dict(cls, record: Mapping[str, Any]) -> "KnowledgeCandidate":
        return cls(
            candidate_id=str(record["candidate_id"]),
            assertion=str(record["assertion"]),
            source_event_ids=tuple(str(item) for item in record.get("source_event_ids", ())),
            source_artifact_ids=tuple(str(item) for item in record.get("source_artifact_ids", ())),
            status=str(record["status"]),
            reviewer=record.get("reviewer"),
            reviewer_note=record.get("reviewer_note"),
        )


class KnowledgeReviewBridge:
    """A bounded local packet store, deliberately isolated from `brain_core`."""

    canonical_write_enabled = False

    def __init__(self, candidates: Iterable[KnowledgeCandidate] = ()) -> None:
        self._candidates = {candidate.candidate_id: candidate for candidate in candidates}

    def correct(
        self,
        assertion: str,
        *,
        source_event_ids: Iterable[str] = (),
        source_artifact_ids: Iterable[str] = (),
    ) -> KnowledgeCandidate:
        event_ids = tuple(source_event_ids)
        artifact_ids = tuple(source_artifact_ids)
        if not assertion.strip() or not (event_ids or artifact_ids):
            raise KnowledgeBridgeViolation("A correction needs an assertion and at least one source reference")
        material = {"assertion": assertion.strip(), "source_event_ids": list(event_ids), "source_artifact_ids": list(artifact_ids)}
        candidate_id = "knw_" + hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()[:20]
        candidate = KnowledgeCandidate(
            candidate_id=candidate_id,
            assertion=assertion.strip(),
            source_event_ids=event_ids,
            source_artifact_ids=artifact_ids,
            status="pending_human_review",
        )
        self._candidates[candidate_id] = candidate
        return candidate

    def search(self, query: str) -> list[KnowledgeCandidate]:
        normalized = query.casefold().strip()
        return [candidate for candidate in self._candidates.values() if normalized in candidate.assertion.casefold()]

    def review(self, candidate_id: str, reviewer: str, approved: bool, note: str) -> KnowledgeCandidate:
        if not reviewer.strip() or reviewer.casefold() in {"codex", "executor"}:
            raise KnowledgeBridgeViolation("A named non-executor human reviewer is required")
        candidate = self._candidates[candidate_id]
        if candidate.status != "pending_human_review":
            raise KnowledgeBridgeViolation("Only pending candidates can be reviewed")
        reviewed = KnowledgeCandidate(
            candidate_id=candidate.candidate_id,
            assertion=candidate.assertion,
            source_event_ids=candidate.source_event_ids,
            source_artifact_ids=candidate.source_artifact_ids,
            status="approved_reusable_candidate" if approved else "rejected",
            reviewer=reviewer,
            reviewer_note=note,
        )
        self._candidates[candidate_id] = reviewed
        return reviewed

    def to_records(self) -> list[dict[str, Any]]:
        return [candidate.to_dict() for candidate in sorted(self._candidates.values(), key=lambda item: item.candidate_id)]

    @classmethod
    def from_records(cls, records: Iterable[Mapping[str, Any]]) -> "KnowledgeReviewBridge":
        return cls(KnowledgeCandidate.from_dict(record) for record in records)
