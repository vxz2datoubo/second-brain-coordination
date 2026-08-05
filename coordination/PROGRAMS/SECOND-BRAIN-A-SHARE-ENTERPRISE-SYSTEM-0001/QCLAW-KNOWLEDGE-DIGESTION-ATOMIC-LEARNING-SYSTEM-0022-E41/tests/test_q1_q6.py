"""E41 Q1-Q6 — Comprehensive Test Suite

Tests for taxonomy, digestion, contradiction, cognition, skill lifecycle,
and synthetic corpus validation.
"""
import unittest, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"


# =========================== Q1 — TAXONOMY ===========================

class TestTaxonomyAtoms(unittest.TestCase):
    def test_create_atom(self):
        from qclaw_e41_knowledge.taxonomy import Atom, AtomType, EvidenceLayer
        a = Atom.create(AtomType.CONCEPT, EvidenceLayer.AUTHOR_CLAIM,
                        "market makers provide liquidity",
                        "source-001",
                        is_quoted_source=True, provenance="test")
        self.assertEqual(a.atom_type, AtomType.CONCEPT)
        self.assertEqual(a.evidence_layer, EvidenceLayer.AUTHOR_CLAIM)
        self.assertTrue(a.is_quoted_source)
        self.assertEqual(a.confidence, "unknown")
        self.assertEqual(a.verification_state, "unverified")

    def test_atom_id_deterministic(self):
        from qclaw_e41_knowledge.taxonomy import Atom, AtomType, EvidenceLayer
        a1 = Atom.create(AtomType.CONCEPT, EvidenceLayer.AUTHOR_CLAIM,
                         "test", "src", True, "prov")
        a2 = Atom.create(AtomType.CONCEPT, EvidenceLayer.AUTHOR_CLAIM,
                         "test", "src", True, "prov")
        self.assertEqual(a1.atom_id, a2.atom_id)

    def test_atom_id_differs(self):
        from qclaw_e41_knowledge.taxonomy import Atom, AtomType, EvidenceLayer
        a1 = Atom.create(AtomType.CONCEPT, EvidenceLayer.AUTHOR_CLAIM,
                         "text A", "src", True, "prov")
        a2 = Atom.create(AtomType.CONCEPT, EvidenceLayer.AUTHOR_CLAIM,
                         "text B", "src", True, "prov")
        self.assertNotEqual(a1.atom_id, a2.atom_id)

    def test_twelve_atom_types(self):
        from qclaw_e41_knowledge.taxonomy import AtomType, VALID_ATOM_TYPES
        self.assertEqual(len(AtomType), 12)
        self.assertEqual(len(VALID_ATOM_TYPES), 12)

    def test_six_evidence_layers(self):
        from qclaw_e41_knowledge.taxonomy import EvidenceLayer, VALID_EVIDENCE_LAYERS
        self.assertEqual(len(EvidenceLayer), 6)
        self.assertEqual(len(VALID_EVIDENCE_LAYERS), 6)

    def test_never_auto_fact_promotion(self):
        from qclaw_e41_knowledge.taxonomy import separate_evidence_layer
        result = separate_evidence_layer("It is a fact that the sky is blue")
        self.assertEqual(result, "author_claim")

    def test_validate_atom_ok(self):
        from qclaw_e41_knowledge.taxonomy import Atom, AtomType, EvidenceLayer, validate_atom
        a = Atom.create(AtomType.CONCEPT, EvidenceLayer.AUTHOR_CLAIM,
                        "valid atom", "source-001", True, "test")
        violations = validate_atom(a)
        self.assertEqual(violations, [])

    def test_validate_atom_empty_text(self):
        from qclaw_e41_knowledge.taxonomy import Atom, AtomType, EvidenceLayer, validate_atom
        a = Atom.create(AtomType.CONCEPT, EvidenceLayer.AUTHOR_CLAIM,
                        "  ", "src", True, "test")
        violations = validate_atom(a)
        self.assertTrue(any("empty" in v for v in violations))

    def test_classify_conservative_default(self):
        from qclaw_e41_knowledge.taxonomy import classify_atom_type
        at, _ = classify_atom_type("some text")
        self.assertEqual(at, "concept")


