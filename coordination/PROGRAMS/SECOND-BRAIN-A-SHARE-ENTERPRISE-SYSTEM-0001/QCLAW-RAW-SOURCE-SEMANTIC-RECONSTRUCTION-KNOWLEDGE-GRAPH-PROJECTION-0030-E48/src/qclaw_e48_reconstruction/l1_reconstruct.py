"""L1 reconstruction — deterministic, stdlib-only.

R1 fixes (per Issue #216 GPT review id 4904086170):
- The previous Han-to-Han punctuation rule `([一-鿿])(\s*)([一-鿿]) → \1。\3`
  was destructively splitting ordinary Chinese words (讨论 → 讨。论). That
  rule is REMOVED. Default automatic punctuation is now conservative:
  punctuation is only inserted at unterminated line breaks (no `。`, `！`,
  `？`, `;`, `,`) where the next non-whitespace char is a Han character or
  EOF. One insertion per line at most.
- Every accepted edit is now subject to **deterministic overlap arbitration**:
  edits whose byte ranges overlap a higher-priority edit are rejected from
  application (the edit is recorded as an AmbiguityCandidate / UnknownMarker,
  never silently dropped). No two applied edits may overlap L0 ranges.
- `NormalizedSegment.normalized_text` is now materialized as the actual
  applied normalized display text: accepted edits are stitched together in
  order over the L0 byte stream. The original `raw_text` and the per-edit
  `byte_start`/`byte_end` provenance remain the audit surface.
- A small, deterministic ruleset remains (PUBLIC_SAFE Chinese filler / typo /
  ASR homophone patterns and example aliases).
- Any low-confidence edit keeps ``before`` in ``alternatives``; the reconstructor
  NEVER promotes a low-confidence edit into a SOURCE_EXTRACT atom.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
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


# Edit priority: lower number = higher priority. When two edits overlap, the
# higher-priority edit wins and the lower-priority edit is *not* applied
# (it is recorded as an AmbiguityCandidate / UnknownMarker so the L2 stage
# can decide what to do). Priorities are tuned for the R1 canary.
_EDIT_PRIORITY: dict = {
    EditType.TERMINOLOGY_NORMALIZATION: 10,
    EditType.TYPO_CORRECTION: 20,
    EditType.ASR_HOMOPHONE_CORRECTION: 30,
    EditType.FILLER_REMOVAL: 40,
    EditType.PUNCTUATION: 50,
    EditType.SENTENCE_BREAK: 50,
    EditType.ALIAS_REMAP: 60,
    EditType.REFERENCE_RECOVERY: 70,
    EditType.PARAGRAPH_SPLIT: 80,
    EditType.AMBIGUITY_ALTERNATIVE: 90,
    EditType.UNKNOWN_MARKER: 100,
}


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
# PUBLIC_SAFE — no real private text, only generic Chinese filler / typo /
# ASR homophone patterns and example aliases.
#
# R1 FIX: removed the destructively-broad `([一-鿿])(\s*)([一-鿿]) → \1。\3`
# rule that was splitting ordinary words like 讨论 / 如果 / 成交 / 应该.
# Replaced with a *bounded* sentence-final-punctuation rule:
#   - Only fires at line endings where the line is not already terminated
#     by `。`, `！`, `？`, `;`, `,`.
#   - Only fires when the next non-whitespace char (next line) is a Han
#     character or EOF.
#   - Replaces one trailing run of whitespace with `。`.
BUILTIN_RULESET = ReconstructionRuleset(
    rules=(
        # bounded sentence-final punctuation: only insert "。" at unterminated
        # line breaks, where the line's last non-whitespace char is NOT
        # already a sentence terminator (any of 。！？；,;.!?) and the next
        # line starts with a Han character or EOF. This avoids:
        #   - inserting 。 after English "." / "!" / "?" / "," / ";"
        #   - inserting 。 mid-Han-word (R0 had this bug)
        (
            r"([一-鿿])(\s*)\n(?=[一-鿿])",
            r"\1。\n",
            0.95,
            EditType.PUNCTUATION,
            "Insert sentence-final punctuation at unterminated Han-line break (R1 bounded)",
        ),
        # filler_removal: drop standalone filler words. Conservative.
        # Bounded: filler is not preceded or followed by another Han character
        # (so we never eat a normal word that merely contains the filler
        # substring).
        (
            r"(?<![一-鿿])(呃|那个|然后|就是说|基本上|其实)(?![一-鿿])",
            r"",
            0.92,
            EditType.FILLER_REMOVAL,
            "Drop standalone Chinese filler particle (R1 bounded — Han-bounded)",
        ),
        # typo_correction: a small high-confidence typo list.
        (
            r"部份",
            r"部分",
            0.97,
            EditType.TYPO_CORRECTION,
            "Typo: 部份 → 部分",
        ),
        # asr_homophone_correction: a small high-confidence ASR list.
        (
            r"式式",
            r"试试",
            0.95,
            EditType.ASR_HOMOPHONE_CORRECTION,
            "ASR homophone: 式式 → 试试",
        ),
    )
)


def _byte_index(l0_text: str, char_index: int) -> int:
    """Convert a char index in ``l0_text`` to a UTF-8 byte offset.

    Slicing by character index from the decoded text and re-encoding to
    UTF-8 avoids cutting a multibyte sequence in the middle.
    """
    return len(l0_text[:char_index].encode("utf-8"))


# Lookup table: which ``EditType`` is built by which after-text shape.
# Patterns can be reconstructed deterministically from a (rule_name, ...)
# pair; this keeps the after-text logic explicit and testable.
#
# NOTE: This helper is no longer used by the R1 ``_plan_edits`` path, which
# now applies ``re.sub`` against the full L0 text. It is kept for reference
# and as a safety net for unit tests that may want to exercise an isolated
# pattern in isolation.
def _apply_pattern_replacement(pat: re.Pattern, m: re.Match, before: str) -> str:
    """Compute the deterministic post-replacement text for a matched span.

    Kept for backward compatibility with R0 tests; the R1 planner applies
    rules against the full L0 text instead.
    """
    src = pat.pattern
    if src == r"([一-鿿])(\s*)\n(?=[一-鿿])":
        return m.group(1) + "。\n"
    if src == r"(?<![一-鿿])(呃|那个|然后|就是说|基本上|其实)(?![一-鿿])":
        return ""
    if src == r"部份":
        return "部分"
    if src == r"式式":
        return "试试"
    return before


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
    rules: List[Tuple[re.Pattern, str, float, EditType, str]],
    aliases: Iterable[TerminologyAlias],
) -> List[_PlannedEdit]:
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
    # Note: we cannot reuse `pat.sub(repl, before, count=1)` to compute the
    # post-replacement text — many rules use a lookahead (e.g. the
    # sentence-final-punctuation rule looks ahead to `\n(?=[一-鿿])`), so
    # re-substituting against the *match span only* would fail the lookahead
    # and return ``before`` unchanged. We therefore apply the rule against
    # the *full L0 text* with ``count=1`` and slice the resulting ``after``
    # text. This is safe for any pattern (lookahead or simple substring),
    # and it keeps the audit surface (byte_start/byte_end) tied to the
    # FIRST match position in the L0 text.
    for pat, repl, conf, etype, rationale in rules:
        # Find the first match in the full L0 text (one match per pass; we
        # repeat until no more matches are produced, so we capture every
        # occurrence, even within the same line).
        text = l0_text
        while True:
            m = pat.search(text)
            if not m:
                break
            # Apply sub with count=1 against the full text to get the
            # deterministic after-text (including any backreferences).
            new_text = pat.sub(repl, text, count=1)
            # The match m must lie in the original ``text`` (not in
            # ``l0_text``), so we need its char-offset relative to l0_text.
            char_start = m.start() + (len(l0_text) - len(text))
            char_end = m.end() + (len(l0_text) - len(text))
            before = l0_text[char_start:char_end]
            # If the rule produced no change AND it's not an UNKNOWN_MARKER
            # (which is intentionally a no-op tail to register the surface),
            # skip the match so we don't infinitely loop.
            if new_text == text and etype != EditType.UNKNOWN_MARKER:
                text = text[m.end():]
                continue
            if new_text == text and etype == EditType.UNKNOWN_MARKER:
                # UNKNOWN_MARKER is a no-op replacement by design (the
                # surface form is preserved verbatim AND marked as unknown).
                after_text = before
            else:
                tail_orig = text[m.end():]
                prefix = text[:m.start()]
                if not (new_text.startswith(prefix) and new_text.endswith(tail_orig)):
                    # Some rules may shift the tail; fall back to safe path.
                    text = text[m.end():]
                    continue
                after_text = new_text[len(prefix):len(new_text) - len(tail_orig)]
            if after_text == before and etype != EditType.UNKNOWN_MARKER:
                # Conservative: skip pure no-op edits.
                text = text[m.end():]
                continue
            byte_start = _byte_index(l0_text, char_start)
            byte_end = byte_start + len(before.encode("utf-8"))
            planned.append(_PlannedEdit(
                byte_start=byte_start,
                byte_end=byte_end,
                before=before,
                after=after_text,
                confidence=conf,
                edit_type=etype,
                rationale=rationale,
                alternatives=(before,),
            ))
            # Advance past the matched span to find the next occurrence.
            text = text[m.end():]
    planned.sort(key=lambda e: (e.byte_start, e.byte_end, _EDIT_PRIORITY[e.edit_type]))
    return planned


def _arbitrate_overlaps(
    planned: List[_PlannedEdit],
) -> Tuple[List[_PlannedEdit], List[Tuple[_PlannedEdit, str]]]:
    """Apply deterministic overlap arbitration.

    Returns (accepted, rejected_with_reason). An edit is rejected when its
    byte range overlaps a higher-priority edit that already won. The
    arbitration is *stable*: ties (same priority, overlapping range) are
    broken by byte_start ascending then byte_end descending, and the
    earlier-listed edit wins.
    """
    accepted: List[_PlannedEdit] = []
    rejected: List[Tuple[_PlannedEdit, str]] = []
    for e in planned:
        winner = None
        for a in accepted:
            if a.byte_end <= e.byte_start:
                continue  # no overlap
            if e.byte_end <= a.byte_start:
                continue  # no overlap
            # overlap: lower priority number = higher priority = wins
            a_pri = _EDIT_PRIORITY.get(a.edit_type, 1000)
            e_pri = _EDIT_PRIORITY.get(e.edit_type, 1000)
            if a_pri <= e_pri:
                winner = a
                break
            # else: this e has higher priority and should win; existing
            # accepted edits that overlap e will need to be re-checked
            # (handled below).
        if winner is not None:
            rejected.append((e, f"overlaps accepted edit byte range {winner.byte_start}-{winner.byte_end}"))
            continue
        # No winner among accepted edits; but we may evict lower-priority
        # accepted edits that overlap e (e has higher priority).
        new_accepted: List[_PlannedEdit] = []
        evicted_self = False
        for a in accepted:
            if a.byte_end <= e.byte_start or e.byte_end <= a.byte_start:
                new_accepted.append(a)
                continue
            a_pri = _EDIT_PRIORITY.get(a.edit_type, 1000)
            e_pri = _EDIT_PRIORITY.get(e.edit_type, 1000)
            if e_pri < a_pri:
                rejected.append((a, f"evicted by higher-priority edit byte range {e.byte_start}-{e.byte_end}"))
                continue
            # Same priority: stable tie-break by byte_start
            if e_pri == a_pri:
                if e.byte_start < a.byte_start:
                    rejected.append((a, f"evicted by earlier-listed same-priority edit"))
                    continue
                rejected.append((e, f"overlaps same-priority earlier-listed edit byte range {a.byte_start}-{a.byte_end}"))
                new_accepted.append(a)
                evicted_self = True
                break
            new_accepted.append(a)
        if not evicted_self:
            new_accepted.append(e)
        accepted = new_accepted
    accepted.sort(key=lambda e: (e.byte_start, e.byte_end))
    return accepted, rejected


def _materialize_normalized(
    l0_text: str,
    l0_bytes: bytes,
    accepted: List[_PlannedEdit],
    rejected: List[Tuple[_PlannedEdit, str]],
) -> Tuple[str, List[NormalizationEdit], List[AmbiguityCandidate], List[UnknownMarker]]:
    """Build the displayed normalized text by stitching accepted edits over L0.

    Returns (normalized_text, all_edits, ambiguities, unknowns).
    ``all_edits`` includes BOTH ``applied`` (True) and ``pending`` (False)
    edits so the audit surface is complete; only ``applied`` edits contribute
    to ``normalized_text``. The L2 layer reads ``applied=False`` edits as
    "candidate, not promoted to fact" and must not turn them into
    SOURCE_EXTRACT atoms.
    """
    l0_size = len(l0_bytes)
    out: List[str] = []
    cursor = 0
    all_edits: List[NormalizationEdit] = []
    edit_id_counter = 0
    for e in accepted:
        if e.byte_start < cursor:
            # Defensive: should never happen after arbitration, but keep safe.
            continue
        if e.byte_start > l0_size or e.byte_end > l0_size:
            continue
        out.append(l0_bytes[cursor:e.byte_start].decode("utf-8"))
        out.append(e.after)
        cursor = e.byte_end
        all_edits.append(NormalizationEdit(
            edit_id=f"E-{edit_id_counter:04d}",
            edit_type=e.edit_type,
            byte_start=e.byte_start,
            byte_end=e.byte_end,
            before=e.before,
            after=e.after,
            alternatives=e.alternatives,
            confidence=e.confidence,
            rationale=e.rationale,
            applied=True,
        ))
        edit_id_counter += 1
    if cursor < l0_size:
        out.append(l0_bytes[cursor:].decode("utf-8"))

    ambiguities: List[AmbiguityCandidate] = []
    unknowns: List[UnknownMarker] = []
    # An UNKNOWN_MARKER edit is also a view-level UnknownMarker (in
    # addition to its NormalizationEdit representation in seg.edits).
    for e in accepted:
        if e.edit_type == EditType.UNKNOWN_MARKER:
            unknowns.append(UnknownMarker(
                unknown_id=f"U-{len(unknowns):04d}",
                byte_start=e.byte_start,
                byte_end=e.byte_end,
                raw_text=e.before,
                reason=e.rationale,
            ))
    for rej, reason in rejected:
        # All rejected edits are kept as NormalizationEdit with applied=False,
        # so the audit surface is complete (GPT R1 mandatory: every edit
        # is auditable, never silently dropped).
        all_edits.append(NormalizationEdit(
            edit_id=f"E-{edit_id_counter:04d}",
            edit_type=rej.edit_type,
            byte_start=rej.byte_start,
            byte_end=rej.byte_end,
            before=rej.before,
            after=rej.after,
            alternatives=(rej.before, *rej.alternatives),
            confidence=rej.confidence,
            rationale=f"Rejected by arbitration: {reason}",
            applied=False,
        ))
        edit_id_counter += 1
        if rej.edit_type == EditType.UNKNOWN_MARKER:
            unknowns.append(UnknownMarker(
                unknown_id=f"U-{len(unknowns):04d}",
                byte_start=rej.byte_start,
                byte_end=rej.byte_end,
                raw_text=rej.before,
                reason=reason,
            ))
            continue
        # High-confidence rejected because of overlap with another accepted
        # edit OR low-confidence rejected for any reason → record as an
        # ambiguity with the raw surface form retained in candidates. The
        # L2 layer may choose to read these as UNKNOWN.
        ambiguities.append(AmbiguityCandidate(
            ambiguity_id=f"A-{len(ambiguities):04d}",
            byte_start=rej.byte_start,
            byte_end=rej.byte_end,
            raw_text=rej.before,
            candidates=(rej.before, rej.after, *(a for a in rej.alternatives if a != rej.before)),
            chosen=None,
            confidence=rej.confidence,
            rationale=f"Rejected by arbitration: {reason}",
        ))
    # Sort all_edits by byte_start then byte_end for deterministic ordering.
    all_edits.sort(key=lambda e: (e.byte_start, e.byte_end, e.edit_id))
    return "".join(out), all_edits, ambiguities, unknowns


def reconstruct(
    l0_text: str,
    ruleset: ReconstructionRuleset | None = None,
    aliases: Iterable[TerminologyAlias] = (),
    view_id: str = "E48-CANARY-001",
    view_schema_version: str = "1.1",
) -> NormalizedSemanticView:
    """Run the reconstructor on ``l0_text`` and return a L1 view.

    Deterministic. View hash is set by ``with_sha()``. ``view_schema_version``
    is bumped to 1.1 to reflect the R1 changes (bounded punctuation rule,
    deterministic overlap arbitration, materialized normalized_text).
    """
    rules = (ruleset or BUILTIN_RULESET).compile()
    l0_bytes = l0_text.encode("utf-8")
    l0_hash = hashlib.sha256(l0_bytes).hexdigest()
    planned = _plan_edits(l0_text, rules, aliases)
    accepted, rejected = _arbitrate_overlaps(planned)
    normalized_text, all_edits, ambiguities, unknowns = _materialize_normalized(
        l0_text, l0_bytes, accepted, rejected,
    )
    seg = NormalizedSegment(
        segment_id=f"S{view_id}-000",
        byte_start=0,
        byte_end=len(l0_bytes),
        raw_text=l0_text,
        normalized_text=normalized_text,
        confidence=min((e.confidence for e in all_edits if e.applied), default=1.0),
        edits=tuple(all_edits),
    )
    view = NormalizedSemanticView(
        view_id=view_id,
        view_schema_version=view_schema_version,
        l0_source_hash=l0_hash,
        l0_source_size_bytes=len(l0_bytes),
        segments=(seg,),
        ambiguities=tuple(ambiguities),
        aliases=tuple(aliases),
        unknowns=tuple(unknowns),
    ).with_sha()
    return view


__all__ = [
    "BUILTIN_RULESET",
    "ReconstructionRuleset",
    "reconstruct",
]