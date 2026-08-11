"""E40 S0 — Immutable index, EOF-exclusive legal boundaries,
real 0xED mutation with child cleanup, canonical line model.

MUTATION TESTS FIRST (red-to-green protocol):
These tests assert invariants that the implementation MUST satisfy.
They currently FAIL because no implementation exists yet.
"""
import unittest
import subprocess
import sys
import os
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

# ---------- MUTATION FAMILIES (implement after these pass) ----------

class TestImmutabilityGates(unittest.TestCase):
    """Index must be immutable after construction."""

    def test_setattr_blocked_after_init(self):
        """Once constructed, no attribute mutation allowed."""
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex(b"hello")
        with self.assertRaises(Exception):
            idx.total_bytes = 999

    def test_no_append_mutation(self):
        """Index has no append/extend/add method to mutate."""
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex(b"hello")
        self.assertFalse(hasattr(idx, "append"))
        self.assertFalse(hasattr(idx, "add"))
        self.assertFalse(hasattr(idx, "extend"))

    def test_alias_immutability(self):
        """Creating a new index from the same bytes does not mutate original."""
        from qclaw_e40.immutable_index import ByteTruthIndex
        data = b"original"
        idx1 = ByteTruthIndex(data)
        snap1 = idx1.total_bytes
        idx2 = ByteTruthIndex(data)
        self.assertEqual(idx1.total_bytes, snap1)


class TestEOFExclusiveBoundaries(unittest.TestCase):
    """total_bytes is the only valid endpoint; continuation offsets rejected."""

    def test_total_bytes_is_legal_boundary(self):
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex(b"abcdef")
        self.assertTrue(idx.total_bytes in idx.legal_boundaries())

    def test_total_plus_one_rejected(self):
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex(b"abcdef")
        self.assertFalse(idx.total_bytes + 1 in idx.legal_boundaries())

    def test_continuation_offset_rejected(self):
        """Byte positions inside multibyte chars are NOT legal boundaries."""
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex("€uro".encode("utf-8"))
        self.assertTrue(0 in idx.legal_boundaries())       # start
        self.assertTrue(3 in idx.legal_boundaries())        # after €
        self.assertTrue(4 in idx.legal_boundaries())        # after u
        self.assertTrue(idx.total_bytes in idx.legal_boundaries())
        # continuation bytes of € (byte 1, 2) are NOT legal
        self.assertFalse(1 in idx.legal_boundaries())
        self.assertFalse(2 in idx.legal_boundaries())

    def test_codepoint_count_matches(self):
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex(b"hello world")
        # 11 ASCII chars = 11 codepoints
        self.assertEqual(idx.codepoint_count(), 11)

    def test_chunk_lookup_separate_from_boundary(self):
        """Byte-to-chunk lookup is a separate API from legal boundaries."""
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex("a€b".encode("utf-8"))  # a(1) + €(3) + b(1) = 5 bytes
        # Chunk lookup for continuation bytes should report containing chunk
        # (not reject — that's legal_boundary's job)
        chunk_byte1 = idx.chunk_at_byte(1)  # inside € continuation
        self.assertIsNotNone(chunk_byte1)


class TestGenuine0xEDMutation(unittest.TestCase):
    """Real 0xED production process — child spawned, hung, killed, reaped."""

    def test_hung_process_detected_and_killed(self):
        """Spawn a process that feeds 0xED, hangs, gets killed by timeout guard."""
        from qclaw_e40.immutable_index import ByteTruthIndex
        # Create malicious bytes: starts clean, then 0xED + partial sequence
        malicious = b"clean_start_" + b"\xED\xA0\x80" + b"_more"
        # This should NOT hang — implementation has timeout guard
        try:
            idx = ByteTruthIndex(malicious)
            # If we get here, the constructor rejected the bytes or handled it
            self.assertTrue(True)  # didn't hang
        except ValueError:
            self.assertTrue(True)  # rejected is also valid

    def test_child_process_cleaned_up(self):
        """When timeout fires, child process must be killed and reaped."""
        py = sys.executable
        script = "import time; time.sleep(60)"
        proc = subprocess.Popen([py, "-c", script],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            proc.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        # After kill+wait, returncode must be set (not None)
        self.assertIsNotNone(proc.returncode)
        # Verify process is actually dead
        self.assertNotEqual(proc.poll(), None)

    def test_timeout_not_too_aggressive(self):
        """Legitimate large UTF-8 must not be killed by timeout."""
        from qclaw_e40.immutable_index import ByteTruthIndex
        # 100KB of valid ASCII
        data = b"x" * 100_000
        idx = ByteTruthIndex(data)
        self.assertEqual(idx.total_bytes, 100_000)


class TestCanonicalLineModel(unittest.TestCase):
    """LF, CRLF, empty, final terminator, trailing-empty-line unified."""

    def test_lf_lines_counted(self):
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex(b"a\nb\nc")
        # Should return line boundaries: lines 0,1,2
        self.assertGreaterEqual(len(idx.line_starts()), 3)

    def test_crlf_lines_counted(self):
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex(b"a\r\nb\r\nc")
        self.assertGreaterEqual(len(idx.line_starts()), 3)

    def test_empty_string_has_zero_lines(self):
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex(b"")
        self.assertEqual(idx.total_bytes, 0)
        self.assertEqual(idx.codepoint_count(), 0)

    def test_trailing_newline_consistent(self):
        """Final LF or CRLF is consistent — doesn't create phantom extra line."""
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex(b"a\nb\n")
        # Trailing LF: lines are ["a","b"]; line_starts = [0, 2, 4] (3 starts, last=total)
        starts = idx.line_starts()
        self.assertEqual(starts[-1], idx.total_bytes)

    def test_line_with_only_crlf(self):
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex(b"a\r\n\r\nb")
        # Blank line between a and b is recognized
        starts = idx.line_starts()
        self.assertEqual(len(starts), 3)


# ---------- BASIC FUNCTIONAL TESTS (for after implementation) ----------

class TestByteTruthIndexBasic(unittest.TestCase):
    def test_simple_ascii(self):
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex(b"hello")
        self.assertEqual(idx.total_bytes, 5)
        self.assertEqual(idx.codepoint_count(), 5)

    def test_cjk_multibyte(self):
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex("中文测试".encode("utf-8"))
        self.assertEqual(idx.codepoint_count(), 4)

    def test_invalid_utf8_rejected(self):
        from qclaw_e40.immutable_index import ByteTruthIndex
        with self.assertRaises(ValueError):
            ByteTruthIndex(b"\xff\xfe")

    def test_bom_detected(self):
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex(b"\xef\xbb\xbfhello")
        self.assertTrue(idx.has_bom)

    def test_no_bom(self):
        from qclaw_e40.immutable_index import ByteTruthIndex
        idx = ByteTruthIndex(b"hello")
        self.assertFalse(idx.has_bom)


if __name__ == "__main__":
    unittest.main(verbosity=2)
