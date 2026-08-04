"""E39 S1 tests — ByteLedger exact-once coverage with mutation rejection families."""
import unittest
import sys, os

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_strict_byte.utf8_guard import UTF8ByteIndex
from qclaw_strict_byte.ledger import (
    ByteLedger, OwnerSpan, LedgerError,
    OWNER_ATOM_CANDIDATE, OWNER_STRUCTURE, OWNER_UNKNOWN_ERROR,
)


# ═══════════════════════════════════════════════════════════════════════
# OwnerSpan validation
# ═══════════════════════════════════════════════════════════════════════

class TestOwnerSpan(unittest.TestCase):
    def test_valid_span(self):
        s = OwnerSpan(0, 10, OWNER_ATOM_CANDIDATE)
        self.assertEqual(s.byte_start, 0)
        self.assertEqual(s.byte_end, 10)
        self.assertEqual(s.byte_length, 10)
        self.assertEqual(s.owner, OWNER_ATOM_CANDIDATE)

    def test_struct_owner(self):
        s = OwnerSpan(0, 5, OWNER_STRUCTURE, "h1")
        self.assertEqual(s.owner, OWNER_STRUCTURE)
        self.assertEqual(s.label, "h1")

    def test_unknown_owner(self):
        s = OwnerSpan(5, 8, OWNER_UNKNOWN_ERROR, "bad bytes")
        self.assertEqual(s.owner, OWNER_UNKNOWN_ERROR)

    def test_negative_start(self):
        with self.assertRaises(LedgerError) as ctx:
            OwnerSpan(-1, 5, OWNER_ATOM_CANDIDATE)
        self.assertIn("out_of_range", str(ctx.exception))

    def test_negative_end(self):
        with self.assertRaises(LedgerError) as ctx:
            OwnerSpan(0, -1, OWNER_ATOM_CANDIDATE)
        self.assertIn("out_of_range", str(ctx.exception))

    def test_inverted(self):
        with self.assertRaises(LedgerError) as ctx:
            OwnerSpan(5, 3, OWNER_ATOM_CANDIDATE)
        self.assertIn("inverted", str(ctx.exception))

    def test_zero_length(self):
        with self.assertRaises(LedgerError) as ctx:
            OwnerSpan(5, 5, OWNER_ATOM_CANDIDATE)
        self.assertIn("zero_length", str(ctx.exception))

    def test_invalid_owner(self):
        with self.assertRaises(LedgerError) as ctx:
            OwnerSpan(0, 5, "ILLEGAL_OWNER")
        self.assertIn("invalid_owner", str(ctx.exception))


# ═══════════════════════════════════════════════════════════════════════
# ByteLedger happy path
# ═══════════════════════════════════════════════════════════════════════

