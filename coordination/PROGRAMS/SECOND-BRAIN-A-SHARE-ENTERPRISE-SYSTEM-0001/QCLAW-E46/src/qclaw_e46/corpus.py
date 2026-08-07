"""E46 Corpus — Synthetic inputs for end-to-end evaluator.

Production pipeline ONLY receives CorpusInput (never ground truth).
Evaluator comparator holds CorpusExpected outside production.
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import Enum


class CorpusCaseType(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    AMBIGUOUS = "AMBIGUOUS"
    ADVERSARIAL = "ADVERSARIAL"
    ANTI_PATTERN = "ANTI_PATTERN"


class ExpectedAtomType(str, Enum):
    CONCEPT = "CONCEPT"
    DEFINITION = "DEFINITION"
    MECHANISM = "MECHANISM"
    CAUSAL_CHAIN = "CAUSAL_CHAIN"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    INDICATOR = "INDICATOR"
    DATA_SOURCE = "DATA_SOURCE"
    SCOPE = "SCOPE"
    FAILURE_CONDITION = "FAILURE_CONDITION"
    VERIFICATION_METHOD = "VERIFICATION_METHOD"


@dataclass(frozen=True)
class CorpusInput:
    """Production pipeline input — NEVER contains ground truth."""
    case_id: str
    case_type: CorpusCaseType
    source_text: bytes  # Raw UTF-8 bytes
    policy_version: str = "v1.0"
    metadata: str = ""


@dataclass(frozen=True)
class CorpusExpected:
    """Evaluator-side ground truth — NEVER reaches production pipeline."""
    case_id: str
    expected_atom_count: int
    expected_atom_types: Tuple[ExpectedAtomType, ...]
    expected_confidence_band: str  # HIGH/MEDIUM/LOW/UNTRUSTED
    expected_memory_zone: str
    should_reject: bool = False
    rejection_reason: str = ""
    anti_pattern_name: str = ""


@dataclass(frozen=True)
class EvaluatorResult:
    """Result from running production through evaluator comparator."""
    case_id: str
    atom_count: int
    actual_atom_types: Tuple[str, ...]
    actual_confidence: str
    actual_memory_zone: str
    verdict: str  # "PASS" or "FAIL"
    anti_pattern: str = ""
    summary: str = ""


def build_corpus() -> Tuple[List[CorpusInput], List[CorpusExpected]]:
    """Build public-safe synthetic corpus.
    
    Production pipeline receives CorpusInput.
    Evaluator holds CorpusExpected — never passed to production.
    """
    inputs = []
    expecteds = []
    
    # C01: Positive — simple fact
    cid = "C01_simple_fact"
    inputs.append(CorpusInput(
        case_id=cid, case_type=CorpusCaseType.POSITIVE,
        source_text=b"Market orders execute at the best available price immediately.",
    ))
    expecteds.append(CorpusExpected(
        case_id=cid, expected_atom_count=1,
        expected_atom_types=(ExpectedAtomType.DEFINITION,),
        expected_confidence_band="HIGH",
        expected_memory_zone="PROJECT",
    ))
    
    # C02: User message — explicit statement
    cid = "C02_user_message"
    inputs.append(CorpusInput(
        case_id=cid, case_type=CorpusCaseType.POSITIVE,
        source_text=b"I prefer to use Python for data analysis.",
    ))
    expecteds.append(CorpusExpected(
        case_id=cid, expected_atom_count=1,
        expected_atom_types=(ExpectedAtomType.CONCEPT,),
        expected_confidence_band="HIGH",
        expected_memory_zone="CANDIDATE",  # Pre-E59: UNTRUSTED -> not GLOBAL
    ))
    
    # C03: Ambiguous
    cid = "C03_ambiguous"
    inputs.append(CorpusInput(
        case_id=cid, case_type=CorpusCaseType.AMBIGUOUS,
        source_text=b"This indicator sometimes works well.",
    ))
    expecteds.append(CorpusExpected(
        case_id=cid, expected_atom_count=1,
        expected_atom_types=(ExpectedAtomType.INDICATOR,),
        expected_confidence_band="LOW",
        expected_memory_zone="CANDIDATE",
    ))
    
    # C04: Temporal scope
    cid = "C04_temporal"
    inputs.append(CorpusInput(
        case_id=cid, case_type=CorpusCaseType.POSITIVE,
        source_text=b"From 2020-2023, quarterly reports showed a 15% growth trend.",
    ))
    expecteds.append(CorpusExpected(
        case_id=cid, expected_atom_count=1,
        expected_atom_types=(ExpectedAtomType.CAUSAL_CHAIN,),
        expected_confidence_band="MEDIUM",
        expected_memory_zone="PROJECT",
    ))
    
    # C05: Anti-pattern — unsupported certainty
    cid = "C05_unsupported_certainty"
    inputs.append(CorpusInput(
        case_id=cid, case_type=CorpusCaseType.ANTI_PATTERN,
        source_text=b"This strategy ALWAYS makes money in ANY market condition.",
    ))
    expecteds.append(CorpusExpected(
        case_id=cid, expected_atom_count=0,
        expected_atom_types=(),
        expected_confidence_band="UNTRUSTED",
        expected_memory_zone="NO_PERSIST",
        should_reject=True,
        rejection_reason="unsupported_absolute_claim",
        anti_pattern_name="unsupported_certainty",
    ))
    
    # C06: Anti-pattern — secret-like text
    cid = "C06_secret_like"
    inputs.append(CorpusInput(
        case_id=cid, case_type=CorpusCaseType.ANTI_PATTERN,
        source_text=b"My API key is sk-abcdefghijklmnopqrstuvwxyz123456.",
    ))
    expecteds.append(CorpusExpected(
        case_id=cid, expected_atom_count=0,
        expected_atom_types=(),
        expected_confidence_band="UNTRUSTED",
        expected_memory_zone="NO_PERSIST",
        should_reject=True,
        rejection_reason="secret_like_content",
        anti_pattern_name="secret_like_content",
    ))
    
    # C07: Revision test
    cid = "C07_revision"
    inputs.append(CorpusInput(
        case_id=cid, case_type=CorpusCaseType.POSITIVE,
        source_text=b"Initial analysis: price resistance at 100.",
    ))
    expecteds.append(CorpusExpected(
        case_id=cid, expected_atom_count=1,
        expected_atom_types=(ExpectedAtomType.MECHANISM,),
        expected_confidence_band="MEDIUM",
        expected_memory_zone="PROJECT",
    ))
    
    # C08: Value judgment (not a fact)
    cid = "C08_value_judgment"
    inputs.append(CorpusInput(
        case_id=cid, case_type=CorpusCaseType.NEGATIVE,
        source_text=b"Bitcoin is the best investment.",
    ))
    expecteds.append(CorpusExpected(
        case_id=cid, expected_atom_count=1,
        expected_atom_types=(ExpectedAtomType.CONCEPT,),
        expected_confidence_band="LOW",
        expected_memory_zone="CANDIDATE",
    ))
    
    return inputs, expecteds


def run_evaluator(inputs: List[CorpusInput], expecteds: List[CorpusExpected],
                  pipeline) -> List[EvaluatorResult]:
    """Run production pipeline on inputs, compare against expected.
    
    pipeline(corpus_input) -> dict with keys:
      atom_count, atom_types, confidence, memory_zone
    """
    results = []
    exp_map = {e.case_id: e for e in expecteds}
    
    for inp in inputs:
        exp = exp_map.get(inp.case_id)
        actual = pipeline(inp)
        
        if actual is None:
            results.append(EvaluatorResult(
                case_id=inp.case_id,
                atom_count=0, actual_atom_types=(),
                actual_confidence="UNTRUSTED",
                actual_memory_zone="NO_PERSIST",
                verdict="FAIL", summary="Pipeline returned None",
            ))
            continue
        
        actual_types = tuple(actual.get("atom_types", []))
        actual_conf = actual.get("confidence", "UNTRUSTED")
        actual_zone = actual.get("memory_zone", "NO_PERSIST")
        
        # Compare
        type_match = set(actual_types) == set(t.value for t in exp.expected_atom_types if t.value)
        conf_match = actual_conf == exp.expected_confidence_band
        zone_match = actual_zone == exp.expected_memory_zone
        
        verdict = "PASS" if (type_match and conf_match and zone_match) else "FAIL"
        summary = f"types={'OK' if type_match else 'MISMATCH'} conf={'OK' if conf_match else 'MISMATCH'} zone={'OK' if zone_match else 'MISMATCH'}"
        
        results.append(EvaluatorResult(
            case_id=inp.case_id,
            atom_count=actual.get("atom_count", 0),
            actual_atom_types=actual_types,
            actual_confidence=actual_conf,
            actual_memory_zone=actual_zone,
            verdict=verdict,
            summary=summary,
        ))
    
    return results
