from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "apps" / "web" / "verified_experience_player.html"


class CreativeWebPlayerTests(unittest.TestCase):
    def test_static_player_only_accepts_verified_synthetic_catalogues(self) -> None:
        source = PLAYER.read_text(encoding="utf-8")
        self.assertIn("CreativeRuntimeExperienceArtifact/v1", source)
        self.assertIn("scenario_catalog_verified", source)
        self.assertIn("sequence_plan_verified", source)
        self.assertIn("VerifiedInteractiveSequencePlan/v1", source)
        self.assertIn("Sequence cut policy", source)
        self.assertIn("nodeSequenceSteps", source)
        self.assertIn("action_label", source)
        self.assertIn("target_frame_id", source)
        self.assertIn("Catalogue edge consequence does not match its target frame.", source)
        self.assertIn("Last consequence", source)
        self.assertIn("consequenceSummary", source)
        self.assertIn("choiceImpactPreview", source)
        self.assertIn("Verified impact:", source)
        self.assertIn("choice-preview", source)
        self.assertIn("canonicalJson", source)
        self.assertIn("Lighting", source)
        self.assertIn("Spatial axis", source)
        self.assertIn("VerifiedCutContract/v1", source)
        self.assertIn("validateCutContract", source)
        self.assertIn("new_scene_axis_reestablished", source)
        self.assertIn("Verified journey", source)
        self.assertIn("renderJourney", source)
        self.assertIn("Restart verified journey", source)
        self.assertIn("from_timeline_hash", source)
        self.assertIn("interactive_frame_verified", source)
        self.assertIn("client_story_authority === false", source)
        self.assertIn("edge.to_timeline_hash", source)
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)
        self.assertNotIn("WebSocket", source)
        self.assertNotIn("navigator.sendBeacon", source)
        self.assertNotIn("https://", source)
        self.assertNotIn("http://", source)
        self.assertNotIn("<script src=", source)


if __name__ == "__main__":
    unittest.main()