class TestByteLedger(unittest.TestCase):
    def setUp(self):
        self.idx = UTF8ByteIndex(b"abcdefghij")
        self.ledger = ByteLedger(self.idx)

    def test_initial_state(self):
        self.assertFalse(self.ledger.frozen)
        self.assertEqual(self.ledger.total_bytes, 10)

    def test_add_single_span(self):
        span = self.ledger.add(0, 10, OWNER_ATOM_CANDIDATE)
        self.assertEqual(span.byte_start, 0)
        self.assertEqual(span.byte_end, 10)
        self.assertEqual(len(self.ledger.spans), 1)

    def test_add_multiple_non_overlapping(self):
        self.ledger.add(0, 3, OWNER_STRUCTURE)
        self.ledger.add(3, 7, OWNER_ATOM_CANDIDATE)
        self.ledger.add(7, 10, OWNER_STRUCTURE)
        self.assertEqual(len(self.ledger.spans), 3)

    def test_full_coverage_check(self):
        self.ledger.add(0, 10, OWNER_ATOM_CANDIDATE)
        diag = self.ledger.check()
        self.assertTrue(diag["complete"])
        self.assertEqual(diag["gap_count"], 0)
        self.assertEqual(diag["overlap_count"], 0)
        self.assertEqual(diag["covered"], 10)

    def test_gap_detection(self):
        self.ledger.add(0, 3, OWNER_ATOM_CANDIDATE)
        self.ledger.add(7, 10, OWNER_ATOM_CANDIDATE)
        diag = self.ledger.check()
        self.assertFalse(diag["complete"])
        self.assertEqual(diag["gap_count"], 1)
        self.assertEqual(diag["gaps"], [(3, 7)])

    def test_overlap_rejected_on_add(self):
        """Overlap is rejected at add() time."""
        self.ledger.add(0, 6, OWNER_ATOM_CANDIDATE)
        with self.assertRaises(LedgerError) as ctx:
            self.ledger.add(4, 10, OWNER_STRUCTURE)
        self.assertIn("overlap", str(ctx.exception))

    def test_finalize_success(self):
        self.ledger.add(0, 10, OWNER_ATOM_CANDIDATE)
        self.ledger.finalize()
        self.assertTrue(self.ledger.frozen)

    def test_finalize_with_gaps_raises(self):
        self.ledger.add(0, 5, OWNER_ATOM_CANDIDATE)
        with self.assertRaises(LedgerError) as ctx:
            self.ledger.finalize()
        self.assertIn("finalize_failed", str(ctx.exception))

    def test_finalize_idempotent(self):
        self.ledger.add(0, 10, OWNER_ATOM_CANDIDATE)
        self.ledger.finalize()
        self.ledger.finalize()  # no-op
        self.assertTrue(self.ledger.frozen)

    def test_add_after_freeze_raises(self):
        self.ledger.add(0, 10, OWNER_ATOM_CANDIDATE)
        self.ledger.finalize()
        with self.assertRaises(LedgerError) as ctx:
            self.ledger.add(0, 5, OWNER_STRUCTURE)
        self.assertIn("frozen", str(ctx.exception))

    def test_out_of_range_start(self):
        with self.assertRaises(LedgerError) as ctx:
            self.ledger.add(10, 10, OWNER_ATOM_CANDIDATE)
        self.assertIn("out_of_range", str(ctx.exception))

    def test_out_of_range_end(self):
        with self.assertRaises(LedgerError) as ctx:
            self.ledger.add(0, 11, OWNER_ATOM_CANDIDATE)
        self.assertIn("out_of_range", str(ctx.exception))

    def test_illegal_boundary_start(self):
        # For a 10-byte ASCII string, every byte is a boundary, so this
        # is only testable with CJK. Create UTF8ByteIndex with CJK.
        idx2 = UTF8ByteIndex("中".encode("utf-8"))  # 3 bytes, 1 codepoint
        ledger2 = ByteLedger(idx2)
        # byte 1 is mid-codepoint (not a boundary)
        with self.assertRaises(LedgerError) as ctx:
            ledger2.add(1, 3, OWNER_ATOM_CANDIDATE)
        self.assertIn("illegal_boundary", str(ctx.exception))

    def test_eof_is_legal_boundary(self):
        # end=total_bytes is always legal
        self.ledger.add(0, 10, OWNER_ATOM_CANDIDATE)
        self.assertEqual(len(self.ledger.spans), 1)

    def test_duplicate_exact_range(self):
        """Two spans with exactly same range — overlap reject."""
        self.ledger.add(0, 5, OWNER_ATOM_CANDIDATE)
        with self.assertRaises(LedgerError) as ctx:
            self.ledger.add(0, 5, OWNER_STRUCTURE)
        self.assertIn("overlap", str(ctx.exception))

    def test_empty_input_check(self):
        idx = UTF8ByteIndex(b"")
        ledger = ByteLedger(idx)
        diag = ledger.check()
        self.assertEqual(diag["total_bytes"], 0)
        self.assertTrue(diag["complete"])

    def test_owner_counts(self):
        self.ledger.add(0, 3, OWNER_STRUCTURE, "h1")
        self.ledger.add(3, 8, OWNER_ATOM_CANDIDATE, "a1")
        self.ledger.add(8, 10, OWNER_STRUCTURE, "h2")
        diag = self.ledger.check()
        self.assertEqual(diag["owners"].get(OWNER_STRUCTURE), 2)
        self.assertEqual(diag["owners"].get(OWNER_ATOM_CANDIDATE), 1)
        self.assertEqual(diag["covered"], 10)


