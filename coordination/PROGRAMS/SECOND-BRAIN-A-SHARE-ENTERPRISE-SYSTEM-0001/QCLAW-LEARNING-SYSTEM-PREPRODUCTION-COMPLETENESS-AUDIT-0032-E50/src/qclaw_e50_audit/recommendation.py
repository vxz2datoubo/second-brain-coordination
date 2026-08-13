"""Risk-critical readiness recommendation.

R2 mandatory: recommendation must be risk-critical, not a naive count of
PARTIAL dimensions. Any unresolved critical authority/provenance/privacy/
stale-recall/skill-promotion gap => NOT_READY. Only when every critical
gate is PASS may we consider READY_FOR_BOUNDED_REAL_SOURCE_PILOT (never
READY_FOR_PRODUCTION_CANDIDATE_LEARNING without GPT acceptance).
"""
from __future__ import annotations

from .evidence_matrix import DimensionVerdict, VERDICT_PASS


NOT_READY = "NOT_READY"
READY_FOR_BOUNDED_REAL_SOURCE_PILOT = "READY_FOR_BOUNDED_REAL_SOURCE_PILOT"
READY_FOR_PRODUCTION_CANDIDATE_LEARNING = "READY_FOR_PRODUCTION_CANDIDATE_LEARNING"


def recommend(dimensions: list[DimensionVerdict]) -> dict:
    critical = [d for d in dimensions if d.critical]
    non_pass_critical = [d for d in critical if d.verdict != VERDICT_PASS]

    blockers: list[str] = []
    for d in non_pass_critical:
        blockers.append(f"{d.dimension}({d.verdict}): {d.rationale}")

    # A critical PARTIAL/FAIL/BLOCKED gate is a release blocker, full stop.
    if non_pass_critical:
        recommendation = NOT_READY
        summary = (
            f"{len(non_pass_critical)} critical gate(s) not PASS: "
            + "; ".join(d.dimension for d in non_pass_critical)
        )
    else:
        # All critical gates PASS. Bounded real-source pilot is the highest
        # level QCLAW may recommend WITHOUT GPT acceptance of E50.
        recommendation = READY_FOR_BOUNDED_REAL_SOURCE_PILOT
        summary = (
            "All critical authority/provenance/privacy/stale-recall/"
            "skill-promotion gates PASS. Ready for a BOUNDED real-source "
            "pilot ONLY after GPT independently accepts E50."
        )

    # Production candidate learning is never self-issued.
    never_production = (
        "READY_FOR_PRODUCTION_CANDIDATE_LEARNING requires GPT acceptance of E50 "
        "and a separate production-authority gate; never self-issued by QCLAW."
    )

    return {
        "recommendation": recommendation,
        "summary": summary,
        "blockers": blockers,
        "critical_pass_count": len(critical) - len(non_pass_critical),
        "critical_total": len(critical),
        "production_learning_note": never_production,
    }
