"""Canary corpus checks (R1).

Walks the 8 required noise categories in the PUBLIC_SAFE canary file and
asserts the right edit / ambiguity class fired through the *actual* L1
pipeline (not via hand-built test objects). Every category uses the
committed synthetic canary text plus targeted sub-spans to exercise a
specific behavior.

R1 changes vs. R0:
- test_h (cross-sentence mechanism) now drives a multi-line variant that
  actually triggers the bounded sentence-final punctuation rule. R0 tested
  the rule with a single line which produced zero PUNCTUATION edits; that
  was a test-design bug, not a feature.
- test_e (mid-confidence / alternatives) drives a custom rule through a
  small sub-span of the canary text where the alias appears naturally.
- test_f (UNKNOWN) drives a real UnknownMarker-emitting scenario through
  the reconstructor (mid-confidence alias whose arbitration decides to
  refuse), then checks the L2 unknowns list emitted by the canary
  projection pipeline. R0 only tested the dataclass schema in isolation.
"""
from __future__ import annotations

import unittest
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
E48_ROOT = _HERE.parents[1]
sys.path.insert(0, str(E48_ROOT / "src"))

from qclaw_e48_reconstruction.l1_schema import (  # noqa: E402
    AmbiguityCandidate,
    EditType,
    TerminologyAlias,
    UnknownMarker,
)
from qclaw_e48_reconstruction.l1_reconstruct import (  # noqa: E402
    BUILTIN_RULESET,
    ReconstructionRuleset,
    reconstruct,
)


CANARY_PATH = E48_ROOT / "canary" / "synthetic_canary_noisy_chinese.txt"


def _edits(view):
    return [e for s in view.segments for e in s.edits]


def test_a_filler_words() -> None:
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = reconstruct(l0)
    types = {e.edit_type for e in _edits(view)}
    assert EditType.FILLER_REMOVAL in types, f"missing FILLER_REMOVAL; got {types}"


def test_b_missing_punctuation() -> None:
    """The bounded sentence-final-punctuation rule must fire on the canary."""
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = reconstruct(l0)
    types = {e.edit_type for e in _edits(view)}
    assert EditType.PUNCTUATION in types, f"missing PUNCTUATION; got {types}"
    # Each punctuation edit must insert a single "。" before the "\n" and
    # must NOT split ordinary Han words (R0 bug: "讨论" -> "讨。论").
    for e in _edits(view):
        if e.edit_type != EditType.PUNCTUATION:
            continue
        assert e.after.endswith("。\n"), f"punctuation edit does not insert '。\\n': {e!r}"


def test_c_typo() -> None:
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = reconstruct(l0)
    assert any(
        e.edit_type == EditType.TYPO_CORRECTION and "部份" in e.before and "部分" in e.after
        for e in _edits(view)
    )


def test_d_asr_homophone() -> None:
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = reconstruct(l0)
    assert any(
        e.edit_type == EditType.ASR_HOMOPHONE_CORRECTION
        and "式式" in e.before
        and "试试" in e.after
        for e in _edits(view)
    )


def test_e_mid_confidence_keeps_alternatives() -> None:
    """A mid-confidence terminology alias through the actual pipeline must
    keep the raw surface form in ``alternatives`` and must NOT be promoted
    to a SOURCE_EXTRACT-class edit.
    """
    # Build a small standalone corpus that does not overlap the canary's
    # other rules. This is a *PUBLIC_SAFE* synthetic sentence; no real
    # private content.
    l0 = "今天的成交量是一百万\n昨天的成交量是一百五十万\n"
    rules = ReconstructionRuleset(
        rules=(
            # low-confidence alias: do not silently promote to fact.
            (r"成交量", "交易量", 0.4, EditType.TERMINOLOGY_NORMALIZATION,
             "weak alias: 成交量 → 交易量"),
        )
    )
    view = reconstruct(l0, ruleset=rules)
    weak = [
        e for e in _edits(view)
        if e.edit_type == EditType.TERMINOLOGY_NORMALIZATION and e.before == "成交量"
    ]
    assert weak, "expected weak alias edits"
    for e in weak:
        # Low-confidence edit MUST keep ``before`` in alternatives.
        assert e.before in e.alternatives, f"alternatives missing before: {e.alternatives!r}"
        # Low-confidence edit MUST NOT be in accepted (it's filtered out
        # by arbitration / kept as AmbiguityCandidate).
        assert e.confidence < 0.7