# =========================== Q2 — DIGESTION ===========================

class TestDigestionPipeline(unittest.TestCase):
    def test_extract_paragraphs(self):
        from qclaw_e41_knowledge.digestion import extract
        spans = extract("src1", "First paragraph.\n\nSecond paragraph.")
        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[0].quoted_content, "First paragraph.")
        self.assertEqual(spans[1].quoted_content, "Second paragraph.")

    def test_extract_empty(self):
        from qclaw_e41_knowledge.digestion import extract
        spans = extract("src1", "   \n\n  \n  ")
        self.assertEqual(len(spans), 0)

    def test_interpret_direct_quote(self):
        from qclaw_e41_knowledge.digestion import SourceSpan, interpret
        span = SourceSpan(source_id="s1", content="original text")
        seg = interpret(span)
        self.assertEqual(seg.status, "direct_quote")
        self.assertEqual(seg.normalized_text, "original text")

    def test_distinguish_quote_vs_interpretation(self):
        from qclaw_e41_knowledge.digestion import (
            SourceSpan, interpret, distinguish_quote_from_interpretation
        )
        span = SourceSpan(source_id="s1", content="text")
        seg = interpret(span)
        self.assertEqual(distinguish_quote_from_interpretation(seg), "QUOTED_SOURCE")

    def test_unsupported_stays_unknown(self):
        from qclaw_e41_knowledge.digestion import (
            SourceSpan, unsupported_interpretation
        )
        span = SourceSpan(source_id="s1", content="ambiguous")
        seg = unsupported_interpretation(span, "cannot determine meaning")
        self.assertEqual(seg.status, "unknown")
        self.assertTrue(seg.unsupported_note)

    def test_normalize_with_map(self):
        from qclaw_e41_knowledge.digestion import SourceSpan, interpret, normalize
        span = SourceSpan(source_id="s1", content="RSI indicator")
        seg = interpret(span)
        seg2 = normalize(seg, {"RSI": "Relative Strength Index"})
        self.assertIn("Relative Strength Index", seg2.normalized_text)

    def test_link_atoms(self):
        from qclaw_e41_knowledge.digestion import SourceSpan, interpret, link
        span = SourceSpan(source_id="s1", content="text")
        seg = interpret(span)
        seg2 = link(seg, ["atom_001", "atom_002"])
        self.assertEqual(seg2.linked_atom_ids, ["atom_001", "atom_002"])

    def test_is_quoted_source(self):
        from qclaw_e41_knowledge.digestion import SourceSpan, interpret, is_quoted_source
        span = SourceSpan(source_id="s1", content="text")
        seg = interpret(span)
        self.assertTrue(is_quoted_source(seg))


# =========================== Q3 — CONTRADICTION ===========================

