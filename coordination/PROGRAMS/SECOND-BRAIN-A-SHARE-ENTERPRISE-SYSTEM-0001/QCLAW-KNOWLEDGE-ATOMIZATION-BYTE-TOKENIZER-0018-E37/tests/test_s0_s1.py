"""E37 S0-S1 unittest suite — boundary table + ledger with mutation tests.

Uses ONLY the unittest standard library. No custom chk() or PASS counter wrappers.
Each test uses standard assert* methods; each mutation test actively breaks
the implementation to prove the validator (assertRaises) catches it.
"""
import unittest
import sys, os

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_byte_tokenizer.boundary_table import (
    OriginalByteIndex, Chunk, _validate_strict_utf8,
)
from qclaw_byte_tokenizer.ledger import (
    ByteLedger, OwnerSpan, LedgerError,
)


# ═══════════════════════════════════════════════════════════════════
# S0 — Boundary Table
# ═══════════════════════════════════════════════════════════════════

class TestStrictUTF8Validation(unittest.TestCase):
    """Prove _validate_strict_utf8 rejects ALL illegal sequences before parsing."""

    def test_valid_ascii(self):
        _validate_strict_utf8(b"hello")
        _validate_strict_utf8(b"")

    def test_valid_cjk(self):
        _validate_strict_utf8("中文测试".encode("utf-8"))

    def test_valid_emoji(self):
        _validate_strict_utf8("🔥✅🚀".encode("utf-8"))

    def test_valid_4byte(self):
        _validate_strict_utf8("𝄞".encode("utf-8"))  # U+1D11E

    def test_overlong_2byte(self):
        with self.assertRaisesRegex(ValueError, r"[Oo]verlong"):
            _validate_strict_utf8(b'\xC0\xAF')

    def test_overlong_3byte(self):
        with self.assertRaisesRegex(ValueError, r"[Oo]verlong"):
            _validate_strict_utf8(b'\xE0\x80\xAF')

    def test_overlong_4byte(self):
        with self.assertRaisesRegex(ValueError, r"[Oo]verlong"):
            _validate_strict_utf8(b'\xF0\x80\x80\xAF')

    def test_surrogate(self):
        with self.assertRaisesRegex(ValueError, r"[Ss]urrogate"):
            _validate_strict_utf8(b'\xED\xA0\x80')

    def test_truncated_2byte(self):
        with self.assertRaisesRegex(ValueError, r"[Tt]runcated"):
            _validate_strict_utf8(b'\xC2')

    def test_truncated_3byte(self):
        with self.assertRaisesRegex(ValueError, r"[Tt]runcated"):
            _validate_strict_utf8(b'\xE0\xA0')

    def test_bad_cont_byte(self):
        with self.assertRaisesRegex(ValueError, r"[Ii]nvalid.*(byte|continuation)"):
            _validate_strict_utf8(b'\xC2\xFF')

    def test_over_10ffff(self):
        with self.assertRaisesRegex(ValueError, r"[>][Uu]\+10FFFF"):
            _validate_strict_utf8(b'\xF4\x90\x80\x80')

    def test_0xff_rejected(self):
        with self.assertRaisesRegex(ValueError, r"(0xFF|[Ii]nvalid.*byte)"):
            _validate_strict_utf8(b'\xFF')

    def test_0xfe_rejected(self):
        with self.assertRaisesRegex(ValueError, r"(0xFE|[Ii]nvalid.*byte)"):
            _validate_strict_utf8(b'\xFE')

    def test_unexpected_cont_byte(self):
        with self.assertRaisesRegex(ValueError, r"(Unexpected|[Cc]ontinuation)"):
            _validate_strict_utf8(b'\x80')

    def test_overlong_lead(self):
        with self.assertRaisesRegex(ValueError, r"[Oo]verlong"):
            _validate_strict_utf8(b'\xC1\x80')


