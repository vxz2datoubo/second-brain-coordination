"""B2 tests — SQLite mission ledger, transactions, checkpoint/replay, backup/recovery."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.durable_mission_kernel import ledger  # noqa: E402
from tools.durable_mission_kernel.schemas import EventType, MissionState  # noqa: E402


class B2LedgerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmp.name) / "mission.sqlite")
        self.ledger = ledger.MissionLedger(self.db)

    def tearDown(self):
        self.ledger.close()
        self._tmp.cleanup()

    def _mission_to_ready(self, mission_id="m1"):
        self.ledger.create_mission(mission_id, "r1", "2026-09-09T00:00:00Z")
        self.ledger.append_event(mission_id=mission_id, event_type=EventType.PLAN_STARTED.value,
                                 actor="W", timestamp_iso="2026-09-09T00:00:01Z")
        self.ledger.append_event(mission_id=mission_id, event_type=EventType.PLAN_COMPLETED.value,
                                 actor="W", timestamp_iso="2026-09-09T00:00:02Z")

    def test_create_mission_and_chain_verifies(self):
        self.ledger.create_mission("m1", "r1", "2026-09-09T00:00:00Z")
        self.assertEqual(self.ledger.current_state("m1"), MissionState.CREATED.value)
        self.assertTrue(self.ledger.verify_chain("m1"))

    def test_state_advances_monotonically(self):
        self._mission_to_ready("m1")
        self.assertEqual(self.ledger.current_state("m1"), MissionState.READY.value)
        self.assertEqual(self.ledger.current_state_seq("m1"), 2)
        self.assertTrue(self.ledger.verify_chain("m1"))

    def test_illegal_transition_raises_and_rolls_back(self):
        self.ledger.create_mission("m1", "r1", "2026-09-09T00:00:00Z")
        with self.assertRaises(ledger.LedgerError):
            self.ledger.append_event(mission_id="m1", event_type=EventType.CANONICALIZATION_COMPLETED.value,
                                     actor="W", timestamp_iso="2026-09-09T00:00:01Z")
        # transaction rolled back: state unchanged, no event appended
        self.assertEqual(self.ledger.current_state("m1"), MissionState.CREATED.value)
        self.assertEqual(self.ledger.current_state_seq("m1"), 0)

    def test_checkpoint_and_replay(self):
        self._mission_to_ready("m1")
        self.ledger.checkpoint("m1", {"phase": "B"}, "2026-09-09T00:00:03Z")
        replayed = self.ledger.replay_state("m1")
        self.assertEqual(replayed["state"], MissionState.READY.value)
        self.assertEqual(replayed["state_seq"], 2)
        self.assertEqual(replayed["aggregate"]["event_count"], 3)  # genesis + 2

    def test_backup_and_recover(self):
        self._mission_to_ready("m1")
        backup_path = str(Path(self._tmp.name) / "backup.sqlite")
        self.ledger.backup(backup_path)
        recovered = ledger.MissionLedger.recover_from_backup(
            backup_path, str(Path(self._tmp.name) / "recovered.sqlite")
        )
        try:
            self.assertEqual(recovered.current_state("m1"), MissionState.READY.value)
            self.assertTrue(recovered.verify_chain("m1"))
        finally:
            recovered.close()

    def test_integrity_check_ok(self):
        self._mission_to_ready("m1")
        self.assertTrue(self.ledger.integrity_check())

    def test_duplicate_mission_rejected(self):
        self.ledger.create_mission("m1", "r1", "2026-09-09T00:00:00Z")
        with self.assertRaises(ledger.LedgerError):
            self.ledger.create_mission("m1", "r2", "2026-09-09T00:00:01Z")


if __name__ == "__main__":
    unittest.main()
