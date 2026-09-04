"""Core coverage-matrix invariant tests (WB-S2).

These are the hard-gate assertions behind
``M-REACHABLE-STATE-DIRECTOR-COMPILABILITY-v1``: coverage must be exactly 1.0 and
no state may fall into the silent ``unclassified`` class.
"""

from __future__ import annotations

import unittest

import sys
from pathlib import Path

# Resolve imports without relying on discover's top-level directory, so the
# probe runs the same way from any discover depth.
_REPO_ROOT = Path(__file__).resolve().parents[3]
for _candidate in (str(_REPO_ROOT), str(_REPO_ROOT / "tools" / "workbuddy")):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from director_matrix import matrix, states  # noqa: E402


class CoverageRatioTest(unittest.TestCase):
    def setUp(self) -> None:
        self.body = matrix.run_matrix()

    def test_coverage_ratio_is_exactly_one(self) -> None:
        self.assertEqual(self.body["coverage_ratio"], 1.0)

    def test_no_unclassified_scenario(self) -> None:
        self.assertEqual(self.body["unclassified_count"], 0)
        self.assertEqual(self.body["unclassified"], [])

    def test_no_nondeterministic_state(self) -> None:
        self.assertEqual(self.body["nondeterministic_count"], 0)
        self.assertEqual(self.body["nondeterministic"], [])

    def test_scenario_accounting_is_consistent(self) -> None:
        variants = len(states.missing_asset_variants())
        expected = self.body["reachable_states"] * (1 + variants)
        self.assertEqual(self.body["scenarios"], expected)
        self.assertEqual(self.body["covered_scenarios"], expected)

    def test_every_state_compiles_deterministically_with_full_assets(self) -> None:
        for row in self.body["rows"]:
            self.assertEqual(row["full_assets_classification"], matrix.CLASS_COMPILES, row["state_key"])
            self.assertTrue(row["deterministic"], row["state_key"])

    def test_every_missing_variant_declares_missing_asset(self) -> None:
        for row in self.body["rows"]:
            for variant in row["missing_asset_variants"]:
                self.assertEqual(variant["classification"], matrix.CLASS_MISSING, row["state_key"])


class ClassifyTest(unittest.TestCase):
    def test_full_assets_compiles(self) -> None:
        state = states.reachable_states()[0]
        self.assertEqual(matrix.classify(state, states.full_asset_index()), matrix.CLASS_COMPILES)

    def test_missing_asset_classified_explicitly(self) -> None:
        state = states.reachable_states()[0]
        _, assets = states.missing_asset_variants()[0]
        self.assertEqual(matrix.classify(state, assets), matrix.CLASS_MISSING)

    def test_non_missing_quality_failure_is_unclassified_not_silent(self) -> None:
        # A hard finding that is NOT missing_asset (identity not adult) must be
        # surfaced as unclassified, proving the probe never hides a third class.
        state = states.reachable_states()[0]
        assets = states.full_asset_index()
        assets["art_character_mira"]["adult"] = False
        self.assertEqual(matrix.classify(state, assets), matrix.CLASS_UNCLASSIFIED)


if __name__ == "__main__":
    unittest.main()
