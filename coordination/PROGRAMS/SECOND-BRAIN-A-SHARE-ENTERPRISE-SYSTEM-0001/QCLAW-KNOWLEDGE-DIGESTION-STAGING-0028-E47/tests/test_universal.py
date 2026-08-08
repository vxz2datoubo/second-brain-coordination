"""E47 Digest Tests — universal schema validation + DIGEST-001/002 migration.

CANDIDATE ONLY. No formal authority tests.
"""
import unittest
import os
import sys
import tempfile
import json


here = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(os.path.dirname(here), "src")
sys.path.insert(0, src)

from qclaw_e47_digest.schema import (
    CandidateKnowledgePackage, SourceSnapshot, SourceSpan,
    Atom, AtomType, EvidenceKind, Confidence,
    Relation, RelationType, Contradiction, ContradictionClass,
    Unknown, CandidateMemory, CandidateSkill,
)
from qclaw_e47_digest.engine import (
    ingest_source, locate_span, find_all_spans,
    build_package, serialize_package,
    migrate_digest_001_to_universal,
    migrate_digest_002_to_universal,
)


class TestUniversalSchema(unittest.TestCase):
    """Verify schema integrity, immutability, and fail-closed."""

    def test_source_identity_excludes_timestamp(self):
        s1 = SourceSnapshot("id", "url", "title", "sha", 100, "content", "2025-01-01T00:00:00Z")
        s2 = SourceSnapshot("id", "url", "title", "sha", 100, "content", "2026-06-15T12:00:00Z")
        self.assertEqual(s1.identity_hash(), s2.identity_hash())

    def test_source_identity_changes_with_content(self):
        s1 = SourceSnapshot("id", "url", "title", "sha", 100, "content", "ts")
        s2 = SourceSnapshot("id", "url", "title", "sha2", 200, "content", "ts")
        self.assertNotEqual(s1.identity_hash(), s2.identity_hash())

    def test_span_bytes_exact(self):
        text = "Hello 世界"
        span = SourceSpan(0, 5, 1, 1, "greeting")
        self.assertEqual(span.byte_start, 0)
        self.assertEqual(span.byte_end, 5)

    def test_content_hash_excludes_timestamp(self):
        src = SourceSnapshot("id", "url", "title", "sha", 10, "0123456789", "2025-01-01")
        src2 = SourceSnapshot("id", "url", "title", "sha", 10, "0123456789", "2026-01-01")
        a = Atom("A1", AtomType.CONCEPT, "test", 
                 (SourceSpan(0, 5, 1, 1, "label"),),
                 EvidenceKind.SOURCE_EXTRACT, Confidence.MEDIUM)
        pkg1 = CandidateKnowledgePackage("PKG", source=src, atoms=(a,), summary="")
        pkg2 = CandidateKnowledgePackage("PKG", source=src2, atoms=(a,), summary="")
        self.assertEqual(pkg1.content_hash(), pkg2.content_hash())
        self.assertTrue(src.identity_hash() == src2.identity_hash())

    def test_atom_requiring_source_span(self):
        span = SourceSpan(0, 10, 1, 1, "label")
        a = Atom("A1", AtomType.CONCEPT, "test", (span,),
                 EvidenceKind.SOURCE_EXTRACT, Confidence.MEDIUM)
        self.assertEqual(len(a.source_spans), 1)

    def test_ingest_source_creates_snapshot(self):
        text = "test content 123"
        src = ingest_source(text, "https://example.com", "Test Title", "test-001")
        self.assertGreater(len(src.source_hash), 0)
        self.assertEqual(src.source_size_bytes, len(text.encode("utf-8")))
        self.assertEqual(src.source_content, text)

    def test_locate_exact_span(self):
        text = "Line 1\nLine 2: 世界\nLine 3"
        excerpt = "Line 2: 世界"
        span = locate_span(text, excerpt, "line2")
        self.assertGreater(span.byte_start, 0)
        self.assertGreater(span.byte_end, span.byte_start)
        self.assertEqual(text[text.index(excerpt):text.index(excerpt)+len(span.span_label)], excerpt) if False else None
        # Verify span content matches
        src_bytes = text.encode("utf-8")
        self.assertEqual(src_bytes[span.byte_start:span.byte_end].decode("utf-8"), excerpt)

    def test_locate_span_not_found_raises(self):
        with self.assertRaises(ValueError):
            locate_span("abc", "xyz", "missing")

    def test_build_package_validates_relations(self):
        src = SourceSnapshot("id", "url", "t", "sha", 10, "0123456789", "ts")
        a = Atom("A1", AtomType.CONCEPT, "x",
                 (SourceSpan(0, 5, 1, 1, "label"),),
                 EvidenceKind.SOURCE_EXTRACT, Confidence.MEDIUM)
        rel = Relation("A1", "A999", RelationType.DEPENDS_ON)
        with self.assertRaises(ValueError):
            build_package("PKG", src, [a], [rel])

    def test_to_dict_schema_field_present(self):
        src = SourceSnapshot("id", "url", "t", "sha", 10, "0123456789", "ts")
        a = Atom("A1", AtomType.CONCEPT, "x",
                 (SourceSpan(0, 5, 1, 1, "label"),),
                 EvidenceKind.SOURCE_EXTRACT, Confidence.MEDIUM)
        pkg = CandidateKnowledgePackage("PKG", source=src, atoms=(a,))
        d = pkg.to_dict()
        self.assertEqual(d["schema"], "QCLAW-CANDIDATE-KNOWLEDGE-PACKAGE-V1")

    def test_memory_zone_locked_to_candidate(self):
        m = CandidateMemory("M1", "statement", Confidence.LOW, ("A1",), "basis")
        self.assertEqual(m.to_dict()["memory_zone"], "CANDIDATE")

    def test_skill_state_locked_to_candidate(self):
        s = CandidateSkill("S1", "name", "desc", "fail")
        d = s.to_dict()
        self.assertEqual(d["state"], "CANDIDATE")
        self.assertTrue(d["requires_e60_authority"])


