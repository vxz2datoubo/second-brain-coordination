"""Red regressions against the exact frozen E40 S0 candidate.

These tests intentionally run before E52 production implementation.  The
candidate is kept in a separate namespace and may never become E52 production
code.  Initial failures are evidence, not a green acceptance claim.
"""
from __future__ import annotations

import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_PATH = PROGRAM_ROOT / "src" / "e52_strict_byte" / "e40_candidate" / "immutable_index.py"
FROZEN_CANDIDATE_SHA256 = "abea1e50dfe37cfa22908d7cf11c3402da1a0083796e944af3f31c52c57699b2"


def load_frozen_candidate():
    spec = importlib.util.spec_from_file_location("e52_e40_frozen_candidate", CANDIDATE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen E40 candidate")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestFrozenSourceIdentity(unittest.TestCase):
    def test_exact_candidate_blob_content_is_preserved(self):
        self.assertEqual(hashlib.sha256(CANDIDATE_PATH.read_bytes()).hexdigest(), FROZEN_CANDIDATE_SHA256)


class TestRecordedE40S0Failures(unittest.TestCase):
    def setUp(self):
        self.module = load_frozen_candidate()
        self.index = self.module.ByteTruthIndex("a€b".encode("utf-8"))

    def test_private_total_bytes_assignment_is_rejected(self):
        """Review finding: E40 catches its own AttributeError and mutates state."""
        with self.assertRaises(AttributeError):
            self.index._total_bytes = 999

    def test_explicit_boundary_to_codepoint_api_includes_eof(self):
        """A legal-boundary set is not an offset-to-codepoint-index API."""
        self.assertEqual(self.index.codepoint_index_at_boundary(0), 0)
        self.assertEqual(self.index.codepoint_index_at_boundary(self.index.total_bytes), 3)
        with self.assertRaises(ValueError):
            self.index.codepoint_index_at_boundary(2)

    def test_containing_lookup_is_explicitly_named_and_excludes_eof(self):
        """Continuation lookup and boundary lookup must not share one ambiguous API."""
        containing = self.index.chunk_containing_byte(2)
        self.assertEqual((containing.byte_start, containing.byte_end), (1, 4))
        with self.assertRaises(IndexError):
            self.index.chunk_containing_byte(self.index.total_bytes)

    def test_canonical_line_records_represent_final_terminator_without_empty_span(self):
        """The reviewed tuple-only starts cannot encode trailing-empty-line semantics."""
        idx = self.module.ByteTruthIndex(b"a\r\n\r\n")
        records = idx.line_records()
        self.assertTrue(all(record.content_start < record.content_end or record.has_trailing_empty_line for record in records))
        self.assertTrue(all(record.terminator_start < record.terminator_end for record in records if record.terminator_end is not None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
