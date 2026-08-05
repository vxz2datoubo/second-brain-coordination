"""S1 exact ownership tests for all six synthetic input formats."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from e52_strict_byte.adapters import adapt
from e52_strict_byte.ledger import LedgerBuilder, Owner


class TestLedgerProductGates(unittest.TestCase):
    def test_rejects_overlap_and_gaps(self):
        builder = LedgerBuilder(3)
        builder.add(0, 2, Owner.STRUCTURE, "first")
        with self.assertRaises(ValueError):
            builder.add(1, 3, Owner.ATOM_CANDIDATE, "overlap")
        with self.assertRaises(ValueError):
            builder.finalize()

    def test_rejects_zero_length_and_post_finalize_mutation(self):
        builder = LedgerBuilder(1)
        with self.assertRaises(ValueError):
            builder.add(0, 0, Owner.STRUCTURE, "empty")
        builder.add(0, 1, Owner.STRUCTURE, "whole")
        ledger = builder.finalize()
        self.assertEqual(ledger.manifest()["owner_bytes"][Owner.STRUCTURE.value], 1)
        with self.assertRaises(RuntimeError):
            builder.add(0, 1, Owner.STRUCTURE, "again")


class TestSixFormatAdapters(unittest.TestCase):
    def assert_exact_partition(self, source: bytes, format_name: str):
        result = adapt(source, format_name)
        spans = result.ledger.spans()
        self.assertEqual(result.ledger.total_bytes, len(source))
        self.assertEqual(sum(span.byte_end - span.byte_start for span in spans), len(source))
        self.assertEqual([span.byte_start for span in spans], sorted(span.byte_start for span in spans))
        for previous, current in zip(spans, spans[1:]):
            self.assertEqual(previous.byte_end, current.byte_start)
        self.assertTrue(all(span.byte_start < span.byte_end for span in spans))
        return result

    def test_txt_and_markdown_keep_terminators(self):
        for format_name in ("txt", "markdown"):
            result = self.assert_exact_partition(b"one\r\n\r\ntwo\n", format_name)
            self.assertTrue(any(span.label == "line_terminator" for span in result.ledger.spans()))

    def test_json_valid_is_partitioned_and_trailing_is_unknown(self):
        valid = self.assert_exact_partition(b'{"a":"x\\u4e2d","b":true}', "json")
        self.assertFalse(any(span.owner == Owner.UNKNOWN_ERROR for span in valid.ledger.spans()))
        trailing = self.assert_exact_partition(b'{"a":1} trailing', "json")
        self.assertEqual(trailing.ledger.spans()[0].owner, Owner.UNKNOWN_ERROR)

    def test_json_invalid_escape_is_unknown(self):
        result = self.assert_exact_partition(b'{"a":"\\q"}', "json")
        self.assertEqual(result.ledger.spans()[0].owner, Owner.UNKNOWN_ERROR)

    def test_jsonl_is_line_bounded_and_owns_blank_terminator(self):
        source = b'{"a":1}\n\n{"b":2}\r\n'
        result = self.assert_exact_partition(source, "jsonl")
        labels = [span.label for span in result.ledger.spans()]
        self.assertEqual(labels.count("jsonl_terminator"), 3)

    def test_structured_conversation_preserves_role_colon_spaces_metadata_and_body(self):
        source = b'  user: [t=1] hello\n\nassistant:ok\r\n'
        result = self.assert_exact_partition(source, "conversation_structured")
        labels = {span.label for span in result.ledger.spans()}
        self.assertTrue({"conversation_leading_space", "conversation_role", "conversation_colon", "conversation_separator_space", "conversation_metadata", "conversation_body", "conversation_terminator"}.issubset(labels))

    def test_plain_conversation_and_empty_input(self):
        self.assert_exact_partition(b'hello\n\nworld', "conversation_plain")
        empty = adapt(b"", "txt")
        self.assertEqual(empty.ledger.spans(), ())
        self.assertEqual(empty.ledger.total_bytes, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
