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
