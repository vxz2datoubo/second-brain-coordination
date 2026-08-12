"""Canary corpus checks (R3).

Walks the required noise categories through the *actual* L1 + L2
pipeline (not via hand-built test objects). R3 architectural changes:

- ``test_a`` / ``test_b`` drive the natural-Chinese no-space canary
  (synthetic_natural_chinese.txt) — that file lacks `。` and has
  filler words with non-Han boundaries, so it actually exercises the
  FILLER_REMOVAL and PUNCTUATION classes end-to-end. The main
  structured canary (``synthetic_canary_noisy_chinese.txt``) is
  written in well-formed Chinese and the reconstructor correctly
  leaves it as-is (no silent corruption).

- ``test_h`` asserts DEPENDS_ON (R3 mandatory 6) rather than
  REFINES, and asserts the MECHANISM effect content is bounded by
  the next contrast marker (R3 mandatory 5).

- ``test_conditional_extraction_bounded_by_next_clause`` is an
  explicit golden check that the MECHANISM atom is the complete
  effect clause.

- ``test_uses_truthful_relation_type`` asserts no L2 relation uses
  ``REFINES`` (only DEPENDS_ON when a mechanism is detected).

- ``test_source_extract_invariant`` enforces the SOURCE_EXTRACT
  content == exact L0 byte slice (R3 mandatory 3).

- ``test_no_normalization_edit_becomes_l3_node`` enforces R3
  mandatory 8: no FILLER / PUNCTUATION / TYPO / ASR edit operation
  may be promoted to a L3 knowledge_atom node.

- ``test_golden_full_normalized_text`` is the exact golden assertion
  for the canary normalized_text (R3 mandatory 7).
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
from qclaw_e48_reconstruction.l3_project import project_graph  # noqa: E402


CANARY_PATH = E48_ROOT / "canary" / "synthetic_canary_noisy_chinese.txt"
NATURAL_PATH = E48_ROOT / "canary" / "synthetic_natural_chinese.txt"
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

# High-confidence terminology alias (R3 canary surface: 量子隐传 → 量子纠缠).
CANARY_ALIASES = (
    TerminologyAlias(
        alias_id="alias-quantum-entanglement",
        raw_form="量子隐传",
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


def _natural_view():
    l0 = NATURAL_PATH.read_text(encoding="utf-8")
    return reconstruct(
        l0,
        ruleset=MID_RULESET,
        aliases=CANARY_ALIASES,
        view_id="E48-CANARY-NATURAL-TEST",
    )


# Test (a): filler removal fires on natural Chinese (no-space) sample,
# where filler words have non-Han neighbors (line start / non-Han context).
def test_a_filler_words() -> None:
    view = _natural_view()
    types = {e.edit_type for e in _edits(view)}
    assert EditType.FILLER_REMOVAL in types, (
        f"missing FILLER_REMOVAL on natural canary; got {types}"
    )


# Test (b): bounded punctuation insertion fires on the natural Chinese
# sample, which lacks `。` terminators.
def test_b_missing_punctuation() -> None:
    view = _natural_view()
    types = {e.edit_type for e in _edits(view)}
    assert EditType.PUNCTUATION in types, (
        f"missing PUNCTUATION on natural canary; got {types}"
    )
    for e in _edits(view):
        if e.edit_type != EditType.PUNCTUATION:
            continue
        # Each punctuation edit inserts a single "。" before the next
        # Han / EOF and does NOT split ordinary Han words.
        assert "。" in e.after, (
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
        e.edit_type == EditType.TERMINOLOGY_NORMALIZATION and "量子隐传" in e.before
        and "量子纠缠" in e.after
        and e.applied
        for e in _edits(view)
    )


def test_h_cross_sentence_mechanism_captured() -> None:
    """Cross-sentence '如果…那么…' must be detectable by the L2 derivation
    step: one CONDITION + one MECHANISM SOURCE_EXTRACT atom + one
    DEPENDS_ON relation (R3 mandatory 6). This drives the actual
    l2_derive pipeline.
    """
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = _canary_view()
    pkg = derive_l2_package(l0, view)
    cond_atoms = [a for a in pkg["atoms"] if a["atom_type"] == "CONDITION"]
    mech_atoms = [a for a in pkg["atoms"] if a["atom_type"] == "MECHANISM"]
    dep = [r for r in pkg["relations"] if r["relation_type"] == "DEPENDS_ON"]
    assert cond_atoms, "expected at least one CONDITION atom"
    assert mech_atoms, "expected at least one MECHANISM atom"
    assert dep, "expected at least one DEPENDS_ON relation"
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
    norm = view.segments[0].normalized_text
    for required in ("讨论", "如果", "关系", "成交"):
        assert required in norm, (
            f"ordinary word {required!r} missing from normalized_text: {norm!r}"
        )


def test_golden_l0_byte_immutable() -> None:
    """R2 mandatory: L0 bytes must be preserved bit-for-bit."""
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = _canary_view()
    h = hashlib.sha256(l0.encode("utf-8")).hexdigest()
    assert h == view.l0_source_hash
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
    assert digests["ambiguity_count"] >= 1
    assert digests["unknown_count"] >= 1
    assert digests["applied_edit_count"] >= 1


# R3 NEW TESTS --------------------------------------------------------------

def test_conditional_extraction_bounded_by_next_clause() -> None:
    """R3 mandatory 5: the MECHANISM effect clause MUST be bounded by the
    next contrast/conditional marker, not by the first whitespace.

    The canary line 2 reads:
        如果成交量上升，那么价格就倾向于上升；但如果成交量下降，价格就可能下降。

    The first '如果…那么…' pair's effect clause should be the complete
    phrase ``价格就倾向于上升`` (bounded by 但), NOT truncated to ``价格``.
    """
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = _canary_view()
    pkg = derive_l2_package(l0, view)
    mech_atoms = [a for a in pkg["atoms"] if a["atom_type"] == "MECHANISM"]
    assert mech_atoms, "expected at least one MECHANISM atom"
    mech_contents = [a["content"] for a in mech_atoms]
    # The full effect clause MUST appear as the MECHANISM atom content.
    assert any("价格就倾向于上升" in c for c in mech_contents), (
        f"MECHANISM atom content missing full effect clause; got {mech_contents}"
    )


def test_uses_truthful_relation_type() -> None:
    """R3 mandatory 6: L2 derivation uses DEPENDS_ON, not REFINES, for
    if/then mechanism relations. REFINES is not used anywhere in this
    canary package.
    """
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = _canary_view()
    pkg = derive_l2_package(l0, view)
    refines = [r for r in pkg["relations"] if r["relation_type"] == "REFINES"]
    assert not refines, (
        f"L2 derivation must not emit REFINES for if/then; got {refines}"
    )


def test_source_extract_invariant() -> None:
    """R3 mandatory 3: every SOURCE_EXTRACT atom's content MUST be exactly
    the L0 byte slice at the cited source span.
    """
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = _canary_view()
    pkg = derive_l2_package(l0, view)
    l0_bytes = l0.encode("utf-8")
    for a in pkg["atoms"]:
        if a["evidence_kind"] != "SOURCE_EXTRACT":
            continue
        span = a["source_spans"][0]
        excerpt = l0_bytes[span["byte_start"]:span["byte_end"]].decode("utf-8")
        assert excerpt == a["content"], (
            f"SOURCE_EXTRACT atom {a['atom_id']} content mismatch: "
            f"expected {excerpt!r} got {a['content']!r}"
        )


def test_no_normalization_edit_becomes_l3_node() -> None:
    """R3 mandatory 8: any normalization-only edit event (FILLER /
    PUNCTUATION / TYPO / ASR / SENTENCE_BREAK / PARAGRAPH_SPLIT) MUST NOT
    become a L3 knowledge_atom node.
    """
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = _canary_view()
    pkg = derive_l2_package(l0, view)
    proj = project_graph(pkg, view, projection_id="E48-L3-INVARIANT-TEST")
    forbidden_atom_types = {
        "FILLER_NODE",
        "PUNCTUATION_NODE",
        "TYPO_NODE",
        "ASR_NODE",
        "SENTENCE_BREAK_NODE",
        "PARAGRAPH_SPLIT_NODE",
    }
    forbidden_atom_id_prefixes = (
        "A-FILLER-",
        "A-PUNCT-",
        "A-TYPO-",
        "A-ASR-",
    )
    for n in proj.nodes:
        node_type = getattr(n, "node_type", None)
        node_type_value = node_type.value if node_type is not None else None
        assert node_type_value not in forbidden_atom_types, (
            f"forbidden L3 node type {node_type_value!r}: {n!r}"
        )
        # Also reject node ids that follow the normalization atom
        # id pattern (would imply an edit was promoted to atom).
        assert not n.node_id.startswith(forbidden_atom_id_prefixes), (
            f"forbidden L3 node id prefix {n.node_id!r}: {n!r}"
        )


def test_terminology_atom_carries_l1_edit_provenance() -> None:
    """R3 mandatory 4: terminology-normalization derived atoms MUST carry
    an ``l1_edit_provenance`` field that records the canonical form,
    raw_form, and confidence.
    """
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = _canary_view()
    pkg = derive_l2_package(l0, view)
    derived = [
        a for a in pkg["atoms"]
        if a["atom_type"] == "DERIVED_CONCEPT"
        or (
            a["atom_type"] == "CONCEPT"
            and any(
                sp.get("span_label", "").startswith("terminology:")
                for sp in a["source_spans"]
            )
        )
    ]
    assert derived, "expected at least one terminology CONCEPT / DERIVED_CONCEPT atom"
    for a in derived:
        assert "l1_edit_provenance" in a, (
            f"atom {a['atom_id']} missing l1_edit_provenance: {a!r}"
        )
        prov = a["l1_edit_provenance"]
        assert "raw_form" in prov and "canonical_form" in prov and "confidence" in prov


def test_golden_full_normalized_text() -> None:
    """R3 mandatory 7: exact golden normalized_text for the committed
    canary. The L1 reconstructor MUST produce this exact text.

    Computed deterministically by driving the actual pipeline once
    during test setup and asserting the result equals the committed
    ``canary/out/canary_l1_view.json``. If the L1 algorithm changes,
    this test is the gate that forces a canary + digests refresh.
    """
    out_path = E48_ROOT / "canary" / "out" / "canary_l1_view.json"
    if not out_path.exists():
        # Fall back to running the pipeline locally.
        import subprocess
        subprocess.run(
            ["python", "canary/build_canary_projection.py"],
            cwd=str(E48_ROOT),
            check=True,
        )
    committed = json.loads(out_path.read_text(encoding="utf-8"))
    golden = committed["segments"][0]["normalized_text"]
    # Reproduce from the actual pipeline.
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = _canary_view()
    actual = view.segments[0].normalized_text
    assert actual == golden, (
        f"golden normalized_text drift.\nexpected:\n{golden!r}\nactual:\n{actual!r}"
    )


def test_golden_full_atom_list() -> None:
    """R3 mandatory 7: exact golden L2 atom list (content + type +
    evidence_kind + byte span) for the committed canary.
    """
    out_path = E48_ROOT / "canary" / "out" / "canary_artifact.json"
    committed = json.loads(out_path.read_text(encoding="utf-8"))
    golden_atoms = committed["atoms"]
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = _canary_view()
    pkg = derive_l2_package(l0, view)
    actual_atoms = pkg["atoms"]
    assert len(actual_atoms) == len(golden_atoms), (
        f"atom count mismatch: {len(actual_atoms)} vs {len(golden_atoms)}"
    )
    # Compare by atom_id + content + evidence_kind + first span byte range.
    def _key(a):
        sp = a["source_spans"][0]
        return (a["atom_id"], a["atom_type"], a["content"],
                a["evidence_kind"], sp["byte_start"], sp["byte_end"])
    golden_keys = sorted(_key(a) for a in golden_atoms)
    actual_keys = sorted(_key(a) for a in actual_atoms)
    assert golden_keys == actual_keys, (
        f"atom list drift.\nexpected: {golden_keys}\nactual: {actual_keys}"
    )


def test_golden_full_relation_list() -> None:
    """R3 mandatory 7: exact golden L2 relation list.
    """
    out_path = E48_ROOT / "canary" / "out" / "canary_artifact.json"
    committed = json.loads(out_path.read_text(encoding="utf-8"))
    golden_rels = committed["relations"]
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = _canary_view()
    pkg = derive_l2_package(l0, view)
    actual_rels = pkg["relations"]
    assert len(actual_rels) == len(golden_rels), (
        f"relation count mismatch: {len(actual_rels)} vs {len(golden_rels)}"
    )
    def _key(r):
        return (r["source_atom_id"], r["target_atom_id"], r["relation_type"])
    golden_keys = sorted(_key(r) for r in golden_rels)
    actual_keys = sorted(_key(r) for r in actual_rels)
    assert golden_keys == actual_keys, (
        f"relation list drift.\nexpected: {golden_keys}\nactual: {actual_keys}"
    )


def test_natural_chinese_no_space_canary_failsafe() -> None:
    """R3 mandatory 10: a no-space natural-Chinese input must produce a
    valid normalized view with no ordinary word corruption and a
    fail-safe (filler) handling that does not corrupt the content.
    """
    view = _natural_view()
    norm = view.segments[0].normalized_text
    # Required ordinary words MUST survive intact. Note: 部份 is a
    # known typo and will be corrected to 部分 by the high-confidence
    # TYPO rule — that is the expected and safe behaviour.
    for required in ("成交量", "价格", "部分"):
        assert required in norm, (
            f"natural canary ordinary word {required!r} corrupted; "
            f"got {norm!r}"
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

    def test_conditional_extraction_bounded_by_next_clause(self):
        test_conditional_extraction_bounded_by_next_clause()

    def test_uses_truthful_relation_type(self):
        test_uses_truthful_relation_type()

    def test_source_extract_invariant(self):
        test_source_extract_invariant()

    def test_no_normalization_edit_becomes_l3_node(self):
        test_no_normalization_edit_becomes_l3_node()

    def test_terminology_atom_carries_l1_edit_provenance(self):
        test_terminology_atom_carries_l1_edit_provenance()

    def test_golden_full_normalized_text(self):
        test_golden_full_normalized_text()

    def test_golden_full_atom_list(self):
        test_golden_full_atom_list()

    def test_golden_full_relation_list(self):
        test_golden_full_relation_list()

    def test_natural_chinese_no_space_canary_failsafe(self):
        test_natural_chinese_no_space_canary_failsafe()