"""E45 Q6 — Separated ground-truth corpus evaluator

Production input and ground truth are different types.
Production never receives expected outcomes, should_fail, or anti-pattern labels.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Any, Tuple
import hashlib


# ----- Production input (no ground truth) -----

@dataclass(frozen=True)
class CorpusInput:
    """What production sees — raw bytes, identity."""
    case_id: str
    input_bytes: bytes
    source_identity: str

    def __hash__(self):
        return hash(self.case_id)


# ----- Ground truth (held by evaluator, never passed to production) -----

@dataclass(frozen=True)
class CorpusExpected:
    """Ground truth held outside production pipeline."""
    case_id: str
    expected_origin: str  # e.g. "source_fact", "user_explicit", "hypothesis"
    expected_memory_zone: str  # "global"/"project"/"candidate"/"do_not_persist"
    expected_atom_types: tuple  # expected atom types from this input
    min_atoms: int = 0


# ----- Evaluator (outside production) -----

@dataclass
class CorpusCase:
    """A complete test case — input (to production) and expected (for evaluator)."""
    input: CorpusInput
    expected: CorpusExpected


def build_corpus() -> List[CorpusCase]:
    """Deterministic synthetic corpus. Production never sees 'expected'."""
    return [
        # C1: Source document fact
        CorpusCase(
            input=CorpusInput("C1", b"RSI(14) above 70 indicates overbought conditions",
                            "research_note_1"),
            expected=CorpusExpected("C1", "source_fact", "project", ("concept",), 1),
        ),
        # C2: User explicit fact
        CorpusCase(
            input=CorpusInput("C2", b"I know that MACD crossover is a momentum signal",
                            "user_msg_42"),
            expected=CorpusExpected("C2", "user_explicit", "global", ("indicator",), 1),
        ),
        # C3: Hypothesis — NOT a fact
        CorpusCase(
            input=CorpusInput("C3", b"Maybe RSI divergence predicts reversals in all markets",
                            "blog_post_7"),
            expected=CorpusExpected("C3", "hypothesis", "candidate", ("hypothesis_claim",), 0),
        ),
        # C4: Author claim
        CorpusCase(
            input=CorpusInput("C4", b"Expert trader says Bollinger Bands work best on 20-period",
                            "trading_article_3"),
            expected=CorpusExpected("C4", "author_claim", "candidate", ("indicator",), 1),
        ),
        # C5: Empty input — should produce zero atoms
        CorpusCase(
            input=CorpusInput("C5", b"", "empty_source"),
            expected=CorpusExpected("C5", "unknown", "do_not_persist", (), 0),
        ),
        # C6: Secret-like content — redact, don't leak
        CorpusCase(
            input=CorpusInput("C6", b"api_key=sk-1234567890abcdef1234567890abcdef",
                            "config_leak"),
            expected=CorpusExpected("C6", "unknown", "do_not_persist", (), 0),
        ),
        # C7: Paraphrase duplicate
        CorpusCase(
            input=CorpusInput("C7", b"Overbought conditions are indicated when RSI crosses above 70",
                            "research_note_2"),
            expected=CorpusExpected("C7", "source_fact", "project", ("concept",), 1),
        ),
        # C8: Value judgment
        CorpusCase(
            input=CorpusInput("C8", b"RSI is the best indicator for day trading",
                            "opinion_blog"),
            expected=CorpusExpected("C8", "value_judgment", "candidate", ("opinion",), 0),
        ),
    ]


# ----- Pipeline (production: only sees CorpusInput) -----

def run_pipeline(ci: CorpusInput,
                 capability_fn,  # makes VerifiedEvidenceCapabilityView from bytes
                 factory,        # EvidenceFactory
                 master_registry,
                 cognition_engine,
                 skill_factory) -> dict:
    """Production pipeline. Gets ONLY CorpusInput, never CorpusExpected."""
    # Capability from input bytes
    cap = capability_fn(ci.input_bytes, ci.source_identity)

    # Record → Bundle → Atom
    record = factory.create_record(cap)
    bundle = factory.create_bundle([record])
    atom = factory.create_atom(bundle)

    # Master record
    master = master_registry.create_master(bundle, f"master_{ci.case_id}")

    # Cognition / memory routing
    cognition = cognition_engine.derive_entry(bundle)

    return {
        "case_id": ci.case_id,
        "atoms": [atom.atom_id],
        "atom_count": 1,
        "master_id": master.object_id,
        "memory_zone": cognition.memory_zone.value,
        "origin": cap.origin.value,
    }


# ----- Evaluator (holds ground truth, compares) -----

def evaluate_corpus(cases: List[CorpusCase],
                    capability_fn,
                    factory,
                    master_registry,
                    cognition_engine,
                    skill_factory) -> dict:
    """Evaluator compares pipeline output against ground truth."""
    results = []
    for case in cases:
        output = run_pipeline(case.input, capability_fn, factory,
                             master_registry, cognition_engine, skill_factory)
        exp = case.expected
        passed = (
            output["origin"] == exp.expected_origin
            and output["memory_zone"] == exp.expected_memory_zone
            and output["atom_count"] >= exp.min_atoms
        )
        results.append({"case_id": case.input.case_id, "passed": passed, "output": output})

    return {
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": sum(1 for r in results if not r["passed"]),
        "results": results,
    }
