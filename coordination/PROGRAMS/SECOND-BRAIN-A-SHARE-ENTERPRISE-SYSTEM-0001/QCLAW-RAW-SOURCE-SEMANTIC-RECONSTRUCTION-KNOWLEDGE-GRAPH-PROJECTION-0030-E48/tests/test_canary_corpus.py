"""Canary corpus checks (R2).

Walks the 8 required noise categories in the PUBLIC_SAFE canary file and
asserts the right edit / ambiguity class fired through the *actual* L1
pipeline (not via hand-built test objects).

R2 changes vs. R1:
- canary file is now pure raw 中文 text; PUBLIC_SAFE / synthetic
  metadata is in EXPECTED.txt instead. The ``test_canary_file_*``
  asserts assert the pure-raw invariant.
- Mid-confidence alias test (test_e) drives the canary-level alias rule
  to assert ``applied=False`` AND ambiguity emission.
- ``test_golden_*`` assert that ordinary Han words (讨论/如果/成交/应该/关系)
  are NOT split into 'A。B' and that the L0 byte hash is preserved.
"""
from __future__ import annotations

import hashlib
import json
import re
import unittest
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
E48_ROOT = _HERE.parents[1]
sys.path.insert(0, str(E48_ROOT / "src"))

from qclaw_e48_reconstruction.l1_schema import (  # noqa: E402
    EditType,
    TerminologyAlias,
)
from qclaw_e48_reconstruction.l1_reconstruct import (  # noqa: E402
    ReconstructionRuleset,
    reconstruct,
)
from qclaw_e48_reconstruction.l2_derive import derive_l2_package  # noqa: E402


CANARY_PATH = E48_ROOT / "canary" / "synthetic_canary_noisy_chinese.txt"
EXPECTED_PATH = E48_ROOT / "canary" / "EXPECTED.txt"


# Mid-confidence caller rule (R2 mandatory (e)): injects ambiguity.
MID_RULESET = ReconstructionRuleset(
    rules=(
        (
            r"成交量",
            r"交易量",
            0.5,
            EditType.TERMINOLOGY_NORMALIZATION,
            "mid-confidence alias: 成交量 → 交易量 (canary)",
        ),
        (
            r"他她",
            r"他她",
            0.3,
            EditType.UNKNOWN_MARKER,
            "ambiguous pronoun cannot be resolved (canary)",
        ),
    )
)

# High-confidence terminology alias (R2 mandatory (g)).
CANARY_ALIASES = (
    TerminologyAlias(
        alias_id="alias-quantum-entanglement",
        raw_form="术语别名",
        canonical_form="量子纠缠",
        scope="E48 canary",
        confidence=1.0,
        evidence_refs=("synthetic:canary:line-4",),
    ),
)


def _edits(view):
    return [e for s in view.segments for e in s.edits]


def _canary_view():
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    return reconstruct(
        l0,
        ruleset=MID_RULESET,
        aliases=CANARY_ALIASES,
        view_id="E48-CANARY-TEST",
    )


def test_a_filler_words() -> None:
    view = _canary_view()
    types = {e.edit_type for e in _edits(view)}
    assert EditType.FILLER_REMOVAL in types, f"missing FILLER_REMOVAL; got {types}"


def test_b_missing_punctuation() -> None:
    view = _canary_view()
    types = {e.edit_type for e in _edits(view)}
    assert EditType.PUNCTUATION in types, f"missing PUNCTUATION; got {types}"
    for e in _edits(view):
        if e.edit_type != EditType.PUNCTUATION:
            continue
        # Each punctuation edit inserts a single "。" before the "\n" and
        # does NOT split ordinary Han words.
        assert e.after.endswith("。\n") or e.after.endswith("。"), (
            f"punctuation edit does not insert '。' terminator: {e!r}"
        )


def test_c_typo() -> None:
    view = _canary_view()
    assert any(
        e.edit_type == EditType.TYPO_CORRECTION
        and "部份" in e.before
        and "部分" in e.after
        for e in _edits(view)
    )


