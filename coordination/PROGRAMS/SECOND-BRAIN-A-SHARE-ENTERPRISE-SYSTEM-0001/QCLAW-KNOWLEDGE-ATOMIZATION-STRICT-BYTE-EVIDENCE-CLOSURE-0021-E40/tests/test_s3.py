"""E40 S3 — Redaction mutation + functional tests"""
import unittest, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"


class TestRedactionMutation(unittest.TestCase):
    """Prove redaction violations are rejected/identified."""

    def test_api_key_redacted(self):
        from qclaw_e40.redact import redact
        src = b"use: sk-test12345678901234567890key here"
        result = redact(src)
        self.assertGreaterEqual(result.resolved_count, 1)
        self.assertNotEqual(result.original_length, result.redacted_length)
        # Secret text must not appear in output
        self.assertNotIn(b"sk-test12345678901234567890key", result.redacted_bytes)

    def test_secret_not_in_output(self):
        from qclaw_e40.redact import redact
        src = b'password = "supersecret1234"'
        result = redact(src)
        self.assertNotIn(b"supersecret1234", result.redacted_bytes)

    def test_no_secret_hash_persisted(self):
        """Redaction result must not contain hash/fingerprint of secret."""
        from qclaw_e40.redact import redact
        import hashlib
        secret = b"supersecret1234"
        src = b"password=" + secret
        result = redact(src)
        h = hashlib.sha256(secret).hexdigest().encode()
        self.assertNotIn(h, result.redacted_bytes)

    def test_mapping_has_lineage(self):
        from qclaw_e40.redact import redact
        src = b"api_key: sk-abcd1234abcdefghijklmnopqrstuvwxyz"
        result = redact(src)
        self.assertGreaterEqual(len(result.mapping), 1)
        for m in result.mapping:
            self.assertIsNotNone(m.original_span)
            self.assertIsNotNone(m.redacted_span)

    def test_no_output_contains_original_secret_bytes(self):
        """Check every mapping: original_span text never in output."""
        from qclaw_e40.redact import redact
        src = b"token=ghp_abcdefghijklmnopqrstuvwxyz1234567890ABCD"
        result = redact(src)
        for m in result.mapping:
            orig = src[m.original_span[0]:m.original_span[1]]
            self.assertNotIn(orig, result.redacted_bytes)

    def test_safe_example_preserved(self):
        from qclaw_e40.redact import redact
        src = b"use: sk-test1234567890safe_example_tokenhere"
        safe = [b"sk-test1234567890safe_example_tokenhere"]
        result = redact(src, safe_examples=safe)
        self.assertIn(safe[0], result.redacted_bytes)


class TestRedactionFunctional(unittest.TestCase):
    def test_no_secrets_no_change(self):
        from qclaw_e40.redact import redact
        src = b"hello world, nothing to hide here"
        result = redact(src)
        self.assertEqual(result.redacted_bytes, src)
        self.assertEqual(result.resolved_count, 0)

    def test_multiple_secrets(self):
        from qclaw_e40.redact import redact
        src = (b'api_key=sk-1234abcde5678fghij9012klmn3456opqr\n'
               b'token=ghp_1234567890abcdefghijklmnopqrstuv')
        result = redact(src)
        # Both secrets redacted
        self.assertNotIn(b"sk-1234abcde", result.redacted_bytes)
        self.assertNotIn(b"ghp_1234567890abcdef", result.redacted_bytes)

    def test_r1_r2_labels_unique(self):
        from qclaw_e40.redact import redact
        src = b"api1=sk-aaaa1234bbbb5678cccc9012ddddeeee\napi2=sk-ffff1234gggg5678hhhh9012iiiijjjj"
        result = redact(src)
        labels = {m.replacement_label for m in result.mapping}
        self.assertEqual(len(labels), len(result.mapping))

    def test_empty_source(self):
        from qclaw_e40.redact import redact
        result = redact(b"")
        self.assertEqual(result.original_length, 0)
        self.assertEqual(result.redacted_bytes, b"")

    def test_irreversible_mapping(self):
        """Redaction mapping tracks both original and redacted positions."""
        from qclaw_e40.redact import redact
        src = b"x = sk-test12345678901234567890key;"
        result = redact(src)
        for m in result.mapping:
            self.assertGreater(m.redacted_span[1], m.redacted_span[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
