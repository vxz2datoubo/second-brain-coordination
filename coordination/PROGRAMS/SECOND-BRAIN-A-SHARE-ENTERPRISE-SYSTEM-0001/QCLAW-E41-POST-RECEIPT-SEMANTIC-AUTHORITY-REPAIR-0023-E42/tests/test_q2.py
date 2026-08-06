"""E42 Q2 — Source Traceability Tests"""
import unittest, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_e42.source_trace import (
    SourceDocument, SourceSpan, extract_paragraphs,
    TerminologyMapping, DigestedSegment, LinkRegistry,
)


class TestSourceDocument(unittest.TestCase):
    def test_create_document(self):
        doc = SourceDocument.create("D001", b"hello world")
        self.assertEqual(doc.document_id, "D001")
        self.assertEqual(doc.length, 11)
        self.assertEqual(doc.digest, doc.digest)  # deterministic
        self.assertEqual(len(doc.digest), 64)

    def test_slice_verified(self):
        doc = SourceDocument.create("D002", b"0123456789")
        self.assertEqual(doc.slice(2, 5), b"234")

    def test_slice_out_of_range_rejected(self):
        doc = SourceDocument.create("D003", b"test")
        with self.assertRaises(IndexError):
            doc.slice(-1, 2)
        with self.assertRaises(IndexError):
            doc.slice(0, 5)
        with self.assertRaises(IndexError):
            doc.slice(3, 2)

    def test_requires_bytes(self):
        with self.assertRaises(TypeError):
            SourceDocument.create("D004", "not bytes")

    def test_different_content_different_digest(self):
        d1 = SourceDocument.create("D1", b"hello")
        d2 = SourceDocument.create("D2", b"world")
        self.assertNotEqual(d1.digest, d2.digest)

    def test_same_content_same_digest(self):
        d1 = SourceDocument.create("D1", b"same")
        d2 = SourceDocument.create("D2", b"same")
        self.assertEqual(d1.digest, d2.digest)


class TestSourceSpan(unittest.TestCase):
    def setUp(self):
        self.doc = SourceDocument.create("SDOC", b"This is a test.")

    def test_valid_span(self):
        span = SourceSpan(self.doc, 0, 4)
        self.assertEqual(span.content, b"This")
        self.assertEqual(span.content_utf8, "This")

    def test_span_content_from_document_not_caller(self):
        """Content always retrieved from document slice."""
        span = SourceSpan(self.doc, 5, 7)
        self.assertEqual(span.content, b"is")

    def test_out_of_range_rejected(self):
        with self.assertRaises(IndexError):
            SourceSpan(self.doc, 0, 100)

    def test_inverted_span_rejected(self):
        with self.assertRaises(ValueError):
            SourceSpan(self.doc, 5, 2)

    def test_span_role(self):
        span = SourceSpan(self.doc, 0, 4, "header")
        self.assertEqual(span.span_role, "header")

    def test_with_role(self):
        span = SourceSpan(self.doc, 0, 4, "content")
        self.assertEqual(span.with_role("header").span_role, "header")


class TestExtractParagraphs(unittest.TestCase):
    def test_single_paragraph(self):
        doc = SourceDocument.create("P1", b"One paragraph.")
        paras = extract_paragraphs(doc)
        self.assertEqual(len(paras), 1)
        self.assertEqual(paras[0].text, "One paragraph.")

    def test_multiple_paragraphs(self):
        doc = SourceDocument.create("P2",
            b"First paragraph.\n\nSecond paragraph.\n\nThird.")
        paras = extract_paragraphs(doc)
        self.assertEqual(len(paras), 3)

    def test_leading_whitespace_preserved(self):
        doc = SourceDocument.create("P3", b"\n\nContent.\n\nMore.")
        paras = extract_paragraphs(doc)
        self.assertEqual(len(paras), 2)
        self.assertEqual(paras[0].text, "Content.")

    def test_no_strip_content(self):
        """Content text must not be stripped — exact bytes preserved."""
        doc = SourceDocument.create("P4", b"  leading spaces  .\n\nMore.")
        paras = extract_paragraphs(doc)
        self.assertEqual(paras[0].text, "  leading spaces  .")

    def test_empty_input(self):
        doc = SourceDocument.create("P5", b"   \n\n   ")
        paras = extract_paragraphs(doc)
        self.assertEqual(len(paras), 0)

    def test_crlf_paragraphs(self):
        doc = SourceDocument.create("P6",
            b"A line.\r\n\r\nB line.\r\n\r\nC line.")
        paras = extract_paragraphs(doc)
        self.assertEqual(len(paras), 3)

    def test_span_offsets_in_range(self):
        doc = SourceDocument.create("P7", b"Para 1.\n\nPara 2.")
        paras = extract_paragraphs(doc)
        for p in paras:
            for s in p.spans:
                self.assertTrue(s.byte_start >= 0)
                self.assertTrue(s.byte_end <= doc.length)
                self.assertTrue(s.byte_start <= s.byte_end)


