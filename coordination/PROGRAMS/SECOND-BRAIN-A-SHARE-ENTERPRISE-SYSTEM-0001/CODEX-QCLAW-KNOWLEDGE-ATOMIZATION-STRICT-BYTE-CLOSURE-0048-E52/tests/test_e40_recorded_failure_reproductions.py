"""Continuing executable evidence of the exact frozen E40 S0 defects.

The initial red run is retained in REPRODUCTION-LOG.md.  These assertions now
state the candidate defects positively so the normal E52 suite can remain
green while proving that the isolated candidate was never silently promoted.
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


class TestRecordedE40S0DefectEvidence(unittest.TestCase):
    def setUp(self):
        self.module = load_frozen_candidate()
        self.index = self.module.ByteTruthIndex("a€b".encode("utf-8"))

    def test_private_total_bytes_assignment_remains_possible(self):
        """Review finding: E40 catches its own AttributeError and mutates state."""
        self.index._total_bytes = 999
        self.assertEqual(self.index.total_bytes, 999)

    def test_explicit_boundary_to_codepoint_api_is_absent(self):
        """A legal-boundary set is not an offset-to-codepoint-index API."""
        self.assertFalse(hasattr(self.index, "codepoint_index_at_boundary"))

    def test_containing_lookup_is_not_explicitly_named(self):
        """Continuation lookup and boundary lookup are not distinct in E40."""
        self.assertFalse(hasattr(self.index, "chunk_containing_byte"))
        self.assertEqual((self.index.chunk_at_byte(2).byte_start, self.index.chunk_at_byte(2).byte_end), (1, 4))

    def test_canonical_line_records_are_absent(self):
        """The reviewed tuple-only starts cannot encode trailing-empty-line semantics."""
        idx = self.module.ByteTruthIndex(b"a\r\n\r\n")
        self.assertFalse(hasattr(idx, "line_records"))
        self.assertEqual(idx.line_starts()[-1], idx.total_bytes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
