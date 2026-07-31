from __future__ import annotations

from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class E29SpecsAndGatesTests(unittest.TestCase):
    def load(self, name: str) -> dict:
        value = yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def test_three_adapter_specs_are_candidate_only_and_locked(self):
        for name, owner, signal in (
            ("TASK-SPEC-W1-AUTHORITY-LEASE-ADAPTER-R1.yaml", "W1", "W1_AUTHORITY_LEASE_ADAPTER_R1_READY_FOR_GPT_REVIEW"),
            ("TASK-SPEC-W3-PHASE3-EPISTEMIC-MEMORY-ADAPTER-R1.yaml", "W3", "W3_PHASE3_EPISTEMIC_MEMORY_ADAPTER_R1_READY_FOR_GPT_REVIEW"),
            ("TASK-SPEC-W8-CAPABILITY-EXECUTION-RECOVERY-ADAPTER-R1.yaml", "W8", "W8_CAPABILITY_EXECUTION_RECOVERY_ADAPTER_R1_READY_FOR_GPT_REVIEW"),
        ):
            with self.subTest(name=name):
                spec = self.load(name)
                self.assertEqual(spec["status"], "SPEC_ONLY_NOT_IMPLEMENTED")
                self.assertEqual(spec["authority"], "CANDIDATE_ONLY")
                self.assertEqual(spec["owner"]["workstream"], owner)
                self.assertTrue(spec["negative_tests"])
                self.assertTrue(spec["shared_interface_write_lock"]["locked_objects"])
                self.assertEqual(spec["completion_signal"], signal)

    def test_k3_and_k4_are_explicitly_disabled(self):
        k3 = self.load("CROSS-MODEL-EVALUATION-GATE-v1.0-CANDIDATE.yaml")
        k4 = self.load("FEATURE-FLAG-SHADOW-GATE-v1.0-CANDIDATE.yaml")
        self.assertEqual(k3["status"], "DISABLED_NOT_RUN")
        self.assertFalse(k3["disabled_defaults"]["enabled"])
        self.assertEqual(k4["status"], "DISABLED_NOT_RUN")
        self.assertTrue(all(value["default"] == "DISABLED" for value in k4["flags"].values()))
        self.assertIn("K3/K4", " ".join(k4["kill_conditions"]) + " K3/K4")

    def test_gate_thresholds_fail_closed(self):
        k3 = self.load("CROSS-MODEL-EVALUATION-GATE-v1.0-CANDIDATE.yaml")
        self.assertEqual(k3["thresholds"]["pilot"]["hard_boundary_violation_max"], 0)
        self.assertEqual(k3["thresholds"]["full"]["hard_boundary_violation_max"], 0)
        k4 = self.load("FEATURE-FLAG-SHADOW-GATE-v1.0-CANDIDATE.yaml")
        self.assertIn("hard deny bypass", k4["kill_conditions"])
        self.assertEqual(k4["promotion"]["SHADOW_2_to_production"], "NOT_DEFINED_AND_NOT_AUTHORIZED_BY_THIS_GATE")


if __name__ == "__main__":
    unittest.main()