class TestTerminologyMapping(unittest.TestCase):
    def test_apply_simple(self):
        tm = TerminologyMapping("M1", 1, rules=(("RSI", "Relative Strength Index"),))
        self.assertEqual(tm.apply("RSI indicator"), "Relative Strength Index indicator")

    def test_version_immutable(self):
        tm = TerminologyMapping("M2", 1, rules=(("a", "b"),))
        self.assertEqual(tm.version, 1)

    def test_no_match_no_change(self):
        tm = TerminologyMapping("M3", 1, rules=(("XYZ", "ABC"),))
        self.assertEqual(tm.apply("hello"), "hello")

    def test_does_not_alter_original(self):
        """Mapping is a separate step, never silently alters quoted content."""
        tm = TerminologyMapping("M4", 1, rules=(("old", "new"),))
        original = "old term"
        result = tm.apply(original)
        self.assertEqual(result, "new term")
        self.assertEqual(original, "old term")  # original unchanged


class TestDigestedSegment(unittest.TestCase):
    def setUp(self):
        self.doc = SourceDocument.create("S1", b"Some source text content.")

    def test_create_segment(self):
        span = SourceSpan(self.doc, 0, 4)
        seg = DigestedSegment(
            segment_id="SEG1",
            source_span=span,
            normalized_text="Some",
            interpretation_status="direct_quote",
        )
        self.assertEqual(seg.segment_id, "SEG1")
        self.assertTrue(seg.is_quoted_source)

    def test_not_quoted(self):
        span = SourceSpan(self.doc, 0, 4)
        seg = DigestedSegment(
            segment_id="SEG2",
            source_span=span,
            normalized_text="Some",
            interpretation_status="interpreted",
        )
        self.assertFalse(seg.is_quoted_source)

    def test_linked_atom_ids_immutable(self):
        span = SourceSpan(self.doc, 0, 4)
        seg = DigestedSegment(
            segment_id="SEG3",
            source_span=span,
            normalized_text="Some",
            interpretation_status="direct_quote",
            linked_atom_ids=("A1", "A2"),
        )
        self.assertIsInstance(seg.linked_atom_ids, tuple)

    def test_provenance_recorded(self):
        span = SourceSpan(self.doc, 0, 4)
        seg = DigestedSegment(
            segment_id="SEG4",
            source_span=span,
            normalized_text="Some",
            interpretation_status="direct_quote",
            provenance=("SRC001", "PARSER_V1"),
        )
        self.assertIn("SRC001", seg.provenance)


class TestLinkRegistry(unittest.TestCase):
    def test_validate_registered(self):
        reg = LinkRegistry.create({"A1", "A2", "A3"})
        self.assertTrue(reg.validate("A1"))
        self.assertFalse(reg.validate("A4"))

    def test_filter_valid(self):
        reg = LinkRegistry.create({"A1", "A2"})
        filtered = reg.filter_valid(("A1", "A3", "A2", "A4"))
        self.assertEqual(filtered, ("A1", "A2"))

    def test_empty_registry_rejects_all(self):
        reg = LinkRegistry.create(set())
        self.assertFalse(reg.validate("anything"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
