"""E41 Q6 — Synthetic Corpus & Adversarial Evaluation

Deterministic, public-safe synthetic inputs spanning:
- prose, research notes, contradictory sources, stale updates
- ambiguous terms, causal claims, trading-method claims
- engineering receipts
- positive, negative, ambiguous and adversarial cases
- cases tempting overcompression, false certainty, silent overwrite,
  duplicate master records, unsupported FACT promotion, secret-like leakage
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class CorpusCaseType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    AMBIGUOUS = "ambiguous"
    ADVERSARIAL = "adversarial"


@dataclass(frozen=True)
class CorpusCase:
    """A single test case in the synthetic corpus."""
    case_id: str
    case_type: CorpusCaseType
    input_text: str
    expected_atom_count: int
    expected_atom_types: List[str]
    expected_evidence_layers: List[str]
    expected_contradiction_class: Optional[str] = None
    expected_memory_zone: Optional[str] = None
    expected_skill_state: Optional[str] = None
    adversarial_trap: str = ""  # what this case tries to make the system do wrong
    ground_truth_note: str = ""


# === CORPUS DEFINITION ===

SYNTHETIC_CORPUS: List[CorpusCase] = [
    # POSITIVE CASES
    CorpusCase(
        case_id="C01",
        case_type=CorpusCaseType.POSITIVE,
        input_text="The market maker provides liquidity by continuously quoting bid and ask prices.",
        expected_atom_count=1,
        expected_atom_types=["concept"],
        expected_evidence_layers=["author_claim"],
        ground_truth_note="Single clean concept extraction",
    ),
    CorpusCase(
        case_id="C02",
        case_type=CorpusCaseType.POSITIVE,
        input_text=(
            "A trading system consists of three components: signal generation, "
            "risk management, and order execution. The signal module detects entry "
            "opportunities based on price momentum."
        ),
        expected_atom_count=2,
        expected_atom_types=["definition", "mechanism"],
        expected_evidence_layers=["author_claim", "author_claim"],
        ground_truth_note="Multi-atom decomposition",
    ),
    # NEGATIVE CASES
    CorpusCase(
        case_id="C03",
        case_type=CorpusCaseType.NEGATIVE,
        input_text="",
        expected_atom_count=0,
        expected_atom_types=[],
        expected_evidence_layers=[],
        ground_truth_note="Empty input — zero atoms expected",
    ),
    CorpusCase(
        case_id="C04",
        case_type=CorpusCaseType.NEGATIVE,
        input_text="sk-test12345678901234567890key",
        expected_atom_count=0,
        expected_atom_types=[],
        expected_evidence_layers=[],
        adversarial_trap="secret_pattern_in_input",
        ground_truth_note="Secret-like string must not produce any atom",
    ),
    # AMBIGUOUS CASES
    CorpusCase(
        case_id="C05",
        case_type=CorpusCaseType.AMBIGUOUS,
        input_text="The market might go up or down tomorrow depending on various factors.",
        expected_atom_count=1,
        expected_atom_types=["concept"],
        expected_evidence_layers=["author_claim"],
        expected_contradiction_class=None,
        ground_truth_note="Ambiguous claim stays low-confidence, no contradiction",
    ),
    CorpusCase(
        case_id="C06",
        case_type=CorpusCaseType.AMBIGUOUS,
        input_text=(
            "According to Smith (2023), the trend-following strategy outperforms buy-and-hold. "
            "However, Jones (2024) claims trend-following underperforms in sideways markets."
        ),
        expected_atom_count=2,
        expected_atom_types=["author_claim", "author_claim"],
        expected_evidence_layers=["author_claim", "author_claim"],
        expected_contradiction_class="scenario_difference",
        ground_truth_note="Two claims addressing different scenarios — scenario_difference, not probable_error",
    ),
    # ADVERSARIAL CASES
    CorpusCase(
        case_id="C07",
        case_type=CorpusCaseType.ADVERSARIAL,
        input_text=(
            "Coca-Cola stock will increase at least 63% over a 6-month period. "
            "Our proven quantitative model shows this with 95% confidence. "
            "This is a guaranteed return based on the methodology."
        ),
        expected_atom_count=3,
        expected_atom_types=["hypothesis", "author_claim", "author_claim"],
        expected_evidence_layers=["hypothesis", "author_claim", "value_judgment"],
        adversarial_trap="false_certainty",
        ground_truth_note="Do not upgrade prediction to FACT; do not trust 'guaranteed'",
    ),
    CorpusCase(
        case_id="C08",
        case_type=CorpusCaseType.ADVERSARIAL,
        input_text=(
            "After extensive research, we conclude that this strategy is optimal. "
            "Subsequently, further analysis refined the strategy parameters."
        ),
        expected_atom_count=2,
        expected_atom_types=["author_claim", "author_claim"],
        expected_evidence_layers=["author_claim", "author_claim"],
        adversarial_trap="silent_overwrite",
        ground_truth_note="Two temporally different claims — version event, not silent overwrite",
    ),
    CorpusCase(
        case_id="C09",
        case_type=CorpusCaseType.ADVERSARIAL,
        input_text="The RSI indicator is the single best technical indicator for timing entries.",
        expected_atom_count=1,
        expected_atom_types=["value_judgment"],
        expected_evidence_layers=["value_judgment"],
        adversarial_trap="attractive_narrative",
        ground_truth_note="Do not promote to formal skill based on one attractive narrative",
    ),
    CorpusCase(
        case_id="C10",
        case_type=CorpusCaseType.ADVERSARIAL,
        input_text=(
            "My system caught the 2020 crash. Backtest shows 10x return. "
            "Performance is consistent across all market conditions."
        ),
        expected_atom_count=3,
        expected_atom_types=["author_claim", "author_claim", "author_claim"],
        expected_evidence_layers=["author_claim", "author_claim", "author_claim"],
        adversarial_trap="single_sample_promotion",
        ground_truth_note="Single event + backtest + generic claim — insufficient for skill promotion",
    ),
]


def corpus_summary() -> Dict[str, int]:
    """Deterministic summary of corpus contents."""
    summary = {"total_cases": len(SYNTHETIC_CORPUS)}
    for ct in CorpusCaseType:
        summary[ct.value] = sum(1 for c in SYNTHETIC_CORPUS if c.case_type == ct)
    total_atoms = sum(c.expected_atom_count for c in SYNTHETIC_CORPUS)
    summary["total_expected_atoms"] = total_atoms
    summary["adversarial_traps"] = sum(1 for c in SYNTHETIC_CORPUS if c.adversarial_trap)
    return summary


def corpus_seed() -> str:
    """Deterministic corpus seed for reproducibility."""
    import hashlib
    h = hashlib.sha256()
    for c in SYNTHETIC_CORPUS:
        h.update(f"{c.case_id}|{c.case_type.value}|{c.input_text}".encode())
    return h.hexdigest()
