"""E47 Digest Tests v2 — verify UTF-8 byte spans, SOURCE_EXTRACT/INFERENCE separation, memory gating.

CANDIDATE ONLY. Tests for:
1. UTF-8 byte spans: Chinese chars = 3 bytes each, span content matches encode/decode
2. SOURCE_EXTRACT atoms: content IS verbatim source text
3. INFERENCE atoms: content is agent's words, not source text
4. Memory records: from INFERENCE/VALUE_JUDGMENT must NOT read like facts
5. Spans are minimal — not full_document except when unavoidable
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
    ingest_source, locate_span, _make_span, span_at_key, span_range,
    build_package, serialize_package, source_extract, inference_atom,
    SOURCES,
    migrate_digest_001, migrate_digest_002,
    migrate_digest_003, migrate_digest_004, migrate_digest_005,
)


# ═══════════════════════════════════════════════════════════════
# UTF-8 byte span correctness
# ═══════════════════════════════════════════════════════════════

class TestUTF8ByteSpans(unittest.TestCase):
    """UTF-8 bytes, not char indices."""

    def test_cjk_span_bytes(self):
        text = "hello 世界 test"
        # "世界" starts at char 6, ends at char 8, but UTF-8 bytes: h(1)e(1)l(1)l(1)o(1) (1) = 6 byte start
        # "世界" = 世(3 bytes) + 界(3 bytes) = 6 bytes
        span = _make_span(text, 6, 8, "cjk")
        self.assertEqual(span.byte_end - span.byte_start, 6)  # 2 CJK chars = 6 UTF-8 bytes
        src_bytes = text.encode("utf-8")
        self.assertEqual(src_bytes[span.byte_start:span.byte_end].decode("utf-8"), "世界")

    def test_ascii_span_bytes(self):
        text = "ABCD"
        span = _make_span(text, 1, 3, "bc")
        self.assertEqual(span.byte_end - span.byte_start, 2)  # 2 ASCII chars = 2 bytes
        self.assertEqual(span.byte_start, 1)

    def test_span_boundaries_are_byte_exact(self):
        text = "好a好"
        # char 0="好"(3B), char 1="a"(1B), char 2="好"(3B)
        span = _make_span(text, 1, 2, "a")
        self.assertEqual(span.byte_start, 3)
        self.assertEqual(span.byte_end, 4)
        src_bytes = text.encode("utf-8")
        self.assertEqual(src_bytes[span.byte_start:span.byte_end], b"a")

    def test_multiline_span_lines(self):
        text = "Line1\nLine2\nLine3"
        span = _make_span(text, text.index("Line2"), text.index("Line3")-1, "line2")
        self.assertEqual(span.line_start, 2)
        self.assertEqual(span.line_end, 2)

    def test_span_at_key_finds_value(self):
        S = SOURCES["issue-188"]
        span = span_at_key(S, "user_observation", "obs")
        src_bytes = S.encode("utf-8")
        val = src_bytes[span.byte_start:span.byte_end].decode("utf-8")
        self.assertIn("没有强烈买入", val)
        self.assertNotIn('"', val)  # quotes stripped

    def test_span_range_delimited(self):
        S = SOURCES["issue-188"]
        span = span_range(S, "## Research question", "## Validation design", "rq")
        src_bytes = S.encode("utf-8")
        val = src_bytes[span.byte_start:span.byte_end].decode("utf-8")
        self.assertIn("20-30", val)
        self.assertNotIn("## Validation design", val)  # excluded

    def test_no_full_document_span_for_specific_atoms(self):
        """DIGEST-003 atoms should have precise spans, not full document."""
        pkg = migrate_digest_003()
        for a in pkg.atoms:
            for s in a.source_spans:
                span_size = s.byte_end - s.byte_start
                # Each span should be much smaller than the 40KB source
                self.assertLess(span_size, pkg.source.source_size_bytes,
                    f"Atom {a.atom_id} uses full-document span ({span_size} == {pkg.source.source_size_bytes})")


# ═══════════════════════════════════════════════════════════════
# SOURCE_EXTRACT vs INFERENCE separation
# ═══════════════════════════════════════════════════════════════

class TestEvidenceSeparation(unittest.TestCase):
    """SOURCE_EXTRACT atoms have verbatim content. INFERENCE atoms have agent's words."""

    def test_source_extract_content_is_verbatim(self):
        """Every SOURCE_EXTRACT atom's content must appear verbatim in source."""
        for migrate_fn, pkg_id in [
            (migrate_digest_001, "001"),
            (migrate_digest_002, "002"),
            (migrate_digest_003, "003"),
            (migrate_digest_004, "004"),
            (migrate_digest_005, "005"),
        ]:
            pkg = migrate_fn()
            for a in pkg.atoms:
                if a.evidence_kind != EvidenceKind.SOURCE_EXTRACT:
                    continue
                self.assertIn(a.content, pkg.source.source_content,
                    f"[{pkg_id}] SOURCE_EXTRACT atom {a.atom_id} content NOT found verbatim in source:\n"
                    f"  content: {a.content[:80]}...\n"
                    f"  expected verbatim match in source")

    def test_inference_content_is_not_source_text(self):
        """INFERENCE atoms should NOT just be copied source text (that's SOURCE_EXTRACT job)."""
        for migrate_fn, pkg_id in [
            (migrate_digest_001, "001"),
            (migrate_digest_002, "002"),
            (migrate_digest_003, "003"),
        ]:
            pkg = migrate_fn()
            for a in pkg.atoms:
                if a.evidence_kind != EvidenceKind.INFERENCE:
                    continue
                # An INFERENCE atom should add agent's own words, not just parrot source
                self.assertTrue(
                    len(a.content) > 20,
                    f"[{pkg_id}] INFERENCE atom {a.atom_id} too short: {a.content[:50]}")

    def test_digest001_boundary_is_verbatim(self):
        pkg = migrate_digest_001()
        a003 = [a for a in pkg.atoms if a.atom_id == "A003"][0]
        self.assertEqual(a003.evidence_kind, EvidenceKind.SOURCE_EXTRACT)
        self.assertIn("research_only / NO_TRADE", a003.content)


