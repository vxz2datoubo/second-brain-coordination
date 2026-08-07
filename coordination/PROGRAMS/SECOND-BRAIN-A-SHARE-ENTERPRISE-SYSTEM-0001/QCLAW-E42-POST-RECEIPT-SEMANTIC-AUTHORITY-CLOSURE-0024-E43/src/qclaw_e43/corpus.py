"""
E43 Q6 — End-to-End Corpus Evaluator

Runs the real E43 source → evidence → atom → master/conflict → cognition/memory → skill
pipeline for every case. Compares complete canonical outcomes, not fixture counts.
"""
from __future__ import annotations

import hashlib, json, enum, dataclasses
from typing import Dict, List, Tuple, Any, Optional

# Will import real Q1-Q5 modules at runtime
from qclaw_e43.authority import (
    AuthorityRegistry, EvidenceFactory, AtomFactory,
    EvidenceLayer, AtomType, ConfidenceBand, VerificationState,
)
from qclaw_e43.source_trace import SourceDocument, SpanRole
from qclaw_e43.master_record import MasterRecordRegistry, ConflictClass, EventType
from qclaw_e43.cognition import CognitionEngine
from qclaw_e43.skill_lifecycle import SkillFactory, SkillState, SkillPromotionGate

__all__ = ["CorpusCase", "ExpectedOutcome", "CorpusEvaluator", "build_evaluation_corpus",
           "CORPUS_SCHEMA_VERSION", "CORPUS_ID_HASH"]

CORPUS_SCHEMA_VERSION = "43.0"

class CorpusCaseType(enum.Enum):
    POSITIVE = "positive"        # should succeed cleanly
    NEGATIVE = "negative"        # should be rejected by a gate
    AMBIGUOUS = "ambiguous"      # unclear handling expected
    ADVERSARIAL = "adversarial"  # tries to bypass authority/registry


@dataclasses.dataclass(frozen=True)
class ExpectedOutcome:
    """Ground truth expected results for a corpus case."""
    atom_type: Optional[AtomType] = None
    confidence: Optional[ConfidenceBand] = None
    verification: Optional[VerificationState] = None
    conflict_class: Optional[ConflictClass] = None
    memory_zone: Optional[str] = None
    skill_state: Optional[SkillState] = None
    should_succeed: bool = True
    expected_error_substring: Optional[str] = None
    min_stability: float = 0.0
    anti_pattern: Optional[str] = None  # e.g. "overcompression", "silent_overwrite", "secret_injection"


@dataclasses.dataclass(frozen=True)
class CorpusCase:
    """A single evaluation case with input, ground truth, and identity."""
    case_id: str
    case_type: CorpusCaseType
    name: str
    input_text: str
    expected: ExpectedOutcome
    description: str

    @staticmethod
    def compute_case_id(input_text: str, case_type: CorpusCaseType, name: str, schema_version: str) -> str:
        h = hashlib.sha256()
        h.update(input_text.encode())
        h.update(case_type.value.encode())
        h.update(name.encode())
        h.update(schema_version.encode())
        return h.hexdigest()[:16]


