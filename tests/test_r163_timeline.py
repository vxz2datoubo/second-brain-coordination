from __future__ import annotations

import unittest

from creative_runtime.contracts import PlayerAction
from creative_runtime.ledger import CreativeLedger
from creative_runtime.scene_graph import SceneGraph, synthetic_three_scene_manifest
from creative_runtime.timeline import TimelineViolation, build_prefix_timeline


class R163TimelineTruthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = SceneGraph(synthetic_three_scene_manifest())

    def _ledger(self, actions: list[str]) -> CreativeLedger:
        ledger = CreativeLedger()
        state = self.graph.initial_state()
        ledger.append(
            "story_initialized",
            {"state": state.to_dict()},
            "2030-01-01T00:00:00Z",
        )
        for minute, action_id in enumerate(actions, start=1):
            next_state, action = self.graph.apply(state, action_id)
            ledger.append(
                "player_action",
                {
                    "action": PlayerAction(action_id, "choice", action.label).to_dict(),
                    "transition_id": action.transition_id,
                    "resulting_patch": {
                        **dict(action.patch),
                        "scene_id": next_state.scene_id,
                        "beat_id": next_state.beat_id,
                    },
                },
                f"2030-01-01T00:{minute:02d}:00Z",
            )
            state = next_state
        return ledger

    def test_three_action_timeline_is_exact_prefix_state_not_final_state_repeated(self) -> None:
        ledger = self._ledger(["listen", "knock", "promise"])
        timeline = build_prefix_timeline(ledger, self.graph)

        self.assertEqual(len(timeline), 4)
        states = [entry.state.to_dict() for entry in timeline]
        self.assertEqual(
            [(item["scene_id"], item["beat_id"]) for item in states],
            [
                ("archive_gate", "arrival"),
                ("archive_gate", "echo"),
                ("interior_archive", "threshold"),
                ("interior_archive", "accord"),
            ],
        )
        self.assertEqual([item["risk_level"] for item in states], [0, 1, 1, 0])
        self.assertEqual([item["relationships"]["mira"] for item in states], [0, 0, 1, 2])
        self.assertEqual(states[0]["known_facts"], [])
        self.assertEqual(states[1]["known_facts"], ["a witness is inside"])
        self.assertEqual(states[2]["known_facts"], ["a witness is inside"])
        self.assertEqual(states[3]["known_facts"], ["a witness is inside"])
        self.assertEqual(
            [item["flags"] for item in states],
            [{}, {}, {"clue": "heard"}, {"clue": "heard"}],
        )
        self.assertEqual(
            [entry.action_id for entry in timeline],
            [None, "listen", "knock", "promise"],
        )
        self.assertEqual(
            [entry.transition_id for entry in timeline],
            [None, "gate_listen", "echo_knock", "threshold_promise"],
        )
        self.assertEqual(states[1]["risk_level"], 1)
        self.assertEqual(states[1]["known_facts"], ["a witness is inside"])
        self.assertEqual(states[2]["relationships"]["mira"], 1)
        self.assertEqual(states[2]["flags"], {"clue": "heard"})
        self.assertEqual(states[3]["relationships"]["mira"], 2)
        self.assertEqual(states[3]["risk_level"], 0)
        self.assertNotEqual(states[1], states[-1])
        self.assertNotEqual(states[2], states[-1])

    def test_each_entry_exposes_all_required_consequence_fields(self) -> None:
        timeline = build_prefix_timeline(self._ledger(["listen", "knock", "promise"]), self.graph)
        required = {"scene_id", "beat_id", "risk_level", "relationships", "known_facts", "flags"}
        for entry in timeline:
            self.assertTrue(required.issubset(entry.to_dict()["state"]))

    def test_wrong_transition_id_fails_closed_even_with_valid_ledger_hash_chain(self) -> None:
        ledger = CreativeLedger()
        state = self.graph.initial_state()
        ledger.append("story_initialized", {"state": state.to_dict()}, "2030-01-01T00:00:00Z")
        next_state, action = self.graph.apply(state, "listen")
        ledger.append(
            "player_action",
            {
                "action": PlayerAction("listen", "choice", action.label).to_dict(),
                "transition_id": "forged_transition",
                "resulting_patch": {
                    **dict(action.patch),
                    "scene_id": next_state.scene_id,
                    "beat_id": next_state.beat_id,
                },
            },
            "2030-01-01T00:01:00Z",
        )
        with self.assertRaisesRegex(TimelineViolation, "transition_id disagrees"):
            build_prefix_timeline(ledger, self.graph)

    def test_graph_inconsistent_patch_fails_closed_even_when_event_chain_is_valid(self) -> None:
        ledger = CreativeLedger()
        state = self.graph.initial_state()
        ledger.append("story_initialized", {"state": state.to_dict()}, "2030-01-01T00:00:00Z")
        next_state, action = self.graph.apply(state, "listen")
        ledger.append(
            "player_action",
            {
                "action": PlayerAction("listen", "choice", action.label).to_dict(),
                "transition_id": action.transition_id,
                "resulting_patch": {
                    **dict(action.patch),
                    "risk_delta": 2,
                    "scene_id": next_state.scene_id,
                    "beat_id": next_state.beat_id,
                },
            },
            "2030-01-01T00:01:00Z",
        )
        with self.assertRaisesRegex(TimelineViolation, "resulting_patch disagrees"):
            build_prefix_timeline(ledger, self.graph)

    def test_unknown_action_fails_closed(self) -> None:
        ledger = CreativeLedger()
        state = self.graph.initial_state()
        ledger.append("story_initialized", {"state": state.to_dict()}, "2030-01-01T00:00:00Z")
        ledger.append(
            "player_action",
            {
                "action": PlayerAction("invent", "choice", "Invent an edge").to_dict(),
                "transition_id": "invented_edge",
                "resulting_patch": {"beat_id": "echo"},
            },
            "2030-01-01T00:01:00Z",
        )
        with self.assertRaisesRegex(TimelineViolation, "not legal"):
            build_prefix_timeline(ledger, self.graph)


if __name__ == "__main__":
    unittest.main()
