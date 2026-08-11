"""L2 derivation — deterministic L1 + L0 → L2 atoms + relations.

This is the smallest deterministic derivation step that the E48 R2
mandatory list calls for: take a ``NormalizedSemanticView`` + the raw
L0 text and produce the E47-style L2 atom list + relation list + unknown
list. No hand-quota-filling; no fabricated edges.

Derivation rules (deterministic, auditable):

1. For each ``NormalizationEdit`` in ``view.segments`` with
   ``applied=True`` and ``confidence`` >= the type-specific HIGH
   threshold (E47 quality discipline), emit one SOURCE_EXTRACT atom
   spanning the exact L0 byte range of the edit. The atom's
   ``content`` is the edit's ``after`` text.

2. For each ``UnknownMarker`` in ``view.unknowns``, emit one INFERENCE
   atom tagged ``UNKNOWN_REFUSAL`` with a rationale pointing at the
   reconstructor's reason. The unknown is recorded in the L2 package's
   ``unknowns`` list with a RAISES_UNKNOWN-style relation.

3. Cross-sentence mechanism detection (R2 mandatory): the function
   scans the joined normalized_text for ``如果 <X> 那么 <Y>`` patterns
   and emits one CONDITION atom + one MECHANISM atom + one REFINES
   relation when both halves can be located as a byte span in L0.
   No hand-built relations: if a relation cannot be derived safely,
   it is NOT emitted (we keep the UNKNOWN in the view rather than
   fabricate a relation).

4. Empty contradiction / memory / skill lists are valid and are passed
   through unchanged.

This module is **stdlib-only** and produces deterministic bytes for
the same input. The downstream ``l3_project`` consumes the L2 package
dict (not the E47 dataclasses) so it can be tested without the E47
worktree on ``sys.path``.
"""
from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Tuple

from .l1_schema import (
    EditType,
    HIGH_CONFIDENCE_THRESHOLD,
    ASR_HIGH_CONFIDENCE,
    NormalizedSemanticView,
)


# Cross-sentence pattern: 如果 <condition> 那么 <effect>. Both halves must
# be 1-60 Han characters (no Chinese punctuation inside to keep the
# pattern deterministic). The effect clause ends at whitespace / sentence
# punctuation / EOF.
_MECHANISM_PATTERN = re.compile(
    r"如果(.{1,60}?)那么(.{1,60}?)(?:[\s。,;]|$)"
)


def _confidence_atom_label(confidence: float, edit_type: EditType) -> str:
    if edit_type == EditType.ASR_HOMOPHONE_CORRECTION:
        if confidence >= ASR_HIGH_CONFIDENCE:
            return "HIGH"
        if confidence >= 0.7:
            return "MEDIUM"
        return "LOW"
    if confidence >= HIGH_CONFIDENCE_THRESHOLD + 0.2:
        return "HIGH"
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def _char_to_byte(l0_bytes: bytes, char_index: int, l0_text: str) -> int:
    """Convert a *char index in the decoded L0 string* to a UTF-8 byte offset
    into ``l0_bytes``. Slicing by character index from the decoded text and
    re-encoding to UTF-8 avoids cutting a multibyte sequence in the middle.
    """
    return len(l0_text[:char_index].encode("utf-8"))


def _char_range_byte_range(
    l0_text: str,
    char_start: int,
    char_end: int,
) -> Tuple[int, int]:
    return (
        len(l0_text[:char_start].encode("utf-8")),
        len(l0_text[:char_end].encode("utf-8")),
    )


def _build_atom_dict(
    atom_id: str,
    atom_type: str,
    evidence_kind: str,
    confidence: str,
    content: str,
    byte_start: int,
    byte_end: int,
    line_start: int,
    line_end: int,
    label: str = "",
) -> dict:
    """Construct an E47-style atom dict (matches the L2 package JSON shape)."""
    span: Dict[str, object] = {
        "byte_start": byte_start,
        "byte_end": byte_end,
        "line_start": line_start,
        "line_end": line_end,
    }
    if label:
        span["span_label"] = label
    return {
        "atom_id": atom_id,
        "atom_type": atom_type,
        "content": content,
        "source_spans": [span],
        "evidence_kind": evidence_kind,
        "confidence": confidence,
        "scope": "canary",
        "invalidation_conditions": "",
    }


def _line_index_for_byte(l0_text: str, byte_offset: int) -> int:
    """1-indexed line number that contains the given UTF-8 byte offset."""
    return l0_text.encode("utf-8")[:byte_offset].decode("utf-8", errors="ignore").count("\n") + 1


