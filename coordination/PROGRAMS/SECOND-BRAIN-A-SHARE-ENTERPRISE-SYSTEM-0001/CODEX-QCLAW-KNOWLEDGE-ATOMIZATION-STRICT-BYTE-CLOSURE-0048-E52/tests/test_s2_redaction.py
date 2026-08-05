"""S2 redaction product tests using only synthetic credential-shaped fixtures."""
from __future__ import annotations

import dataclasses
import inspect
import sys
import unittest
from pathlib import Path


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from e52_strict_byte.redaction import RedactionCategory, RedactionMapping, RedactionResult, redact


class TestProductionRedaction(unittest.TestCase):
    def test_no_safe_example_parameter_or_secret_bearing_public_fields(self):
        self.assertNotIn("safe_examples", inspect.signature(redact).parameters)
        result_fields = {field.name for field in dataclasses.fields(RedactionResult)}
        mapping_fields = {field.name for field in dataclasses.fields(RedactionMapping)}
        forbidden = {"matched", "secret", "hash", "fingerprint", "length"}
        self.assertFalse(any(fragment in name for name in result_fields | mapping_fields for fragment in forbidden))

    def test_api_token_password_and_connection_string_are_removed(self):
        marker = b"SYNTHETIC_VALUE_1234567890"
        source = b"api_key=" + marker + b" token=" + marker + b" password=synthetic-pass-123 postgres://alice:" + marker + b"@example/db"
        result = redact(source)
        self.assertNotIn(marker, result.redacted_bytes)
        self.assertEqual(len(result.mappings), 4)
        self.assertEqual(result.categories[0], RedactionCategory.API_KEY)
        self.assertTrue(all(mapping.irreversible_sequence == index for index, mapping in enumerate(result.mappings, 1)))

    def test_private_key_variants_are_redacted_as_one_block(self):
        for key_type in (b"RSA", b"EC", b"DSA", b"OPENSSH", b"PGP"):
            body = b"SYNTHETICBLOCK0123456789"
            source = b"prefix -----BEGIN " + key_type + b" PRIVATE KEY-----\n" + body + b"\n-----END " + key_type + b" PRIVATE KEY----- suffix"
            result = redact(source)
            self.assertNotIn(body, result.redacted_bytes)
            self.assertEqual(result.categories, (RedactionCategory.PRIVATE_KEY,))

    def test_overlap_order_is_deterministic_and_preserves_only_allowed_spans(self):
        source = b"api_key=SYNTHETIC_VALUE_1234567890 token=SYNTHETIC_VALUE_1234567890"
        first = redact(source)
        second = redact(source)
        self.assertEqual(first, second)
        self.assertEqual(first.mappings, tuple(sorted(first.mappings, key=lambda item: item.original_span)))
        self.assertTrue(all(hasattr(mapping, "original_span") and hasattr(mapping, "replacement_span") for mapping in first.mappings))

    def test_no_match_returns_safe_identity_without_hidden_source_metadata(self):
        result = redact(b"ordinary public-safe text")
        self.assertEqual(result.redacted_bytes, b"ordinary public-safe text")
        self.assertEqual(result.mappings, ())
        self.assertEqual(result.categories, ())


if __name__ == "__main__":
    unittest.main(verbosity=2)