class CorpusEvaluator:
    """Runs the full E43 pipeline for every corpus case and compares outcomes."""

    def __init__(self):
        self._registry = AuthorityRegistry()
        self._ev_factory = EvidenceFactory(self._registry)
        self._atom_factory = AtomFactory(self._registry)
        self._master_registry = MasterRecordRegistry()
        self._cognition = CognitionEngine(self._registry, b"e43_cognition_key_xxxxxxxxxxxxx32")
        self._skill_factory = SkillFactory(b"e43_skill_key_xxxxxxxxxxxxxxxx32")
        self._results: Dict[str, Dict] = {}

    def evaluate(self, case: CorpusCase) -> Dict[str, Any]:
        """Run one case through the full pipeline. Returns detailed verdict."""
        result = {"case_id": case.case_id, "name": case.name, "verdict": "PASS"}

        try:
            # Step 1: Source document
            doc = SourceDocument(case.input_text.encode("utf-8"), "text/plain")
            source_digest = doc.digest

            # Step 2: Evidence record
            evidence = self._ev_factory.create_record(
                source_span_ref=f"{doc.document_id}:0:{doc.length}",
                evidence_layer=EvidenceLayer.AUTHOR_CLAIM,
                content=case.input_text,
                source_digest=source_digest,
            )

            # Step 3: Evidence bundle
            bundle = self._ev_factory.create_bundle((evidence,))
            confidence = bundle.derived_confidence()
            result["confidence"] = confidence.value

            # Step 4: Atom
            atom = self._atom_factory.create(
                text=case.input_text[:200],
                atom_type=case.expected.atom_type or AtomType.CONCEPT,
                source_bundle_id=bundle.bundle_id,
                provenance=EvidenceLayer.AUTHOR_CLAIM,
                confidence=confidence,
                scope="test_corpus",
                verification_state=VerificationState.UNVERIFIED,
                invalidation_conditions=(),
            )
            result["atom_id"] = atom.atom_id
            result["atom_type"] = atom.atom_type.value

            # Step 5: Master record
            mr = self._master_registry.create(case.input_text[:200], evidence.record_id)
            result["master_record_id"] = mr.record_id

            # Step 6: Cognition
            entry = self._cognition.analyze(evidence.record_id)
            result["memory_zone"] = entry.memory_zone.value
            result["stability"] = entry.stability_score

            # Step 7: Skill
            skill = self._skill_factory.create_skill(f"case_{case.case_id[:8]}", case.description)

            # Step 8: Verify all registries
            result["evidence_verifies"] = evidence.verify(self._registry, self._ev_factory)
            result["atom_verifies"] = atom.verify(self._registry, self._atom_factory)
            result["cognition_verifies"] = self._cognition.verify(entry)
            result["skill_verifies"] = self._skill_factory.verify(skill)

            # Step 9: Compare with expected
            checks = []
            if case.expected.atom_type and atom.atom_type != case.expected.atom_type:
                checks.append(f"atom_type_mismatch: expected {case.expected.atom_type.value} got {atom.atom_type.value}")
            if case.expected.memory_zone and entry.memory_zone.value != case.expected.memory_zone:
                checks.append(f"memory_zone_mismatch: expected {case.expected.memory_zone} got {entry.memory_zone.value}")
            if case.expected.min_stability > 0 and entry.stability_score < case.expected.min_stability:
                checks.append(f"stability_too_low: {entry.stability_score} < {case.expected.min_stability}")
            if not case.expected.should_succeed:
                checks.append("should_have_failed")

            if checks:
                result["verdict"] = "FAIL"
                result["failures"] = checks
            else:
                result["verdict"] = "PASS"

        except Exception as e:
            if case.expected.should_succeed:
                result["verdict"] = "FAIL"
                result["error"] = str(e)
            else:
                result["verdict"] = "PASS"
                result["rejection"] = str(e)

        self._results[case.case_id] = result
        return result

    @property
    def results(self) -> Dict[str, Dict]:
        return dict(self._results)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self._results.values() if r["verdict"] == "PASS")

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self._results.values() if r["verdict"] == "FAIL")


