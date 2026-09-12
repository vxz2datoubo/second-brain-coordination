"""Evidence reasoning over retrieved atoms.

The reason step does not just echo the top hit — it aggregates supporting and
contradicting evidence, separates fact from inference, and reports exactly what
would make the answer wrong. This is what turns a lookup into a reasoned answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .atom import KnowledgeAtom
from .retrieve import detect_conflicts, retrieve


@dataclass(frozen=True)
class ReasonedAnswer:
    question: str
    subject: str | None
    answer: str | None
    confidence: float
    evidence_count: int
    contradicting_count: int
    caveats: tuple[str, ...]
    sources: tuple[str, ...]

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.6 and self.contradicting_count == 0


def reason(
    atoms: Iterable[KnowledgeAtom],
    query: str,
    now: str,
    *,
    top_k: int = 10,
) -> ReasonedAnswer:
    """Produce a reasoned answer with confidence, evidence and caveats.

    The primary answer is the most *relevant* retrieved atom (retrieval already
    ranks by keyword match, then confidence), not the most confident atom on an
    unrelated topic.
    """

    atom_list = list(atoms)
    results = retrieve(atom_list, query, now, top_k=top_k)
    if not results:
        return ReasonedAnswer(
            question=query,
            subject=None,
            answer=None,
            confidence=0.0,
            evidence_count=0,
            contradicting_count=0,
            caveats=("no time-valid evidence found",),
            sources=(),
        )

    primary = results[0].atom

    conflicts = detect_conflicts(result.atom for result in results)
    contradicting = sum(len(conflict.contents) - 1 for conflict in conflicts)

    # Confidence is the top atom's confidence, penalized by any contradiction.
    confidence = primary.confidence * (1.0 / (1.0 + contradicting * 0.5))

    caveats: list[str] = []
    if primary.nature != "fact":
        caveats.append("answer is inference, not a verified fact")
    if contradicting > 0:
        caveats.append(f"{contradicting} contradicting statement(s) found")

    supporting = [result.atom for result in results if result.atom.subject == primary.subject]
    sources = tuple(sorted({result.atom.provenance.source_type for result in results}))

    return ReasonedAnswer(
        question=query,
        subject=primary.subject,
        answer=primary.content,
        confidence=round(confidence, 4),
        evidence_count=len(supporting),
        contradicting_count=contradicting,
        caveats=tuple(caveats),
        sources=sources,
    )
