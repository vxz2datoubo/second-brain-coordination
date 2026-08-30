from __future__ import annotations

import unittest

from creative_runtime.continuity import GraphBeat, GraphTransition, StoryGraph
from creative_runtime.contracts import StoryState


class CreativeSceneQualifiedViewTests(unittest.TestCase):
    def test_same_beat_id_in_two_scenes_keeps_its_own_text_and_legal_actions(self) -> None:
        graph = StoryGraph(
            "SharedBeatNames/v1",
            (
                GraphBeat("platform", "arrival", "Platform arrival text."),
                GraphBeat("vault", "arrival", "Vault arrival text."),
            ),
            (
                GraphTransition("tr_platform", "platform", "arrival", "listen", "Listen at platform", {"scene_id": "vault", "beat_id": "arrival"}),
                GraphTransition("tr_vault", "vault", "arrival", "leave", "Leave vault", {"beat_id": "arrival"}),
            ),
        )
        platform = graph.cli_view_for(StoryState("platform", "arrival"))
        vault = graph.cli_view_for(StoryState("vault", "arrival"))
        self.assertEqual(platform["text"], "Platform arrival text.")
        self.assertEqual(vault["text"], "Vault arrival text.")
        self.assertEqual(set(platform["options"]), {"listen"})
        self.assertEqual(set(vault["options"]), {"leave"})


if __name__ == "__main__":
    unittest.main()
