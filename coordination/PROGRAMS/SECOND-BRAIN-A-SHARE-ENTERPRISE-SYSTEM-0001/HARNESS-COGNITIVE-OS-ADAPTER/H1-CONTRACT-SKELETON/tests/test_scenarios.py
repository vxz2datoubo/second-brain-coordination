from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cognitive_os_h1.scenario_runner import execute_scenario  # noqa: E402


class ScenarioTest(unittest.TestCase):
    def test_s1_to_s10_are_executable_public_safe_scenarios(self):
        scenarios = json.loads((ROOT / "fixtures" / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]
        self.assertEqual([item["id"] for item in scenarios], ["S1","S2","S3","S4","S5","S6","S7","S8","S9","S10"])
        for spec in scenarios:
            with self.subTest(scenario=spec["id"]):
                receipt = execute_scenario(spec)
                self.assertEqual(receipt.final_disposition, spec["final_disposition"])
                self.assertEqual(receipt.transitions_checked, len(spec["expected_transitions"]))
                self.assertEqual({error.code for error in receipt.errors}, set(spec["expected_errors"]))


if __name__ == "__main__": unittest.main()
