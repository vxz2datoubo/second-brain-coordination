"""Mechanical benchmark for the shadow cognitive loop.

Scores four capabilities that a minimal cognitive loop must demonstrably have:

1. retrieval hit     — does the top hit point at the right subject?
2. reasoning         — does the reasoned answer match the expected fact?
3. conflict detection — are planted disagreements surfaced, not hidden?
4. feedback loop     — does a correct/incorrect outcome nudge confidence?

The corpus is deliberately synthetic and small so the benchmark stays
deterministic and fast; it proves the loop closes, not that it knows the world.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .atom import KnowledgeAtom
from .feedback import apply_outcome, record_prediction
from .ingest import ingest
from .reason import reason
from .retrieve import detect_conflicts, retrieve
from .store import ShadowStore


@dataclass(frozen=True)
class CorpusEntry:
    content: str
    subject: str
    topic: str
    nature: str = "fact"
    confidence: float = 0.9
    time_valid_from: str | None = None
    time_valid_to: str | None = None


@dataclass(frozen=True)
class Question:
    query: str
    expected_subject: str
    expected_answer: str


def seed_corpus() -> list[CorpusEntry]:
    """A synthetic corpus with facts, an inference, a stale atom, and a conflict."""

    return [
        CorpusEntry("星光科技主营业务是AI视频生成", "星光科技", "主营业务", "fact", 0.9),
        CorpusEntry("星光科技已经完成上市", "星光科技", "上市状态", "fact", 0.95),
        CorpusEntry("星光科技的估值可能偏高", "星光科技", "估值", "inference", 0.6),
        CorpusEntry("星光科技首席执行官是李明", "星光科技", "CEO", "fact", 0.85),
        CorpusEntry("星光科技首席执行官是王强", "星光科技", "CEO", "fact", 0.8),
        CorpusEntry("星光科技主营业务是传统视频剪辑", "星光科技", "主营业务", "fact", 0.9,
                    time_valid_to="2020-01-01T00:00:00+00:00"),
    ]


def seed_questions() -> list[Question]:
    return [
        Question("星光科技主营业务是什么", "星光科技", "星光科技主营业务是AI视频生成"),
        Question("星光科技上市了吗", "星光科技", "星光科技已经完成上市"),
        Question("星光科技估值如何", "星光科技", "星光科技的估值可能偏高"),
    ]


def _populate(store: ShadowStore, corpus: Sequence[CorpusEntry]) -> None:
    for entry in corpus:
        ingest(
            store,
            content=entry.content,
            subject=entry.subject,
            topic=entry.topic,
            nature=entry.nature,
            confidence=entry.confidence,
            time_valid_from=entry.time_valid_from,
            time_valid_to=entry.time_valid_to,
        )


def score_retrieval(store: ShadowStore, questions: Sequence[Question], now: str) -> tuple[int, int]:
    atoms = store.all_atoms()
    hits = 0
    for question in questions:
        results = retrieve(atoms, question.query, now, top_k=1)
        if results and results[0].atom.subject == question.expected_subject:
            hits += 1
    return hits, len(questions)


def score_reasoning(store: ShadowStore, questions: Sequence[Question], now: str) -> tuple[int, int]:
    atoms = store.all_atoms()
    hits = 0
    for question in questions:
        answer = reason(atoms, question.query, now)
        if answer.answer == question.expected_answer:
            hits += 1
    return hits, len(questions)


def score_conflict_detection(store: ShadowStore) -> tuple[int, int]:
    conflicts = detect_conflicts(store.all_atoms())
    ceo_conflicts = [c for c in conflicts if c.topic == "CEO"]
    return 1 if ceo_conflicts else 0, 1


def score_feedback_loop(store: ShadowStore, now: str) -> tuple[int, int]:
    """A correct prediction should raise confidence; a wrong one should lower it."""

    atoms_before = store.list_atoms(subject="星光科技", topic="主营业务")
    before = {a.atom_id: a.confidence for a in atoms_before}

    feedback_id = record_prediction(
        store, "星光科技主营业务是什么", "星光科技",
        "星光科技主营业务是AI视频生成", 0.9,
    )
    apply_outcome(store, feedback_id, "星光科技", "星光科技主营业务是AI视频生成", now)

    atoms_after = store.list_atoms(subject="星光科技", topic="主营业务")
    after = {a.atom_id: a.confidence for a in atoms_after}
    raised = any(after.get(k, 0.0) > before.get(k, 0.0) for k in before)
    return 1 if raised else 0, 1


def run_benchmark(store: ShadowStore | None = None, now: str = "2099-01-01T00:00:00+00:00") -> dict[str, Any]:
    """Populate a shadow store and score the four capabilities."""

    owns_store = store is None
    if store is None:
        store = ShadowStore(":memory:")
    try:
        _populate(store, seed_corpus())
        questions = seed_questions()
        retrieval_hits, retrieval_total = score_retrieval(store, questions, now)
        reasoning_hits, reasoning_total = score_reasoning(store, questions, now)
        conflict_hits, conflict_total = score_conflict_detection(store)
        feedback_hits, feedback_total = score_feedback_loop(store, now)
        return {
            "schema": "ShadowCognitiveLoopBenchmark/v1",
            "retrieval": {"hits": retrieval_hits, "total": retrieval_total},
            "reasoning": {"hits": reasoning_hits, "total": reasoning_total},
            "conflict_detection": {"hits": conflict_hits, "total": conflict_total},
            "feedback_loop": {"hits": feedback_hits, "total": feedback_total},
            "total_hits": retrieval_hits + reasoning_hits + conflict_hits + feedback_hits,
            "total_questions": retrieval_total + reasoning_total + conflict_total + feedback_total,
        }
    finally:
        if owns_store:
            store.close()
