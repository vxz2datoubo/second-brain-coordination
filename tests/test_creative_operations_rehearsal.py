from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creative_operations_rehearsal", ROOT / "tools" / "rehearse_creative_operations.py")
assert SPEC and SPEC.loader
rehearsal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rehearsal)


class CreativeOperationsRehearsalTests(unittest.TestCase):
    def test_three_synthetic_sessions_have_isolated_idempotent_lifecycles(self) -> None:
        report = rehearsal.rehearse_operations(3)
        self.assertEqual(report["schema"], "CreativeRuntimeSyntheticOperationsRehearsal/v1")
        self.assertEqual(report["status"], "synthetic_operations_rehearsal_verified")
        self.assertEqual(report["session_count"], 3)
        self.assertEqual(report["per_session_event_count"], 3)
        self.assertEqual(report["total_event_count"], 9)
        self.assertEqual(report["idempotent_retry_count"], 3)
        self.assertEqual(report["independent_slot_count"], 3)
        self.assertEqual(report["scenario_session_counts"], {"harbor_protocol": 1, "night_signal": 2})
        self.assertEqual(report["all_final_scenes"], ["beacon_room", "signal_room"])
        self.assertEqual(report["operations_metrics"]["verified_slot_count"], 3)
        self.assertEqual(report["operations_metrics"]["active_lock_count"], 0)
        self.assertTrue(report["boundary"]["synthetic_only"])
        self.assertFalse(report["boundary"]["production_capacity_claim"])
        self.assertTrue(all(item["retry_status"] == "command_already_applied" for item in report["sessions"]))
        self.assertEqual([item["scenario"] for item in report["sessions"]], ["night_signal", "harbor_protocol", "night_signal"])

    def test_rehearsal_rejects_unbounded_or_empty_session_counts(self) -> None:
        for value in (0, 17, -1, "3"):
            with self.assertRaisesRegex(ValueError, "session_count"):
                rehearsal.rehearse_operations(value)


if __name__ == "__main__":
    unittest.main()