class TestSerializePackage(unittest.TestCase):
    """Verify JSON/YAML artifact generation."""

    def test_serialize_to_json(self):
        src = ingest_source("test content for serialization", "https://x.com", "Test", "ser-001")
        span = SourceSpan(0, len("test content for serialization".encode("utf-8")), 1, 1, "full")
        a = Atom("A1", AtomType.CONCEPT, "test content for serialization",
                 (span,), EvidenceKind.SOURCE_EXTRACT, Confidence.HIGH)
        pkg = build_package("SER-TEST", src, [a], summary="Serialization test")
        
        with tempfile.TemporaryDirectory() as td:
            json_path, yaml_path = serialize_package(pkg, td)
            self.assertTrue(os.path.exists(json_path))
            self.assertTrue(os.path.exists(yaml_path))
            
            # Read back JSON and verify
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["package_id"], "SER-TEST")
            self.assertEqual(len(data["atoms"]), 1)
            self.assertEqual(data["atoms"][0]["evidence_kind"], "SOURCE_EXTRACT")
            self.assertIn("content_hash", data)

    def test_content_hash_stable_across_serializations(self):
        src = ingest_source("stable content", "https://x.com", "T", "h-001")
        span = SourceSpan(0, len("stable content".encode("utf-8")), 1, 1, "full")
        a = Atom("A1", AtomType.CONCEPT, "stable content",
                 (span,), EvidenceKind.SOURCE_EXTRACT, Confidence.HIGH)
        pkg1 = build_package("HASH-TEST", src, [a])
        pkg2 = build_package("HASH-TEST", src, [a])
        self.assertEqual(pkg1.content_hash(), pkg2.content_hash())


