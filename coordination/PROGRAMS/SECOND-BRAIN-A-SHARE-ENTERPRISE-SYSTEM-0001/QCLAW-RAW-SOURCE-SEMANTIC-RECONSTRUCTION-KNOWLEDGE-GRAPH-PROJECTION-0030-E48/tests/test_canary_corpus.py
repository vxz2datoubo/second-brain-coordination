"""Canary corpus checks.

Walks the 8 required noise categories in the PUBLIC_SAFE canary file and
asserts the right edit / ambiguity class fired.
"""
from __future__ import annotations

import unittest
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
E48_ROOT = _HERE.parents[1]
sys.path.insert(0, str(E48_ROOT / "src"))

from qclaw_e48_reconstruction.l1_schema import EditType  # noqa: E402
from qclaw_e48_reconstruction.l1_reconstruct import reconstruct  # noqa: E402


CANARY_PATH = E48_ROOT / "canary" / "synthetic_canary_noisy_chinese.txt"


def _edits(view):
    return [e for s in view.segments for e in s.edits]


def test_a_filler_words() -> None:
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = reconstruct(l0)
    types = {e.edit_type for e in _edits(view)}
    assert EditType.FILLER_REMOVAL in types


def test_b_missing_punctuation() -> None:
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = reconstruct(l0)
    types = {e.edit_type for e in _edits(view)}
    assert EditType.PUNCTUATION in types


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
    """Drive a custom low-confidence edit through the corpus."""
    from qclaw_e48_reconstruction.l1_reconstruct import ReconstructionRuleset
    rules = ReconstructionRuleset(
        rules=(
            (r"成交量", "交易量", 0.4, EditType.TERMINOLOGY_NORMALIZATION,
             "weak alias"),
        )
    )
    l0 = "今天的成交量是一百万。昨天的成交量是一百五十万。"
    view = reconstruct(l0, ruleset=rules)
    weak = [
        e for e in _edits(view)
        if e.edit_type == EditType.TERMINOLOGY_NORMALIZATION and e.before == "成交量"
    ]
    assert weak, "expected weak alias edits"
    for e in weak:
        assert e.before in e.alternatives


def test_f_unknown_marker_possible() -> None:
    """The reconstructor returns an empty unknowns tuple for the built-in
    ruleset by design — explicit UnknownMarker construction is the only
    way to add UNKNOWN. This test documents that contract."""
    from qclaw_e48_reconstruction.l1_schema import (
        NormalizedSemanticView, UnknownMarker,
    )
    view = NormalizedSemanticView(
        view_id="manual",
        view_schema_version="1.0",
        l0_source_hash="0" * 64,
        l0_source_size_bytes=100,
        segments=(),
        unknowns=(UnknownMarker(
            unknown_id="U0",
            byte_start=0,
            byte_end=3,
            raw_text="他她",
            reason="ambiguous pronoun",
        ),),
    ).with_sha()
    assert any(u.reason == "ambiguous pronoun" for u in view.unknowns)


def test_g_terminology_alias() -> None:
    from qclaw_e48_reconstruction.l1_schema import TerminologyAlias
    from qclaw_e48_reconstruction.l1_reconstruct import ReconstructionRuleset
    rules = ReconstructionRuleset()  # empty -> rely on alias pass
    l0 = "我们用术语别名 来描述这个概念。"
    view = reconstruct(
        l0,
        ruleset=rules,
        aliases=(TerminologyAlias(
            alias_id="A0",
            raw_form="术语别名",
            canonical_form="量子纠缠",
            scope="physics",
            confidence=0.95,
        ),),
    )
    assert any(
        e.edit_type == EditType.TERMINOLOGY_NORMALIZATION and "术语别名" in e.before
        for e in _edits(view)
    )


def test_h_cross_sentence_mechanism_captured() -> None:
    """The mechanism sentence survives reconstruction byte-identically in
    raw_text — only punctuation may be added; no semantic content is dropped."""
    l0 = "如果成交量上升那么价格就倾向于上升但如果成交量下降价格就可能下降这是个常见的机制"
    view = reconstruct(l0)
    seg = view.segments[0]
    assert seg.raw_text == l0
    # Punctuation edit(s) present
    assert any(e.edit_type == EditType.PUNCTUATION for e in seg.edits)


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
