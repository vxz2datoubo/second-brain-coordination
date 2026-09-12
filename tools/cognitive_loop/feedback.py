"""Feedback loop: record a prediction, observe the outcome, update confidence.

This closes the cognitive loop. A reasoned prediction is recorded, the real
outcome is later observed, and the confidence of the atoms that supported the
prediction is nudged up or down. Correct answers strengthen their evidence;
wrong answers decay, so the loop learns instead of merely storing.
"""

from __future__ import annotations

from dataclasses import dataclass

from .atom import FeedbackRecord, KnowledgeAtom
from .store import ShadowStore


@dataclass(frozen=True)
class FeedbackOutcome:
    was_correct: bool
    updated_atoms: tuple[KnowledgeAtom, ...]


def record_prediction(
    store: ShadowStore,
    question: str,
    subject: str,
    answer: str,
    confidence: float,
) -> int:
    """Persist a prediction and return its feedback id."""

    record = FeedbackRecord(
        question=question,
        predicted_subject=subject,
        predicted_answer=answer,
        predicted_confidence=confidence,
    )
    return store.add_feedback(record)


def _adjust(confidence: float, correct: bool, learning_rate: float) -> float:
    if correct:
        return min(1.0, confidence + (1.0 - confidence) * learning_rate)
    return max(0.0, confidence * (1.0 - learning_rate))


def apply_outcome(
    store: ShadowStore,
    feedback_id: int,
    observed_subject: str,
    observed_answer: str,
    resolved_at: str,
    *,
    learning_rate: float = 0.2,
) -> FeedbackOutcome:
    """Observe an outcome and update the confidence of supporting atoms."""

    resolved = store.resolve_feedback(feedback_id, observed_subject, observed_answer, resolved_at)
    if resolved is None:
        return FeedbackOutcome(was_correct=False, updated_atoms=())

    related = store.list_atoms(subject=resolved.predicted_subject)
    updated: list[KnowledgeAtom] = []
    for atom in related:
        # Only nudge the atom that backed the prediction, not every atom on the subject.
        if atom.content != resolved.predicted_answer:
            continue
        new_confidence = _adjust(atom.confidence, resolved.was_correct is True, learning_rate)
        if abs(new_confidence - atom.confidence) > 1e-9:
            updated.append(atom.with_confidence(round(new_confidence, 4)))
    for atom in updated:
        store.upsert_atom(atom)
    return FeedbackOutcome(was_correct=resolved.was_correct is True, updated_atoms=tuple(updated))
