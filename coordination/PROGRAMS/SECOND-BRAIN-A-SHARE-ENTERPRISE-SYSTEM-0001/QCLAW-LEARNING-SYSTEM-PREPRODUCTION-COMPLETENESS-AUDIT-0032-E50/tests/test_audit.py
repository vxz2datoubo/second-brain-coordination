"""Unit tests for E50 R2 audit modules (canonical-system audit).

These tests verify the audit harness itself is wired correctly: each
dimension module runs against the vendored canonical snapshot and returns
a valid DimensionVerdict, and the runner produces a coherent matrix +
risk-critical recommendation.
"""
from __future__ import annotations

import os
import sys
import unittest

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from qclaw_e50_audit import runner  # noqa: E402
from qclaw_e50_audit.evidence_matrix import (  # noqa: E402
    VERDICT_PASS, VERDICT_PARTIAL, VERDICT_FAIL, VERDICT_BLOCKED,
    VERDICT_NOT_AVAILABLE,
)


class TestDimensions(unittest.TestCase):
    def test_all_dimensions_return_verdict(self):
        result = runner.run_audit()
        dims = result["matrix"]["dimensions"]
        self.assertEqual(len(dims), 12)
        valid = {VERDICT_PASS, VERDICT_PARTIAL, VERDICT_FAIL,
                 VERDICT_BLOCKED, VERDICT_NOT_AVAILABLE}
        for d in dims:
            self.assertIn(d["verdict"], valid, f"{d['dimension']} bad verdict")
            self.assertIn(d["dimension"], [f"D{i}" for i in range(1, 13)])

    def test_canonical_head_sha_bound(self):
        result = runner.run_audit()
        sha = result["canonical_head_sha"]
        self.assertEqual(len(sha), 40)
        self.assertTrue(all(c in "0123456789abcdef" for c in sha))

    def test_critical_dimensions_flag(self):
        result = runner.run_audit()
        dims = result["matrix"]["dimensions"]
        critical = {d["dimension"] for d in dims if d["critical"]}
        # authority/provenance/privacy/stale-recall/skill-promotion gates
        self.assertIn("D1", critical)
        self.assertIn("D4", critical)
        self.assertIn("D6", critical)
        self.assertIn("D7", critical)
        self.assertIn("D8", critical)
        self.assertIn("D9", critical)

    def test_recommendation_is_not_ready_on_partial_critical(self):
        result = runner.run_audit()
        rec = result["recommendation"]
        # D3/D5/D10 are PARTIAL critical gates -> must be NOT_READY
        self.assertEqual(rec["recommendation"], "NOT_READY")
        self.assertGreaterEqual(len(rec["blockers"]), 1)

    def test_coverage_consistent(self):
        result = runner.run_audit()
        cov = result["coverage"]
        self.assertEqual(cov["fixture_total"], 13)
        self.assertGreaterEqual(cov["unsupported"], 8)

    def test_no_local_standin_pass_credit(self):
        # The audit must not import the _untrusted_test_double modules for
        # canonical credit. Verify dimension modules are the canonical-audit
        # ones (they live in dimensions/, not _untrusted_test_double/).
        from qclaw_e50_audit.dimensions import d1_ingestion
        modfile = d1_ingestion.__file__
        self.assertNotIn("_untrusted_test_double", modfile)


if __name__ == "__main__":
    unittest.main()
