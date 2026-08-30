from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

from creative_runtime.continuity import GraphBeat, GraphTransition, StoryGraph
from creative_runtime.contracts import StoryState
from creative_runtime.coverage import RouteCoverageViolation, cover_routes, coverage_for_scenario, director_coverage_for_scenario


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_route_coverage", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativeRouteCoverageTests(unittest.TestCase):
    def test_every_terminal_route_and_transition_of_three_scene_graph_is_verified(self) -> None:
        report = coverage_for_scenario("three_scene")
        self.assertTrue(report.complete)
        self.assertEqual(len(report.routes), 6)
        self.assertEqual(len(report.covered_transition_ids), 8)
        self.assertEqual(report.covered_transition_ids, report.expected_transition_ids)
        self.assertEqual(report.terminal_state_counts, {"dawn_courtyard/return": 6})
        self.assertTrue(all(route.director_can_generate for route in report.routes))
        self.assertTrue(all(route.director_metrics["hard_finding_count"] == 0 for route in report.routes))
        self.assertEqual(coverage_for_scenario("three_scene").report_hash, report.report_hash)

    def test_legacy_graph_keeps_multiple_safe_terminal_outcomes_covered(self) -> None:
        report = coverage_for_scenario("legacy_archive")
        self.assertTrue(report.complete)
        self.assertEqual(len(report.routes), 6)
        self.assertEqual(len(report.covered_transition_ids), 7)
        self.assertEqual(report.terminal_state_counts, {"synthetic_archive/courtyard": 4, "synthetic_archive/resolution": 2})

    def test_night_signal_is_a_longer_multi_space_route_with_all_branches_covered(self) -> None:
        report = coverage_for_scenario("night_signal")
        self.assertTrue(report.complete)
        self.assertEqual(report.graph_revision, "NightSignalGraph/v1")
        self.assertEqual(len(report.routes), 12)
        self.assertEqual(len(report.covered_transition_ids), 14)
        self.assertEqual(report.terminal_state_counts, {"riverside_dawn/dawn_return": 12})
        self.assertTrue(all(route.director_can_generate for route in report.routes))

        with self.subTest("playable route"):
            import tempfile

            with tempfile.TemporaryDirectory() as directory:
                workspace = Path(directory)
                creativectl.run(["--workspace", str(workspace), "init", "--scenario", "night_signal"])
                for action in ("listen", "approach", "listen", "approach", "listen", "leave"):
                    creativectl.run(["--workspace", str(workspace), "choose", action])
                final = creativectl.run(["--workspace", str(workspace), "replay"])
                director = creativectl.run(["--workspace", str(workspace), "director"])
                self.assertEqual(final["state"]["scene_id"], "riverside_dawn")
                self.assertTrue(director["quality_report"]["can_generate"])
                self.assertIn("art_scene_riverside_dawn", director["shots"][0]["reference_artifact_ids"])

    def test_harbor_protocol_is_a_second_multi_space_interactive_film_with_exhaustive_coverage(self) -> None:
        report = coverage_for_scenario("harbor_protocol")
        self.assertTrue(report.complete)
        self.assertEqual(report.graph_revision, "HarborProtocolGraph/v1")
        self.assertEqual(len(report.routes), 14)
        self.assertEqual(len(report.covered_transition_ids), 12)
        self.assertEqual(report.terminal_state_counts, {"sunrise_pier/daylight_return": 14})
        self.assertTrue(all(route.director_can_generate for route in report.routes))
        self.assertTrue(all(route.director_metrics["hard_finding_count"] == 0 for route in report.routes))

        with self.subTest("playable route with visible earned consequences"):
            import tempfile

            with tempfile.TemporaryDirectory() as directory:
                workspace = Path(directory)
                creativectl.run(["--workspace", str(workspace), "init", "--scenario", "harbor_protocol"])
                for action in ("listen", "approach", "listen", "approach", "listen"):
                    creativectl.run(["--workspace", str(workspace), "choose", action])
                final = creativectl.run(["--workspace", str(workspace), "replay"])
                timeline = creativectl.run(["--workspace", str(workspace), "timeline"])
                director = creativectl.run(["--workspace", str(workspace), "director"])
                catalogue = creativectl.run(["catalog", "--scenario", "harbor_protocol"])
                self.assertEqual(final["state"]["scene_id"], "sunrise_pier")
                self.assertEqual(final["state"]["flags"]["forum"], "witnessed")
                self.assertEqual(timeline["entries"][-1]["consequence"]["relationship_delta"], {"mira": 1})
                self.assertTrue(director["quality_report"]["can_generate"])
                self.assertIn("art_scene_sunrise_pier", director["shots"][0]["reference_artifact_ids"])
                self.assertEqual(catalogue["status"], "scenario_catalog_verified")
                self.assertEqual(len(catalogue["covered_transition_ids"]), 12)
                self.assertTrue(all(edge["target_frame_id"] for edge in catalogue["edges"]))

    def test_cli_coverage_is_read_only_and_rejects_an_unbounded_cycle(self) -> None:
        cli_report = creativectl.run(["coverage", "--scenario", "three_scene"])
        self.assertEqual(cli_report["status"], "route_coverage_verified")
        self.assertEqual(cli_report["route_count"], 6)
        graph = StoryGraph(
            "CycleGraph/v1",
            (GraphBeat("loop", "start", "A bounded test loop."),),
            (GraphTransition("tr_cycle", "loop", "start", "listen", "Loop", {"beat_id": "start"}),),
        )
        with self.assertRaisesRegex(RouteCoverageViolation, "fixed exhaustive route depth"):
            cover_routes(graph, StoryState("loop", "start"), max_steps=2)

    def test_director_coverage_compiles_every_reachable_prefix_and_scene_profile(self) -> None:
        for scenario, expected_profiles in (
            ("three_scene", {"archive_gate", "interior_archive", "dawn_courtyard"}),
            ("night_signal", {"station_platform", "signal_room", "archive_vault", "control_room", "riverside_dawn"}),
            ("harbor_protocol", {"harbor_observatory", "beacon_room", "map_archive", "public_forum", "sunrise_pier"}),
        ):
            with self.subTest(scenario=scenario):
                report = director_coverage_for_scenario(scenario)
                self.assertTrue(report.complete)
                self.assertEqual(set(report.covered_scene_profile_ids), expected_profiles)
                self.assertEqual(report.covered_transition_ids, report.expected_transition_ids)
                self.assertTrue(all(entry.director_can_generate for entry in report.entries))
                self.assertTrue(all(entry.director_metrics["hard_finding_count"] == 0 for entry in report.entries))
                self.assertEqual(director_coverage_for_scenario(scenario).report_hash, report.report_hash)
        cli_report = creativectl.run(["director-coverage", "--scenario", "harbor_protocol"])
        self.assertEqual(cli_report["status"], "director_coverage_verified")
        self.assertEqual(set(cli_report["covered_scene_profile_ids"]), {"harbor_observatory", "beacon_room", "map_archive", "public_forum", "sunrise_pier"})


if __name__ == "__main__":
    unittest.main()