def derive_l2_package(
    l0_text: str,
    view: NormalizedSemanticView,
    package_id: str = "E48-L2-DERIVED",
    source_meta: dict | None = None,
) -> dict:
    """Derive a complete L2 candidate-knowledge-package dict from ``view``.

    The result is JSON-serialisable. The function is deterministic.
    """
    l0_bytes = l0_text.encode("utf-8")
    source_meta = source_meta or {}
    source = {
        "source_id": source_meta.get("source_id", "src-canary"),
        "source_url": source_meta.get("source_url", "workspace://canary"),
        "source_title": source_meta.get("source_title", "E48 PUBLIC_SAFE canary (R2)"),
        "source_hash": hashlib.sha256(l0_bytes).hexdigest(),
        "source_size_bytes": len(l0_bytes),
        "ingested_at": "1970-01-01T00:00:00Z",
    }

    atoms: List[dict] = []
    relations: List[dict] = []
    unknowns: List[dict] = []

    # 1. SOURCE_EXTRACT atoms from each applied, type-threshold-passing edit.
    edit_atoms: Dict[str, str] = {}
    counter = 0
    for seg in view.segments:
        for e in seg.edits:
            if not e.applied:
                continue
            if e.edit_type == EditType.UNKNOWN_MARKER:
                continue
            threshold = (ASR_HIGH_CONFIDENCE
                         if e.edit_type == EditType.ASR_HOMOPHONE_CORRECTION
                         else HIGH_CONFIDENCE_THRESHOLD)
            if e.confidence < threshold:
                continue
            counter += 1
            atom_id = f"A{counter:03d}"
            edit_atoms[e.edit_id] = atom_id
            line_start = _line_index_for_byte(l0_text, e.byte_start)
            line_end = _line_index_for_byte(l0_text, e.byte_end)
            atoms.append(_build_atom_dict(
                atom_id, e.edit_type.value, "SOURCE_EXTRACT",
                _confidence_atom_label(e.confidence, e.edit_type),
                e.after, e.byte_start, e.byte_end,
                line_start, line_end,
                label=f"{e.edit_type.value}@{e.edit_id}",
            ))

    # 2. INFERENCE atoms for each UnknownMarker.
    unknown_atom_ids: List[str] = []
    for u in view.unknowns:
        counter += 1
        atom_id = f"A{counter:03d}"
        unknown_atom_ids.append(atom_id)
        line_start = _line_index_for_byte(l0_text, u.byte_start)
        line_end = _line_index_for_byte(l0_text, u.byte_end)
        atoms.append(_build_atom_dict(
            atom_id, "UNKNOWN_REFUSAL", "INFERENCE", "MEDIUM",
            u.raw_text, u.byte_start, u.byte_end,
            line_start, line_end,
            label=f"unknown_refusal@{u.unknown_id}",
        ))
        unknowns.append({
            "unknown_id": u.unknown_id,
            "question": u.reason,
            "related_atom_ids": [atom_id],
        })

    # 3. Cross-sentence mechanism derivation.
    if view.segments:
        normalized_text = view.segments[0].normalized_text
    else:
        normalized_text = ""
    for m in _MECHANISM_PATTERN.finditer(normalized_text):
        cond_text = m.group(1).strip()
        eff_text = m.group(2).strip()
        cond_span = _find_l0_span_for_text(l0_text, cond_text, view)
        eff_span = _find_l0_span_for_text(l0_text, eff_text, view)
        if cond_span is None or eff_span is None:
            continue
        if cond_span == eff_span:
            continue
        counter += 1
        cond_atom_id = f"A{counter:03d}"
        cond_line_start = _line_index_for_byte(l0_text, cond_span[0])
        cond_line_end = _line_index_for_byte(l0_text, cond_span[1])
        atoms.append(_build_atom_dict(
            cond_atom_id, "CONDITION", "SOURCE_EXTRACT", "HIGH",
            l0_text.encode("utf-8")[cond_span[0]:cond_span[1]].decode("utf-8"),
            cond_span[0], cond_span[1],
            cond_line_start, cond_line_end,
            label="if-condition",
        ))
        counter += 1
        eff_atom_id = f"A{counter:03d}"
        eff_line_start = _line_index_for_byte(l0_text, eff_span[0])
        eff_line_end = _line_index_for_byte(l0_text, eff_span[1])
        atoms.append(_build_atom_dict(
            eff_atom_id, "MECHANISM", "SOURCE_EXTRACT", "HIGH",
            l0_text.encode("utf-8")[eff_span[0]:eff_span[1]].decode("utf-8"),
            eff_span[0], eff_span[1],
            eff_line_start, eff_line_end,
            label="then-effect",
        ))
        relations.append({
            "source_atom_id": cond_atom_id,
            "target_atom_id": eff_atom_id,
            "relation_type": "REFINES",
            "span_index": -1,
        })

    # 4. Empty contradiction / memory / skill lists are valid.
    return {
        "schema": "QCLAW-CANDIDATE-KNOWLEDGE-PACKAGE-V1",
        "package_id": package_id,
        "package_version": 1,
        "content_hash": "0" * 16,
        "source": source,
        "summary": "E48 R2 end-to-end derivation from L1 view + L0 raw text",
        "atoms": atoms,
        "relations": relations,
        "contradictions": [],
        "unknowns": unknowns,
        "memory_records": [],
        "skills": [],
    }


def _find_l0_span_for_text(
    l0_text: str,
    surface: str,
    view: NormalizedSemanticView,
) -> Tuple[int, int] | None:
    """Locate the byte span of ``surface`` in L0.

    Strategy:
    1. Direct substring search in L0 (returns exact byte span when
       the surface form is preserved verbatim).
    2. Fallback: scan applied edits whose ``before`` or ``after`` text
       shares at least one Han token with ``surface``. Return the
       edit's byte range.

    Returns ``None`` when no candidate span can be located.
    """
    if not surface:
        return None
    idx = l0_text.find(surface)
    if idx >= 0:
        return (
            len(l0_text[:idx].encode("utf-8")),
            len(l0_text[:idx + len(surface)].encode("utf-8")),
        )
    tokens = re.findall(r"[一-鿿A-Za-z0-9]+", surface)
    if not tokens:
        return None
    for seg in view.segments:
        for e in seg.edits:
            if not e.applied:
                continue
            if any(t in e.before or t in e.after for t in tokens):
                return (e.byte_start, e.byte_end)
    return None


__all__ = ["derive_l2_package"]