class TestContradictionGovernance(unittest.TestCase):
    def test_merge_duplicates_no_overwrite(self):
        from qclaw_e41_knowledge.contradiction import merge_duplicates
        recs = {}
        r1 = merge_duplicates(recs, "hello world", "prov-A")
        r2 = merge_duplicates(recs, "hello world", "prov-B")
        self.assertGreater(len(r2.provenance_list), 1)

    def test_merge_different_content_keeps_both(self):
        from qclaw_e41_knowledge.contradiction import merge_duplicates
        recs = {}
        r1 = merge_duplicates(recs, "content A", "prov-A")
        r2 = merge_duplicates(recs, "content B", "prov-B")
        self.assertNotEqual(r1.object_id, r2.object_id)

    def test_classify_conflict_default_unresolved(self):
        from qclaw_e41_knowledge.contradiction import classify_conflict
        cc = classify_conflict("completely different text here yeah", "nothing similar at all")
        self.assertEqual(cc, "unresolved")

    def test_classify_definition_mismatch(self):
        from qclaw_e41_knowledge.contradiction import classify_conflict
        cc = classify_conflict(
            "RSI is a momentum indicator measuring speed and change",
            "RSI is a momentum indicator measuring speed and magnitude"
        )
        self.assertEqual(cc, "definition_mismatch")

    def test_prohibit_silent_overwrite(self):
        from qclaw_e41_knowledge.contradiction import (
            MasterRecord, prohibit_silent_overwrite
        )
        current = MasterRecord(
            object_id="obj1", current_content="old",
            provenance_list=["p1"]
        )
        violations = prohibit_silent_overwrite(current, "new")
        self.assertTrue(len(violations) > 0)

    def test_prohibit_no_violation_same_content(self):
        from qclaw_e41_knowledge.contradiction import (
            MasterRecord, prohibit_silent_overwrite
        )
        current = MasterRecord(
            object_id="obj1", current_content="same",
            provenance_list=["p1"]
        )
        violations = prohibit_silent_overwrite(current, "same")
        self.assertEqual(violations, [])

    def test_add_version_event(self):
        from qclaw_e41_knowledge.contradiction import (
            MasterRecord, add_version_event, VersionEventType
        )
        rec = MasterRecord(object_id="o1", current_content="old", provenance_list=["p1"])
        rec2 = add_version_event(rec, VersionEventType.CORRECTION, "old", "new", "fixed typo")
        self.assertEqual(rec2.current_content, "new")
        self.assertEqual(len(rec2.version_history), 1)


# =========================== Q4 — COGNITION ===========================

class TestCognitionMapping(unittest.TestCase):
    def test_classify_layer_known_stated(self):
        from qclaw_e41_knowledge.cognition import classify_layer
        self.assertEqual(
            classify_layer(is_stated=True, is_known=True, is_readable=True),
            "known_and_stated"
        )

    def test_classify_layer_unknown_needs_layering(self):
        from qclaw_e41_knowledge.cognition import classify_layer
        self.assertEqual(
            classify_layer(is_stated=False, is_known=False, is_readable=False),
            "unknown_and_needs_layering"
        )

    def test_classify_quality_explicit_fact(self):
        from qclaw_e41_knowledge.cognition import classify_quality
        q = classify_quality(has_direct_evidence=True, has_corroboration=True,
                             source_is_user=True)
        self.assertEqual(q, "explicit_user_fact")

    def test_classify_quality_low_confidence(self):
        from qclaw_e41_knowledge.cognition import classify_quality
        q = classify_quality(has_direct_evidence=False, has_corroboration=False,
                             source_is_user=False)
        self.assertEqual(q, "low_confidence_guess")

    def test_route_explicit_fact_to_global(self):
        from qclaw_e41_knowledge.cognition import (
            CognitionEntry, route_to_memory, CognitionLayer, InferenceQuality
        )
        entry = CognitionEntry(
            entry_id="e1", subject="test",
            layer=CognitionLayer.KNOWN_AND_STATED,
            quality=InferenceQuality.EXPLICIT_USER_FACT,
            content="data", memory_zone="global",
            supporting_evidence=["ev1"],
        )
        zone = route_to_memory(entry)
        self.assertEqual(zone, "global")

    def test_route_low_confidence_to_unpersisted(self):
        from qclaw_e41_knowledge.cognition import (
            CognitionEntry, route_to_memory, CognitionLayer, InferenceQuality
        )
        entry = CognitionEntry(
            entry_id="e2", subject="guess",
            layer=CognitionLayer.UNKNOWN_BUT_READABLE,
            quality=InferenceQuality.LOW_CONFIDENCE_GUESS,
            content="guess", memory_zone="unpersisted",
        )
        zone = route_to_memory(entry)
        self.assertEqual(zone, "unpersisted")

    def test_validate_low_confidence_cant_be_global(self):
        from qclaw_e41_knowledge.cognition import (
            CognitionEntry, validate_memory_route,
            CognitionLayer, InferenceQuality
        )
        entry = CognitionEntry(
            entry_id="e3", subject="bad",
            layer=CognitionLayer.UNKNOWN_BUT_READABLE,
            quality=InferenceQuality.LOW_CONFIDENCE_GUESS,
            content="guess", memory_zone="global",
        )
        violations = validate_memory_route(entry)
        self.assertTrue(len(violations) > 0)

    def test_validate_no_evidence_global(self):
        from qclaw_e41_knowledge.cognition import (
            CognitionEntry, validate_memory_route,
            CognitionLayer, InferenceQuality
        )
        entry = CognitionEntry(
            entry_id="e4", subject="weak",
            layer=CognitionLayer.KNOWN_AND_STATED,
            quality=InferenceQuality.EXPLICIT_USER_FACT,
            content="data", memory_zone="global",
            supporting_evidence=[],
        )
        violations = validate_memory_route(entry)
        self.assertTrue(len(violations) > 0)


