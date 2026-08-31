from __future__ import annotations

from copy import deepcopy
import unittest

from apps.cli import creativectl
from creative_runtime.flagship_season import FLAGSHIP_SEASON_01, FlagshipSeasonViolation, validate_flagship_season


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


if __name__ == "__main__":
    unittest.main()