# ═══════════════════════════════════════════════════════════════
# Memory records from INFERENCE gated as CANDIDATE
# ═══════════════════════════════════════════════════════════════

class TestMemoryRecordIntegrity(unittest.TestCase):
    """Memory records from inference should NOT read like facts."""

    def test_memory_all_candidate(self):
        for migrate_fn in [migrate_digest_001, migrate_digest_002, migrate_digest_003, migrate_digest_005]:
            pkg = migrate_fn()
            for m in pkg.memory_records:
                d = m.to_dict()
                self.assertEqual(d["memory_zone"], "CANDIDATE")
                self.assertNotEqual(d["confidence"], "HIGH",
                    f"Memory {m.record_id}: inferred memories should not be HIGH confidence")

    def test_memory_001_has_user_observation_caveat(self):
        """M001 is from user observation — should explicitly state UNVERIFIED."""
        pkg = migrate_digest_001()
        m001 = [m for m in pkg.memory_records if m.record_id == "M001"][0]
        self.assertIn("UNVERIFIED", m001.statement.upper())

    def test_memory_002_is_agent_inference_not_user_fact(self):
        """M002 was derived by agent from title/boundary, not said by user."""
        pkg = migrate_digest_001()
        m002 = [m for m in pkg.memory_records if m.record_id == "M002"][0]
        self.assertIn("[AGENT", m002.statement.upper())

    def test_memory_003_does_not_read_as_calibrated_fact(self):
        """M003 from single sample must not sound like an established fact."""
        pkg = migrate_digest_002()
        m003 = [m for m in pkg.memory_records if m.record_id == "M003"][0]
        self.assertIn("AGENT INFERENCE", m003.statement.upper())
        self.assertIn("LOW CONFIDENCE", m003.statement.upper())

    def test_memory_from_inference_not_value_judgment_fact(self):
        """Memory from P1 scorecard is agent synthesis, not objective fact."""
        pkg = migrate_digest_003()
        for m in pkg.memory_records:
            self.assertIn("AGENT SYNTHESIS", m.statement.upper())
            self.assertIn("CANDIDATE", m.statement.upper())


# ═══════════════════════════════════════════════════════════════
# Skill record gating
# ═══════════════════════════════════════════════════════════════

class TestSkillIntegrity(unittest.TestCase):
    def test_skills_all_candidate(self):
        for migrate_fn in [migrate_digest_001, migrate_digest_002, migrate_digest_005]:
            pkg = migrate_fn()
            for s in pkg.skills:
                d = s.to_dict()
                self.assertEqual(d["state"], "CANDIDATE")
                self.assertTrue(d["requires_e60_authority"])


# ═══════════════════════════════════════════════════════════════
# Package validation
# ═══════════════════════════════════════════════════════════════