# =========================== Q5 — SKILL LIFECYCLE ===========================

class TestSkillLifecycle(unittest.TestCase):
    def test_propose_candidate(self):
        from qclaw_e41_knowledge.skill_lifecycle import propose_candidate
        skill = propose_candidate("RSI Strategy", "A momentum-based entry strategy")
        self.assertEqual(skill.state, "candidate")

    def test_candidate_to_experimental(self):
        from qclaw_e41_knowledge.skill_lifecycle import (
            propose_candidate, Skill, promote, SkillPromotionGate
        )
        skill = propose_candidate("test", "desc")
        skill = Skill(
            skill_id=skill.skill_id, name=skill.name,
            state=skill.state, description=skill.description,
            scope=skill.scope, test_cases=["test1"],
        )
        result = promote(skill, SkillPromotionGate(
            reproducible_tests_count=0, distinct_cases_count=0,
            counterexamples_documented=0, scope_defined=False,
            failure_conditions_documented=False, rollback_plan_exists=False,
        ))
        self.assertEqual(result.state, "experimental")

    def test_experimental_to_formal_needs_full_gate(self):
        from qclaw_e41_knowledge.skill_lifecycle import (
            Skill, promote, SkillPromotionGate
        )
        skill = Skill(
            skill_id="s1", name="test", state="experimental",
            description="desc", scope="defined",
            failure_conditions=["fc1"], test_cases=["t1", "t2", "t3"],
            counterexamples=["ce1"],
        )
        gate = SkillPromotionGate(
            reproducible_tests_count=3, distinct_cases_count=2,
            counterexamples_documented=1, scope_defined=True,
            failure_conditions_documented=True, rollback_plan_exists=True,
        )
        result = promote(skill, gate)
        self.assertEqual(result.state, "formal")

    def test_single_sample_not_formal(self):
        from qclaw_e41_knowledge.skill_lifecycle import single_sample_not_formal
        self.assertTrue(single_sample_not_formal())

    def test_single_sample_incomplete_gate(self):
        from qclaw_e41_knowledge.skill_lifecycle import (
            Skill, promote, SkillPromotionGate
        )
        skill = Skill(
            skill_id="s2", name="test", state="experimental",
            description="desc", scope="vague",
            failure_conditions=[], test_cases=["only one"],
        )
        gate = SkillPromotionGate(
            reproducible_tests_count=0, distinct_cases_count=0,
            counterexamples_documented=0, scope_defined=False,
            failure_conditions_documented=False, rollback_plan_exists=False,
        )
        result = promote(skill, gate)
        self.assertEqual(result.state, "experimental")

    def test_demote_formal(self):
        from qclaw_e41_knowledge.skill_lifecycle import (
            Skill, demote
        )
        skill = Skill(
            skill_id="s3", name="test", state="formal",
            description="desc", scope="defined",
        )
        result = demote(skill, "found reproducibility issue")
        self.assertEqual(result.state, "demoted")

    def test_deprecate(self):
        from qclaw_e41_knowledge.skill_lifecycle import (
            Skill, deprecate
        )
        skill = Skill(skill_id="s4", name="test", state="formal",
                      description="desc", scope="defined")
        result = deprecate(skill, "outdated")
        self.assertEqual(result.state, "deprecated")
        self.assertEqual(result.deprecation_reason, "outdated")

    def test_supersede(self):
        from qclaw_e41_knowledge.skill_lifecycle import (
            Skill, supersede
        )
        skill = Skill(skill_id="s5", name="test", state="formal",
                      description="desc", scope="defined")
        result = supersede(skill, "new-skill-id")
        self.assertEqual(result.state, "superseded")
        self.assertEqual(result.superseded_by, "new-skill-id")