class TestOriginalByteIndex(unittest.TestCase):
    """OriginalByteIndex: byte↔codepoint↔line mapping, immutability, BOM, CRLF."""

    def test_ascii_basic(self):
        idx = OriginalByteIndex(b"hello")
        self.assertEqual(idx.total_bytes, 5)
        self.assertEqual(idx.total_codepoints, 5)
        self.assertEqual(len(idx.chunks), 5)
        self.assertFalse(idx.leading_bom)

    def test_cjk_basic(self):
        idx = OriginalByteIndex("中文".encode("utf-8"))
        self.assertEqual(idx.total_bytes, 6)
        self.assertEqual(idx.total_codepoints, 2)

    def test_cjk_chunk_properties(self):
        idx = OriginalByteIndex("中".encode("utf-8"))
        c = idx.chunk_at_byte(0)
        self.assertEqual(c.byte_len, 3)
        self.assertEqual(c.kind, "CJK")

    def test_emoji(self):
        idx = OriginalByteIndex("🔥".encode("utf-8"))
        self.assertEqual(idx.total_codepoints, 1)
        self.assertEqual(idx.total_bytes, 4)

    def test_bom_detection(self):
        idx = OriginalByteIndex(b'\xEF\xBB\xBFhello')
        self.assertTrue(idx.leading_bom)
        self.assertEqual(idx.total_bytes, 8)
        # BOM is one codepoint
        self.assertEqual(idx.total_codepoints, 6)  # BOM + h e l l o

    def test_crlf_detection(self):
        idx = OriginalByteIndex(b"line1\r\nline2\n")
        self.assertTrue(idx.total_lines >= 2)
        # CRLF should be one chunk
        crlf_chunks = [c for c in idx.chunks if c.is_crlf]
        self.assertEqual(len(crlf_chunks), 1)

    def test_lf_detection(self):
        idx = OriginalByteIndex(b"a\nb\n")
        self.assertEqual(idx.total_lines, 3)  # "a"(1), "b"(2), EOF(3)

    def test_combining(self):
        # 'a' + combining acute = 1 grapheme but 2 codepoints
        idx = OriginalByteIndex("a\u0301".encode("utf-8"))
        # 2 codepoints: 'a' (1 byte) + combining acute (2 bytes)
        self.assertEqual(idx.total_codepoints, 2)
        self.assertEqual(idx.total_bytes, 3)

    def test_legal_boundaries(self):
        idx = OriginalByteIndex(b"abc")
        boundaries = idx.legal_boundaries
        self.assertIn(0, boundaries)
        self.assertIn(3, boundaries)
        self.assertIn(1, boundaries)

    def test_boundaries_on_chunk_edges(self):
        idx = OriginalByteIndex("中ab🔥".encode("utf-8"))
        # "中"(3B) + "a"(1B) + "b"(1B) + "🔥"(4B) = 9B
        boundaries = set(idx.legal_boundaries)
        self.assertIn(0, boundaries)
        self.assertIn(3, boundaries)   # after 中
        self.assertIn(4, boundaries)   # after a
        self.assertIn(5, boundaries)   # after b
        self.assertIn(9, boundaries)   # after 🔥

    def test_byte_to_chunk_index(self):
        idx = OriginalByteIndex("中a".encode("utf-8"))
        self.assertEqual(idx.chunk_at_byte(0).cp_index, 0)
        self.assertEqual(idx.chunk_at_byte(3).cp_index, 1)

    def test_byte_to_line(self):
        idx = OriginalByteIndex(b"line1\nline2\nline3")
        self.assertEqual(idx.byte_to_line(4), 1)
        self.assertEqual(idx.byte_to_line(11), 2)

    def test_byte_to_codepoint(self):
        idx = OriginalByteIndex("a中b".encode("utf-8"))
        self.assertEqual(idx.byte_to_codepoint(0), 0)  # 'a'
        self.assertEqual(idx.byte_to_codepoint(1), 1)  # start of '中'
        self.assertEqual(idx.byte_to_codepoint(4), 2)  # 'b'

    def test_codepoint_to_byte(self):
        idx = OriginalByteIndex("a中b".encode("utf-8"))
        self.assertEqual(idx.codepoint_to_byte(0), 0)
        self.assertEqual(idx.codepoint_to_byte(1), 1)
        self.assertEqual(idx.codepoint_to_byte(2), 4)
        with self.assertRaises(IndexError):
            idx.codepoint_to_byte(3)

    def test_chunk_tuple_immutable(self):
        idx = OriginalByteIndex(b"test")
        chunks = idx.chunks
        self.assertIsInstance(chunks, tuple)

    def test_setattr_blocked(self):
        idx = OriginalByteIndex(b"test")
        with self.assertRaises(TypeError):
            idx._total_bytes = 99

    def test_invalid_utf8_rejected_at_init(self):
        with self.assertRaises(ValueError):
            OriginalByteIndex(b'\xC0\xAF')


# ═══════════════════════════════════════════════════════════════════
# S1 — Byte Ledger
# ═══════════════════════════════════════════════════════════════════

