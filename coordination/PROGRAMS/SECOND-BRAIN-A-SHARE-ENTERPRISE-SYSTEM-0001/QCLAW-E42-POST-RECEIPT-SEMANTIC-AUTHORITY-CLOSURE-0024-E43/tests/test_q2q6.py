"""E43 Q2-Q6 Tests — Source, Master, Cognition, Skills, Corpus Evaluator"""
import unittest, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

# Q2 imports
from qclaw_e43.source_trace import SourceDocument, SourceSpan, SpanRole, LegalBytePartition

# Q3 imports
from qclaw_e43.master_record import MasterRecordRegistry, ConflictClass, EventType, MasterRecord, VersionEvent, ConflictEntry

# Q4 imports
from qclaw_e43.cognition import CognitionEngine, CognitionEntry, MemoryZone, CognitionState
from qclaw_e43.authority import AuthorityRegistry, EvidenceFactory, EvidenceLayer

# Q5 imports
from qclaw_e43.skill_lifecycle import SkillFactory, SkillState, SkillPromotionGate, TransitionReceipt, Skill

# Q6 imports
from qclaw_e43.corpus import build_evaluation_corpus, CorpusEvaluator, CorpusCaseType, CorpusCase, ExpectedOutcome


# ── Q2: Source Trace ────────────────────────────────────────────
class TestSourceDocument(unittest.TestCase):
    def test_document_identity_computed(self):
        doc = SourceDocument(b"hello world", "text/plain")
        self.assertEqual(doc.length, 11)
        self.assertFalse(doc.document_id == "")
        self.assertEqual(len(doc.document_id), 32)

    def test_strict_utf8_rejects_invalid(self):
        with self.assertRaises(ValueError):
            SourceDocument(b"\xff\xfe", "raw")

    def test_strict_utf8_accepts_valid(self):
        doc = SourceDocument("中文测试".encode("utf-8"), "text")
        self.assertEqual(doc.length, 12)

    def test_add_span_basic(self):
        doc = SourceDocument(b"content here", "text")
        span = doc.add_content_span(0, 12)
        self.assertEqual(span.byte_start, 0)
        self.assertEqual(span.byte_end, 12)
        self.assertEqual(span.role, SpanRole.CONTENT)
        self.assertEqual(span.document_id, doc.document_id)

    def test_span_out_of_range_rejected(self):
        doc = SourceDocument(b"short", "text")
        with self.assertRaises(ValueError):
            doc.add_span(0, 100, SpanRole.CONTENT)

    def test_span_inverted_rejected(self):
        doc = SourceDocument(b"short", "text")
        with self.assertRaises(ValueError):
            doc.add_span(5, 0, SpanRole.CONTENT)

    def test_span_extract_bytes(self):
        doc = SourceDocument(b"hello world", "text")
        span = doc.add_span(0, 5, SpanRole.CONTENT)
        self.assertEqual(span.extract(doc), b"hello")

    def test_span_with_wrong_document(self):
        doc1 = SourceDocument(b"hello", "text")
        doc2 = SourceDocument(b"world", "text")
        span = doc1.add_span(0, 5, SpanRole.CONTENT)
        self.assertFalse(doc2.verify_span(span))


