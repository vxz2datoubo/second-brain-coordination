from __future__ import annotations

from copy import deepcopy
import tempfile
import unittest
from pathlib import Path

from apps.cli import creativectl
from creative_runtime.continuity import glass_harbor_story_graph
from creative_runtime.coverage import cover_routes
from creative_runtime.flagship_season import FLAGSHIP_SEASON_01, FlagshipSeasonViolation, validate_flagship_season
from creative_runtime.script_packages import script_for_ledger


class FlagshipSeasonTests(unittest.TestCase):
    def test_authoring_bible_has_three_acts_six_chapters_and_twelve_meaningful_choices(self) -> None:
        report = validate_flagship_season()
        self.assertEqual("flagship_season_authoring_valid", report["status"])
        self.assertEqual(3, report["act_count"])
        self.assertEqual(6, report["chapter_count"])
        self.assertEqual(12, report["primary_choice_count"])
        self.assertEqual(100, report["choice_coverage_percent"])
        self.assertFalse(report["runtime_ready"])

    def test_invalid_choice_without_cost_feedback_or_change_is_rejected(self) -> None:
        season = deepcopy(FLAGSHIP_SEASON_01)
        season["chapters"][0]["choices"][0]["changes"] = []
        with self.assertRaisesRegex(FlagshipSeasonViolation, "durable-change"):
            validate_flagship_season(season)
        season = deepcopy(FLAGSHIP_SEASON_01)
        season["chapters"][5]["choices"][1]["cost"] = ""
        with self.assertRaisesRegex(FlagshipSeasonViolation, "feedback, cost, and later echo"):
            validate_flagship_season(season)

    def test_cli_exposes_authoring_content_without_claiming_runtime_or_media_readiness(self) -> None:
        response = creativectl.run(["flagship-season"])
        self.assertEqual("glass-harbor-season-01", response["season"]["script_id"])
        self.assertFalse(response["validation"]["runtime_ready"])
        self.assertFalse(response["boundary"]["external_assets_loaded"])
        self.assertFalse(response["boundary"]["generated_media_loaded"])

    def test_flagship_graph_has_twelve_verified_edges_and_a_replayable_ending(self) -> None:
        graph = glass_harbor_story_graph()
        coverage = cover_routes(graph, creativectl.SCENARIOS["glass_harbor"], max_steps=6)
        self.assertTrue(coverage.complete)
        self.assertEqual(12, len(coverage.covered_transition_ids))
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--script-id", "glass-harbor-season-01", "--script-revision", "GlassHarborSeason01/v1"])
            for action in ("listen", "listen", "listen", "listen", "listen", "listen"):
                creativectl.run(["--workspace", str(workspace), "choose", action])
            replay = creativectl.run(["--workspace", str(workspace), "replay"])
            self.assertEqual("ending_dawn", replay["state"]["beat_id"])
            self.assertEqual("glass-harbor-season-01", script_for_ledger(creativectl._load_session(workspace)).script_id)


if __name__ == "__main__":
    unittest.main()
