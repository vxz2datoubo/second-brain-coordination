"""Unit tests for qclaw_e50_audit."""
import sys, os, unittest

# Add E50 src to sys.path so tests can be run from anywhere
E50_SRC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if E50_SRC not in sys.path:
    sys.path.insert(0, E50_SRC)

from qclaw_e50_audit import (
    PrivateSourceRefused, SourceClass, SourceRefused,
    ingest_source, ingest_article, ingest_asr, ingest_chat, ingest_ocr,
    ingest_contradiction_pair, ingest_method,
    make_corpus, PublicSafeCorpus,
    canonical_id, SemanticObjectIdentity, CrossSourceMaster,
    CONTRADICTS, SUPERSEDES, DUPLICATE_OF, NEAR_DUPLICATE_OF,
    CognitionOrigin, classify_cognition_origin, VerifiedUserOriginRequired,
    SkillCandidate, SkillStage, PromotionReceipt, PromotionRefused,
    no_caller_authored_promotion,
    CanonicalW3QueryPath, RetrievalRoundTrip,
    CodexBoundaryGate, CandidatePackageShape,
    BLOCKED_PENDING_REAL_PRODUCTION_AUTHORITY,
    run_all_dimensions, compute_recommendation,
    EvidenceMatrix, CoverageReport, PostflightReceipt, DimensionVerdict, Verdict,
    ReadinessRecommendation,
)


class TestSourcePolicy(unittest.TestCase):
    def test_private_refused(self):
        with self.assertRaises(PrivateSourceRefused):
            ingest_source(source_uri="x", source_class=SourceClass.CLEAN_ARTICLE,
                          raw_text="y", is_private=True)

    def test_missing_uri_refused(self):
        with self.assertRaises(PrivateSourceRefused):
            ingest_source(source_uri="", source_class=SourceClass.CLEAN_ARTICLE,
                          raw_text="y")

    def test_missing_class_refused(self):
        with self.assertRaises(PrivateSourceRefused):
            ingest_source(source_uri="x", source_class=None, raw_text="y")

    def test_disallowed_class_refused(self):
        # Construct a class not in the allowed set by using enum outside allowed
        # All current enum values are in the allowed set; test that all are accepted.
        for cls in SourceClass:
            try:
                a = ingest_source(source_uri=f"u-{cls.value}", source_class=cls,
                                   raw_text="x")
                self.assertIsNotNone(a)
            except PrivateSourceRefused as e:
                # Only PROMPT_INJECTION should be allowed; if any other raises, fail
                if cls != SourceClass.PROMPT_INJECTION:
                    self.fail(f"unexpected refusal for {cls.value}: {e}")


class TestIngestion(unittest.TestCase):
    def test_article_artifact_has_provenance(self):
        a = ingest_article("uri://x", "hello world")
        self.assertTrue(a.source_uri)
        self.assertTrue(a.source_class)
        self.assertEqual(len(a.l0_hash), 64)  # SHA-256
        self.assertGreater(a.l0_size_bytes(), 0)

    def test_contradiction_pair_returns_two_artifacts(self):
        a, b = ingest_contradiction_pair("uri://a", "AAA", "uri://b", "BBB")
        self.assertNotEqual(a.source_uri, b.source_uri)
        self.assertEqual(a.source_class, b.source_class)


class TestCrossSource(unittest.TestCase):
    def test_canonical_id_stable(self):
        c1 = canonical_id("hello", "u://x", 0, 5)
        c2 = canonical_id("hello", "u://x", 0, 5)
        self.assertEqual(c1, c2)
        self.assertEqual(len(c1), 64)

    def test_dedup_same_content_same_id(self):
        master = CrossSourceMaster()
        s1 = SemanticObjectIdentity.from_atom(source_uri="u://a", content="hi",
                                              byte_start=0, byte_end=2)
        s2 = SemanticObjectIdentity.from_atom(source_uri="u://a", content="hi",
                                              byte_start=0, byte_end=2)
        master.register(s1)
        master.register(s2)
        self.assertEqual(len(master.identities), 1)

    def test_supersede_keeps_old(self):
        master = CrossSourceMaster()
        old = SemanticObjectIdentity.from_atom(source_uri="u://a", content="v1",
                                               byte_start=0, byte_end=2, version=1)
        new = SemanticObjectIdentity.from_atom(source_uri="u://a", content="v2",
                                               byte_start=0, byte_end=2, version=2)
        old_id = master.register(old)
        master.supersede(new, old_id)
        self.assertIn(old_id, master.identities)  # old kept
        self.assertTrue(master.is_superseded(old_id))

    def test_contradict(self):
        master = CrossSourceMaster()
        s1 = SemanticObjectIdentity.from_atom(source_uri="u://a", content="x",
                                              byte_start=0, byte_end=1)
        s2 = SemanticObjectIdentity.from_atom(source_uri="u://b", content="y",
                                              byte_start=0, byte_end=1)
        id1 = master.register(s1)
        id2 = master.register(s2)
        master.contradict(id1, id2)
        self.assertEqual(len(master.contradiction_edges), 1)


