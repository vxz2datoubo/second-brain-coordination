"""B7 tests — failure injection + synthetic endurance canary."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.durable_mission_kernel import endurance, ledger  # noqa: E402
from tools.durable_mission_kernel.schemas import EventType, MissionState  # noqa: E402


class B7EnduranceTests(unittest.TestCase):
    def test_synthetic_endurance_canary_passes(self):
        with tempfile.TemporaryDirectory() as td:
            canary = endurance.SyntheticEnduranceCanary(
                str(Path(td) / "canary.sqlite"), episodes=3, inject_worker_failure=True)
            report = canary.run()
            self.assertTrue(report.chain_verified)
            self.assertEqual(report.final_state, MissionState.COMPLETE.value)
            self.assertEqual(report.worker_failures_injected, 1)
            self.assertGreaterEqual(report.context_rollovers, 1)
            self.assertTrue(report.passed)
            self.assertTrue(any("worker_failure" in e for e in report.evidence))

    def test_crash_reopen_keeps_chain_consistent(self):
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "m.sqlite")
            led = ledger.MissionLedger(db)
            led.create_mission("m1", "r1", "2026-09-09T00:00:00Z")
            led.append_event(mission_id="m1", event_type=EventType.PLAN_STARTED.value,
                             actor="W", timestamp_iso="2026-09-09T00:00:01Z")
            led.append_event(mission_id="m1", event_type=EventType.PLAN_COMPLETED.value,
                             actor="W", timestamp_iso="2026-09-09T00:00:02Z")
            # simulate crash: close without graceful shutdown
            led.close()
            # reopen (WAL recovery)
            led2 = ledger.MissionLedger(db)
            try:
                self.assertTrue(led2.verify_chain("m1"))
                self.assertEqual(led2.current_state("m1"), MissionState.READY.value)
            finally:
                led2.close()


if __name__ == "__main__":
    unittest.main()