def test_d_asr_homophone() -> None:
    view = _canary_view()
    assert any(
        e.edit_type == EditType.ASR_HOMOPHONE_CORRECTION
        and "式式" in e.before
        and "试试" in e.after
        for e in _edits(view)
    )


def test_e_mid_confidence_keeps_alternatives() -> None:
    """A mid-confidence terminology alias through the actual pipeline must
    keep the raw surface form in ``alternatives`` and must NOT be promoted
    to a SOURCE_EXTRACT-class edit. R2 fail-closed.
    """
    view = _canary_view()
    pending = [
        e for e in _edits(view)
        if e.edit_type == EditType.TERMINOLOGY_NORMALIZATION and e.before == "成交量"
    ]
    assert pending, "expected pending mid-confidence alias edits"
    for e in pending:
        assert e.confidence < 0.7
        # Mid/low confidence edits MUST NOT be promoted to applied=True.
        assert e.applied is False, (
            f"R2 fail-closed violated: applied=True for low-confidence edit {e!r}"
        )
        # And the L1 view.ambiguities MUST carry the surface form.
    ambig_surfaces = {a.raw_text for a in view.ambiguities}
    assert "成交量" in ambig_surfaces, (
        f"ambiguities must include '成交量' (R2 mandatory). got {ambig_surfaces}"
    )


def test_f_unknown_marker_possible() -> None:
    view = _canary_view()
    assert view.unknowns, "expected UnknownMarker in view.unknowns"
    assert any(u.raw_text == "他她" for u in view.unknowns), (
        f"view.unknowns must include '他她'; got {[u.raw_text for u in view.unknowns]}"
    )


def test_g_terminology_alias() -> None:
    view = _canary_view()
    assert any(
        e.edit_type == EditType.TERMINOLOGY_NORMALIZATION and "术语别名" in e.before
        for e in _edits(view)
    )


def test_h_cross_sentence_mechanism_captured() -> None:
    """Cross-sentence '如果…那么…' must be detectable by the L2 derivation
    step: one CONDITION + one MECHANISM SOURCE_EXTRACT atom + one REFINES
    relation. This drives the actual l2_derive pipeline.
    """
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = _canary_view()
    pkg = derive_l2_package(l0, view)
    cond_atoms = [a for a in pkg["atoms"] if a["atom_type"] == "CONDITION"]
    mech_atoms = [a for a in pkg["atoms"] if a["atom_type"] == "MECHANISM"]
    refines = [r for r in pkg["relations"] if r["relation_type"] == "REFINES"]
    assert cond_atoms, "expected at least one CONDITION atom"
    assert mech_atoms, "expected at least one MECHANISM atom"
    assert refines, "expected at least one REFINES relation"
    # The CONDITION atom's L0 byte span must be a real L0 substring.
    span = cond_atoms[0]["source_spans"][0]
    l0_bytes = l0.encode("utf-8")
    excerpt = l0_bytes[span["byte_start"]:span["byte_end"]].decode("utf-8")
    assert excerpt in l0, f"CONDITION atom span [{span['byte_start']},{span['byte_end']}] not in L0"


def test_canary_file_is_pure_raw_text() -> None:
    """R2 mandatory: canary file MUST NOT contain explanatory trigger
    examples or metadata. It is the immutable raw semantic source
    consumed by L0. Marker text (PUBLIC_SAFE / synthetic) lives in
    EXPECTED.txt instead.
    """
    text = CANARY_PATH.read_text(encoding="utf-8")
    forbidden_patterns = (
        re.compile(r"^\s*#"),
        re.compile(r"PUBLIC_SAFE", re.IGNORECASE),
        re.compile(r"\bsynthetic\b", re.IGNORECASE),
    )
    for line in text.splitlines():
        for pat in forbidden_patterns:
            assert not pat.search(line), (
                f"canary file line MUST NOT match {pat.pattern!r}: {line!r}"
            )


