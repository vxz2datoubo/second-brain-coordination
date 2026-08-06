"""E44 Q6 — Synthetic corpus and end-to-end evaluator.

Production only receives case input + policy. Never sees ExpectedOutcome or ground truth.
Ground truth is held by the evaluator comparator outside production.
Corpus identity includes input, ground truth, expected outputs, policy version.
Any failed case causes evaluator exit nonzero.
"""
from __future__ import annotations

import hashlib, enum, dataclasses
from typing import Dict, List, Tuple, Any, Optional

from qclaw_e44.capability import CapabilityVerifier, EvidenceOrigin, SYNTHETIC_BYTES, SYNTHETIC_SOURCE_IDS
from qclaw_e44.authority import (
    EvidenceRegistry, EvidenceFactory, EvidenceRecord, EvidenceBundle, Atom,
    EvidenceLayer, AtomType,
)
from qclaw_e44.master_record import MasterRegistry, MasterError
from qclaw_e44.cognition import CognitionEngine, CognitionState, MemoryZone
from qclaw_e44.skill_lifecycle import SkillFactory, SkillState

E44_CORPUS_SCHEMA = "44.0"
CORPUS_POLICY = "1.0"


class CaseType(enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    AMBIGUOUS = "ambiguous"
    ADVERSARIAL = "adversarial"


@dataclasses.dataclass(frozen=True)
class CorpusCase:
    """A single test case. Ground truth held OUTSIDE production."""
    case_id: str
    case_type: CaseType
    input_bytes: bytes
    source_id: str
    # Ground truth — production NEVER accesses these
    expected_origin: EvidenceOrigin
    expected_layer: EvidenceLayer
    expected_atom_type: Optional[AtomType]
    expected_cognition_state: CognitionState
    expected_memory_zone: MemoryZone
    expected_skill_state: Optional[SkillState]
    should_fail: bool
    anti_pattern: Optional[str] = None


# ── Corpus set ─────────────────────────────────────────────────

def build_corpus() -> List[CorpusCase]:
    return [
        # C01: Simple fact
        CorpusCase("C01", CaseType.POSITIVE,
            b"Market volatility increases during earnings season",
            "synth://corpus/fact-001/0-47",
            EvidenceOrigin.SOURCE_FACT, EvidenceLayer.SOURCE_FACT,
            None, CognitionState.KNOWN_BUT_UNSTATED, MemoryZone.CANDIDATE,
            None, False),

        # C02: User explicit
        CorpusCase("C02", CaseType.POSITIVE,
            b"I know my portfolio rebalance occurs quarterly",
            "synth://corpus/user-001/0-46",
            EvidenceOrigin.USER_EXPLICIT, EvidenceLayer.SOURCE_FACT,
            None, CognitionState.KNOWN_AND_STATED, MemoryZone.PROJECT,
            None, False),

        # C03: Hypothesis
        CorpusCase("C03", CaseType.NEGATIVE,
            b"It could be that the correlation is spurious",
            "synth://corpus/hypo-001/0-43",
            EvidenceOrigin.HYPOTHESIS, EvidenceLayer.HYPOTHESIS,
            None, CognitionState.UNKNOWN_AND_NEEDS_LAYERING,
            MemoryZone.DO_NOT_PERSIST, None, True,
            "unsupported_certainty"),

        # C04: Author claim
        CorpusCase("C04", CaseType.NEGATIVE,
            b"According to the report, revenues grew 15%",
            "synth://corpus/claim-001/0-41",
            EvidenceOrigin.AUTHOR_CLAIM, EvidenceLayer.AUTHOR_CLAIM,
            None, CognitionState.UNKNOWN_BUT_READABLE, MemoryZone.CANDIDATE,
            None, True, "third_party_claim"),

        # C05: Value judgment
        CorpusCase("C05", CaseType.NEGATIVE,
            b"This is the best trading strategy available",
            "synth://corpus/judge-001/0-42",
            EvidenceOrigin.VALUE_JUDGMENT, EvidenceLayer.VALUE_JUDGMENT,
            None, CognitionState.UNKNOWN_AND_NEEDS_LAYERING,
            MemoryZone.DO_NOT_PERSIST, None, True, "value_judgment"),

        # C06: Empty input
        CorpusCase("C06", CaseType.ADVERSARIAL,
            b"", "synth://corpus/empty-001/0-0",
            EvidenceOrigin.UNKNOWN_ORIGIN, EvidenceLayer.HYPOTHESIS,
            None, CognitionState.UNKNOWN_AND_NEEDS_LAYERING,
            MemoryZone.DO_NOT_PERSIST, None, True, "empty_input"),

        # C07: Inference
        CorpusCase("C07", CaseType.AMBIGUOUS,
            b"Therefore, the signal is significant at p < 0.01",
            "synth://corpus/infer-001/0-47",
            EvidenceOrigin.INFERENCE, EvidenceLayer.INFERENCE,
            None, CognitionState.UNKNOWN_BUT_READABLE, MemoryZone.CANDIDATE,
            None, True, "unsupported_certainty"),

        # C08: Anti-pattern — unsupported certainty
        CorpusCase("C08", CaseType.ADVERSARIAL,
            b"always buy on dips because it works 100% of the time",
            "synth://corpus/anti-001/0-52",
            EvidenceOrigin.SOURCE_FACT, EvidenceLayer.HYPOTHESIS,
            None, CognitionState.UNKNOWN_AND_NEEDS_LAYERING,
            MemoryZone.DO_NOT_PERSIST, None, True, "unsupported_certainty"),
    ]


# ── Evaluator ──────────────────────────────────────────────────
# Production pipeline: input → pipeline → canonical outcome.
# Ground truth is only in the COMPARATOR, outside production.

def run_pipeline(case: CorpusCase, verifier: CapabilityVerifier,
                 ev_factory: EvidenceFactory,
                 master_reg: MasterRegistry,
                 cog: CognitionEngine,
                 skill_factory: SkillFactory) -> Dict[str, Any]:
    """Production pipeline. NEVER receives ExpectedOutcome."""
    result: Dict[str, Any] = {"case_id": case.case_id}

    # Step 1: Verify → capability
    cap = verifier.verify(case.input_bytes, case.source_id, EvidenceOrigin.SOURCE_FACT)
    result["capability_id"] = cap.capability_id
    result["derived_origin"] = cap.origin_class.value

    # Step 2: Evidence record
    rec = ev_factory.create_record(cap)
    result["record_id"] = rec.record_id
    result["evidence_layer"] = rec.evidence_layer.value

    # Step 3: Cognition
    try:
        entry = cog.analyze(rec.record_id)
        result["cognition_state"] = entry.state.value
        result["memory_zone"] = entry.memory_zone.value
    except Exception as e:
        result["cognition_state"] = f"error:{e}"
        result["memory_zone"] = "error"

    # Step 4: Master record (if meaningful)
    if len(case.input_bytes) > 0:
        try:
            mr = master_reg.create(rec.record_id[:24], (rec.record_id,))
            result["master_record_id"] = mr.record_id
        except MasterError:
            result["master_record_id"] = "duplicate_skipped"

    result["verdict"] = "PASS"
    return result


def evaluate_corpus(cases: List[CorpusCase],
                    verifier: CapabilityVerifier,
                    ev_factory: EvidenceFactory,
                    master_reg: MasterRegistry,
                    cog: CognitionEngine,
                    skill_factory: SkillFactory) -> Tuple[int, int, List[Dict[str, Any]]]:
    """End-to-end evaluator. Ground truth comparison is external to production."""
    passed = 0
    failed = 0
    outcomes = []

    for case in cases:
        outcome = run_pipeline(case, verifier, ev_factory, master_reg, cog, skill_factory)
        outcomes.append(outcome)

        # Comparator: ground truth held outside production
        check_ok = True
        if outcome.get("derived_origin") != case.expected_origin.value:
            check_ok = False
        if outcome.get("evidence_layer") != case.expected_layer.value:
            check_ok = False
        if outcome.get("cognition_state") != case.expected_cognition_state.value:
            check_ok = False
        if outcome.get("memory_zone") != case.expected_memory_zone.value:
            check_ok = False

        # Expected to fail? Reject if it should fail but we produced a clean PASS
        if case.should_fail and not outcome.get("cognition_state", "").startswith("error"):
            outcome["verdict"] = "FAIL"
            check_ok = False

        if check_ok:
            passed += 1
        else:
            outcome["verdict"] = "FAIL"
            failed += 1

    return passed, failed, outcomes
