import unittest
from global_signal_shadow.scenarios import SCENARIO_IDS, run_all

class ScenarioMatrixTest(unittest.TestCase):
    def test_r001_to_r020_are_observed_mechanisms(self) -> None:
        reports = run_all()
        self.assertEqual([row["id"] for row in reports], list(SCENARIO_IDS))
        self.assertTrue(all(row["observed"] and row["result"] == "PASS" for row in reports), reports)
