"""L1 NormalizedSemanticView — derived, auditable reconstruction layer.

Layer contract (per W3 blueprint + E48 plan §3):
- L0 bytes & hash never change.
- Every NormalizedSegment carries exact L0 byte offsets.
- Every NormalizationEdit carries before/after/confidence/rationale/alternatives.
- Ambiguous edits (confidence < 0.7) keep ``alternatives`` and never silently
  become a SOURCE_EXTRACT atom.
- Explicit UNKNOWN for unresolved pronouns / homophones / structure.

Derived view carries a 64-hex ``view_sha256`` separate from L0 hash. See
``digests.py`` for canonicalization contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .digests import canonical_json, sha256_hex


class EditType(str, Enum):
    PUNCTUATION = "punctuation"
    SENTENCE_BREAK = "sentence_break"
    FILLER_REMOVAL = "filler_removal"
    TYPO_CORRECTION = "typo_correction"
    ASR_HOMOPHONE_CORRECTION = "asr_homophone_correction"
    TERMINOLOGY_NORMALIZATION = "terminology_normalization"
    ALIAS_REMAP = "alias_remap"
    REFERENCE_RECOVERY = "reference_recovery"
    PARAGRAPH_SPLIT = "paragraph_split"
    AMBIGUITY_ALTERNATIVE = "ambiguity_alternative"
    UNKNOWN_MARKER = "unknown_marker"


# Below this confidence threshold, the raw text MUST remain in ``alternatives``
# and the edit MUST NOT silently become a L2 SOURCE_EXTRACT atom.
HIGH_CONFIDENCE_THRESHOLD = 0.7
# For ASR homophone corrections we are stricter than the typo threshold.
ASR_HIGH_CONFIDENCE = 0.9


@dataclass(frozen=True)
class NormalizationEdit:
    edit_id: str
    edit_type: EditType
    byte_start: int           # exact byte offset over the L0 UTF-8 bytes
    byte_end: int             # exclusive
    before: str               # exact L0 byte slice (utf-8 decoded)
    after: str                # proposed replacement; equal to before for unknown_marker
    alternatives: Tuple[str, ...] = ()   # MUST include ``before`` when confidence < threshold
    confidence: float = 1.0   # 0.0–1.0
    rationale: str = ""
    evidence_refs: Tuple[str, ...] = ()  # e.g. ("terminology:quantum-entanglement",)
    applied: bool = True      # R1: True if this edit was applied to normalized_text;
                              #       False if it was kept for audit only (e.g. low-confidence,
                              #       kept uncertain, alternatives retained)

    def is_low_confidence(self) -> bool:
        if self.edit_type == EditType.ASR_HOMOPHONE_CORRECTION:
            return self.confidence < ASR_HIGH_CONFIDENCE
        return self.confidence < HIGH_CONFIDENCE_THRESHOLD

    def to_dict(self) -> dict:
        return {
            "edit_id": self.edit_id,
            "edit_type": self.edit_type.value,
            "byte_start": self.byte_start,
            "byte_end": self.byte_end,
            "before": self.before,
            "after": self.after,
            "alternatives": list(self.alternatives),
            "confidence": self.confidence,
            "rationale": self.rationale,
            "evidence_refs": list(self.evidence_refs),
            "applied": self.applied,
        }


@dataclass(frozen=True)
class NormalizedSegment:
    """One corrected run over a precise L0 byte span."""
    segment_id: str
    byte_start: int
    byte_end: int
    raw_text: str        # exact L0 slice at byte_start:byte_end
    normalized_text: str # joined ``after`` of applied edits
    confidence: float    # minimum edit confidence in this segment (0.0–1.0)
    edits: Tuple[NormalizationEdit, ...] = ()

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "byte_start": self.byte_start,
            "byte_end": self.byte_end,
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "confidence": self.confidence,
            "edits": [e.to_dict() for e in self.edits],
        }


@dataclass(frozen=True)
class AmbiguityCandidate:
    """A point in the text where reconstruction deliberately keeps alternatives."""
    ambiguity_id: str
    byte_start: int
    byte_end: int
    raw_text: str
    candidates: Tuple[str, ...]
    chosen: Optional[str]       # explicit None means "kept ambiguous"
    confidence: float
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "ambiguity_id": self.ambiguity_id,
            "byte_start": self.byte_start,
            "byte_end": self.byte_end,
            "raw_text": self.raw_text,
            "candidates": list(self.candidates),
            "chosen": self.chosen,
            "confidence": self.confidence,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class TerminologyAlias:
    """Controlled vocabulary mapping."""
    alias_id: str
    raw_form: str
    canonical_form: str
    scope: str = ""
    confidence: float = 1.0
    evidence_refs: Tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "alias_id": self.alias_id,
            "raw_form": self.raw_form,
            "canonical_form": self.canonical_form,
            "scope": self.scope,
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class UnknownMarker:
    """A point where the reconstructor explicitly refused to interpret."""
    unknown_id: str
    byte_start: int
    byte_end: int
    raw_text: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "unknown_id": self.unknown_id,
            "byte_start": self.byte_start,
            "byte_end": self.byte_end,
            "raw_text": self.raw_text,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class NormalizedSemanticView:
    """Derived view over L0. Carries its own ``view_sha256``.

    ``l0_source_hash`` is the L0 SHA-256; if it ever changes post-construction,
    this view is invalid (caller must rebuild).
    """
    view_id: str
    view_schema_version: str
    l0_source_hash: str          # 64-hex SHA-256 of L0 raw text bytes
    l0_source_size_bytes: int
    segments: Tuple[NormalizedSegment, ...]
    ambiguities: Tuple[AmbiguityCandidate, ...] = ()
    aliases: Tuple[TerminologyAlias, ...] = ()
    unknowns: Tuple[UnknownMarker, ...] = ()
    view_sha256: str = ""        # computed below

    def with_sha(self) -> "NormalizedSemanticView":
        canonical = {
            "view_id": self.view_id,
            "view_schema_version": self.view_schema_version,
            "l0_source_hash": self.l0_source_hash,
            "l0_source_size_bytes": self.l0_source_size_bytes,
            "segments": [s.to_dict() for s in self.segments],
            "ambiguities": [a.to_dict() for a in self.ambiguities],
            "aliases": [a.to_dict() for a in self.aliases],
            "unknowns": [u.to_dict() for u in self.unknowns],
        }
        sha = sha256_hex(canonical_json(canonical))
        if sha == self.view_sha256:
            return self
        return NormalizedSemanticView(
            view_id=self.view_id,
            view_schema_version=self.view_schema_version,
            l0_source_hash=self.l0_source_hash,
            l0_source_size_bytes=self.l0_source_size_bytes,
            segments=self.segments,
            ambiguities=self.ambiguities,
            aliases=self.aliases,
            unknowns=self.unknowns,
            view_sha256=sha,
        )

    def to_dict(self) -> dict:
        v = self.with_sha()
        return {
            "schema": "QCLAW-E48-NORMALIZED-SEMANTIC-VIEW-V1",
            "view_id": v.view_id,
            "view_schema_version": v.view_schema_version,
            "view_sha256": v.view_sha256,
            "l0_source_hash": v.l0_source_hash,
            "l0_source_size_bytes": v.l0_source_size_bytes,
            "segments": [s.to_dict() for s in v.segments],
            "ambiguities": [a.to_dict() for a in v.ambiguities],
            "aliases": [a.to_dict() for a in v.aliases],
            "unknowns": [u.to_dict() for u in v.unknowns],
        }

    def validate(self) -> List[str]:
        """Self-validate. Empty list = OK.

        Checks:
        - segment byte bounds within L0 size
        - edit byte bounds within L0 size
        - low-confidence edits carry ``before`` in ``alternatives``
        """
        errs: List[str] = []
        for s in self.segments:
            if s.byte_start < 0 or s.byte_end <= s.byte_start:
                errs.append(f"Segment {s.segment_id}: invalid range")
            if s.byte_end > self.l0_source_size_bytes:
                errs.append(f"Segment {s.segment_id}: end out of L0 size")
            for e in s.edits:
                if e.byte_start < 0 or e.byte_end <= e.byte_start:
                    errs.append(f"Edit {e.edit_id}: invalid range")
                if e.byte_end > self.l0_source_size_bytes:
                    errs.append(f"Edit {e.edit_id}: end out of L0 size")
                if e.is_low_confidence() and e.before not in e.alternatives:
                    errs.append(
                        f"Edit {e.edit_id}: low-confidence ({e.confidence:.2f}) "
                        f"edit missing ``before`` in alternatives"
                    )
        return errs


__all__ = [
    "EditType",
    "HIGH_CONFIDENCE_THRESHOLD",
    "ASR_HIGH_CONFIDENCE",
    "NormalizationEdit",
    "NormalizedSegment",
    "AmbiguityCandidate",
    "TerminologyAlias",
    "UnknownMarker",
    "NormalizedSemanticView",
]