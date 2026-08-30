from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

from creative_runtime.continuity import GraphBeat, GraphTransition, StoryGraph
from creative_runtime.contracts import StoryState
from creative_runtime.coverage import RouteCoverageViolation, cover_routes, coverage_for_scenario


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


if __name__ == "__main__":
    unittest.main()
