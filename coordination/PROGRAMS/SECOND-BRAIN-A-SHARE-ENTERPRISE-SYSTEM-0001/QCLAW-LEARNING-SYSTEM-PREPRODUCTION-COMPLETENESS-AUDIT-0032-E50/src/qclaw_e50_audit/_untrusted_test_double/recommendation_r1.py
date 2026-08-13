"""recommendation — E50 explicit readiness recommendation.

Recommendation must be exactly one of:
  - NOT_READY
  - READY_FOR_BOUNDED_REAL_SOURCE_PILOT
  - READY_FOR_PRODUCTION_CANDIDATE_LEARNING

Rules:
  - NOT_READY: any D returns FAIL OR > 2 return PARTIAL OR D4/D8 returns PARTIAL OR D1/D6/D9/D10 returns FAIL
  - READY_FOR_BOUNDED_REAL_SOURCE_PILOT: all D1–D12 PASS or PARTIAL, no FAIL; D4/D8 ≥ PARTIAL
  - READY_FOR_PRODUCTION_CANDIDATE_LEARNING: all D1–D12 PASS; D4/D8 PASS
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .audit_runner import EvidenceMatrix, Verdict


class ReadinessRecommendation(str, Enum):
    NOT_READY = "NOT_READY"
    READY_FOR_BOUNDED_REAL_SOURCE_PILOT = "READY_FOR_BOUNDED_REAL_SOURCE_PILOT"
    READY_FOR_PRODUCTION_CANDIDATE_LEARNING = "READY_FOR_PRODUCTION_CANDIDATE_LEARNING"


@dataclass(frozen=True)
class ReadinessVerdict:
    recommendation: ReadinessRecommendation
    rationale: str
    pass_count: int
    partial_count: int
    fail_count: int


def compute_recommendation(matrix: EvidenceMatrix) -> ReadinessVerdict:
    passes = matrix.passes()
    partials = matrix.partials()
    fails = matrix.fails()

    n_pass = len(passes)
    n_partial = len(partials)
    n_fail = len(fails)

    # NOT_READY conditions
    if n_fail > 0:
        return ReadinessVerdict(
            recommendation=ReadinessRecommendation.NOT_READY,
            rationale=f"{n_fail} dimension(s) FAILED; real-source learning not safe.",
            pass_count=n_pass, partial_count=n_partial, fail_count=n_fail,
        )
    if n_partial > 2:
        return ReadinessVerdict(
            recommendation=ReadinessRecommendation.NOT_READY,
            rationale=f">{2} dimensions PARTIAL; not safe for real-source learning.",
            pass_count=n_pass, partial_count=n_partial, fail_count=n_fail,
        )

    # D4 / D8 are PARTIAL → NOT_READY
    d4 = matrix.get("D4")
    d8 = matrix.get("D8")
    if d4 and d4.verdict == Verdict.PARTIAL:
        return ReadinessVerdict(
            recommendation=ReadinessRecommendation.NOT_READY,
            rationale="D4 (cross-source mastering) PARTIAL; not safe for real-source learning.",
            pass_count=n_pass, partial_count=n_partial, fail_count=n_fail,
        )
    if d8 and d8.verdict == Verdict.PARTIAL:
        return ReadinessVerdict(
            recommendation=ReadinessRecommendation.NOT_READY,
            rationale="D8 (retrieval round-trip) PARTIAL; stale recall risk.",
            pass_count=n_pass, partial_count=n_partial, fail_count=n_fail,
        )

    # READY_FOR_PRODUCTION_CANDIDATE_LEARNING: all PASS, D4/D8 PASS
    if n_fail == 0 and n_partial == 0:
        if d4 and d4.verdict == Verdict.PASS and d8 and d8.verdict == Verdict.PASS:
            return ReadinessVerdict(
                recommendation=ReadinessRecommendation.READY_FOR_PRODUCTION_CANDIDATE_LEARNING,
                rationale="All D1-D12 PASS; D4+D8 PASS; ready for production candidate learning.",
                pass_count=n_pass, partial_count=n_partial, fail_count=n_fail,
            )

    # READY_FOR_BOUNDED_REAL_SOURCE_PILOT
    if n_fail == 0 and n_partial <= 2:
        return ReadinessVerdict(
            recommendation=ReadinessRecommendation.READY_FOR_BOUNDED_REAL_SOURCE_PILOT,
            rationale=f"All dimensions PASS or PARTIAL (≤2); bounded real-source pilot allowed with whitelist.",
            pass_count=n_pass, partial_count=n_partial, fail_count=n_fail,
        )

    return ReadinessVerdict(
        recommendation=ReadinessRecommendation.NOT_READY,
        rationale="Default NOT_READY",
        pass_count=n_pass, partial_count=n_partial, fail_count=n_fail,
    )