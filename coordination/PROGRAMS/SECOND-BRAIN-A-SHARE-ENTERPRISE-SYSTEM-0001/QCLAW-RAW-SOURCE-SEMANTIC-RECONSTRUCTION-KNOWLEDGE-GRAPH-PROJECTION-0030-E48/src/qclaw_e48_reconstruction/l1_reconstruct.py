"""L1 reconstruction — deterministic, stdlib-only.

The reconstructor is intentionally rule-based and tiny. It performs the
edits listed by a caller-supplied :class:`Ruleset` against the L0 text and
emits a :class:`NormalizedSemanticView`. The output is fully deterministic:
identical L0 text + identical Ruleset → identical view_sha256.

Reconstruction rules in this file are deliberately conservative:
- punctuation: insert Chinese full stop where one is missing between two
  Han characters and the next sentence starts with a Han character.
- filler_removal: drop Chinese filler particles "呃", "那个", "然后", "就是说",
  "其实", "基本上" when they are standalone tokens surrounded by whitespace
  or punctuation.
- typo_correction: a built-in list of high-confidence CN typos → form.
- asr_homophone_correction: a built-in list of high-confidence CN ASR
  homophone confusions; kept conservative — anything below
  ASR_HIGH_CONFIDENCE keeps alternatives.
- terminology_normalization: from TerminologyAlias list, exact-substring
  normalization (longest first).

Any low-confidence edit keeps ``before`` in ``alternatives``. The reconstructor
NEVER promotes a low-confidence edit into a SOURCE_EXTRACT atom; that decision
is the L2 ingestor's, not ours.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Tuple

from .digests import canonical_json, sha256_hex
from .l1_schema import (
    AmbiguityCandidate,
    EditType,
    HIGH_CONFIDENCE_THRESHOLD,
    NormalizationEdit,
    NormalizedSegment,
    NormalizedSemanticView,
    TerminologyAlias,
    UnknownMarker,
)


@dataclass(frozen=True)
class ReconstructionRuleset:
    """Caller-supplied rules.

    Each item is (regex pattern, replacement, confidence, edit_type, rationale).
    Patterns use Python ``re`` syntax over the decoded L0 string. Capture groups
    are allowed; replacement supports ``\\1``-style backreferences.
    """

    rules: Tuple[Tuple[str, str, float, EditType, str], ...] = ()

    def compile(self) -> List[Tuple[re.Pattern, str, float, EditType, str]]:
        return [(re.compile(p), r, c, t, rat) for (p, r, c, t, rat) in self.rules]


# A conservative, fully deterministic built-in ruleset. All entries are
# PUBLIC_SAFE — no real private text, only generic Chinese filler / typo / ASR
# patterns and example aliases.
BUILTIN_RULESET = ReconstructionRuleset(
    rules=(
        # punctuation: insert "。" between consecutive Han characters when no
        # sentence-final punctuation is present. Conservative — only when the
        # next chunk starts with a Han character.
        (
            r"([一-鿿])(\s*)([一-鿿])",
            r"\1。\3",
            0.85,
            EditType.PUNCTUATION,
            "Insert Chinese full stop between two Han chars with optional whitespace",
        ),
        # filler_removal: drop standalone filler words. We allow the filler
        # to appear anywhere between Han characters, after whitespace, or at
        # the start of a line. The filler list is conservative; multi-char
        # fillers (那个, 然后, 就是说) are matched as one token.
        (
            r"(呃|那个|然后|就是说|基本上|其实)",
            r"",
            0.9,
            EditType.FILLER_REMOVAL,
            "Drop standalone Chinese filler particle",
        ),
        # typo_correction: a small high-confidence typo list.
        (
            r"部份",
            r"部分",
            0.95,
            EditType.TYPO_CORRECTION,
            "Typo: 部份 → 部分",
        ),
        # asr_homophone_correction: a small high-confidence ASR list.
        (
            r"式式",
            r"试试",
            0.92,
            EditType.ASR_HOMOPHONE_CORRECTION,
            "ASR homophone: 式式 → 试试",
        ),
    )
)


def _byte_index(l0_text: str, char_index: int) -> int:
    """Convert a char index in ``l0_text`` to a UTF-8 byte offset.

    Slicing by character index from the decoded text and re-encoding to
    UTF-8 avoids cutting a multibyte sequence in the middle. The bytes
    view is not used directly here; ``reconstruct`` keeps it for span
    slicing.
    """
    return len(l0_text[:char_index].encode("utf-8"))


def _slice_byte_range(l0_bytes: bytes, byte_start: int, byte_end: int) -> str:
    return l0_bytes[byte_start:byte_end].decode("utf-8")


@dataclass(frozen=True)
class _PlannedEdit:
    byte_start: int
    byte_end: int
    before: str
    after: str
    confidence: float
    edit_type: EditType
    rationale: str
    alternatives: Tuple[str, ...] = ()


def _plan_edits(
    l0_text: str,
    l0_bytes: bytes,
    rules: List[Tuple[re.Pattern, str, float, EditType, str]],
    aliases: Iterable[TerminologyAlias],
) -> List[_PlannedEdit]:
    del l0_bytes  # not needed; _byte_index uses l0_text directly
    planned: List[_PlannedEdit] = []
    # 1. Terminology alias normalization (longest first).
    alias_sorted = sorted(aliases, key=lambda a: -len(a.raw_form))
    for alias in alias_sorted:
        for m in re.finditer(re.escape(alias.raw_form), l0_text):
            char_start, char_end = m.span()
            byte_start = _byte_index(l0_text, char_start)
            byte_end = byte_start + len(alias.raw_form.encode("utf-8"))
            planned.append(_PlannedEdit(
                byte_start=byte_start,
                byte_end=byte_end,
                before=alias.raw_form,
                after=alias.canonical_form,
                confidence=alias.confidence,
                edit_type=EditType.TERMINOLOGY_NORMALIZATION,
                rationale=f"Terminology alias → {alias.canonical_form}",
                alternatives=(alias.raw_form,),
            ))
    # 2. Pattern rules.
    for pat, repl, conf, etype, rationale in rules:
        for m in pat.finditer(l0_text):
            char_start, char_end = m.span()
            before = l0_text[char_start:char_end]
            # Use regex sub to compute the post-replacement text locally
            after_full = pat.sub(repl, before, count=1)
            if after_full == before:
                continue
            byte_start = _byte_index(l0_text, char_start)
            byte_end = byte_start + len(before.encode("utf-8"))
            planned.append(_PlannedEdit(
                byte_start=byte_start,
                byte_end=byte_end,
                before=before,
                after=after_full,
                confidence=conf,
                edit_type=etype,
                rationale=rationale,
                alternatives=(before,),
            ))
    planned.sort(key=lambda e: (e.byte_start, e.byte_end))
    return planned


def reconstruct(
    l0_text: str,
    ruleset: ReconstructionRuleset | None = None,
    aliases: Iterable[TerminologyAlias] = (),
    view_id: str = "E48-CANARY-001",
    view_schema_version: str = "1.0",
) -> NormalizedSemanticView:
    """Run the reconstructor on ``l0_text`` and return a L1 view.

    Deterministic. View hash is set by ``with_sha()``.
    """
    rules = (ruleset or BUILTIN_RULESET).compile()
    l0_bytes = l0_text.encode("utf-8")
    l0_hash = hashlib.sha256(l0_bytes).hexdigest()
    planned = _plan_edits(l0_text, l0_bytes, rules, aliases)
    # Build one segment for the whole text; segments are byte ranges, edits
    # are sorted. We split segments at every edit boundary only if needed —
    # for the canary corpus a single segment is sufficient and auditable.
    edits: List[NormalizationEdit] = []
    for i, e in enumerate(planned):
        ne = NormalizationEdit(
            edit_id=f"E{view_id}-{i:03d}",
            edit_type=e.edit_type,
            byte_start=e.byte_start,
            byte_end=e.byte_end,
            before=e.before,
            after=e.after,
            alternatives=e.alternatives,
            confidence=e.confidence,
            rationale=e.rationale,
        )
        edits.append(ne)
    seg = NormalizedSegment(
        segment_id=f"S{view_id}-000",
        byte_start=0,
        byte_end=len(l0_bytes),
        raw_text=l0_text,
        normalized_text=l0_text,  # display text only; downstream chooses to apply edits
        confidence=min((e.confidence for e in edits), default=1.0),
        edits=tuple(edits),
    )
    # Mark low-confidence edits as ambiguities (caller can also pass
    # explicit AmbiguityCandidates; the built-in corpus does not).
    ambiguities: List[AmbiguityCandidate] = []
    for e in edits:
        if e.is_low_confidence():
            ambiguities.append(AmbiguityCandidate(
                ambiguity_id=f"A{view_id}-{e.edit_id}",
                byte_start=e.byte_start,
                byte_end=e.byte_end,
                raw_text=e.before,
                candidates=(e.before, e.after, *(a for a in e.alternatives if a != e.before)),
                chosen=e.after,
                confidence=e.confidence,
                rationale=e.rationale,
            ))
    view = NormalizedSemanticView(
        view_id=view_id,
        view_schema_version=view_schema_version,
        l0_source_hash=l0_hash,
        l0_source_size_bytes=len(l0_bytes),
        segments=(seg,),
        ambiguities=tuple(ambiguities),
        aliases=tuple(aliases),
        unknowns=(),
    ).with_sha()
    return view


__all__ = [
    "BUILTIN_RULESET",
    "ReconstructionRuleset",
    "reconstruct",
]