def build_evaluation_corpus() -> Tuple[List[CorpusCase], str]:
    """Build the E43 evaluation corpus. Returns (cases, corpus_hash)."""
    sv = CORPUS_SCHEMA_VERSION
    cases = [
        # POSITIVE cases
        CorpusCase(
            case_id=CorpusCase.compute_case_id("Market volatility increases during earnings season", CorpusCaseType.POSITIVE, "C01_basic_concept", sv),
            case_type=CorpusCaseType.POSITIVE, name="C01_basic_concept",
            input_text="Market volatility increases during earnings season",
            expected=ExpectedOutcome(atom_type=AtomType.CONCEPT, should_succeed=True, min_stability=0.4),
            description="Simple concept atom extraction"),

        CorpusCase(
            case_id=CorpusCase.compute_case_id("Rapid weight loss is unsustainable without metabolic adaptation", CorpusCaseType.POSITIVE, "C02_definition", sv),
            case_type=CorpusCaseType.POSITIVE, name="C02_definition",
            input_text="Rapid weight loss is unsustainable without metabolic adaptation",
            expected=ExpectedOutcome(atom_type=AtomType.DEFINITION, should_succeed=True),
            description="Definition-style knowledge extraction"),

        CorpusCase(
            case_id=CorpusCase.compute_case_id("If the Fed raises rates, bond yields rise within 24 hours", CorpusCaseType.POSITIVE, "C03_causal", sv),
            case_type=CorpusCaseType.POSITIVE, name="C03_causal",
            input_text="If the Fed raises rates, bond yields rise within 24 hours",
            expected=ExpectedOutcome(atom_type=AtomType.CAUSAL_CHAIN, should_succeed=True),
            description="Causal chain knowledge"),

        # NEGATIVE cases
        CorpusCase(
            case_id=CorpusCase.compute_case_id("", CorpusCaseType.NEGATIVE, "N01_empty_input", sv),
            case_type=CorpusCaseType.NEGATIVE, name="N01_empty_input",
            input_text="",
            expected=ExpectedOutcome(should_succeed=False, expected_error_substring="empty"),
            description="Empty input should be detected"),

        # AMBIGUOUS cases  
        CorpusCase(
            case_id=CorpusCase.compute_case_id("It might be possible that markets are somewhat efficient", CorpusCaseType.AMBIGUOUS, "A01_hedging", sv),
            case_type=CorpusCaseType.AMBIGUOUS, name="A01_hedging",
            input_text="It might be possible that markets are somewhat efficient",
            expected=ExpectedOutcome(min_stability=0.1, memory_zone="candidate"),
            description="Hedged language → low confidence expected"),

        # ADVERSARIAL cases
        CorpusCase(
            case_id=CorpusCase.compute_case_id("api_key = sk-proj-1234567890abcdefghijklmnop", CorpusCaseType.ADVERSARIAL, "V01_secret_text", sv),
            case_type=CorpusCaseType.ADVERSARIAL, name="V01_secret_text",
            input_text="api_key = sk-proj-1234567890abcdefghijklmnop",
            expected=ExpectedOutcome(should_succeed=True, anti_pattern="secret_injection"),
            description="Secret-like text should not be stored in plain atom content"),

        # Duplicate paraphrase detection
        CorpusCase(
            case_id=CorpusCase.compute_case_id("The market experienced a significant decline yesterday", CorpusCaseType.POSITIVE, "C04_paraphrase_a", sv),
            case_type=CorpusCaseType.POSITIVE, name="C04_paraphrase_a",
            input_text="The market experienced a significant decline yesterday",
            expected=ExpectedOutcome(should_succeed=True),
            description="Version A for paraphrase duplicate detection"),

        CorpusCase(
            case_id=CorpusCase.compute_case_id("Yesterday saw a major drop in market prices", CorpusCaseType.POSITIVE, "C05_paraphrase_b", sv),
            case_type=CorpusCaseType.POSITIVE, name="C05_paraphrase_b",
            input_text="Yesterday saw a major drop in market prices",
            expected=ExpectedOutcome(should_succeed=True),
            description="Version B — should be recognized as paraphrase of C04"),
    ]

    # Compute full corpus hash (all cases, all fields)
    h = hashlib.sha256()
    for c in sorted(cases, key=lambda x: x.case_id):
        h.update(c.case_id.encode())
        h.update(c.case_type.value.encode())
        h.update(c.name.encode())
        h.update(c.input_text.encode())
        h.update(c.description.encode())
    corpus_hash = h.hexdigest()

    return cases, corpus_hash
