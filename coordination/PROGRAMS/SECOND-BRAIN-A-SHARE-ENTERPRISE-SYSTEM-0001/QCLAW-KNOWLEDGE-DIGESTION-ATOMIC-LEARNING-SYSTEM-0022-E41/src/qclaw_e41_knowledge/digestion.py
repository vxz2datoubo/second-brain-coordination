"""E41 Q2 — Digestion Pipeline & Traceability

Faithful extraction before interpretation.
Preserve exact source references; distinguish quoted source
from system-generated interpretation.
Deterministic decomposition, normalization, terminology mapping,
atom linking. Unsupported interpretation stays UNKNOWN or CANDIDATE.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum


class DigestionPhase(str, Enum):
    EXTRACTION = "extraction"
    INTERPRETATION = "interpretation"
    NORMALIZATION = "normalization"
    LINKING = "linking"


class InterpretationStatus(str, Enum):
    DIRECT_QUOTE = "direct_quote"
    PARAPHRASE = "paraphrase"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SourceSpan:
    """Exact reference to source content."""
    source_id: str
    content: str
    start_offset: int = 0
    end_offset: int = -1  # -1 = entire content

    @property
    def quoted_content(self) -> str:
        if self.end_offset == -1:
            return self.content
        return self.content[self.start_offset:self.end_offset]


@dataclass(frozen=True)
class DigestedSegment:
    """A segment produced by the digestion pipeline."""
    phase: DigestionPhase
    status: InterpretationStatus
    source_span: SourceSpan
    normalized_text: str = ""
    interpretation: str = ""
    linked_atom_ids: List[str] = field(default_factory=list)
    unsupported_note: str = ""


def extract(source_id: str, content: str) -> List[SourceSpan]:
    """Faithful extraction — returns source spans without interpretation.
    
    Splits on paragraph boundaries. Every span preserves exact source text.
    """
    if not content.strip():
        return []
    spans = []
    for para in content.split("\n\n"):
        text = para.strip()
        if text:
            spans.append(SourceSpan(source_id=source_id, content=text))
    return spans


def interpret(span: SourceSpan) -> DigestedSegment:
    """Interpret a source span.
    
    Default: DIRECT_QUOTE with normalized_text = source content.
    No unsupported auto-inference — stays faithful to source.
    """
    return DigestedSegment(
        phase=DigestionPhase.INTERPRETATION,
        status=InterpretationStatus.DIRECT_QUOTE,
        source_span=span,
        normalized_text=span.quoted_content,
    )


def normalize(segment: DigestedSegment, terminology_map: Optional[dict] = None) -> DigestedSegment:
    """Normalize terminology. Default: pass-through.
    
    If terminology_map is provided, apply mapping to normalized_text.
    """
    if terminology_map and segment.normalized_text:
        text = segment.normalized_text
        for source_term, target_term in terminology_map.items():
            text = text.replace(source_term, target_term)
        return DigestedSegment(
            phase=DigestionPhase.NORMALIZATION,
            status=segment.status,
            source_span=segment.source_span,
            normalized_text=text,
            interpretation=segment.interpretation,
        )
    return DigestedSegment(
        phase=DigestionPhase.NORMALIZATION,
        status=segment.status,
        source_span=segment.source_span,
        normalized_text=segment.normalized_text,
        interpretation=segment.interpretation,
    )


def link(segment: DigestedSegment, atoms: List[str]) -> DigestedSegment:
    """Link a segment to existing atoms. Pure linking, no interpretation."""
    return DigestedSegment(
        phase=DigestionPhase.LINKING,
        status=segment.status,
        source_span=segment.source_span,
        normalized_text=segment.normalized_text,
        interpretation=segment.interpretation,
        linked_atom_ids=list(atoms),
    )


def unsupported_interpretation(span: SourceSpan, reason: str) -> DigestedSegment:
    """Mark a segment as UNKNOWN due to unsupported interpretation.
    
    Never silently promoted — stays UNKNOWN with explicit reason.
    """
    return DigestedSegment(
        phase=DigestionPhase.INTERPRETATION,
        status=InterpretationStatus.UNKNOWN,
        source_span=span,
        unsupported_note=reason,
    )


def is_quoted_source(segment: DigestedSegment) -> bool:
    """Check if segment preserves direct source text."""
    return segment.status == InterpretationStatus.DIRECT_QUOTE


def distinguish_quote_from_interpretation(segment: DigestedSegment) -> str:
    """Return a label distinguishing quote vs interpretation."""
    if segment.status == InterpretationStatus.DIRECT_QUOTE:
        return "QUOTED_SOURCE"
    if segment.status == InterpretationStatus.PARAPHRASE:
        return "SYSTEM_PARAPHRASE"
    if segment.status == InterpretationStatus.INFERRED:
        return "SYSTEM_INFERENCE"
    return "SYSTEM_UNKNOWN"
