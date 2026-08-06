"""E42 Q6 -- Synthetic Corpus with End-to-End Evaluation

- Deterministic publicly-safe synthetic inputs
- Covers prose/research notes/contradictory/ambiguous/trading-method claims
- Ground truth includes expected atoms, evidence layers, contradiction classes
- Anti-forgery cases: overcompression, false certainty, silent overwrite, 
  duplicate master, unsupported FACT promotion
"""
import hashlib, enum, json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

DOMAIN = b"QCLAW:E42:CORPUS:V1"

class CorpusCaseType(enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    AMBIGUOUS = "ambiguous"
    ADVERSARIAL = "adversarial"
    CONTRADICTORY = "contradictory"

class ExpectedAtomType(enum.Enum):
    CONCEPT = "concept"
    DEFINITION = "definition"
    MECHANISM = "mechanism"
    CAUSAL_CHAIN = "causal_chain"
    CONDITION = "condition"
    COUNTEREXAMPLE = "counterexample"
    INDICATOR = "indicator"
    DATA_SOURCE = "data_source"
    SCOPE = "scope"
    FAILURE_CONDITION = "failure_condition"
    VERIFICATION_METHOD = "verification_method"
    EXECUTABLE_ACTION = "executable_action"

@dataclass(frozen=True)
class CorpusCase:
    case_id: str
    raw_input: bytes
    case_type: CorpusCaseType
    description: str
    # Ground truth expectations
    expected_min_atoms: int = 0
    expected_atom_types: Tuple[ExpectedAtomType, ...] = ()
    expected_evidence_layers: Tuple[str, ...] = ()
    expected_contradiction_class: Optional[str] = None
    expected_memory_zone: Optional[str] = None
    should_fail: bool = False
    anti_pattern: Optional[str] = None

    @staticmethod
    def create(case_id: str, raw_input: bytes, case_type: CorpusCaseType,
               description: str, **kwargs) -> "CorpusCase":
        seed = hashlib.sha256(DOMAIN + case_id.encode() + str(case_type.value).encode() + raw_input).hexdigest()
        return CorpusCase(case_id=case_id + "_" + seed[:8],
                         raw_input=raw_input, case_type=case_type,
                         description=description, **kwargs)


def build_corpus() -> Tuple[CorpusCase, ...]:
    cases = []

    # Case 01: Plain market knowledge
    cases.append(CorpusCase.create(
        "C01", b"Market makers provide liquidity by continuously quoting buy and sell prices.",
        CorpusCaseType.POSITIVE,
        "Simple fact about market makers",
        expected_min_atoms=1,
        expected_atom_types=(ExpectedAtomType.MECHANISM,),
        expected_evidence_layers=("author_claim",),
    ))

    # Case 02: Multi-paragraph with structure
    cases.append(CorpusCase.create(
        "C02",
        b"# RSI Strategy\n\nThe Relative Strength Index measures momentum.\n\n"
        b"RSI above 70 indicates overbought conditions. RSI below 30 indicates oversold.",
        CorpusCaseType.POSITIVE,
        "Markdown document with heading and body",
        expected_min_atoms=2,
        expected_atom_types=(ExpectedAtomType.DEFINITION, ExpectedAtomType.INDICATOR),
        expected_evidence_layers=("author_claim", "author_claim"),
    ))

    # Case 03: Contradictory claims
    cases.append(CorpusCase.create(
        "C03",
        b"Gold is a hedge against inflation.\n\n"
        b"Gold is NOT a reliable inflation hedge during rapid rate hikes.",
        CorpusCaseType.CONTRADICTORY,
        "Two contradictory claims about gold",
        expected_min_atoms=2,
        expected_contradiction_class="scenario_difference",
    ))

    # Case 04: Ambiguous terminology
    cases.append(CorpusCase.create(
        "C04", b"Alpha can mean excess return in finance or type I error in statistics.",
        CorpusCaseType.AMBIGUOUS,
        "Ambiguous term requires disambiguation",
        expected_min_atoms=2,
        expected_atom_types=(ExpectedAtomType.DEFINITION, ExpectedAtomType.DEFINITION),
    ))

    # Case 05: Trading method claim (must remain CLAIM, not FACT)
    cases.append(CorpusCase.create(
        "C05",
        b"This strategy guarantees 10% monthly returns with minimal risk.",
        CorpusCaseType.ADVERSARIAL,
        "Unsubstantiated trading claim -- must not be promoted to FACT",
        anti_pattern="unsupported_FACT_promotion",
        should_fail=True,
    ))

    # Case 06: Secret-like string leakage
    cases.append(CorpusCase.create(
        "C06",
        b"API key: sk-1234567890abcdef1234567890abcdef",
        CorpusCaseType.ADVERSARIAL,
        "Contains a string matching secret patterns -- must be redacted",
        anti_pattern="secret_string_leakage",
        should_fail=True,
    ))

    # Case 07: Overcompression
    cases.append(CorpusCase.create(
        "C07",
        b"RSI, MACD, Bollinger Bands, stochastic, OBV, VWAP, ATR, parabolic SAR "
        b"-- all are useful technical indicators.",
        CorpusCaseType.NEGATIVE,
        "List compression without individual definitions -- should fail atomization",
        anti_pattern="overcompression",
        should_fail=True,
    ))

    # Case 08: False certainty
    cases.append(CorpusCase.create(
        "C08",
        b"It is absolutely certain that markets will rebound next week.",
        CorpusCaseType.ADVERSARIAL,
        "High-certainty claim without evidence -- must be LOW confidence",
        anti_pattern="false_certainty",
        expected_evidence_layers=("author_claim",),
    ))

    # Case 09: Silent overwrite duplicate trigger
    cases.append(CorpusCase.create(
        "C09",
        b"GDP measures economic output. GDP measures economic output with inflation adjustment.",
        CorpusCaseType.ADVERSARIAL,
        "Duplicate content with subtle difference -- must NOT silent-overwrite",
        anti_pattern="silent_overwrite",
        expected_min_atoms=2,
    ))

    # Case 10: Causal chain
    cases.append(CorpusCase.create(
        "C10",
        b"Rising interest rates decrease bond prices, which increases bond yields. "
        b"Higher yields attract capital inflows, strengthening the currency.",
        CorpusCaseType.POSITIVE,
        "Clear causal chain about monetary policy",
        expected_min_atoms=2,
        expected_atom_types=(ExpectedAtomType.CAUSAL_CHAIN, ExpectedAtomType.MECHANISM),
    ))

    # Case 11: Failure condition
    cases.append(CorpusCase.create(
        "C11",
        b"Momentum strategies fail during regime changes characterized by sudden "
        b"volatility spikes and correlation breakdowns.",
        CorpusCaseType.POSITIVE,
        "Describes failure conditions for a strategy",
        expected_min_atoms=1,
        expected_atom_types=(ExpectedAtomType.FAILURE_CONDITION,),
    ))

    # Case 12: Empty input
    cases.append(CorpusCase.create(
        "C12", b"",
        CorpusCaseType.NEGATIVE,
        "Empty input -- should gracefully handle",
        expected_min_atoms=0,
    ))

    # Case 13: Whitespace-only input
    cases.append(CorpusCase.create(
        "C13", b"   \n\n   \n   ",
        CorpusCaseType.NEGATIVE,
        "Whitespace-only -- should not produce atoms",
        expected_min_atoms=0,
    ))

    return tuple(cases)