# ═══════════════════════════════════════════════════════════════════════
# Mutation rejection families
# ═══════════════════════════════════════════════════════════════════════

class TestMutationLedgerOwners(unittest.TestCase):
    def setUp(self):
        idx = UTF8ByteIndex(b"ABCDEFGHIJ")
        self.ledger = ByteLedger(idx)

    def test_duplicate_exact_range_rejected(self):
        self.ledger.add(0, 5, OWNER_ATOM_CANDIDATE)
        with self.assertRaises(LedgerError):
            self.ledger.add(0, 5, OWNER_STRUCTURE)

    def test_end_beyond_total_rejected(self):
        with self.assertRaises(LedgerError):
            self.ledger.add(0, 100, OWNER_ATOM_CANDIDATE)

    def test_frozen_ledger_rejects_add(self):
        self.ledger.add(0, 10, OWNER_ATOM_CANDIDATE)
        self.ledger.finalize()
        with self.assertRaises(LedgerError):
            self.ledger.add(0, 2, OWNER_STRUCTURE)

    def test_gap_blocks_finalize(self):
        self.ledger.add(0, 3, OWNER_ATOM_CANDIDATE)
        with self.assertRaises(LedgerError):
            self.ledger.finalize()

    def test_illegal_boundary_inside_cjk_rejected(self):
        idx = UTF8ByteIndex("中文".encode("utf-8"))  # 6 bytes
        ledger = ByteLedger(idx)
        with self.assertRaises(LedgerError):
            ledger.add(1, 3, OWNER_ATOM_CANDIDATE)  # byte 1 mid-codepoint

    def test_inverted_span_rejected(self):
        with self.assertRaises(LedgerError):
            self.ledger.add(5, 3, OWNER_ATOM_CANDIDATE)

    def test_overlap_not_swallowed(self):
        self.ledger.add(0, 5, OWNER_ATOM_CANDIDATE)
        with self.assertRaises(LedgerError):
            self.ledger.add(3, 8, OWNER_STRUCTURE)

    def test_zero_length_rejected(self):
        with self.assertRaises(LedgerError):
            self.ledger.add(3, 3, OWNER_STRUCTURE)

    def test_unknown_owner_accepted(self):
        self.ledger.add(0, 5, OWNER_UNKNOWN_ERROR, "test")
        self.assertEqual(self.ledger.spans[0].owner, OWNER_UNKNOWN_ERROR)


class TestMutationUTF8(unittest.TestCase):
    def test_0xFF_not_parsed(self):
        with self.assertRaises((ValueError, UnicodeDecodeError)):
            UTF8ByteIndex(b"\xFF")

    def test_overlong_C0_AF_rejected(self):
        with self.assertRaises((ValueError, UnicodeDecodeError)):
            UTF8ByteIndex(b"\xC0\xAF")

    def test_surrogate_ED_A0_80_rejected(self):
        with self.assertRaises((ValueError, UnicodeDecodeError)):
            UTF8ByteIndex(b"\xED\xA0\x80")

    def test_0xA0_rejected_as_continuation(self):
        """Unexpected continuation byte (0xA0 = 0x80-0xBF range)."""
        # E0 prefix expects 2 continuation bytes; bare continuation is invalid.
        with self.assertRaises((ValueError, UnicodeDecodeError)):
            UTF8ByteIndex(b"\xA0\xA0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