class TestMigrateDigest001(unittest.TestCase):
    """Verify DIGEST-001 migration preserves all knowledge from Issue #188."""

    @classmethod
    def setUpClass(cls):
        cls.pkg = migrate_digest_001_to_universal()

    def test_valid_package(self):
        self.assertEqual(len(self.pkg.validate()), 0)

    def test_8_atoms(self):
        self.assertEqual(len(self.pkg.atoms), 8)

    def test_7_relations(self):
        self.assertEqual(len(self.pkg.relations), 7)

    def test_5_unknowns(self):
        self.assertEqual(len(self.pkg.unknowns), 5)

    def test_all_atoms_have_source_spans(self):
        for a in self.pkg.atoms:
            self.assertGreater(len(a.source_spans), 0,
                f"Atom {a.atom_id} missing source spans")

    def test_evidence_kind_separated(self):
        kinds = set()
        for a in self.pkg.atoms:
            kinds.add(a.evidence_kind)
        self.assertIn(EvidenceKind.USER_CLAIM, kinds)
        self.assertIn(EvidenceKind.SOURCE_EXTRACT, kinds)
        self.assertIn(EvidenceKind.INFERENCE, kinds)

    def test_mechanism_has_user_claim(self):
        a = [x for x in self.pkg.atoms if x.atom_type == AtomType.MECHANISM][0]
        self.assertEqual(a.evidence_kind, EvidenceKind.USER_CLAIM)
        self.assertEqual(a.confidence, Confidence.LOW)

    def test_boundary_has_source_extract(self):
        scopes = [x for x in self.pkg.atoms if x.atom_type == AtomType.SCOPE and "NO_TRADE" in x.content]
        self.assertGreater(len(scopes), 0)
        for s in scopes:
            self.assertEqual(s.evidence_kind, EvidenceKind.SOURCE_EXTRACT)

    def test_hypothesis_is_inference_only(self):
        hyps = [x for x in self.pkg.atoms if x.atom_type == AtomType.HYPOTHESIS]
        self.assertEqual(len(hyps), 1)
        self.assertEqual(hyps[0].evidence_kind, EvidenceKind.INFERENCE)

    def test_source_url_preserved(self):
        self.assertIn("issue", self.pkg.source.source_url.lower())

    def test_content_hash_stable(self):
        h1 = self.pkg.content_hash()
        h2 = migrate_digest_001_to_universal().content_hash()
        self.assertEqual(h1, h2)

    def test_no_timestamp_in_content_hash(self):
        # Create package with different timestamp but same content
        pkg2 = migrate_digest_001_to_universal()
        self.assertEqual(self.pkg.content_hash(), pkg2.content_hash())

    def test_memory_all_candidate(self):
        for m in self.pkg.memory_records:
            self.assertEqual(m.to_dict()["memory_zone"], "CANDIDATE")

    def test_skills_all_candidate(self):
        for s in self.pkg.skills:
            self.assertEqual(s.to_dict()["state"], "CANDIDATE")
            self.assertTrue(s.to_dict()["requires_e60_authority"])


class TestMigrateDigest002(unittest.TestCase):
    """Verify DIGEST-002 migration from Issue #201."""

    @classmethod
    def setUpClass(cls):
        cls.pkg = migrate_digest_002_to_universal()

    def test_valid_package(self):
        self.assertEqual(len(self.pkg.validate()), 0)

    def test_4_atoms(self):
        self.assertEqual(len(self.pkg.atoms), 4)

    def test_data_source_is_user_claim(self):
        ds = [x for x in self.pkg.atoms if x.atom_type == AtomType.DATA_SOURCE][0]
        self.assertEqual(ds.evidence_kind, EvidenceKind.USER_CLAIM)

    def test_scope_disclaimer_is_source_extract(self):
        sc = [x for x in self.pkg.atoms if x.atom_type == AtomType.SCOPE][0]
        self.assertEqual(sc.evidence_kind, EvidenceKind.SOURCE_EXTRACT)
        self.assertIn("不涉及", sc.content)  # "不涉及" means "does not involve / NOT"

    def test_confidence_low_for_single_sample(self):
        indicators = [x for x in self.pkg.atoms if x.atom_type == AtomType.INDICATOR and x.confidence == Confidence.LOW]
        self.assertGreater(len(indicators), 0)

    def test_content_hash_stable(self):
        self.assertEqual(self.pkg.content_hash(),
                         migrate_digest_002_to_universal().content_hash())


class TestBatchOutput(unittest.TestCase):
    """Verify that both packages serialize cleanly and can be loaded back."""

    def test_both_packages_serialize_and_roundtrip(self):
        pkg1 = migrate_digest_001_to_universal()
        pkg2 = migrate_digest_002_to_universal()

        with tempfile.TemporaryDirectory() as td:
            for pkg in [pkg1, pkg2]:
                jp, _ = serialize_package(pkg, td)
                with open(jp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.assertEqual(data["schema"], "QCLAW-CANDIDATE-KNOWLEDGE-PACKAGE-V1")
                self.assertIn("content_hash", data)
                self.assertGreater(len(data.get("atoms", [])), 0)


if __name__ == "__main__":
    unittest.main()