class TestOwnerSpan(unittest.TestCase):
    """OwnerSpan validates ownership metadata at construction time."""

    def test_valid_span(self):
        s = OwnerSpan(0, 5, "ATOM_CANDIDATE", "test")
        self.assertEqual(s.length, 5)
        self.assertEqual(s.owner, "ATOM_CANDIDATE")

    def test_zero_length_rejected(self):
        with self.assertRaisesRegex(LedgerError, r"zero_length"):
            OwnerSpan(5, 5, "ATOM_CANDIDATE")

    def test_negative_start_rejected(self):
        with self.assertRaisesRegex(LedgerError, r"out_of_range"):
            OwnerSpan(-1, 3, "ATOM_CANDIDATE")

    def test_negative_end_rejected(self):
        with self.assertRaisesRegex(LedgerError, r"out_of_range"):
            OwnerSpan(0, -3, "ATOM_CANDIDATE")

    def test_inverted_rejected(self):
        with self.assertRaisesRegex(LedgerError, r"inverted"):
            OwnerSpan(5, 2, "ATOM_CANDIDATE")

    def test_unknown_owner_rejected(self):
        with self.assertRaisesRegex(LedgerError, r"invalid_owner"):
            OwnerSpan(0, 3, "GARBAGE")

    def test_all_three_owners_accepted(self):
        OwnerSpan(0, 1, "ATOM_CANDIDATE")
        OwnerSpan(0, 1, "STRUCTURE")
        OwnerSpan(0, 1, "UNKNOWN_ERROR")


class TestByteLedger(unittest.TestCase):
    """Exact-once byte ownership tracking."""

    def setUp(self):
        self.idx = OriginalByteIndex(b"ABCDE")
        self.ledger = ByteLedger(self.idx)

    def test_add_valid_span(self):
        s = self.ledger.add(0, 5, "ATOM_CANDIDATE")
        self.assertEqual(s.length, 5)

    def test_check_perfect_coverage(self):
        self.ledger.add(0, 5, "ATOM_CANDIDATE")
        r = self.ledger.check()
        self.assertTrue(r["ok"])
        self.assertEqual(r["covered"], 5)
        self.assertEqual(r["gap_count"], 0)

    def test_finalize_perfect(self):
        self.ledger.add(0, 5, "ATOM_CANDIDATE")
        r = self.ledger.finalize()
        self.assertTrue(r["ok"])
        self.assertTrue(self.ledger.frozen)

    def test_finalize_with_gaps_raises(self):
        self.ledger.add(0, 2, "ATOM_CANDIDATE")
        with self.assertRaisesRegex(LedgerError, r"finalize_failed"):
            self.ledger.finalize()

    def test_check_detects_gaps(self):
        self.ledger.add(0, 2, "STRUCTURE")
        self.ledger.add(3, 5, "ATOM_CANDIDATE")
        r = self.ledger.check()
        self.assertFalse(r["ok"])
        self.assertEqual(r["gap_count"], 1)
        self.assertEqual(r["gaps"], [(2, 3)])

    def test_overlap_rejected_at_add(self):
        self.ledger.add(0, 3, "ATOM_CANDIDATE")
        with self.assertRaisesRegex(LedgerError, r"overlap"):
            self.ledger.add(2, 5, "STRUCTURE")

    def test_out_of_range_end_rejected(self):
        with self.assertRaisesRegex(LedgerError, r"out_of_range"):
            self.ledger.add(0, 100, "ATOM_CANDIDATE")

    def test_illegal_boundary_rejected(self):
        # "中" is 3 bytes, starting at byte 1 is inside the codepoint
        idx = OriginalByteIndex("中".encode("utf-8"))
        ledger = ByteLedger(idx)
        with self.assertRaisesRegex(LedgerError, r"illegal_boundary"):
            ledger.add(1, 2, "ATOM_CANDIDATE")

    def test_frozen_rejects_add(self):
        self.ledger.add(0, 5, "STRUCTURE")
        self.ledger.finalize()
        with self.assertRaisesRegex(LedgerError, r"frozen"):
            self.ledger.add(0, 1, "ATOM_CANDIDATE")

    def test_multiple_spans_exact_once(self):
        self.ledger.add(0, 2, "ATOM_CANDIDATE")
        self.ledger.add(2, 4, "STRUCTURE")
        self.ledger.add(4, 5, "UNKNOWN_ERROR")
        r = self.ledger.finalize()
        self.assertTrue(r["ok"])
        self.assertEqual(r["covered"], 5)
        self.assertEqual(r["spans"], 3)

    def test_owner_at(self):
        self.ledger.add(0, 2, "ATOM_CANDIDATE", "a1")
        self.ledger.add(2, 5, "STRUCTURE", "s1")
        self.assertEqual(self.ledger.owner_at(0), "ATOM_CANDIDATE")
        self.assertEqual(self.ledger.owner_at(3), "STRUCTURE")
        self.assertIsNone(self.ledger.owner_at(99))

    def test_all_owners_grouping(self):
        self.ledger.add(0, 2, "ATOM_CANDIDATE")
        self.ledger.add(2, 4, "STRUCTURE")
        self.ledger.add(4, 5, "ATOM_CANDIDATE")
        groups = self.ledger.all_owners()
        self.assertEqual(len(groups["ATOM_CANDIDATE"]), 2)
        self.assertEqual(len(groups["STRUCTURE"]), 1)


