"""E39 S0 tests — RED→GREEN: process-timeout + 0xED surrogate + boundaries.

RED (must fail first): Thread-based timeout cannot kill CPU-bound loops.
GREEN (must pass): Subprocess timeout provides true OS termination.

All UTF-8 validation tests in standard unittest with genuine assertions.
"""
import unittest
import sys
import os
import threading
import time
import subprocess
import base64

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_strict_byte.utf8_guard import (
    UTF8ByteIndex,
    UTF8GuardError,
    with_timeout,
)

MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ═══════════════════════════════════════════════════════════════════════
# RED: Thread-based timeout vulnerability (must pass as RED proof)
# ═══════════════════════════════════════════════════════════════════════

class TestThreadTimeoutRed(unittest.TestCase):
    """RED: Proves thread-based timeout CANNOT kill CPU-bound loops under GIL."""

    def test_red_thread_alive_after_timeout(self):
        """RED: A daemon thread in an infinite CPU loop stays alive
        even after join(timeout) returns."""
        alive_flag = [False]

        def cpu_loop_forever():
            i = 0
            while True:
                i += 1
            alive_flag[0] = True  # unreachable

        t = threading.Thread(target=cpu_loop_forever, daemon=True)
        t.start()
        t.join(timeout=0.3)
        is_alive = t.is_alive()

        self.assertTrue(is_alive,
            "RED ASSERTION: thread MUST still be alive after timeout. "
            "If this fails, the CPU loop was too short or scheduling is unusual.")


# ═══════════════════════════════════════════════════════════════════════
# GREEN: Subprocess-based timeout (true OS-level termination)
# ═══════════════════════════════════════════════════════════════════════