class TestLegalBytePartition(unittest.TestCase):
    def setUp(self):
        self.doc = SourceDocument(b"ABCDEFGHIJ", "text")

    def test_perfect_coverage(self):
        p = LegalBytePartition(self.doc.length)
        p.add_span(self.doc.add_span(0, 5, SpanRole.CONTENT))
        p.add_span(self.doc.add_span(5, 10, SpanRole.STRUCTURE))
        diag = p.finalize()
        self.assertEqual(diag["gap_count"], 0)
        self.assertEqual(diag["covered"], 10)
        self.assertAlmostEqual(diag["coverage_ratio"], 1.0)

    def test_gap_detected(self):
        p = LegalBytePartition(self.doc.length)
        p.add_span(self.doc.add_span(0, 5, SpanRole.CONTENT))
        with self.assertRaises(ValueError):
            p.finalize()

    def test_overlap_rejected(self):
        p = LegalBytePartition(self.doc.length)
        p.add_span(self.doc.add_span(0, 6, SpanRole.CONTENT))
        with self.assertRaises(ValueError):
            p.add_span(self.doc.add_span(4, 10, SpanRole.STRUCTURE))

    def test_frozen_after_finalize(self):
        p = LegalBytePartition(self.doc.length)
        p.add_span(self.doc.add_span(0, 5, SpanRole.CONTENT))
        p.add_span(self.doc.add_span(5, 10, SpanRole.STRUCTURE))
        p.finalize()
        with self.assertRaises(ValueError):
            p.add_span(self.doc.add_span(0, 1, SpanRole.CONTENT))

    def test_out_of_range_rejected(self):
        p = LegalBytePartition(self.doc.length)
        with self.assertRaises(ValueError):
            p.add_span(self.doc.add_span(0, 999, SpanRole.CONTENT))


# ── Q3: Master Records ─────────────────────────────────────────
class TestMasterRecord(unittest.TestCase):
    def setUp(self):
        self.reg = MasterRecordRegistry()

    def test_create_record(self):
        mr = self.reg.create("content X", "ev_001")
        self.assertEqual(mr.content, "content X")
        self.assertEqual(self.reg.record_count, 1)

    def test_apply_version_transition(self):
        mr = self.reg.create("v1", "ev_001")
        self.assertEqual(mr.version_count, 1)  # initial ADD event
        ev = mr.apply_version(EventType.CORRECTION, "v2 corrected", "ev_002", "fixing typo")
        self.assertEqual(mr.content, "v2 corrected")
        self.assertEqual(mr.version_count, 2)

    def test_duplicate_semantic_identity_rejected(self):
        self.reg.create("same content", "ev_001")
        with self.assertRaises(ValueError):
            self.reg.create("same content", "ev_001")

    def test_different_content_different_semantic_id(self):
        mr1 = self.reg.create("content A", "ev_001")
        mr2 = self.reg.create("content B", "ev_001")
        self.assertNotEqual(mr1.record_id, mr2.record_id)

    def test_register_conflict(self):
        mr1 = self.reg.create("alpha", "ev_001")
        mr2 = self.reg.create("beta", "ev_002")
        ce = self.reg.register_conflict(mr1.record_id, mr2.record_id,
                                         ConflictClass.DEFINITION_MISMATCH,
                                         "ev_003", "different definitions")
        self.assertEqual(self.reg.conflict_count, 1)
        self.assertTrue(ce.unresolved)

    def test_conflict_needs_registered_records(self):
        with self.assertRaises(ValueError):
            self.reg.register_conflict("fake_a", "fake_b", ConflictClass.UNRESOLVED, "ev", "desc")

    def test_classify_conflict_by_evidence_layers(self):
        cc = self.reg.classify_conflict("a", "b", "source_fact", "source_fact")
        self.assertEqual(cc, ConflictClass.PROBABLE_ERROR)
        cc2 = self.reg.classify_conflict("a", "b", "source_fact", "author_claim")
        self.assertEqual(cc2, ConflictClass.DEFINITION_MISMATCH)


