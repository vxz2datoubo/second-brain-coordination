from __future__ import annotations

from dataclasses import replace
import unittest

from creative_runtime.continuity import compile_director_sequence, directed_beats_from_ledger, validate_sequence
from creative_runtime.contracts import StoryState
from creative_runtime.director import synthetic_asset_index
from creative_runtime.ledger import CreativeLedger
from creative_runtime.scene_graph import SceneGraph, SceneGraphViolation, synthetic_three_scene_manifest


def ledger_with_actions(*action_ids: str) -> tuple[CreativeLedger, SceneGraph]:
    graph = SceneGraph(synthetic_three_scene_manifest())
    ledger = CreativeLedger()
    state = graph.initial_state()
    ledger.append("story_initialized", {"state": state.to_dict()}, "2030-01-01T00:00:00Z")
    for index, action_id in enumerate(action_ids, start=1):
        state, action = graph.apply(state, action_id)
        ledger.append(
            "player_action",
            {
                "action": {"action_id": action_id, "kind": "choice", "text": action.label, "confidence": 1.0},
                "transition_id": action.transition_id,
                "resulting_patch": {**action.patch, "scene_id": state.scene_id, "beat_id": state.beat_id},
            },
            f"2030-01-01T00:0{index}:00Z",
        )
    return ledger, graph


class MultiBeatContinuityTests(unittest.TestCase):
    def test_graph_backed_sequence_has_ordered_packets_and_final_handoff(self) -> None:
        ledger, graph = ledger_with_actions("listen", "knock", "promise")
        sequence = compile_director_sequence(ledger, graph, duration_budget_seconds=40)
        self.assertTrue(sequence.can_generate)
        self.assertEqual(len(sequence.beats), 4)
        self.assertEqual(sequence.final_state_handoff["scene_id"], "interior_archive")
        self.assertEqual(sequence.final_state_handoff["beat_id"], "accord")
        packet = sequence.to_dict()
        self.assertEqual(packet["cross_cut_contract"][0]["transition_id"], "gate_listen")
        self.assertEqual(packet["diagnostics"], [])

    def test_causality_tampering_fails_closed_before_compilation(self) -> None:
        ledger, graph = ledger_with_actions("listen")
        ledger.events[1] = replace(ledger.events[1], payload={**ledger.events[1].payload, "transition_id": "not_the_manifest_transition"})
        # This direct fixture simulates a hostile-but-otherwise-shaped record; graph causality rejects it.
        with self.assertRaises(SceneGraphViolation):
            directed_beats_from_ledger(ledger, graph)

    def test_stable_diagnostics_locate_direction_knowledge_and_duration_failures(self) -> None:
        ledger, graph = ledger_with_actions("listen", "knock", "promise")
        sequence = compile_director_sequence(ledger, graph, duration_budget_seconds=90)
        altered_beats = list(sequence.beats)
        altered_beats[1] = replace(
            altered_beats[1],
            state=StoryState(
                scene_id=altered_beats[1].state.scene_id,
                beat_id=altered_beats[1].state.beat_id,
                relationships=altered_beats[1].state.relationships,
                known_facts=("unearned spoiler",),
                risk_level=altered_beats[1].state.risk_level,
                flags=altered_beats[1].state.flags,
            ),
            revealed_facts=(),
        )
        altered_packets = list(sequence.packets)
        changed_shot = replace(altered_packets[1].shots[0], axis="opposite-axis")
        altered_packets[1] = replace(altered_packets[1], shots=(changed_shot,))
        diagnostics = validate_sequence(tuple(altered_beats), tuple(altered_packets), synthetic_asset_index(), 10)
        codes = {item.code for item in diagnostics}
        self.assertTrue({"screen_direction_violation", "spatial_relation_violation", "knowledge_reveal_order_violation", "duration_budget_exceeded"} <= codes)
        self.assertTrue(all(item.locator for item in diagnostics))


if __name__ == "__main__":
    unittest.main()
