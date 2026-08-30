from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from creative_runtime.continuity import TimelineViolation, default_story_graph, graph_for_ledger, replay_timeline, timeline_hash, verified_director_input
from creative_runtime.contracts import PlayerAction, StoryState
from creative_runtime.director import compile_verified_director
from creative_runtime.ledger import CreativeLedger
from creative_runtime.knowledge import KnowledgeReviewBridge, correct_from_verified_timeline


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_continuity", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativeContinuityTests(unittest.TestCase):
    def initialized_ledger(self) -> CreativeLedger:
        ledger = CreativeLedger()
        ledger.append(
            "story_initialized",
            {"state": StoryState(scene_id="synthetic_archive", beat_id="arrival", relationships={"mira": 0}).to_dict()},
            "2030-01-01T00:00:00Z",
        )
        return ledger

    def append_graph_choice(
        self,
        ledger: CreativeLedger,
        action_id: str,
        minute: int,
        *,
        declared_id: str | None = None,
        patch: dict | None = None,
    ) -> None:
        state = ledger.replay()
        transition = default_story_graph().transition_for(state, action_id)
        ledger.append(
            "player_action",
            {
                "action": PlayerAction(action_id, "choice", transition.label).to_dict(),
                "resulting_patch": patch if patch is not None else dict(transition.resulting_patch),
                "transition_id": declared_id if declared_id is not None else transition.transition_id,
                "graph_revision": default_story_graph().revision,
            },
            f"2030-01-01T00:{minute:02d}:00Z",
        )

    def test_each_timeline_row_is_its_own_replayed_prefix(self) -> None:
        ledger = self.initialized_ledger()
        self.append_graph_choice(ledger, "listen", 1)
        self.append_graph_choice(ledger, "approach", 2)
        self.append_graph_choice(ledger, "listen", 3)
        entries = replay_timeline(ledger)
        self.assertEqual([entry.state.beat_id for entry in entries], ["arrival", "echo", "threshold", "resolution"])
        self.assertEqual([entry.state.risk_level for entry in entries], [0, 1, 1, 0])
        self.assertEqual([entry.state.relationships["mira"] for entry in entries], [0, 0, 1, 2])
        self.assertEqual(entries[2].consequence["relationship_delta"], {"mira": 1})
        self.assertEqual(entries[3].consequence["risk_delta"], -1)
        self.assertNotEqual(entries[1].prefix_hash, entries[3].prefix_hash)
        self.assertEqual(verified_director_input(ledger).state, entries[-1].state)
        director = compile_verified_director(ledger)
        self.assertEqual(director.compilation.brief.story_state, entries[-1].state)
        self.assertEqual(director.verified_input.timeline_hash, timeline_hash(entries))

    def test_hash_valid_but_semantically_forged_patch_fails_closed(self) -> None:
        ledger = self.initialized_ledger()
        self.append_graph_choice(
            ledger,
            "listen",
            1,
            patch={"beat_id": "echo", "reveal_facts": ["a witness is inside", "invented fact"], "risk_delta": 1},
        )
        with self.assertRaisesRegex(TimelineViolation, "semantically equal"):
            replay_timeline(ledger)
        with self.assertRaisesRegex(TimelineViolation, "semantically equal"):
            compile_verified_director(ledger)
        bridge = KnowledgeReviewBridge()
        with self.assertRaisesRegex(TimelineViolation, "semantically equal"):
            correct_from_verified_timeline(bridge, "Never accept forged story evidence.", ledger, default_story_graph())
        self.assertEqual(bridge.to_records(), [])

    def test_hash_valid_wrong_transition_id_fails_closed(self) -> None:
        ledger = self.initialized_ledger()
        self.append_graph_choice(ledger, "listen", 1, declared_id="tr_forged")
        with self.assertRaisesRegex(TimelineViolation, "transition_id"):
            replay_timeline(ledger)

    def test_hash_valid_unknown_action_fails_closed(self) -> None:
        ledger = self.initialized_ledger()
        ledger.append(
            "player_action",
            {
                "action": PlayerAction("invent", "choice", "Invent an unsupported outcome").to_dict(),
                "resulting_patch": {"beat_id": "echo"},
            },
            "2030-01-01T00:01:00Z",
        )
        with self.assertRaisesRegex(TimelineViolation, "No legal transition"):
            replay_timeline(ledger)

    def test_legacy_session_without_new_ids_is_checked_by_exact_patch(self) -> None:
        ledger = self.initialized_ledger()
        transition = default_story_graph().transition_for(ledger.replay(), "listen")
        ledger.append(
            "player_action",
            {
                "action": PlayerAction("listen", "choice", transition.label).to_dict(),
                "resulting_patch": dict(transition.resulting_patch),
            },
            "2030-01-01T00:01:00Z",
        )
        entries = replay_timeline(ledger)
        self.assertEqual(entries[-1].state.beat_id, "echo")

    def test_cli_emits_graph_ids_and_can_print_a_verified_timeline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init"])
            creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            creativectl.run(["--workspace", str(workspace), "choose", "approach"])
            timeline = creativectl.run(["--workspace", str(workspace), "timeline"])
            director = creativectl.run(["--workspace", str(workspace), "director"])
            understanding = creativectl.run(["--workspace", str(workspace), "understanding"])
            derived = creativectl.run(["--workspace", str(workspace), "knowledge", "derive", "A cautious choice can preserve a witness lead."])
            self.assertEqual(timeline["status"], "timeline_verified")
            self.assertEqual(len(timeline["entries"]), 3)
            self.assertEqual(timeline["entries"][-1]["state"]["beat_id"], "threshold")
            self.assertTrue(timeline["entries"][-1]["transition_id"].startswith("tr_"))
            self.assertEqual(timeline["timeline_hash"], timeline_hash(replay_timeline(creativectl._load_session(workspace))))
            self.assertEqual(director["status"], "director_verified")
            self.assertTrue(director["quality_report"]["can_generate"])
            self.assertEqual(understanding["status"], "understanding_mapped")
            self.assertEqual(understanding["drift_assessments"][0]["status"], "pass")
            self.assertEqual(derived["status"], "pending_human_review")
            self.assertEqual(derived["verified_timeline_candidate"]["candidate"]["source_event_ids"], [timeline["entries"][-1]["event_id"]])

    def test_three_scene_route_retains_scene_by_scene_consequences(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "three_scene"])
            creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            creativectl.run(["--workspace", str(workspace), "choose", "approach"])
            creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            creativectl.run(["--workspace", str(workspace), "choose", "leave"])
            ledger = creativectl._load_session(workspace)
            self.assertEqual(graph_for_ledger(ledger).revision, "ArchiveJourneyGraph/v1")
            timeline = creativectl.run(["--workspace", str(workspace), "timeline"])
            self.assertEqual(
                [(entry["state"]["scene_id"], entry["state"]["beat_id"]) for entry in timeline["entries"]],
                [
                    ("archive_gate", "arrival"),
                    ("archive_gate", "echo"),
                    ("interior_archive", "threshold"),
                    ("interior_archive", "accord"),
                    ("dawn_courtyard", "return"),
                ],
            )
            self.assertEqual(timeline["entries"][2]["consequence"]["flag_changes"], {"clue": "heard"})
            director = creativectl.run(["--workspace", str(workspace), "director"])
            self.assertEqual(director["verified_input"]["graph_revision"], "ArchiveJourneyGraph/v1")
            self.assertIn("art_scene_dawn_courtyard", director["shots"][0]["reference_artifact_ids"])


if __name__ == "__main__":
    unittest.main()