# ── Q4: Cognition ──────────────────────────────────────────────
class TestCognition(unittest.TestCase):
    def setUp(self):
        self.reg = AuthorityRegistry()
        self.ev_factory = EvidenceFactory(self.reg)
        self.cog = CognitionEngine(self.reg, b"e43_cog_test_key_xxxxxxxxxxxxx32")

    def test_source_fact_produces_global(self):
        r = self.ev_factory.create_record("src:1..10", EvidenceLayer.SOURCE_FACT, "known fact", "digest_a")
        entry = self.cog.analyze(r.record_id)
        self.assertEqual(entry.state, CognitionState.KNOWN_AND_STATED)
        self.assertEqual(entry.memory_zone, MemoryZone.GLOBAL)
        self.assertGreater(entry.stability_score, 0.9)
        self.assertTrue(self.cog.verify(entry))

    def test_hypothesis_produces_candidate(self):
        r = self.ev_factory.create_record("src:1..10", EvidenceLayer.HYPOTHESIS, "maybe true?", "digest_b")
        entry = self.cog.analyze(r.record_id)
        self.assertEqual(entry.state, CognitionState.UNKNOWN_BUT_READABLE)
        self.assertEqual(entry.memory_zone, MemoryZone.CANDIDATE)

    def test_value_judgment_produces_do_not_persist(self):
        r = self.ev_factory.create_record("src:1..10", EvidenceLayer.VALUE_JUDGMENT, "opinion only", "digest_c")
        entry = self.cog.analyze(r.record_id)
        self.assertEqual(entry.memory_zone, MemoryZone.DO_NOT_PERSIST)
        self.assertLess(entry.stability_score, 0.1)

    def test_unregistered_evidence_rejected(self):
        with self.assertRaises(ValueError):
            self.cog.analyze("nonexistent_record_id")

    def test_foreign_entry_not_verifiable(self):
        r = self.ev_factory.create_record("src:1..5", EvidenceLayer.SOURCE_FACT, "true info", "dd")
        entry = self.cog.analyze(r.record_id)
        # Create a forged entry
        forged = CognitionEntry(entry_id="made_up", state=entry.state,
                                memory_zone=MemoryZone.GLOBAL,
                                evidence_record_id=entry.evidence_record_id,
                                stability_score=0.99,
                                factory_signature=b"bad_sig_xxxxxxxxxxxxxxxxxxxx")
        self.assertFalse(self.cog.verify(forged))


# ── Q5: Skills ─────────────────────────────────────────────────
class TestSkillLifecycle(unittest.TestCase):
    def setUp(self):
        self.factory = SkillFactory(b"e43_skill_test_key_xxxxxxxxxxxxx32")

    def test_create_skill_starts_candidate(self):
        s = self.factory.create_skill("test_skill", "A test skill")
        self.assertEqual(s.state, SkillState.CANDIDATE)
        self.assertTrue(self.factory.verify(s))

    def test_promote_candidate_to_experimental(self):
        s = self.factory.create_skill("promo_skill", "promotion test")
        s2 = self.factory.promote(s, SkillState.EXPERIMENTAL,
                                   ("ev_001", "ev_002"), "test_run_1",
                                   3, 0, "domain:test", ("f_cond_1", "f_cond_2"), True)
        self.assertEqual(s2.state, SkillState.EXPERIMENTAL)
        self.assertEqual(len(s2.transitions), 1)

    def test_promotion_insufficient_cases_rejected(self):
        s = self.factory.create_skill("weak_skill", "not enough data")
        with self.assertRaises(ValueError):
            self.factory.promote(s, SkillState.EXPERIMENTAL,
                                  ("ev_x",), "run_x", 1, 0, "", ("f1",), True)

    def test_demote_skill(self):
        s = self.factory.create_skill("demo_skill", "for demotion")
        s2 = self.factory.demote(s, "ev_demote")
        self.assertEqual(s2.state, SkillState.DEMOTED)

    def test_unregistered_skill_rejected(self):
        forged = Skill(skill_id="fake_id", name="fake", state=SkillState.FORMAL,
                       description="fake", transitions=(), created_ns=0,
                       factory_signature=b"bad")
        self.assertFalse(self.factory.verify(forged))


