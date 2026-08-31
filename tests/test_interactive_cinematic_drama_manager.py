from __future__ import annotations

from dataclasses import replace
import tempfile
import unittest
from pathlib import Path

from apps.cli import creativectl
from creative_runtime.continuity import graph_for_initial_state
from creative_runtime.contracts import NarrativeProposal, StoryState
from creative_runtime.drama_manager import DramaManagerViolation, primary_choice_consequence_coverage, propose_offline_narrative, select_verified_dramatic_beat


class DramaManagerTests(unittest.TestCase):
    def test_every_synthetic_primary_choice_has_a_durable_change_and_feedback(self) -> None:
        scenarios = (
            StoryState("synthetic_archive", "arrival", {"mira": 0}),
            StoryState("archive_gate", "arrival", {"mira": 0}),
            StoryState("station_platform", "platform_arrival", {"mira": 0}),
            StoryState("harbor_observatory", "dock_arrival", {"mira": 0}),
        )
        for initial in scenarios:
            report = primary_choice_consequence_coverage(graph_for_initial_state(initial))
            self.assertEqual(100, report["coverage_percent"])
            self.assertTrue(report["entries"])
            self.assertTrue(all(entry["changed_dimensions"] and entry["feedback_type"] for entry in report["entries"]))

    def test_proposal_is_candidate_only_but_exact_legal_edge_is_selectable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "three_scene"])
            ledger = creativectl._load_session(workspace)
            proposal = propose_offline_narrative(ledger, "listen")
            selection = select_verified_dramatic_beat(ledger, proposal)
            self.assertEqual("NarrativeProposal/v1", proposal.schema)
            self.assertEqual("echo", selection.selected_beat_id)
            self.assertEqual(1, len(ledger.events))
            self.assertIn(proposal.candidate_presentation["feedback_type"], {"new_clue", "companion_reaction", "risk_shift", "task_or_record_progress", "scene_progress"})

    def test_stale_or_forged_proposals_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "three_scene"])
            ledger = creativectl._load_session(workspace)
            valid = propose_offline_narrative(ledger, "listen")
            with self.assertRaisesRegex(DramaManagerViolation, "not legal"):
                select_verified_dramatic_beat(ledger, replace(valid, proposed_transition_id="forged_transition"))
            with self.assertRaisesRegex(DramaManagerViolation, "feedback type"):
                select_verified_dramatic_beat(ledger, replace(valid, candidate_presentation={"feedback_type": "invented"}))
            creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            advanced = creativectl._load_session(workspace)
            with self.assertRaisesRegex(DramaManagerViolation, "current verified campaign state"):
                select_verified_dramatic_beat(advanced, valid)

    def test_cli_exposes_source_bound_proposal_and_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "harbor_protocol"])
            response = creativectl.run(["--workspace", str(workspace), "propose", "listen"])
            self.assertEqual("proposal_verified", response["status"])
            coverage = creativectl.run(["drama-coverage", "--scenario", "harbor_protocol"])
            self.assertEqual("primary_choice_consequences_verified", coverage["status"])


if __name__ == "__main__":
    unittest.main()