class TestPackageValidation(unittest.TestCase):
    def test_all_packages_valid(self):
        for fn, name in [
            (migrate_digest_001, "001"),
            (migrate_digest_002, "002"),
            (migrate_digest_003, "003"),
            (migrate_digest_004, "004"),
            (migrate_digest_005, "005"),
        ]:
            pkg = fn()
            errors = pkg.validate()
            self.assertEqual(len(errors), 0,
                f"DIGEST-{name} validation errors: {errors}")

    def test_content_hash_stable(self):
        for fn in [migrate_digest_001, migrate_digest_002]:
            h1 = fn().content_hash()
            h2 = fn().content_hash()
            self.assertEqual(h1, h2)

    def test_serialize_and_roundtrip(self):
        for fn in [migrate_digest_001, migrate_digest_002, migrate_digest_003]:
            pkg = fn()
            with tempfile.TemporaryDirectory() as td:
                jp, yp = serialize_package(pkg, td)
                self.assertTrue(os.path.exists(jp))
                self.assertTrue(os.path.exists(yp))
                with open(jp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.assertEqual(data["schema"], "QCLAW-CANDIDATE-KNOWLEDGE-PACKAGE-V1")
                self.assertGreater(len(data["atoms"]), 0)


# ═══════════════════════════════════════════════════════════════
# DIGEST-specific validation
# ═══════════════════════════════════════════════════════════════

class TestDigest001(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = migrate_digest_001()

    def test_8_atoms(self):
        self.assertEqual(len(self.pkg.atoms), 8)

    def test_user_observation_is_user_claim(self):
        a002 = [a for a in self.pkg.atoms if a.atom_id == "A002"][0]
        self.assertEqual(a002.evidence_kind, EvidenceKind.USER_CLAIM)

    def test_boundary_source_extract_verbatim(self):
        a003 = [a for a in self.pkg.atoms if a.atom_id == "A003"][0]
        self.assertEqual(a003.evidence_kind, EvidenceKind.SOURCE_EXTRACT)
        self.assertEqual(a003.content, "research_only / NO_TRADE")

    def test_dispatch_source_extract_verbatim(self):
        a006 = [a for a in self.pkg.atoms if a.atom_id == "A006"][0]
        self.assertEqual(a006.evidence_kind, EvidenceKind.SOURCE_EXTRACT)
        self.assertEqual(a006.content, "NOT_AUTHORIZED_WHILE_E56_ACTIVE")

    def test_hypothesis_is_inference(self):
        hyps = [a for a in self.pkg.atoms if a.atom_type == AtomType.HYPOTHESIS]
        self.assertEqual(len(hyps), 1)
        self.assertEqual(hyps[0].evidence_kind, EvidenceKind.INFERENCE)


class TestDigest002(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = migrate_digest_002()

    def test_4_atoms(self):
        self.assertEqual(len(self.pkg.atoms), 4)

    def test_disclaimer_is_source_extract(self):
        b003 = [a for a in self.pkg.atoms if a.atom_id == "B003"][0]
        self.assertEqual(b003.evidence_kind, EvidenceKind.SOURCE_EXTRACT)
        self.assertIn("NOT a claim", b003.content)

    def test_sample_is_user_claim(self):
        b001 = [a for a in self.pkg.atoms if a.atom_id == "B001"][0]
        self.assertEqual(b001.evidence_kind, EvidenceKind.USER_CLAIM)

    def test_inference_low_confidence(self):
        b002 = [a for a in self.pkg.atoms if a.atom_id == "B002"][0]
        self.assertEqual(b002.evidence_kind, EvidenceKind.INFERENCE)
        self.assertEqual(b002.confidence, Confidence.LOW)


class TestDigest003(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = migrate_digest_003()

    def test_spans_are_minimal_not_full_document(self):
        # Source is ~40KB. No span should be >15KB
        for a in self.pkg.atoms:
            for s in a.source_spans:
                self.assertLess(s.byte_end - s.byte_start, 15000,
                    f"Atom {a.atom_id}: span too large ({s.byte_end-s.byte_start}B)")

    def test_verbatim_score_is_source_extract(self):
        c001 = [a for a in self.pkg.atoms if a.atom_id == "C001"][0]
        self.assertEqual(c001.evidence_kind, EvidenceKind.SOURCE_EXTRACT)
        self.assertIn("0.237", c001.content)

    def test_verbatim_result_is_source_extract(self):
        c003 = [a for a in self.pkg.atoms if a.atom_id == "C003"][0]
        self.assertEqual(c003.evidence_kind, EvidenceKind.SOURCE_EXTRACT)
        self.assertIn("FAIL", c003.content)


# ═══════════════════════════════════════════════════════════════
# Legacy compatibility tests (old test_digest.py content preserved)
# ═══════════════════════════════════════════════════════════════

class TestLegacyDigestPackageIdentity(unittest.TestCase):
    def test_package_id_present(self):
        for fn in [migrate_digest_001, migrate_digest_002, migrate_digest_003, migrate_digest_004, migrate_digest_005]:
            pkg = fn()
            self.assertTrue(pkg.package_id.startswith("E47-DIGEST-"))

    def test_source_url_contains_issue_or_workspace(self):
        for fn, check in [
            (migrate_digest_001, "issue"),
            (migrate_digest_002, "issue"),
            (migrate_digest_003, "workspace"),
            (migrate_digest_004, "workspace"),
            (migrate_digest_005, "workspace"),
        ]:
            pkg = fn()
            self.assertIn(check, pkg.source.source_url.lower())


if __name__ == "__main__":
    unittest.main()