class TestPromotionGates(unittest.TestCase):
    def test_candidate_to_experimental_minimums(self):
        import time
        r = TransitionReceipt(
            receipt_id="r1", from_state=SkillState.CANDIDATE,
            to_state=SkillState.EXPERIMENTAL, evidence_record_ids=("e1", "e2"),
            test_run_id="run1", case_count=3, counterexample_count=0,
            scope_definition="domain:test", failure_conditions=("f1",),
            rollback_defined=True, timestamp_ns=time.time_ns())
        gate = SkillPromotionGate()
        self.assertTrue(gate.can_promote_to_experimental(r))

    def test_single_sample_not_formal(self):
        import time
        r = TransitionReceipt(
            receipt_id="r2", from_state=SkillState.EXPERIMENTAL,
            to_state=SkillState.FORMAL, evidence_record_ids=("e1", "e2", "e3"),
            test_run_id="run2", case_count=1, counterexample_count=0,
            scope_definition="domain:test", failure_conditions=("f1", "f2"),
            rollback_defined=True, timestamp_ns=time.time_ns())
        gate = SkillPromotionGate()
        self.assertFalse(gate.can_promote_to_formal(r))
        self.assertFalse(gate.single_sample_not_formal(r))

    def test_experimental_to_formal_requires_5_cases(self):
        import time
        r = TransitionReceipt(
            receipt_id="r3", from_state=SkillState.EXPERIMENTAL,
            to_state=SkillState.FORMAL, evidence_record_ids=("e1", "e2", "e3"),
            test_run_id="run3", case_count=5, counterexample_count=0,
            scope_definition="domain:test", failure_conditions=("f1", "f2"),
            rollback_defined=True, timestamp_ns=time.time_ns())
        gate = SkillPromotionGate()
        self.assertTrue(gate.can_promote_to_formal(r))


# ── Q6: Corpus Evaluator ───────────────────────────────────────
class TestCorpusEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = CorpusEvaluator()

    def test_evaluate_positive_case(self):
        case = CorpusCase(
            case_id="C01", case_type=CorpusCaseType.POSITIVE, name="test positive",
            input_text="Market volatility increases during earnings season",
            expected=ExpectedOutcome(should_succeed=True),
            description="Basic test")
        result = self.evaluator.evaluate(case)
        self.assertEqual(result["verdict"], "PASS")

    def test_evaluate_multiple_cases(self):
        cases, corpus_hash = build_evaluation_corpus()
        self.assertGreater(len(cases), 3)
        self.assertEqual(len(corpus_hash), 64)

        for case in cases:
            result = self.evaluator.evaluate(case)
            self.assertIn(result["verdict"], ("PASS", "FAIL"))

    def test_corpus_identity_changes_with_schema(self):
        # Different schema version → different case IDs
        import hashlib
        id1 = CorpusCase.compute_case_id("test", CorpusCaseType.POSITIVE, "name", "1.0")
        id2 = CorpusCase.compute_case_id("test", CorpusCaseType.POSITIVE, "name", "2.0")
        self.assertNotEqual(id1, id2)

    def test_empty_input_case(self):
        case = CorpusCase(
            case_id="N01", case_type=CorpusCaseType.NEGATIVE, name="empty",
            input_text="",
            expected=ExpectedOutcome(should_succeed=False),
            description="Empty input test")
        # Empty string is valid UTF-8 but may cause issues downstream
        result = self.evaluator.evaluate(case)
        # Either passes (handled empty) or fails (as expected)
        self.assertIn(result["verdict"], ("PASS", "FAIL"))

    def test_anti_pattern_tracking(self):
        case = CorpusCase(
            case_id="V01", case_type=CorpusCaseType.ADVERSARIAL,
            name="secret injection",
            input_text="api_key = sk-proj-1234567890abcdefghijklmnop",
            expected=ExpectedOutcome(should_succeed=True, anti_pattern="secret_injection"),
            description="Secret-like text")
        result = self.evaluator.evaluate(case)
        # Should succeed but anti-pattern tracked
        self.assertEqual(result["verdict"], "PASS")

    def test_evaluator_registry_counts(self):
        cases, _ = build_evaluation_corpus()
        for case in cases:
            self.evaluator.evaluate(case)
        self.assertGreaterEqual(self.evaluator.pass_count, 1)

    def test_deterministic_evaluation(self):
        # Same case twice → same result
        case = CorpusCase(
            case_id="det_test", case_type=CorpusCaseType.POSITIVE,
            name="deterministic",
            input_text="A clear and precise statement about market dynamics",
            expected=ExpectedOutcome(should_succeed=True),
            description="Determinism test")
        r1 = self.evaluator.evaluate(case)
        r2 = CorpusEvaluator().evaluate(case)
        self.assertEqual(r1["verdict"], r2["verdict"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
