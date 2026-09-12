"""Shadow Cognitive Loop v0 — public surface."""

from .atom import FeedbackRecord, KnowledgeAtom, Provenance
from .ingest import ingest
from .reason import ReasonedAnswer, reason
from .retrieve import Conflict, RetrievalResult, detect_conflicts, retrieve
from .store import ShadowStore, StoreViolation
from .feedback import FeedbackOutcome, apply_outcome, record_prediction

__all__ = [
    "Conflict",
    "FeedbackOutcome",
    "FeedbackRecord",
    "KnowledgeAtom",
    "Provenance",
    "ReasonedAnswer",
    "RetrievalResult",
    "ShadowStore",
    "StoreViolation",
    "apply_outcome",
    "detect_conflicts",
    "ingest",
    "reason",
    "record_prediction",
    "retrieve",
]