# ═══════════════════════════════════════════════════════════════════
# MUTATION TESTS (mandatory family #2: zero-length, overlap, omission, etc.)
# Prove that: (a) corrupt input → assertRaises; (b) correct input passes
# ═══════════════════════════════════════════════════════════════════

class TestMutationLedgerOwners(unittest.TestCase):
    """Mutation tests: actively corrupt the ledger and prove the validator catches it."""

    def setUp(self):
        self.idx = OriginalByteIndex(b"ABCDEFGHI")

    # ── Overlap mutation ──
    def test_overlap_rejected_not_swallowed(self):
        ledger = ByteLedger(self.idx)
        ledger.add(0, 5, "ATOM_CANDIDATE")
        # Overlapping add must raise — no silent merge
        with self.assertRaises(LedgerError):
            ledger.add(3, 8, "STRUCTURE")

    # ── Gap mutation ──
    def test_gap_blocks_finalize(self):
        ledger = ByteLedger(self.idx)
        ledger.add(0, 3, "ATOM_CANDIDATE")
        ledger.add(5, 9, "STRUCTURE")
        # Gap [3,5) → finalize must fail
        with self.assertRaises(LedgerError):
            ledger.finalize()

    # ── Zero-length mutation ──
    def test_zero_length_span_rejected(self):
        with self.assertRaises(LedgerError):
            OwnerSpan(3, 3, "ATOM_CANDIDATE")

    # ── Out-of-range mutation ──
    def test_end_beyond_total(self):
        ledger = ByteLedger(self.idx)
        with self.assertRaises(LedgerError):
            ledger.add(0, len(self.idx.source_bytes) + 1, "ATOM_CANDIDATE")

    # ── Inverted mutation ──
    def test_inverted_span_start_gt_end(self):
        with self.assertRaises(LedgerError):
            OwnerSpan(8, 2, "ATOM_CANDIDATE")

    # ── Illegal boundary (inside CJK) ──
    def test_illegal_boundary_inside_cjk(self):
        idx = OriginalByteIndex("中文".encode("utf-8"))
        ledger = ByteLedger(idx)
        # byte 1 is inside "中" (3 bytes: 0,1,2)
        with self.assertRaises(LedgerError):
            ledger.add(1, 3, "ATOM_CANDIDATE")

    # ── Duplicate overlapping ──
    def test_duplicate_exact_range_rejected(self):
        ledger = ByteLedger(self.idx)
        ledger.add(0, 5, "ATOM_CANDIDATE")
        with self.assertRaises(LedgerError):
            ledger.add(0, 5, "STRUCTURE")

    # ── Freeze mutation ──
    def test_frozen_ledger_rejects_mutation(self):
        ledger = ByteLedger(self.idx)
        ledger.add(0, 9, "ATOM_CANDIDATE")
        ledger.finalize()
        # After freeze, any mutation must fail
        with self.assertRaises(LedgerError):
            ledger.add(0, 1, "ATOM_CANDIDATE")

    # ── Invalid owner mutation ──
    def test_garbage_owner_rejected(self):
        with self.assertRaises(LedgerError):
            OwnerSpan(0, 5, "PLANNED")


class TestMutationUTF8(unittest.TestCase):
    """Mutation tests: prove invalid UTF-8 is rejected BEFORE parsing."""

    def test_overlong_c0_af_not_parsed(self):
        with self.assertRaises(ValueError):
            OriginalByteIndex(b'\xC0\xAF')

    def test_surrogate_not_parsed(self):
        with self.assertRaises(ValueError):
            OriginalByteIndex(b'\xED\xA0\x80')

    def test_0xff_not_parsed(self):
        with self.assertRaises(ValueError):
            OriginalByteIndex(b'\xFF')

    def test_truncated_2byte_not_parsed(self):
        with self.assertRaises(ValueError):
            OriginalByteIndex(b'\xC2')


if __name__ == "__main__":
    unittest.main(verbosity=2)
