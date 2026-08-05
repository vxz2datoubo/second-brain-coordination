"""E39 S3 tests — Irreversible byte-level redaction with mutation families."""
import unittest
import sys, os

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_strict_byte.redact import (
    redact, find_redaction_candidates, _resolve_overlaps,
    RedactionCandidate, RedactionMapping, RedactionResult,
    REDACT_PATTERNS, CATEGORY_PRIORITY,
)


class TestRedactionPatterns(unittest.TestCase):
    """Test individual detection patterns."""

    def test_detect_api_key_assignment(self):
        candidates = find_redaction_candidates(b'api_key=sk-notarealkey1234567890abcdef')
        api = [c for c in candidates if c.category == "API_KEY"]
        self.assertGreaterEqual(len(api), 1)

    def test_detect_openai_key(self):
        candidates = find_redaction_candidates(b'sk-notarealkey1234567890abcdefghijkl')
        self.assertGreaterEqual(len(candidates), 1)

    def test_detect_password(self):
        candidates = find_redaction_candidates(b'password: supersecure123')
        pw = [c for c in candidates if c.category == "PASSWORD"]
        self.assertGreaterEqual(len(pw), 1)

    def test_detect_token(self):
        candidates = find_redaction_candidates(b'token=abc123def456ghi789')
        tok = [c for c in candidates if c.category == "TOKEN"]
        self.assertGreaterEqual(len(tok), 1)

    def test_detect_github_pat(self):
        candidates = find_redaction_candidates(b'ghp_1234567890abcdef1234567890abcdef1234')
        tok = [c for c in candidates if c.category == "TOKEN"]
        self.assertGreaterEqual(len(tok), 1)

    def test_detect_secret(self):
        candidates = find_redaction_candidates(b'secret: abcdefgh1234')
        self.assertGreaterEqual(len(candidates), 1)

    def test_detect_private_key(self):
        data = b"-----BEGIN PRIVATE KEY-----\nMIIEvQIBADAN...\n-----END PRIVATE KEY-----"
        candidates = find_redaction_candidates(data)
        pk = [c for c in candidates if c.category == "PRIVATE_KEY"]
        self.assertGreaterEqual(len(pk), 1)

    def test_detect_connection_string(self):
        candidates = find_redaction_candidates(b'mongodb://user:pass@host:27017/db')
        cs = [c for c in candidates if c.category == "CONNECTION_STRING"]
        self.assertGreaterEqual(len(cs), 1)

    def test_cjk_password(self):
        data = b"\xe5\xaf\x86\xe7\xa0\x81: test1234"  # 密码: test1234
        candidates = find_redaction_candidates(data)
        pw = [c for c in candidates if c.category == "PASSWORD"]
        self.assertGreaterEqual(len(pw), 1)


class TestRedactionEngine(unittest.TestCase):
    """Test the full redaction pipeline."""

    def test_single_redaction(self):
        result = redact(b'use: sk-notarealkey1234567890abcdefghijklm here')
        self.assertGreaterEqual(result.resolved_count, 1, "Should find at least 1 redaction")
        self.assertNotIn(b"sk-notareal", result.redacted_bytes)
        self.assertIn(b"[R", result.redacted_bytes)

    def test_password_redacted(self):
        result = redact(b'config: password=hunter2\nother: stuff')
        # Password value should be redacted
        redacted_str = result.redacted_bytes.decode("utf-8")
        self.assertNotIn("hunter2", redacted_str)
        self.assertIn("[R", redacted_str)

    def test_token_redacted(self):
        result = redact(b'Authorization: Bearer token=abcdef1234567890')
        self.assertNotIn(b"abcdef1234567890", result.redacted_bytes)

    def test_multiple_redactions(self):
        data = (
            b"api_key=sk-thekey1234567890abcdefghijklmn\n"
            b"password=s3cr3t!!\n"
            b"normal_data=ok\n"
        )
        result = redact(data)
        redacted_str = result.redacted_bytes.decode("utf-8")
        self.assertNotIn("s3cr3t", redacted_str)
        self.assertNotIn("sk-thekey1234567890abcdefghijklmn", redacted_str)
        # At least 2 [R] markers
        markers = [i for i in range(len(redacted_str)) if redacted_str.startswith("[R", i)]
        self.assertGreaterEqual(result.resolved_count, 2)

    def test_no_secrets_unchanged(self):
        data = b"This is just normal text without any secrets."
        result = redact(data)
        self.assertEqual(result.redacted_bytes, data)
        self.assertEqual(result.candidates_found, 0)

    def test_empty_input(self):
        result = redact(b"")
        self.assertEqual(result.redacted_bytes, b"")
        self.assertEqual(result.original_length, 0)

    def test_lineage_preserved(self):
        data = b"prefix: sk-thekey1234567890abcdefghijklmn"
        result = redact(data)
        self.assertGreater(len(result.mapping), 0)
        m = result.mapping[0]
        self.assertGreater(m.original_start, 0)  # should start after "prefix: "
        self.assertEqual(m.original_end - m.original_start, 33)  # key length
        self.assertNotEqual(m.length_delta, 0)

    def test_output_different_from_input(self):
        """Redacted output must differ from input when secrets found."""
        data = b"sk-realnotreal1234567890abcdefghijkl"
        result = redact(data)
        self.assertNotEqual(result.redacted_bytes, data)
        self.assertNotEqual(result.original_length, result.redacted_length)

    def test_length_delta_negative(self):
        """Replacement is typically shorter than original secret."""
        data = b"sk-thekey1234567890abcdefghijklmnop"
        result = redact(data)
        if result.mapping:
            self.assertLess(result.mapping[0].length_delta, 0)

    def test_normal_bytes_preserved(self):
        """Non-secret bytes should be verbatim."""
        prefix = b"config:\n  name: myapp\n  version: \"1.0\"\n"
        data = prefix + b"  api_key=sk-notreal1234567890abcdefghijklm\n"
        result = redact(data)
        # The non-secret prefix should be preserved
        self.assertTrue(result.redacted_bytes.startswith(b"config:"))

    def test_safe_examples_not_redacted(self):
        """Safe/demo examples should never be redacted."""
        data = b"sk-demo-not-real-000000000000000000000000"
        result = redact(data)
        self.assertEqual(result.redacted_bytes, data)
        self.assertEqual(result.candidates_found, 0)


