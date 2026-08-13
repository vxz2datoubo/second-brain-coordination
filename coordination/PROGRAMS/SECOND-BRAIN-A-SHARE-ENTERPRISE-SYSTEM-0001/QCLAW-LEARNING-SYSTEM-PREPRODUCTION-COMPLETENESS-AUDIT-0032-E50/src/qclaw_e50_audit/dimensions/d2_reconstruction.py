"""D2 audit: semantic reconstruction across article/ASR/chat/OCR.

Canonical implementation audited:
- qclaw_e48_foundation.l1_reconstruct.reconstruct  (E48 R3/R4 foundation)
- qclaw_e48_foundation.l1_reconstruct.ReconstructionRuleset

E48 was accepted as foundation credit only. We audit:
- ASR / OCR / chat / article noise tolerance
- ambiguity/UNKNOWN fail-closed
- ordinary Chinese words not corrupted
"""
from __future__ import annotations

from ..canonical import access
from ..evidence_matrix import DimensionVerdict, Evidence, VERDICT_PASS, VERDICT_PARTIAL, VERDICT_FAIL

access.setup_import_path()

from qclaw_e48_foundation.l1_reconstruct import reconstruct, ReconstructionRuleset  # type: ignore  # noqa: E402
from qclaw_e48_foundation.l1_schema import EditType  # type: ignore  # noqa: E402


def _check(name, desc, ok, detail=""):
    return Evidence(check_id=name, description=desc, passed=bool(ok), detail=detail)


def _normalized_text(view) -> str:
    return "".join(seg.normalized_text for seg in view.segments)


def run() -> DimensionVerdict:
    evidence: list[Evidence] = []

    # 1. Clean article Chinese — no edits needed
    clean = "今天我们来讨论一下成交量和价格的关系。"
    view = reconstruct(clean)
    norm = _normalized_text(view)
    evidence.append(_check(
        "d2.clean_article_preserved",
        "E48 reconstruct on clean article Chinese — words preserved",
        all(w in norm for w in ["讨论", "关系", "成交量", "价格"]),
        detail=f"normalized={norm}",
    ))

    # 2. ASR filler at line start — should be removed without corrupting
    asr = "呃，今天我们来讨论一下成交量和价格的关系。"
    view = reconstruct(asr)
    norm = _normalized_text(view)
    evidence.append(_check(
        "d2.asr_filler_removed",
        "E48 reconstruct removes ASR filler at line start",
        "呃" not in norm and "今天我们来讨论" in norm,
        detail=f"normalized={norm}",
    ))

    # 3. OCR typo 部份 -> 部分 — high-confidence correction
    ocr = "这是部份人的常见观点。成交量上升。"
    view = reconstruct(ocr)
    norm = _normalized_text(view)
    evidence.append(_check(
        "d2.ocr_typo_corrected",
        "E48 reconstruct corrects OCR typo 部份 -> 部分",
        "部份" not in norm and "部分" in norm,
        detail=f"normalized={norm}",
    ))

    # 4. Mid-confidence alias must NOT silently overwrite L0
    ruleset = ReconstructionRuleset(rules=(
        (r"成交量", "交易量", 0.5, EditType.TERMINOLOGY_NORMALIZATION, "caller rule"),
    ))
    sample = "如果成交量上升，价格上升。"
    view = reconstruct(sample, ruleset=ruleset)
    norm = _normalized_text(view)
    evidence.append(_check(
        "d2.mid_confidence_alias_fail_closed",
        "Mid-confidence alias does NOT silently alter normalized_text",
        "成交量" in norm,
        detail=f"normalized={norm}, ambiguities={len(view.ambiguities)}",
    ))

    # 5. UNKNOWN marker (low-confidence) is recorded as UnknownMarker
    chat = "他她在会议上发言。"
    ruleset2 = ReconstructionRuleset(rules=(
        (r"他她", "他她", 0.3, EditType.UNKNOWN_MARKER, "low-confidence pronoun"),
    ))
    view = reconstruct(chat, ruleset=ruleset2)
    norm = _normalized_text(view)
    evidence.append(_check(
        "d2.unknown_marker_recorded",
        "UNKNOWN marker is recorded in view.unknowns",
        len(view.unknowns) > 0,
        detail=f"unknown_count={len(view.unknowns)}",
    ))
    evidence.append(_check(
        "d2.unknown_marker_fail_closed",
        "UNKNOWN marker does not silently alter normalized_text",
        "他她" in norm,
        detail=f"normalized={norm}",
    ))

    # 6. Cross-sentence mechanism: both if/then clauses preserved
    mechanism = "如果成交量上升，那么价格就倾向于上升。但如果成交量下降，价格就可能下降。"
    view = reconstruct(mechanism)
    norm = _normalized_text(view)
    evidence.append(_check(
        "d2.mechanism_full_clauses_preserved",
        "Cross-sentence mechanism preserves both if/then clauses",
        ("成交量上升" in norm and "价格就倾向于上升" in norm
         and "成交量下降" in norm and "价格就可能下降" in norm),
        detail=f"len={len(norm)}",
    ))

    # 7. Determinism: same input -> same view_sha256
    v1 = reconstruct("今天我们来讨论一下成交量和价格的关系。")
    v2 = reconstruct("今天我们来讨论一下成交量和价格的关系。")
    evidence.append(_check(
        "d2.deterministic_view_sha",
        "E48 reconstruct is deterministic (same L0 -> same view_sha256)",
        v1.view_sha256 == v2.view_sha256 and len(v1.view_sha256) == 64,
        detail=f"sha={v1.view_sha256[:16]}...",
    ))

    passed = sum(1 for e in evidence if e.passed)
    total = len(evidence)
    if passed == total:
        verdict = VERDICT_PASS
    elif passed >= total - 1:
        verdict = VERDICT_PARTIAL
    else:
        verdict = VERDICT_FAIL
    rationale = f"{passed}/{total} reconstruction gates passed against E48 canonical foundation."

    return DimensionVerdict(
        dimension="D2",
        title="Semantic reconstruction across article/ASR/chat/OCR",
        verdict=verdict,
        rationale=rationale,
        evidence=evidence,
        critical=False,
        notes="E48 R4 was accepted as foundation credit only. We audit that its reconstruction behavior holds across heterogeneous inputs.",
    )