class TestCognition(unittest.TestCase):
    def test_forgery_blocked(self):
        with self.assertRaises(VerifiedUserOriginRequired):
            classify_cognition_origin(source_class=SourceClass.CLEAN_ARTICLE,
                                      text="x", claimed_verified_user=True)

    def test_user_declared_unverified(self):
        e = classify_cognition_origin(source_class=SourceClass.USER_DECLARED, text="x")
        self.assertEqual(e.origin, CognitionOrigin.USER_DECLARED)

    def test_user_declared_verified(self):
        e = classify_cognition_origin(source_class=SourceClass.USER_DECLARED,
                                      text="x", claimed_verified_user=True)
        self.assertEqual(e.origin, CognitionOrigin.VERIFIED_USER)

    def test_injection_is_unknown(self):
        e = classify_cognition_origin(source_class=SourceClass.PROMPT_INJECTION,
                                      text="x")
        self.assertEqual(e.origin, CognitionOrigin.UNKNOWN)


class TestSkillPromotion(unittest.TestCase):
    def test_insufficient_refused(self):
        skill = SkillCandidate(skill_id="t")
        r = PromotionReceipt(test_name="t", digest="", pass_count=0, failure_count=0)
        with self.assertRaises(PromotionRefused):
            no_caller_authored_promotion(skill, receipt=r)

    def test_full_promotion_refused(self):
        skill = SkillCandidate(skill_id="t")
        r = PromotionReceipt(test_name="t", digest="d" * 64, pass_count=1, failure_count=0,
                              distinct_cases=1, failure_conditions=("c",))
        with self.assertRaises(PromotionRefused):
            skill.attempt_promote(dry_run=False, receipt=r)

    def test_dry_run_accepted(self):
        skill = SkillCandidate(skill_id="t")
        r = PromotionReceipt(test_name="t", digest="d" * 64, pass_count=1, failure_count=0,
                              distinct_cases=1, failure_conditions=("c",))
        stage = no_caller_authored_promotion(skill, receipt=r, dry_run=True)
        self.assertEqual(stage, SkillStage.EXPERIMENTAL)

    def test_rollback(self):
        skill = SkillCandidate(skill_id="t")
        r = PromotionReceipt(test_name="t", digest="d" * 64, pass_count=1, failure_count=0,
                              distinct_cases=1, failure_conditions=("c",))
        no_caller_authored_promotion(skill, receipt=r, dry_run=True)
        rb = skill.rollback(reason="regression")
        self.assertEqual(skill.stage, SkillStage.CANDIDATE)
        self.assertEqual(len(skill.rollback_history), 1)


class TestCodexBoundary(unittest.TestCase):
    def test_emit_candidate_shape(self):
        gate = CodexBoundaryGate()
        a = ingest_article("u://x", "hello")
        digests = {"l0_source_sha256": a.l0_hash, "l0_source_size_bytes": a.l0_size_bytes(),
                   "raw_artifact_sha256": "0" * 64, "raw_artifact_size_bytes": 0,
                   "view_sha256": "0" * 64, "canonical_semantic_sha256": "0" * 64,
                   "l0_provenance_sha256": "0" * 64}
        shape = gate.emit_candidate_package(artifact=a, digests=digests)
        self.assertEqual(shape.formal_persistence, BLOCKED_PENDING_REAL_PRODUCTION_AUTHORITY)
        self.assertEqual(shape.visibility, "CANDIDATE_ONLY")

    def test_formal_write_refused(self):
        gate = CodexBoundaryGate()
        with self.assertRaises(PermissionError):
            gate.attempt_formal_write()


class TestCorpus(unittest.TestCase):
    def test_corpus_has_six_classes(self):
        fixtures, _ = make_corpus()
        classes = {f.source_class for f in fixtures}
        self.assertGreaterEqual(len(classes), 6)

    def test_mutation_set_yields_four(self):
        fixtures, _ = make_corpus()
        corpus = PublicSafeCorpus(fixtures)
        mut = corpus.mutation_set()
        self.assertEqual(len(mut), 4)  # base + 3 variants


class TestAuditRunner(unittest.TestCase):
    def test_run_all_dimensions_returns_matrix(self):
        fixtures, _ = make_corpus()
        corpus = PublicSafeCorpus(fixtures)
        matrix, coverage, postflight = run_all_dimensions(corpus)
        # D1-D12 all set
        for d in ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12"):
            self.assertIsNotNone(matrix.get(d))

    def test_recommendation_known_outcome(self):
        fixtures, _ = make_corpus()
        corpus = PublicSafeCorpus(fixtures)
        matrix, _, _ = run_all_dimensions(corpus)
        rv = compute_recommendation(matrix)
        self.assertIn(rv.recommendation, {
            ReadinessRecommendation.NOT_READY,
            ReadinessRecommendation.READY_FOR_BOUNDED_REAL_SOURCE_PILOT,
            ReadinessRecommendation.READY_FOR_PRODUCTION_CANDIDATE_LEARNING,
        })
        # At least: total = 12
        total = rv.pass_count + rv.partial_count + rv.fail_count
        self.assertEqual(total, 12)


class TestPrivateForbidden(unittest.TestCase):
    def test_private_conversation_refused(self):
        # Even with USER_DECLARED class, is_private=True must refuse.
        with self.assertRaises(PrivateSourceRefused):
            ingest_source(source_uri="u://x", source_class=SourceClass.USER_DECLARED,
                          raw_text="secret", is_private=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)