"""Unit tests for the deterministic synthetic campaign generator (WB-S1)."""

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

from campaign_benchmark import synthetic  # noqa: E402
from creative_runtime.contracts import StoryState  # noqa: E402
from creative_runtime.ledger import CreativeLedger  # noqa: E402


class SyntheticCampaignTest(unittest.TestCase):
    def test_build_is_deterministic_for_same_inputs(self) -> None:
        first = synthetic.build_campaign(seed=7, event_count=40)
        second = synthetic.build_campaign(seed=7, event_count=40)
        self.assertEqual(first.to_records(), second.to_records())

    def test_different_seed_changes_campaign(self) -> None:
        first = synthetic.build_campaign(seed=7, event_count=40)
        second = synthetic.build_campaign(seed=8, event_count=40)
        self.assertNotEqual(first.to_records(), second.to_records())

    def test_event_count_is_exact(self) -> None:
        for event_count in (1, 2, 10, 25):
            ledger = synthetic.build_campaign(seed=1, event_count=event_count)
            self.assertEqual(len(ledger.events), event_count)

    def test_single_event_campaign_replays(self) -> None:
        ledger = synthetic.build_campaign(seed=3, event_count=1)
        state = ledger.replay()
        self.assertIsInstance(state, StoryState)
        self.assertEqual(state.beat_id, "bt_open")

    def test_zero_events_rejected(self) -> None:
        with self.assertRaises(ValueError):
            synthetic.build_campaign(seed=1, event_count=0)

    def test_negative_events_rejected(self) -> None:
        with self.assertRaises(ValueError):
            synthetic.build_campaign(seed=1, event_count=-5)

    def test_unknown_style_rejected(self) -> None:
        with self.assertRaises(ValueError):
            synthetic.build_campaign(seed=1, event_count=5, style="real_user_footage")

    def test_all_styles_build(self) -> None:
        for style in synthetic.STYLES:
            ledger = synthetic.build_campaign(seed=2, event_count=20, style=style)
            self.assertEqual(len(ledger.events), 20)
            self.assertEqual(ledger.replay().flags["style"], style)

    def test_both_patch_event_types_are_exercised(self) -> None:
        ledger = synthetic.build_campaign(seed=5, event_count=21)
        types = {event.event_type for event in ledger.events[1:]}
        self.assertEqual(types, {"player_action", "state_patch"})

    def test_chain_verifies_after_round_trip(self) -> None:
        ledger = synthetic.build_campaign(seed=11, event_count=50)
        restored = CreativeLedger.from_records(ledger.to_records())
        restored.verify_chain()
        self.assertEqual(restored.replay().to_dict(), ledger.replay().to_dict())

    def test_same_seed_different_size_differs(self) -> None:
        small = synthetic.build_campaign(seed=4, event_count=10)
        large = synthetic.build_campaign(seed=4, event_count=11)
        self.assertNotEqual(small.to_records(), large.to_records())


class SimulatedHoursTest(unittest.TestCase):
    def test_hours_inside_declared_population_window(self) -> None:
        for seed in range(20):
            hours = synthetic.simulate_campaign_hours(seed=seed, event_count=100)
            self.assertGreaterEqual(hours, 45.0 / 60.0)
            self.assertLessEqual(hours, 60.0 / 60.0)

    def test_hours_are_deterministic(self) -> None:
        self.assertEqual(
            synthetic.simulate_campaign_hours(seed=9, event_count=100),
            synthetic.simulate_campaign_hours(seed=9, event_count=100),
        )

    def test_hours_reject_empty_campaign(self) -> None:
        with self.assertRaises(ValueError):
            synthetic.simulate_campaign_hours(seed=1, event_count=0)


class SummaryTest(unittest.TestCase):
    def test_summary_matches_replay(self) -> None:
        ledger = synthetic.build_campaign(seed=13, event_count=30)
        state = ledger.replay()
        summary = synthetic.summary(ledger)
        self.assertEqual(summary["event_count"], 30)
        self.assertEqual(summary["final_scene_id"], state.scene_id)
        self.assertEqual(summary["known_fact_count"], len(state.known_facts))
        self.assertEqual(summary["head_event_hash"], ledger.events[-1].event_hash)


if __name__ == "__main__":
    unittest.main()