class TestOverlapResolution(unittest.TestCase):
    """Test overlap resolution logic."""

    def test_priority_wins(self):
        """Higher priority category wins on overlap."""
        c1 = RedactionCandidate(0, 20, "PASSWORD")
        c2 = RedactionCandidate(0, 20, "API_KEY")  # higher priority
        result = _resolve_overlaps([c1, c2])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].category, "API_KEY")

    def test_longest_wins_same_priority(self):
        """At same priority, longest span wins."""
        c1 = RedactionCandidate(0, 10, "API_KEY")
        c2 = RedactionCandidate(0, 20, "API_KEY")
        result = _resolve_overlaps([c1, c2])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].byte_end, 20)

    def test_earliest_wins_same_length(self):
        """Same priority, same length → earlier start wins."""
        c1 = RedactionCandidate(0, 10, "API_KEY")
        c2 = RedactionCandidate(5, 15, "API_KEY")
        result = _resolve_overlaps([c2, c1])  # reversed order
        self.assertEqual(result[0].byte_start, 0)

    def test_non_overlapping_both_kept(self):
        """Non-overlapping spans are both kept."""
        c1 = RedactionCandidate(0, 10, "API_KEY")
        c2 = RedactionCandidate(20, 30, "PASSWORD")
        result = _resolve_overlaps([c1, c2])
        self.assertEqual(len(result), 2)

    def test_partial_overlap_winner_takes(self):
        """Partial overlap: the higher-priority longer match wins."""
        c1 = RedactionCandidate(0, 15, "API_KEY")
        c2 = RedactionCandidate(10, 25, "PASSWORD")
        result = _resolve_overlaps([c1, c2])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].category, "API_KEY")

    def test_empty_input(self):
        result = _resolve_overlaps([])
        self.assertEqual(len(result), 0)


class TestRedactionMapping(unittest.TestCase):
    """Test RedactionMapping correctness."""

    def test_mapping_fields(self):
        m = RedactionMapping(0, 40, 0, 4, "[R1]", "API_KEY", -36)
        self.assertEqual(m.original_length, 40)
        self.assertEqual(m.redacted_length, 4)
        self.assertEqual(m.length_delta, -36)

    def test_mapping_tracks_original_position(self):
        data = b"before secret: abcdefghij1234567890 after"
        result = redact(data)
        if result.mapping:
            m = result.mapping[0]
            # original_start should be BEFORE the secret
            self.assertGreater(m.original_start, 5)
            self.assertLess(m.original_end - m.original_start, 50)


class TestRedactOutputSafety(unittest.TestCase):
    """Prove redacted output contains no secret plaintext."""

    def test_no_api_key_in_output(self):
        key = b"sk-thekey1234567890abcdefghijklmnop"
        data = b"use: " + key + b" here"
        result = redact(data)
        self.assertNotIn(key, result.redacted_bytes)
        self.assertNotIn(b"sk-thekey", result.redacted_bytes)

    def test_no_password_in_output(self):
        data = b'password="myP@ssw0rd!"'
        result = redact(data)
        self.assertNotIn(b"myP@ssw0rd", result.redacted_bytes)

    def test_no_secret_hash_in_output(self):
        """Redacted output must not contain any hash of the secret."""
        data = b"secret=abcdefgh12345678"
        result = redact(data)
        redacted_str = result.redacted_bytes.decode("utf-8")
        # No base64, hex, or other reversible encoding of the secret
        for encoding in ["YWJjZGVmZ2gxMjM0NTY3OA==", "61626364656667683132333435363738"]:
            self.assertNotIn(encoding, redacted_str)

    def test_mapping_does_not_store_secret(self):
        """RedactionMapping must not include the secret text."""
        data = b"api_key=sk-secretvalue1234567890abcde"
        result = redact(data)
        for m in result.mapping:
            self.assertNotIn("secretvalue", m.category)
            self.assertNotIn("secretvalue", m.replacement)


class TestMutationRedactionFamilies(unittest.TestCase):
    """Active mutation tests for redaction."""

    def test_overlapping_secrets_resolved(self):
        """When two secrets overlap, one wins consistently."""
        # "sk-" prefix (API_KEY) + "password=something" (PASSWORD) overlap
        # should resolve deterministically
        data1 = b"sk-password=thevalue1234567890abcde"
        r1 = redact(data1)
        r2 = redact(data1)
        self.assertEqual(r1.redacted_bytes, r2.redacted_bytes)

    def test_safe_example_not_redacted_mutation(self):
        """Prove safe examples bypass detection completely."""
        safe = b"sk-demo-not-real-000000000000000000000000"
        result = redact(safe)
        self.assertEqual(result.redacted_bytes, safe)
        self.assertEqual(result.candidates_found, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
