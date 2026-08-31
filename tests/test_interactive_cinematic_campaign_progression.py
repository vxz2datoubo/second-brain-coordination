from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from apps.cli import creativectl
from creative_runtime.campaign_progression import build_campaign_progression


class CampaignProgressionTests(unittest.TestCase):
    def test_progression_is_deterministic_and_rewards_are_source_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "three_scene"])
            creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            creativectl.run(["--workspace", str(workspace), "choose", "approach"])
            ledger = creativectl._load_session(workspace)
            first = build_campaign_progression(ledger)
            second = build_campaign_progression(ledger)
            self.assertEqual(first, second)
            self.assertEqual("campaign_progression_verified", first["status"])
            self.assertEqual("active", first["quest_state"]["status"])
            self.assertEqual(1, first["relationship_states"][0]["trust"])
            self.assertEqual("pressuring", first["antagonist_states"][0]["status"])
            self.assertEqual(first["relationship_states"][0]["known_by_character"], first["antagonist_states"][0]["secret_boundary"])
            self.assertTrue(first["reward_states"])
            self.assertTrue(all(reward["source_event_id"].startswith("evt_") for reward in first["reward_states"]))

    def test_cli_exposes_quest_relationship_reward_and_ending_projection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "harbor_protocol"])
            response = creativectl.run(["--workspace", str(workspace), "campaign"])
            self.assertEqual("PlayerCampaignProgression/v1", response["schema"])
            self.assertIn("quest_state", response)
            self.assertIn("relationship_states", response)
            self.assertIn("antagonist_states", response)
            self.assertIn("reward_states", response)
            self.assertFalse(response["ending"]["is_terminal"])


if __name__ == "__main__":
    unittest.main()
