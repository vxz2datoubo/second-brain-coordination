"""L2 derivation — deterministic L1 + L0 → L2 atoms + relations.

R3 architectural fix (per Issue #216 review id 4904878067, mandatory_r3
items 1-6): L1 normalization provenance is **separated** from L2 knowledge
semantics. Filler removal, punctuation insertion, typo correction and ASR
homophone correction operations remain in L1 ``view.segments[].edits``
as audit/provenance records. They do **not** automatically become L2
knowledge atoms.

Derivation rules (deterministic, auditable):

1. CONDITION + MECHANISM SOURCE_EXTRACT atoms + DEPENDS_ON relation from
   cross-sentence ``如果 X 那么 Y ...`` detection. CONDITION span is
   trimmed to exclude trailing clause-delimiter punctuation (``,`` /
   ``。`` / ``；``) so SOURCE_EXTRACT byte slice contains only semantic
   content (R4 mandatory 3). Effect clause is bounded by the next
   contrast/conditional marker (``但`` / ``如果`` / ``，`` / ``。`` /
   ``；`` / EOF). The relation is ``DEPENDS_ON`` with MECHANISM/effect
   as **source_atom_id** and CONDITION/premise as **target_atom_id**
   (R4 mandatory 1): the mechanism/effect's truth depends on the
   condition premise holding. REFINES is not used in L2 derivation.

2. UNKNOWN_REFUSAL INFERENCE atoms from each ``UnknownMarker`` in
   ``view.unknowns``. The unknown is recorded in the L2 package's
   ``unknowns`` list. Atom ``content`` is the L0 byte slice at the
   unknown's byte span (SOURCE_EXTRACT invariant enforced).

3. Terminology-normalization applied edits (R3 mandatory 4):
   - When the canonical form equals the L0 byte slice at the edit span
     (verbatim), emit a CONCEPT atom with ``evidence_kind=SOURCE_EXTRACT``
     and an ``l1_edit_provenance`` field carrying the canonical_form.
   - When the canonical form differs from the L0 byte slice, emit a
     DERIVED_CONCEPT atom with ``evidence_kind=INFERENCE``, content =
     canonical form, and ``l1_edit_provenance`` carrying raw span +
     canonical form + confidence.

4. SOURCE_EXTRACT invariant (R3 mandatory 3): for every atom with
   ``evidence_kind=SOURCE_EXTRACT``, ``atom.content`` is exactly the
   decoded L0 byte slice at the atom's cited source span. Never a
   normalized/derived substitute. Derived atoms use ``INFERENCE``.

5. Empty contradiction / memory / skill lists are valid and pass through.

This module is **stdlib-only** and produces deterministic bytes for the
same input.
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


# Cross-sentence pattern (R3 fix): effect clause is bounded by the
# next contrast/conditional/sentence marker, NOT by the first whitespace
# (which previously truncated the effect to ``价格``).
_MECHANISM_PATTERN = re.compile(
    r"如果(.{1,80}?)那么(.{1,80}?)(?=但|如果|，|。|；|$)"
)


# Edit types that are *normalization operations only* and MUST NOT
# become L2 knowledge atoms. They remain L1 audit/provenance only.
_NORMALIZATION_ONLY = frozenset({
    EditType.FILLER_REMOVAL,
    EditType.PUNCTUATION,
    EditType.SENTENCE_BREAK,
    EditType.TYPO_CORRECTION,
    EditType.ASR_HOMOPHONE_CORRECTION,
    EditType.PARAGRAPH_SPLIT,
})


# Trailing clause-delimiter punctuation that must be excluded from a
# CONDITION SOURCE_EXTRACT span (R4 mandatory 3). We keep these as
# Han codepoints, never as bytes, to avoid splitting multi-byte UTF-8.
_CONDITION_TRAIL_DELIMS = ("，", "。", "；", "！")


def _trim_condition_span(
    l0_text: str, span: Tuple[int, int]
) -> Tuple[int, int]:
    """Trim trailing clause delimiter from a CONDITION span.

    R4 mandatory 3: ``如果 X，那么`` must yield CONDITION atom whose
    SOURCE_EXTRACT byte slice is ``X`` (the semantic content), not
    ``X，``. Bounded so a span is never shrunk below 1 Han char and
    is never moved past its own start.
    """
    byte_start, byte_end = span
    if byte_end <= byte_start:
        return span
    # Operate on encoded bytes; delimiters are all 3-byte Han codepoints.
    encoded = l0_text.encode("utf-8")
    cur_end = byte_end
    while cur_end - 3 >= byte_start:
        tail = encoded[cur_end - 3:cur_end].decode("utf-8")
        if tail in _CONDITION_TRAIL_DELIMS:
            cur_end -= 3
        else:
            break
    if cur_end > byte_start and cur_end != byte_end:
        return (byte_start, cur_end)
    return span


def _confidence_label(confidence: float, edit_type: EditType) -> str:
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


def _line_index_for_byte(l0_text: str, byte_offset: int) -> int:
    """1-indexed line number that contains the given UTF-8 byte offset."""
    return l0_text.encode("utf-8")[:byte_offset].decode("utf-8", errors="ignore").count("\n") + 1


def _l0_byte_slice(l0_text: str, byte_start: int, byte_end: int) -> str:
    """SOURCE_EXTRACT invariant: content == exact L0 byte slice."""
    return l0_text.encode("utf-8")[byte_start:byte_end].decode("utf-8")


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
    l1_edit_provenance: dict | None = None,
) -> dict:
    """Construct an E47-style atom dict.

    For SOURCE_EXTRACT atoms the caller MUST pass ``content`` as the
    exact L0 byte slice at ``(byte_start, byte_end)``. For INFERENCE /
    derived atoms ``content`` is the canonical / derived form.
    """
    span: Dict[str, object] = {
        "byte_start": byte_start,
        "byte_end": byte_end,
        "line_start": line_start,
        "line_end": line_end,
    }
    if label:
        span["span_label"] = label
    atom: Dict[str, object] = {
        "atom_id": atom_id,
        "atom_type": atom_type,
        "content": content,
        "source_spans": [span],
        "evidence_kind": evidence_kind,
        "confidence": confidence,
        "scope": "canary",
        "invalidation_conditions": "",
    }
    if l1_edit_provenance is not None:
        atom["l1_edit_provenance"] = l1_edit_provenance
    return atom


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
        "source_title": source_meta.get("source_title", "E48 PUBLIC_SAFE canary (R3)"),
        "source_hash": hashlib.sha256(l0_bytes).hexdigest(),
        "source_size_bytes": len(l0_bytes),
        "ingested_at": "1970-01-01T00:00:00Z",
    }

    atoms: List[dict] = []
    relations: List[dict] = []
    unknowns: List[dict] = []
    counter = 0

    # R3 mandatory 1: no edit-as-atom promotion. Filler / punctuation /
    # typo / ASR edits remain L1 audit records; they do NOT become
    # knowledge atoms.

    # R3 mandatory 4: terminology-normalization applied edits produce
    # either CONCEPT (verbatim) or DERIVED_CONCEPT (derived) atoms.
    for seg in view.segments:
        for e in seg.edits:
            if not e.applied:
                continue
            if e.edit_type != EditType.TERMINOLOGY_NORMALIZATION:
                continue
            if e.confidence < HIGH_CONFIDENCE_THRESHOLD:
                continue
            l0_slice = _l0_byte_slice(l0_text, e.byte_start, e.byte_end)
            counter += 1
            atom_id = f"A{counter:03d}"
            line_start = _line_index_for_byte(l0_text, e.byte_start)
            line_end = _line_index_for_byte(l0_text, e.byte_end)
            if l0_slice == e.after:
                # Verbatim: the canonical form is unchanged from L0.
                atoms.append(_build_atom_dict(
                    atom_id, "CONCEPT", "SOURCE_EXTRACT", "HIGH",
                    l0_slice, e.byte_start, e.byte_end,
                    line_start, line_end,
                    label=f"terminology:verbatim:{e.edit_id}",
                    l1_edit_provenance={
                        "edit_id": e.edit_id,
                        "edit_type": e.edit_type.value,
                        "raw_form": l0_slice,
                        "canonical_form": e.after,
                        "confidence": e.confidence,
                        "evidence_refs": list(e.evidence_refs),
                    },
                ))
            else:
                # Derived: canonical differs from L0 surface form.
                atoms.append(_build_atom_dict(
                    atom_id, "DERIVED_CONCEPT", "INFERENCE",
                    _confidence_label(e.confidence, e.edit_type),
                    e.after, e.byte_start, e.byte_end,
                    line_start, line_end,
                    label=f"terminology:derived:{e.edit_id}",
                    l1_edit_provenance={
                        "edit_id": e.edit_id,
                        "edit_type": e.edit_type.value,
                        "raw_form": l0_slice,
                        "canonical_form": e.after,
                        "confidence": e.confidence,
                        "evidence_refs": list(e.evidence_refs),
                    },
                ))

    # R3 mandatory 1 + 2: UNKNOWN_REFUSAL atoms for each UnknownMarker.
    # content = exact L0 byte slice at the unknown's byte span.
    unknown_atom_ids: List[str] = []
    for u in view.unknowns:
        counter += 1
        atom_id = f"A{counter:03d}"
        unknown_atom_ids.append(atom_id)
        line_start = _line_index_for_byte(l0_text, u.byte_start)
        line_end = _line_index_for_byte(l0_text, u.byte_end)
        atoms.append(_build_atom_dict(
            atom_id, "UNKNOWN_REFUSAL", "INFERENCE", "MEDIUM",
            _l0_byte_slice(l0_text, u.byte_start, u.byte_end),
            u.byte_start, u.byte_end,
            line_start, line_end,
            label=f"unknown_refusal:{u.unknown_id}",
            l1_edit_provenance={
                "unknown_id": u.unknown_id,
                "reason": u.reason,
                "raw_text": u.raw_text,
            },
        ))
        unknowns.append({
            "unknown_id": u.unknown_id,
            "question": u.reason,
            "related_atom_ids": [atom_id],
        })

    # R3 mandatory 5 + 6: cross-sentence mechanism derivation with
    # bounded effect + truthful DEPENDS_ON relation. The effect clause
    # is bounded by the next contrast/conditional/sentence marker.
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
        # R4 mandatory 3: trim trailing clause-delimiter punctuation
        # from the CONDITION span so SOURCE_EXTRACT byte slice excludes
        # the comma/period. ``如果 X，那么`` -> CONDITION span = ``X``.
        cond_span = _trim_condition_span(l0_text, cond_span)
        counter += 1
        cond_atom_id = f"A{counter:03d}"
        cond_line_start = _line_index_for_byte(l0_text, cond_span[0])
        cond_line_end = _line_index_for_byte(l0_text, cond_span[1])
        cond_excerpt = _l0_byte_slice(l0_text, cond_span[0], cond_span[1])
        atoms.append(_build_atom_dict(
            cond_atom_id, "CONDITION", "SOURCE_EXTRACT", "HIGH",
            cond_excerpt, cond_span[0], cond_span[1],
            cond_line_start, cond_line_end,
            label="if-condition",
        ))
        counter += 1
        eff_atom_id = f"A{counter:03d}"
        eff_line_start = _line_index_for_byte(l0_text, eff_span[0])
        eff_line_end = _line_index_for_byte(l0_text, eff_span[1])
        eff_excerpt = _l0_byte_slice(l0_text, eff_span[0], eff_span[1])
        atoms.append(_build_atom_dict(
            eff_atom_id, "MECHANISM", "SOURCE_EXTRACT", "HIGH",
            eff_excerpt, eff_span[0], eff_span[1],
            eff_line_start, eff_line_end,
            label="then-effect",
        ))
        # R4 mandatory 1: DEPENDS_ON direction is MECHANISM effect DEPENDS_ON
        # CONDITION premise (MECHANISM is source_atom_id, CONDITION is target).
        # Semantically: the mechanism/effect's truth depends on the condition
        # premise holding; flipping endpoints reads as "mechanism depends on
        # its premise", which is the natural semantic reading.
        relations.append({
            "source_atom_id": eff_atom_id,
            "target_atom_id": cond_atom_id,
            "relation_type": "DEPENDS_ON",
            "span_index": -1,
            "rationale": "MECHANISM effect depends on CONDITION premise (if/then).",
        })

    return {
        "schema": "QCLAW-CANDIDATE-KNOWLEDGE-PACKAGE-V1",
        "package_id": package_id,
        "package_version": 1,
        "content_hash": "0" * 16,
        "source": source,
        "summary": "E48 R3 end-to-end derivation: L1 provenance separated from L2 semantics.",
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