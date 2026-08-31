from __future__ import annotations

import unittest

from creative_runtime.ledger import CreativeLedger
from creative_runtime.review import build_review_packet
from creative_runtime.scene_graph import SceneGraph, synthetic_three_scene_manifest


def scripted_ledger() -> tuple[CreativeLedger, SceneGraph]:
    graph = SceneGraph(synthetic_three_scene_manifest())
    ledger = CreativeLedger()
    state = graph.initial_state()
    ledger.append("story_initialized", {"state": state.to_dict()}, "2030-01-01T00:00:00Z")
    for index, action_id in enumerate(("listen", "knock", "promise", "depart"), start=1):
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


class OfflineReviewPacketTests(unittest.TestCase):
    def test_review_packet_is_reproducible_and_binds_required_evidence(self) -> None:
        ledger, graph = scripted_ledger()
        first = build_review_packet(ledger, graph, duration_budget_seconds=50)
        second = build_review_packet(ledger, graph, duration_budget_seconds=50)
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], "OfflineInteractiveFilmReviewPacket/v1")
        self.assertEqual(first["event_count"], 5)
        self.assertEqual(first["transcript"][-1]["scene_id"], "dawn_courtyard")
        self.assertFalse(first["generation_called"])
        self.assertFalse(first["canonical_knowledge_written"])
        self.assertTrue(first["director"]["can_generate"])
        # Golden deterministic snapshot for the all-synthetic scripted route.
        self.assertEqual(first["event_digest"], "ba57ec9952cd3979a3f770b7ee9957dbe6f56122dbf0eaf126e81f964547c08d")
        self.assertEqual(first["review_digest"], "00fdf4782ce2186dd0dd1a91f236b9293fbd106c8efacda84784bec81eb4e4df")

    def test_manifest_mismatch_cannot_be_packaged_as_review_evidence(self) -> None:
        ledger, _ = scripted_ledger()
        mismatching_manifest = synthetic_three_scene_manifest()
        mismatching_manifest["entry"] = {"scene_id": "dawn_courtyard", "beat_id": "return"}
        mismatching = SceneGraph(mismatching_manifest)
        with self.assertRaises(ValueError):
            build_review_packet(ledger, mismatching)


if __name__ == "__main__":
    unittest.main()
