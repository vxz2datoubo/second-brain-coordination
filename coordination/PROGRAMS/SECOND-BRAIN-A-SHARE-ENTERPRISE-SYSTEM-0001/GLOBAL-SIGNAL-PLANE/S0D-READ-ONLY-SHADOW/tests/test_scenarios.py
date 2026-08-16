from __future__ import annotations

import unittest

from global_signal_shadow.scenarios import SCENARIO_IDS, run_all


class ScenarioMatrixTest(unittest.TestCase):
    def test_r001_to_r020_are_mechanism_derived(self) -> None:
        reports = run_all()
        self.assertEqual([report["id"] for report in reports], list(SCENARIO_IDS))
        self.assertTrue(all(report["observed"] and report["result"] == "PASS" for report in reports), reports)
