from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from creative_runtime.presentation import PresentationViolation, build_interactive_frame
from creative_runtime.ledger import CreativeLedger


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_presentation", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativePresentationTests(unittest.TestCase):
    def test_frame_contains_only_verified_current_state_choices_and_director_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "--slot", "route_b", "init", "--scenario", "night_signal"])
            first = creativectl.run(["--workspace", str(workspace), "--slot", "route_b", "frame"])
            creativectl.run(["--workspace", str(workspace), "--slot", "route_b", "choose", "listen"])
            second = creativectl.run(["--workspace", str(workspace), "--slot", "route_b", "frame"])

            self.assertEqual(first["status"], "interactive_frame_verified")
            self.assertEqual(first["slot_id"], "route_b")
            self.assertEqual(first["state"]["beat_id"], "platform_arrival")
            self.assertEqual({item["action_id"] for item in first["legal_choices"]}, {"listen", "approach", "leave"})
            self.assertEqual(first["accessibility"]["safe_intent"]["schema"], "CreativeSafeIntentProjection/v1")
            self.assertEqual(first["accessibility"]["safe_intent"]["status"], "safe_intent_projection_verified")
            self.assertTrue(all(choice["safe_intent_examples"] for choice in first["legal_choices"]))
            self.assertEqual(second["state"]["beat_id"], "platform_signal")
            self.assertNotEqual(first["frame_id"], second["frame_id"])
            self.assertEqual(second["recent_consequence"]["new_facts"], ["a protected relay is active"])
            self.assertEqual(second["recent_action"]["action_id"], "listen")
            self.assertIsNone(first["recent_action"]["action_id"])
            self.assertEqual(second["accessibility"]["known_facts_only"], ["a protected relay is active"])
            self.assertTrue(second["director"]["shots"])
            self.assertEqual(second["director"]["content_rating"], "non_explicit")

    def test_frame_never_materializes_for_an_empty_or_unverified_ledger(self) -> None:
        with self.assertRaisesRegex(PresentationViolation, "verified story timeline"):
            build_interactive_frame(CreativeLedger())


if __name__ == "__main__":
    unittest.main()
