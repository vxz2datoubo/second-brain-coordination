from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

from creative_runtime.director_review import DirectorReviewViolation, build_director_review_board, verify_director_review_board


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_director_review", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativeDirectorReviewTests(unittest.TestCase):
    def test_board_covers_every_reachable_prefix_with_human_visible_cinematic_cues(self) -> None:
        for scenario, expected_count, expected_scenes in (
            ("three_scene", 12, {"archive_gate", "interior_archive", "dawn_courtyard"}),
            ("night_signal", 24, {"station_platform", "signal_room", "archive_vault", "control_room", "riverside_dawn"}),
            ("harbor_protocol", 24, {"harbor_observatory", "beacon_room", "map_archive", "public_forum", "sunrise_pier"}),
        ):
            with self.subTest(scenario=scenario):
                board = build_director_review_board(scenario).to_dict()
                self.assertEqual(board["schema"], "CreativeDirectorReviewBoard/v1")
                self.assertEqual(board["status"], "director_review_board_verified")
                self.assertEqual(board["card_count"], expected_count)
                self.assertEqual(len({card["timeline_hash"] for card in board["cards"]}), expected_count)
                self.assertEqual({card["state"]["scene_id"] for card in board["cards"]}, expected_scenes)
                self.assertTrue(all(card["quality_report"]["can_generate"] for card in board["cards"]))
                self.assertTrue(all(card["quality_metrics"]["hard_finding_count"] == 0 for card in board["cards"]))
                self.assertTrue(all(card["scene_asset_id"] in card["shots"][0]["reference_artifact_ids"] for card in board["cards"]))
                self.assertTrue(all(card["human_visible_cues"]["lighting"] and card["human_visible_cues"]["sound"] for card in board["cards"]))
                self.assertFalse(board["boundary"]["external_provider_called"])
                self.assertFalse(board["boundary"]["canonical_knowledge_write"])

    def test_board_verifier_rejects_any_changed_quality_or_cinematic_source(self) -> None:
        payload = build_director_review_board("night_signal").to_dict()
        self.assertEqual(verify_director_review_board("night_signal", payload).to_dict(), payload)

        forged_quality = deepcopy(payload)
        forged_quality["cards"][0]["quality_metrics"]["hard_finding_count"] = 1
        with self.assertRaisesRegex(DirectorReviewViolation, "does not exactly match"):
            verify_director_review_board("night_signal", forged_quality)

        forged_axis = deepcopy(payload)
        forged_axis["cards"][0]["shots"][0]["axis"] = "forged-axis"
        with self.assertRaisesRegex(DirectorReviewViolation, "does not exactly match"):
            verify_director_review_board("night_signal", forged_axis)

    def test_cli_reports_the_same_read_only_board(self) -> None:
        cli_board = creativectl.run(["director-review", "--scenario", "harbor_protocol"])
        runtime_board = build_director_review_board("harbor_protocol").to_dict()
        self.assertEqual(cli_board, runtime_board)


if __name__ == "__main__":
    unittest.main()
