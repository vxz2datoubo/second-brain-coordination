"""Unit tests for the director-matrix story-state corpus (WB-S2)."""

from __future__ import annotations

import unittest

import sys
from pathlib import Path

# Resolve imports without relying on discover's top-level directory, so the
# probe runs the same way from any discover depth.
_REPO_ROOT = Path(__file__).resolve().parents[3]
for _candidate in (str(_REPO_ROOT), str(_REPO_ROOT / "tools" / "workbuddy")):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from creative_runtime.contracts import StoryState  # noqa: E402
from creative_runtime.director import synthetic_asset_index  # noqa: E402
from director_matrix import states  # noqa: E402


class CorpusTest(unittest.TestCase):
    def test_full_asset_index_matches_checkpoint(self) -> None:
        # The probe must reuse the checkpoint's registered index, not a fork of it.
        self.assertEqual(states.full_asset_index(), synthetic_asset_index())

    def test_full_asset_index_is_a_copy(self) -> None:
        assets = states.full_asset_index()
        assets["art_character_mira"]["adult"] = False
        self.assertTrue(synthetic_asset_index()["art_character_mira"]["adult"])

    def test_missing_variants_each_remove_exactly_one(self) -> None:
        variants = states.missing_asset_variants()
        self.assertEqual(len(variants), len(states.REFERENCE_ARTIFACT_IDS))
        full = set(states.REFERENCE_ARTIFACT_IDS)
        for label, assets in variants:
            missing = full - set(assets)
            self.assertEqual(len(missing), 1, label)
            self.assertTrue(label.endswith(next(iter(missing))))

    def test_reachable_states_is_deterministic(self) -> None:
        self.assertEqual(states.reachable_states(), states.reachable_states())

    def test_reachable_states_count(self) -> None:
        # scenes x beats x facts x risk = 2 x 2 x 2 x 2
        self.assertEqual(len(states.reachable_states()), 16)

    def test_every_corpus_member_is_a_storystate(self) -> None:
        for state in states.reachable_states():
            self.assertIsInstance(state, StoryState)

    def test_corpus_spans_registered_vocabulary(self) -> None:
        seen_scenes = {state.scene_id for state in states.reachable_states()}
        seen_beats = {state.beat_id for state in states.reachable_states()}
        self.assertEqual(seen_scenes, set(states.SCENES))
        self.assertEqual(seen_beats, set(states.BEATS))

    def test_state_key_is_stable_and_unique(self) -> None:
        keys = [states.state_key(state) for state in states.reachable_states()]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(keys, [states.state_key(s) for s in states.reachable_states()])


if __name__ == "__main__":
    unittest.main()