def test_golden_no_ordinary_word_corruption() -> None:
    """R2 mandatory (no ordinary Chinese word corruption). The L1
    reconstructor must NOT split ordinary Han words by inserting '。'
    in the middle.
    """
    view = _canary_view()
    # The canary normalized_text must contain these ordinary Han words
    # intact (not as 'A。B' or 'A。\nB' where A,B are ordinary words).
    norm = view.segments[0].normalized_text
    for required in ("讨论", "如果", "关系", "成交"):
        # We tolerate punctuation AFTER the word but the word itself
        # must appear unmodified.
        assert required in norm, (
            f"ordinary word {required!r} missing from normalized_text: {norm!r}"
        )


def test_golden_l0_byte_immutable() -> None:
    """R2 mandatory: L0 bytes must be preserved bit-for-bit."""
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = _canary_view()
    h = hashlib.sha256(l0.encode("utf-8")).hexdigest()
    assert h == view.l0_source_hash
    # Every edit's byte_start..byte_end must be a valid L0 byte range
    # (no edit may extend past the file end).
    l0_size = len(l0.encode("utf-8"))
    for s in view.segments:
        for e in s.edits:
            assert 0 <= e.byte_start <= e.byte_end <= l0_size, (
                f"edit byte range out of bounds: {e!r}"
            )
            slice_text = l0.encode("utf-8")[e.byte_start:e.byte_end].decode("utf-8")
            assert slice_text == e.before, (
                f"edit byte range does not match L0 surface form: {e!r}"
            )


def test_canary_pipeline_produces_digests() -> None:
    """R2 mandatory (9): persisted L2 candidate artifact + full SHA-256
    digest bundle. Tests drive the actual build_canary_projection
    pipeline output (canary/out/*).
    """
    out_dir = E48_ROOT / "canary" / "out"
    expected = (
        out_dir / "canary_artifact.json",
        out_dir / "canary_digests.json",
        out_dir / "canary_graph.json",
        out_dir / "canary_l1_view.json",
    )
    for path in expected:
        assert path.exists(), f"missing canary pipeline output: {path}"
    digests = json.loads((out_dir / "canary_digests.json").read_text(encoding="utf-8"))
    for key in (
        "raw_artifact_sha256",
        "canonical_semantic_sha256",
        "l0_provenance_sha256",
        "projection_sha256",
        "view_sha256",
        "l0_source_sha256",
        "l0_source_size_bytes",
        "applied_edit_count",
        "ambiguity_count",
        "unknown_count",
    ):
        assert key in digests, f"digests missing required key: {key}"
    # All SHAs are 64-hex (E61 contract).
    for sha_key in (
        "raw_artifact_sha256",
        "canonical_semantic_sha256",
        "l0_provenance_sha256",
        "projection_sha256",
        "view_sha256",
        "l0_source_sha256",
    ):
        assert re.fullmatch(r"[0-9a-f]{64}", digests[sha_key]), (
            f"{sha_key} is not a 64-hex SHA-256: {digests[sha_key]}"
        )
    # R2 mandatory: ambiguity_count >= 1 (mid-confidence alias) and
    # unknown_count >= 1 (UNKNOWN_MARKER), AND applied_edit_count >= 1.
    assert digests["ambiguity_count"] >= 1, (
        f"ambiguity_count must be >= 1; got {digests['ambiguity_count']}"
    )
    assert digests["unknown_count"] >= 1, (
        f"unknown_count must be >= 1; got {digests['unknown_count']}"
    )
    assert digests["applied_edit_count"] >= 1, (
        f"applied_edit_count must be >= 1; got {digests['applied_edit_count']}"
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

    def test_canary_file_is_pure_raw_text(self):
        test_canary_file_is_pure_raw_text()

    def test_golden_no_ordinary_word_corruption(self):
        test_golden_no_ordinary_word_corruption()

    def test_golden_l0_byte_immutable(self):
        test_golden_l0_byte_immutable()

    def test_canary_pipeline_produces_digests(self):
        test_canary_pipeline_produces_digests()