"""L1 reconstruction tests against the PUBLIC_SAFE canary corpus."""
from __future__ import annotations

import unittest
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
E48_ROOT = _HERE.parents[1]
sys.path.insert(0, str(E48_ROOT / "src"))

from qclaw_e48_reconstruction.l1_schema import (  # noqa: E402
    EditType,
    HIGH_CONFIDENCE_THRESHOLD,
)
from qclaw_e48_reconstruction.l1_reconstruct import (  # noqa: E402
    BUILTIN_RULESET,
    ReconstructionRuleset,
    reconstruct,
)


CANARY_PATH = E48_ROOT / "canary" / "synthetic_canary_noisy_chinese.txt"


def _load_canary() -> str:
    return CANARY_PATH.read_text(encoding="utf-8")


def test_l0_is_immutable() -> None:
    l0 = _load_canary()
    view = reconstruct(l0)
    # Re-hash the original text and confirm we did not mutate it.
    import hashlib
    h = hashlib.sha256(l0.encode("utf-8")).hexdigest()
    assert h == view.l0_source_hash
    assert len(view.segments) >= 1


def test_view_is_deterministic() -> None:
    l0 = _load_canary()
    v1 = reconstruct(l0)
    v2 = reconstruct(l0)
    assert v1.view_sha256 == v2.view_sha256
    assert v1.to_dict() == v2.to_dict()


def test_punctuation_filler_typo_asr_classes_present() -> None:
    from qclaw_e48_reconstruction.l1_schema import TerminologyAlias
    l0 = _load_canary()
    view = reconstruct(
        l0,
        ruleset=ReconstructionRuleset(
            rules=(
                (r"成交量", r"交易量", 0.5, EditType.TERMINOLOGY_NORMALIZATION,
                 "mid-confidence alias: 成交量 → 交易量 (canary)"),
                (r"他她", r"他她", 0.3, EditType.UNKNOWN_MARKER,
                 "ambiguous pronoun cannot be resolved (canary)"),
            )
        ),
        aliases=(TerminologyAlias(
            alias_id="alias-quantum-entanglement",
            raw_form="术语别名",
            canonical_form="量子纠缠",
            scope="E48 canary",
            confidence=1.0,
        ),),
    )
    edit_types = {e.edit_type for s in view.segments for e in s.edits}
    assert EditType.PUNCTUATION in edit_types, "missing punctuation edits"
    assert EditType.FILLER_REMOVAL in edit_types, "missing filler edits"
    assert EditType.TYPO_CORRECTION in edit_types, "missing 部份 → 部分 typo edit"
    assert EditType.ASR_HOMOPHONE_CORRECTION in edit_types, "missing 式式 → 试试 ASR edit"


def test_typo_edit_is_high_confidence() -> None:
    l0 = _load_canary()
    view = reconstruct(l0)
    typo_edits = [
        e for s in view.segments for e in s.edits
        if e.edit_type == EditType.TYPO_CORRECTION
    ]
    assert typo_edits, "expected at least one typo edit"
    for e in typo_edits:
        assert e.confidence >= HIGH_CONFIDENCE_THRESHOLD
        assert e.byte_end > e.byte_start
        # L0 slice must equal ``before``.
        import hashlib
        l0_bytes = l0.encode("utf-8")
        slice_text = l0_bytes[e.byte_start:e.byte_end].decode("utf-8")
        assert slice_text == e.before


def test_low_confidence_edit_keeps_alternatives() -> None:
    """A custom rule below the threshold must keep ``before`` in alternatives."""
    rules = ReconstructionRuleset(
        rules=(
            (r"成交量", "交易量", 0.5, EditType.TERMINOLOGY_NORMALIZATION,
             "weak alias"),
        )
    )
    l0 = "今天的成交量是一百万。"
    view = reconstruct(l0, ruleset=rules)
    edits = [e for s in view.segments for e in s.edits]
    weak = [e for e in edits if e.edit_type == EditType.TERMINOLOGY_NORMALIZATION]
    assert weak, "expected weak alias edits"
    for e in weak:
        assert e.before in e.alternatives, (
            "low-confidence edit MUST keep before in alternatives"
        )
        assert e.confidence < HIGH_CONFIDENCE_THRESHOLD


def test_validation_catches_invalid_span() -> None:
    from qclaw_e48_reconstruction.l1_schema import (
        NormalizedSegment,
        NormalizationEdit,
        NormalizedSemanticView,
    )
    bad_edit = NormalizationEdit(
        edit_id="X0",
        edit_type=EditType.PUNCTUATION,
        byte_start=10,
        byte_end=9,  # invalid
        before="x",
        after="y",
    )
    seg = NormalizedSegment(
        segment_id="S0",
        byte_start=0,
        byte_end=100,
        raw_text="x",
        normalized_text="x",
        confidence=1.0,
        edits=(bad_edit,),
    )
    view = NormalizedSemanticView(
        view_id="BAD-1",
        view_schema_version="1.0",
        l0_source_hash="0" * 64,
        l0_source_size_bytes=100,
        segments=(seg,),
    ).with_sha()
    errs = view.validate()
    assert any("invalid range" in e for e in errs)


def test_view_serializes_to_json_round_trip() -> None:
    import json
    l0 = _load_canary()
    view = reconstruct(l0)
    d = view.to_dict()
    blob = json.dumps(d, ensure_ascii=False, sort_keys=True)
    parsed = json.loads(blob)
    assert parsed["view_sha256"] == view.view_sha256


class TestL1(unittest.TestCase):
    def test_l0_is_immutable(self):
        test_l0_is_immutable()

    def test_view_is_deterministic(self):
        test_view_is_deterministic()

    def test_punctuation_filler_typo_asr_classes_present(self):
        test_punctuation_filler_typo_asr_classes_present()

    def test_typo_edit_is_high_confidence(self):
        test_typo_edit_is_high_confidence()

    def test_low_confidence_edit_keeps_alternatives(self):
        test_low_confidence_edit_keeps_alternatives()

    def test_validation_catches_invalid_span(self):
        test_validation_catches_invalid_span()

    def test_view_serializes_to_json_round_trip(self):
        test_view_serializes_to_json_round_trip()
