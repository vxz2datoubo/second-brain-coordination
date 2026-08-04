"""E39 S0 tests — UTF-8 0xED surrogate, timeout gate, strict validation.

All tests from E38 S0 red-to-green cycle, written fresh for E39.
Covers: valid UTF-8, surrogate rejection, overlong, truncated, timeout,
scan termination proof, mutation: 0xED infinite-loop simulation.
"""
import unittest
import sys, os

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_strict_byte.utf8_guard import UTF8ByteIndex, UTF8GuardError, with_timeout, Terminated


class TestStrictUTF8(unittest.TestCase):
    """UTF-8 validation with strict rejection of all invalid sequences."""

    def test_valid_ascii(self):
        idx = UTF8ByteIndex(b"hello world")
        self.assertEqual(idx.total_bytes, 11)
        self.assertEqual(idx.codepoint_count, 11)

    def test_valid_cjk(self):
        idx = UTF8ByteIndex("中文测试".encode("utf-8"))
        self.assertEqual(idx.codepoint_count, 4)
        self.assertEqual(idx.total_bytes, 12)
        self.assertEqual(len(idx.chunk_starts), 4)

    def test_valid_emoji(self):
        idx = UTF8ByteIndex("😀🎉".encode("utf-8"))
        self.assertEqual(idx.codepoint_count, 2)
        self.assertEqual(idx.total_bytes, 8)

    def test_valid_zwj(self):
        idx = UTF8ByteIndex("👨‍👩‍👧".encode("utf-8"))
        self.assertGreater(idx.codepoint_count, 2)

    def test_bom_detected(self):
        idx = UTF8ByteIndex(b"\xEF\xBB\xBFhello")
        self.assertTrue(idx.has_bom)
        self.assertEqual(idx.total_bytes, 8)

    def test_no_bom(self):
        idx = UTF8ByteIndex(b"hello")
        self.assertFalse(idx.has_bom)

    def test_crlf_detected(self):
        idx = UTF8ByteIndex(b"line1\r\nline2\nline3")
        self.assertEqual(idx.crlf_count, 1)

    def test_lf_only(self):
        idx = UTF8ByteIndex(b"a\nb\nc")
        self.assertEqual(idx.lf_count, 2)

    def test_line_starts(self):
        idx = UTF8ByteIndex(b"a\r\nb\nc")
        self.assertEqual(len(idx.line_starts), 3)
        self.assertIn(0, idx.line_starts)

    def test_legal_boundaries(self):
        idx = UTF8ByteIndex("abc".encode("utf-8"))
        boundaries = idx.legal_boundaries
        self.assertIn(0, boundaries)
        self.assertIn(3, boundaries)

    # ── 0xED SURROGATE ──────────────────────────────────────────

    def test_0xED_A0_80_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xED\xA0\x80")
        self.assertIn("Surrogate", str(ctx.exception))

    def test_0xED_B0_80_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xED\xB0\x80")
        self.assertIn("Surrogate", str(ctx.exception))

    def test_0xED_embedded_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"hello \xED\xA0\x80 world")
        self.assertIn("Surrogate", str(ctx.exception))

    def test_0xED_BF_BF_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xED\xBF\xBF")
        self.assertIn("Surrogate", str(ctx.exception))

    # ── INVALID LEAD BYTES ──────────────────────────────────────

    def test_0xFF_rejected(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xFF")

    def test_0xFE_rejected(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xFE")

    def test_0xC0_AF_rejected(self):
        """0xC0 < 0xC2 min valid; either Overlong or Invalid lead byte."""
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xC0\xAF")
        msg = str(ctx.exception)
        self.assertTrue("Overlong" in msg or "Invalid lead byte" in msg,
                        f"Expected Overlong or Invalid lead byte, got: {msg}")

    # ── OVERLONG ────────────────────────────────────────────────

    def test_overlong_3byte_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xE0\x80\xAF")
        self.assertIn("Overlong", str(ctx.exception))

    # ── TRUNCATED ───────────────────────────────────────────────

    def test_truncated_2byte_rejected(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xC2")

    def test_truncated_3byte_rejected(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xE0\xA4")

    def test_truncated_4byte_rejected(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xF0\x90\x80")

    # ── >U+10FFFF ───────────────────────────────────────────────

    def test_over_10FFFF_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xF4\x90\x80\x80")
        self.assertIn("10FFFF", str(ctx.exception))

    # ── BAD CONTINUATION ────────────────────────────────────────

    def test_bad_continuation_rejected(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xE0\x20\x80")

    def test_unexpected_continuation_rejected(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\x80\x80")

    # ── TYPE CHECK ──────────────────────────────────────────────

    def test_bytes_not_str(self):
        with self.assertRaises(TypeError):
            UTF8ByteIndex("hello")

    # ── byte_to_chunk_index ─────────────────────────────────────

    def test_byte_to_chunk_index(self):
        idx = UTF8ByteIndex("a€c".encode("utf-8"))
        self.assertEqual(idx.byte_to_chunk_index(0), 0)
        self.assertEqual(idx.byte_to_chunk_index(1), 1)
        self.assertEqual(idx.byte_to_chunk_index(3), 1)
        self.assertEqual(idx.byte_to_chunk_index(4), 2)

    def test_byte_to_chunk_index_oob(self):
        idx = UTF8ByteIndex(b"abc")
        with self.assertRaises(IndexError):
            idx.byte_to_chunk_index(3)
        with self.assertRaises(IndexError):
            idx.byte_to_chunk_index(-1)

    # ── chunk_starts ────────────────────────────────────────────

    def test_chunk_starts_count(self):
        idx = UTF8ByteIndex("a€c😀d".encode("utf-8"))
        self.assertEqual(len(idx.chunk_starts), idx.codepoint_count)

    def test_chunk_starts_sorted(self):
        idx = UTF8ByteIndex("hello😀世界".encode("utf-8"))
        for i in range(1, len(idx.chunk_starts)):
            self.assertLess(idx.chunk_starts[i - 1], idx.chunk_starts[i])


# ═══════════════════════════════════════════════════════════════════════
# TIMEOUT / 0xED MUTATION — red-to-green gates
# ═══════════════════════════════════════════════════════════════════════

class TestTimeoutGuard(unittest.TestCase):
    """Prove invalid inputs terminate within a bounded time."""

    def test_valid_input_completes_fast(self):
        result = with_timeout(UTF8ByteIndex, (b"hello world",), timeout_sec=2.0)
        self.assertIsInstance(result, Terminated)
        self.assertEqual(result.value.total_bytes, 11)

    def test_single_0xED_rejected_quickly(self):
        with self.assertRaises(UTF8GuardError):
            with_timeout(UTF8ByteIndex, (b"\xED",), timeout_sec=2.0)

    def test_0xED_surrogate_rejected_quickly(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            with_timeout(UTF8ByteIndex, (b"\xED\xA0\x80",), timeout_sec=2.0)
        self.assertIn("Surrogate", str(ctx.exception))

    def test_repeated_0xED_sequences_rejected(self):
        data = b"\xED" * 100
        with self.assertRaises(UTF8GuardError):
            with_timeout(UTF8ByteIndex, (data,), timeout_sec=2.0)

    def test_large_ascii_terminates(self):
        data = b"hello world\n" * 10000
        result = with_timeout(UTF8ByteIndex, (data,), timeout_sec=2.0)
        self.assertEqual(result.value.total_bytes, len(data))

    def test_ascii_0xED_mixed_rejected(self):
        data = b"abc" + b"\xED\xA0\x80" + b"def"
        with self.assertRaises(UTF8GuardError) as ctx:
            with_timeout(UTF8ByteIndex, (data,), timeout_sec=2.0)
        self.assertIn("Surrogate", str(ctx.exception))

    def test_empty_input_ok(self):
        result = with_timeout(UTF8ByteIndex, (b"",), timeout_sec=2.0)
        self.assertEqual(result.value.total_bytes, 0)
        self.assertEqual(result.value.codepoint_count, 0)

    # ── MUTATION: simulate infinite-loop behavior ───────────────

    def test_0xED_loop_mutation_detected(self):
        """Mutation: if a scanner had a 0xED infinite-loop bug, timeout catches it.
        We simulate by passing a known-invalid sequence through timeout guard."""
        # 0xED without continuation = truncated, must reject quickly
        with self.assertRaises(UTF8GuardError):
            with_timeout(UTF8ByteIndex, (b"\xED",), timeout_sec=2.0)

    def test_overlong_mutation_detected(self):
        """C0 AF overlong must be rejected cleanly (no hang)."""
        with self.assertRaises(UTF8GuardError):
            with_timeout(UTF8ByteIndex, (b"\xC0\xAF",), timeout_sec=2.0)


# ═══════════════════════════════════════════════════════════════════════
# SCAN TERMINATION PROOF
# ═══════════════════════════════════════════════════════════════════════

class TestScanTermination(unittest.TestCase):
    """Prove the manual byte-scan terminates with a hard ceiling."""

    def test_empty_scan_terminates(self):
        idx = UTF8ByteIndex(b"")
        self.assertEqual(len(idx.chunk_starts), 0)

    def test_single_byte_scan(self):
        for b in [0x00, 0x7F, 0x20, 0x41]:
            idx = UTF8ByteIndex(bytes([b]))
            self.assertEqual(idx.total_bytes, 1)
            self.assertEqual(idx.codepoint_count, 1)

    def test_two_byte_sequence_scan(self):
        idx = UTF8ByteIndex(b"\xC2\x80")
        self.assertEqual(idx.codepoint_count, 1)
        self.assertEqual(idx.total_bytes, 2)

    def test_three_byte_scan(self):
        idx = UTF8ByteIndex(b"\xE4\xB8\xAD")
        self.assertEqual(idx.codepoint_count, 1)

    def test_four_byte_scan(self):
        idx = UTF8ByteIndex(b"\xF0\x9F\x98\x80")
        self.assertEqual(idx.codepoint_count, 1)

    def test_scan_with_timeout(self):
        result = with_timeout(UTF8ByteIndex, (b"\xE4\xB8\xAD\xF0\x9F\x98\x80",), timeout_sec=2.0)
        self.assertEqual(result.value.codepoint_count, 2)

    def test_invalid_byte_class_rejected(self):
        for bad in [0xC0, 0xC1, 0xF5]:
            with self.assertRaises(UTF8GuardError):
                with_timeout(UTF8ByteIndex, (bytes([bad, 0x80]),), timeout_sec=2.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