# =========================== Q6 — CORPUS ===========================

class TestCorpus(unittest.TestCase):
    def test_corpus_has_ten_cases(self):
        from qclaw_e41_knowledge.corpus import SYNTHETIC_CORPUS
        self.assertEqual(len(SYNTHETIC_CORPUS), 10)

    def test_corpus_has_all_case_types(self):
        from qclaw_e41_knowledge.corpus import SYNTHETIC_CORPUS, CorpusCaseType
        types = {c.case_type for c in SYNTHETIC_CORPUS}
        self.assertIn(CorpusCaseType.POSITIVE, types)
        self.assertIn(CorpusCaseType.NEGATIVE, types)
        self.assertIn(CorpusCaseType.AMBIGUOUS, types)
        self.assertIn(CorpusCaseType.ADVERSARIAL, types)

    def test_corpus_deterministic_seed(self):
        from qclaw_e41_knowledge.corpus import corpus_seed
        s1 = corpus_seed()
        s2 = corpus_seed()
        self.assertEqual(s1, s2)

    def test_corpus_summary(self):
        from qclaw_e41_knowledge.corpus import corpus_summary
        s = corpus_summary()
        self.assertIn("total_cases", s)
        self.assertIn("total_expected_atoms", s)

    def test_adversarial_cases_have_traps(self):
        from qclaw_e41_knowledge.corpus import SYNTHETIC_CORPUS, CorpusCaseType
        for c in SYNTHETIC_CORPUS:
            if c.case_type == CorpusCaseType.ADVERSARIAL:
                self.assertTrue(c.adversarial_trap, f"{c.case_id} has no trap")

    def test_empty_input_zero_atoms(self):
        from qclaw_e41_knowledge.corpus import SYNTHETIC_CORPUS
        c03 = [c for c in SYNTHETIC_CORPUS if c.case_id == "C03"][0]
        self.assertEqual(c03.expected_atom_count, 0)
        self.assertEqual(c03.expected_atom_types, [])

    def test_secret_like_input_zero_atoms(self):
        from qclaw_e41_knowledge.corpus import SYNTHETIC_CORPUS
        c04 = [c for c in SYNTHETIC_CORPUS if c.case_id == "C04"][0]
        self.assertEqual(c04.expected_atom_count, 0)

    def test_c07_has_false_certainty_trap(self):
        from qclaw_e41_knowledge.corpus import SYNTHETIC_CORPUS
        c07 = [c for c in SYNTHETIC_CORPUS if c.case_id == "C07"][0]
        self.assertEqual(c07.adversarial_trap, "false_certainty")
        self.assertIn("value_judgment", c07.expected_evidence_layers)

    def test_c08_has_silent_overwrite_trap(self):
        from qclaw_e41_knowledge.corpus import SYNTHETIC_CORPUS
        c08 = [c for c in SYNTHETIC_CORPUS if c.case_id == "C08"][0]
        self.assertEqual(c08.adversarial_trap, "silent_overwrite")


if __name__ == "__main__":
    unittest.main(verbosity=2)