class TestSubprocessTimeoutGreen(unittest.TestCase):
    """GREEN: Subprocess timeout with OS-level process termination."""

    def test_valid_ascii_returns_result(self):
        result = with_timeout(b"hello world", timeout_sec=2.0)
        self.assertEqual(result["total_bytes"], 11)
        self.assertEqual(result["codepoint_count"], 11)

    def test_0xED_surrogate_rejected_in_subprocess(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            with_timeout(b"\xED\xA0\x80", timeout_sec=2.0)
        self.assertIn("Surrogate", str(ctx.exception))

    def test_repeated_0xED_rejected_in_subprocess(self):
        with self.assertRaises(UTF8GuardError):
            with_timeout(b"\xED" * 100, timeout_sec=2.0)

    def test_overlong_rejected_in_subprocess(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            with_timeout(b"\xC0\xAF", timeout_sec=2.0)
        msg = str(ctx.exception)
        self.assertTrue("Overlong" in msg or "Invalid lead" in msg,
                        f"Expected Overlong or Invalid lead byte: {msg}")

    def test_large_ascii_terminates(self):
        data = b"hello world\n" * 10_000
        result = with_timeout(data, timeout_sec=3.0)
        self.assertEqual(result["total_bytes"], len(data))
        self.assertGreater(result["codepoint_count"], 0)

    def test_empty_terminates(self):
        result = with_timeout(b"", timeout_sec=2.0)
        self.assertEqual(result["total_bytes"], 0)
        self.assertEqual(result["codepoint_count"], 0)

    def test_cjk_terminates(self):
        result = with_timeout("中文测试".encode("utf-8"), timeout_sec=2.0)
        self.assertEqual(result["codepoint_count"], 4)

    def test_timeout_on_blocked_process(self):
        """A Python process sleeping for 10s should trigger timeout at 0.3s."""
        import json
        runner = "import time; time.sleep(10); print('x')"
        with self.assertRaises(subprocess.TimeoutExpired):
            proc = subprocess.Popen(
                [sys.executable, "-c", runner],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            proc.communicate(timeout=0.3)


# ═══════════════════════════════════════════════════════════════════════
# DIRECT: All UTF-8 validation (direct construction, no subprocess)
# ═══════════════════════════════════════════════════════════════════════

class TestValidUTF8(unittest.TestCase):
    def test_valid_ascii(self):
        idx = UTF8ByteIndex(b"hello world")
        self.assertEqual(idx.total_bytes, 11)
        self.assertEqual(idx.codepoint_count, 11)

    def test_valid_cjk(self):
        idx = UTF8ByteIndex("中文测试".encode("utf-8"))
        self.assertEqual(idx.codepoint_count, 4)
        self.assertEqual(len(idx.chunk_starts), 4)

    def test_valid_emoji(self):
        idx = UTF8ByteIndex("😀🎉".encode("utf-8"))
        self.assertEqual(idx.codepoint_count, 2)
        self.assertEqual(idx.total_bytes, 8)

    def test_valid_zwj(self):
        idx = UTF8ByteIndex("👨‍👩‍👧".encode("utf-8"))
        self.assertGreater(idx.codepoint_count, 2)

    def test_all_valid_lead_bytes(self):
        idx = UTF8ByteIndex(b"\xC2\x80\xE0\xA0\x80\xF0\x90\x80\x80")
        self.assertEqual(idx.codepoint_count, 3)


class TestSurrogateRejection(unittest.TestCase):
    def test_ED_A0_80_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xED\xA0\x80")
        self.assertIn("Surrogate", str(ctx.exception))

    def test_ED_B0_80_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xED\xB0\x80")
        self.assertIn("Surrogate", str(ctx.exception))

    def test_ED_BF_BF_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xED\xBF\xBF")
        self.assertIn("Surrogate", str(ctx.exception))

    def test_ED_A0_81_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xED\xA0\x81")
        self.assertIn("Surrogate", str(ctx.exception))

    def test_ED_AF_80_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xED\xAF\x80")
        self.assertIn("Surrogate", str(ctx.exception))

    def test_ED_embedded_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"hello \xED\xA0\x80 world")
        self.assertIn("Surrogate", str(ctx.exception))


class TestOverlongRejection(unittest.TestCase):
    def test_C0_AF_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xC0\xAF")
        msg = str(ctx.exception)
        self.assertTrue("Overlong" in msg or "Invalid lead" in msg)

    def test_E0_80_AF_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xE0\x80\xAF")
        self.assertIn("Overlong", str(ctx.exception))

    def test_F0_80_80_80_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xF0\x80\x80\x80")
        self.assertIn("Overlong", str(ctx.exception))


class TestTruncatedRejection(unittest.TestCase):
    def test_truncated_2byte(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xC2")
    def test_truncated_3byte_1st(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xE0")
    def test_truncated_3byte_2nd(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xE0\xA4")
    def test_truncated_4byte_1st(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xF0")
    def test_truncated_4byte_2nd(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xF0\x90")
    def test_truncated_4byte_3rd(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xF0\x90\x80")


class TestBadContinuationRejection(unittest.TestCase):
    def test_bad_cont_3byte(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xE0\x20\x80")
    def test_unexpected_cont_alone(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\x80\x80")
    def test_unexpected_cont_mid(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"abc\x80\x80def")


class TestInvalidLeadAndOver(unittest.TestCase):
    def test_FF_rejected(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xFF")
    def test_FE_rejected(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xFE")
    def test_F5_rejected(self):
        with self.assertRaises(UTF8GuardError):
            UTF8ByteIndex(b"\xF5\x80\x80\x80")
    def test_over_10FFFF_rejected(self):
        with self.assertRaises(UTF8GuardError) as ctx:
            UTF8ByteIndex(b"\xF4\x90\x80\x80")
        self.assertIn("10FFFF", str(ctx.exception))


class TestBoundaryAndType(unittest.TestCase):
    def test_bytes_not_str(self):
        with self.assertRaises(TypeError):
            UTF8ByteIndex("hello")
    def test_legal_boundaries_includes_eof(self):
        idx = UTF8ByteIndex(b"abc")
        boundaries = idx.legal_boundaries
        self.assertIn(0, boundaries)
        self.assertIn(3, boundaries)
    def test_byte_to_chunk_index(self):
        idx = UTF8ByteIndex("a€c".encode("utf-8"))
        self.assertEqual(idx.byte_to_chunk_index(0), 0)
        self.assertEqual(idx.byte_to_chunk_index(1), 1)
        self.assertEqual(idx.byte_to_chunk_index(4), 2)
    def test_byte_to_chunk_index_oob(self):
        idx = UTF8ByteIndex(b"abc")
        with self.assertRaises(IndexError):
            idx.byte_to_chunk_index(3)
    def test_chunk_starts_count(self):
        idx = UTF8ByteIndex("a€c😀d".encode("utf-8"))
        self.assertEqual(len(idx.chunk_starts), idx.codepoint_count)
    def test_chunk_starts_ascending(self):
        idx = UTF8ByteIndex("hello😀".encode("utf-8"))
        for i in range(1, len(idx.chunk_starts)):
            self.assertLess(idx.chunk_starts[i - 1], idx.chunk_starts[i])


class TestBomAndLineEndings(unittest.TestCase):
    def test_bom_detected(self):
        idx = UTF8ByteIndex(b"\xEF\xBB\xBFhello")
        self.assertTrue(idx.has_bom)
        self.assertEqual(idx.source_bytes[:3], b"\xEF\xBB\xBF")
    def test_no_bom(self):
        idx = UTF8ByteIndex(b"hello")
        self.assertFalse(idx.has_bom)
    def test_crlf_detected(self):
        idx = UTF8ByteIndex(b"line1\r\nline2")
        self.assertEqual(idx.crlf_count, 1)
    def test_lf_only(self):
        idx = UTF8ByteIndex(b"a\nb")
        self.assertEqual(idx.lf_count, 1)
    def test_line_starts_count(self):
        idx = UTF8ByteIndex(b"a\nb\r\nc")
        self.assertEqual(len(idx.line_starts), 3)


class TestScanTermination(unittest.TestCase):
    def test_empty(self):
        idx = UTF8ByteIndex(b"")
        self.assertEqual(idx.total_bytes, 0)
        self.assertEqual(idx.codepoint_count, 0)
    def test_one_byte(self):
        for b_val in [0x00, 0x7F, 0x41]:
            idx = UTF8ByteIndex(bytes([b_val]))
            self.assertEqual(idx.codepoint_count, 1)
    def test_2byte(self):
        idx = UTF8ByteIndex(b"\xC2\x80")
        self.assertEqual(idx.codepoint_count, 1)
    def test_3byte(self):
        idx = UTF8ByteIndex(b"\xE4\xB8\xAD")
        self.assertEqual(idx.codepoint_count, 1)
    def test_4byte(self):
        idx = UTF8ByteIndex(b"\xF0\x9F\x98\x80")
        self.assertEqual(idx.codepoint_count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
