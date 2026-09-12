"""Hybrid retrieval: BM25 keyword scoring + time-validity + confidence + conflicts.

The retrieval axis of the loop. Pure-Python BM25 is used for keyword relevance
so there is no external vector/index dependency in the shadow slice. Time
validity filters stale atoms, confidence re-ranks, and same-subject conflicts
are surfaced explicitly instead of silently hiding a disagreement.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Iterable, Mapping, Sequence

from .atom import KnowledgeAtom


_WORD_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Minimal CJK+ASCII tokenizer: latin words plus single CJK characters."""

    lowered = text.lower()
    tokens = [match.group() for match in _WORD_RE.finditer(lowered)]
    tokens.extend(ch for ch in lowered if "\u4e00" <= ch <= "\u9fff")
    return tokens


def _term_frequency(tokens: Sequence[str]) -> dict[str, int]:
    freq: dict[str, int] = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    return freq


class BM25:
    """Okapi BM25 over an in-memory corpus of pre-tokenized documents."""

    def __init__(self, documents: Sequence[Sequence[str]], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.documents = [list(doc) for doc in documents]
        self.doc_freqs = [_term_frequency(doc) for doc in self.documents]
        self.doc_lengths = [len(doc) for doc in self.documents]
        self.avgdl = (sum(self.doc_lengths) / len(self.documents)) if self.documents else 0.0
        n_docs = len(self.documents)
        self.idf: dict[str, float] = {}
        for doc in self.doc_freqs:
            for term in doc:
                if term in self.idf:
                    continue
                doc_count = sum(1 for d in self.doc_freqs if term in d)
                self.idf[term] = math.log((n_docs - doc_count + 0.5) / (doc_count + 0.5) + 1.0)

    def score(self, query_tokens: Sequence[str], doc_index: int) -> float:
        query_freq = _term_frequency(query_tokens)
        doc_freq = self.doc_freqs[doc_index]
        doc_len = self.doc_lengths[doc_index]
        score = 0.0
        for term, qf in query_freq.items():
            if term not in doc_freq:
                continue
            df = doc_freq[term]
            idf = self.idf.get(term, 0.0)
            numerator = df * (self.k1 + 1.0)
            denominator = df + self.k1 * (1.0 - self.b + self.b * doc_len / self.avgdl)
            score += idf * (numerator / denominator) * qf
        return score


@dataclass(frozen=True)
class RetrievalResult:
    atom: KnowledgeAtom
    keyword_score: float
    confidence: float
    combined_score: float


@dataclass(frozen=True)
class Conflict:
    subject: str
    topic: str
    atom_ids: tuple[str, ...]
    contents: tuple[str, ...]


def retrieve(
    atoms: Iterable[KnowledgeAtom],
    query: str,
    now: str,
    *,
    top_k: int = 10,
    confidence_weight: float = 1.0,
) -> list[RetrievalResult]:
    """Return time-valid atoms ranked by BM25 keyword score, then confidence."""

    candidates = [atom for atom in atoms if atom.is_time_valid(now)]
    if not candidates:
        return []
    corpus = [tokenize(atom.content + " " + atom.subject + " " + atom.topic) for atom in candidates]
    bm25 = BM25(corpus)
    query_tokens = tokenize(query)
    scored: list[RetrievalResult] = []
    for index, atom in enumerate(candidates):
        keyword = bm25.score(query_tokens, index)
        if keyword <= 0.0:
            continue
        combined = keyword * (1.0 + confidence_weight * atom.confidence)
        scored.append(
            RetrievalResult(
                atom=atom,
                keyword_score=round(keyword, 6),
                confidence=atom.confidence,
                combined_score=round(combined, 6),
            )
        )
    scored.sort(key=lambda item: item.combined_score, reverse=True)
    return scored[:top_k]


def detect_conflicts(atoms: Iterable[KnowledgeAtom]) -> list[Conflict]:
    """Group atoms by (subject, topic) and flag those with differing content."""

    buckets: dict[tuple[str, str], list[KnowledgeAtom]] = {}
    for atom in atoms:
        buckets.setdefault((atom.subject, atom.topic), []).append(atom)
    conflicts: list[Conflict] = []
    for (subject, topic), group in buckets.items():
        contents = sorted({atom.content for atom in group})
        if len(contents) > 1:
            conflicts.append(
                Conflict(
                    subject=subject,
                    topic=topic,
                    atom_ids=tuple(atom.atom_id for atom in group),
                    contents=tuple(contents),
                )
            )
    conflicts.sort(key=lambda item: (item.subject, item.topic))
    return conflicts