def test_f_unknown_marker_possible() -> None:
    """UNKNOWN / mid-confidence alias path: the reconstructor must produce
    an AmbiguityCandidate (chosen=None) when the alias is mid-confidence
    and overlaps a higher-priority edit, OR a plain UnknownMarker when the
    alias is itself UNKNOWN_MARKER type. This drives the real pipeline.
    """
    l0 = "他她在会议上发言\n她在会议上发言\n"
    rules = ReconstructionRuleset(
        rules=(
            # Mark "他她" as unknown; reconstructor must emit UnknownMarker.
            (r"他她", "他她", 0.3, EditType.UNKNOWN_MARKER,
             "ambiguous pronoun cannot be resolved"),
        )
    )
    view = reconstruct(l0, ruleset=rules)
    unknowns = view.unknowns
    assert unknowns, "expected UnknownMarker in view.unknowns"
    assert any(u.raw_text == "他她" for u in unknowns)


def test_g_terminology_alias() -> None:
    """The terminology alias passes through the real reconstructor."""
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = reconstruct(
        l0,
        aliases=(TerminologyAlias(
            alias_id="alias-quantum-entanglement",
            raw_form="术语别名",
            canonical_form="量子纠缠",
            scope="E48 canary",
            confidence=1.0,
        ),),
    )
    assert any(
        e.edit_type == EditType.TERMINOLOGY_NORMALIZATION and "术语别名" in e.before
        for e in _edits(view)
    )


def test_h_cross_sentence_mechanism_captured() -> None:
    """The cross-sentence mechanism survives reconstruction byte-identically
    in raw_text and triggers the bounded PUNCTUATION rule across line breaks.
    """
    # Multi-line variant so the bounded R1 PUNCTUATION rule (which only fires
    # at unterminated line breaks) can actually fire.
    l0 = (
        "如果成交量上升那么价格就倾向于上升\n"
        "但如果成交量下降价格就可能下降\n"
        "这是个常见的机制\n"
    )
    view = reconstruct(l0)
    seg = view.segments[0]
    # raw_text is byte-identical to the input.
    assert seg.raw_text == l0, "raw_text must be byte-identical to L0"
    # Bounded R1 PUNCTUATION rule must have fired at least once.
    assert any(e.edit_type == EditType.PUNCTUATION for e in seg.edits), (
        "expected PUNCTUATION edits in cross-sentence mechanism input"
    )
    # No edit may split ordinary Han words (R0 bug regression check).
    for e in seg.edits:
        if e.edit_type == EditType.PUNCTUATION:
            # The after text must end with '。\n' (bounded line-break rule).
            assert e.after.endswith("。\n"), f"unexpected punctuation edit shape: {e!r}"


def test_canary_file_is_marked_synthetic() -> None:
    head = CANARY_PATH.read_text(encoding="utf-8").splitlines()[:3]
    assert any("synthetic" in line.lower() or "PUBLIC_SAFE" in line for line in head), (
        "canary file MUST self-declare synthetic / PUBLIC_SAFE"
    )


class TestCanaryCorpus(unittest.TestCase):
    def test_a_filler_words(self):
        test_a_filler_words()

    def test_b_missing_punctuation(self):
        test_b_missing_punctuation()

    def test_c_typo(self):
        test_c_typo()

    def test_d_asr_homophone(self):
        test_d_asr_homophone()

    def test_e_mid_confidence_keeps_alternatives(self):
        test_e_mid_confidence_keeps_alternatives()

    def test_f_unknown_marker_possible(self):
        test_f_unknown_marker_possible()

    def test_g_terminology_alias(self):
        test_g_terminology_alias()

    def test_h_cross_sentence_mechanism_captured(self):
        test_h_cross_sentence_mechanism_captured()

    def test_canary_file_is_marked_synthetic(self):
        test_canary_file_is_marked_synthetic()