from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import unittest

from creative_runtime import StoryBibleViolation, flagship_story_fixture, validate_story_bibles


class StoryBibleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.package, self.graph, self.bibles = flagship_story_fixture()

    def assert_violation(self, code, bundle=None, package=None) -> None:
        with self.assertRaises(StoryBibleViolation) as caught:
            validate_story_bibles(bundle or self.bibles, self.graph, package or self.package)
        self.assertEqual(caught.exception.code, code)

    def test_bibles_cover_all_graph_scenes_and_assets(self) -> None:
        self.assertEqual({item.scene_id for item in self.bibles.scenes}, {item.scene_id for item in self.graph.choices})
        self.assertTrue(all(item.age >= 18 for item in self.bibles.characters))
        self.assertEqual(self.bibles.bible_hash, flagship_story_fixture()[2].bible_hash)

    def test_contract_is_immutable(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            self.bibles.characters[0].age = 10
        with self.assertRaises(TypeError):
            self.package.world_bible["title"] = "forged"

    def test_non_adult_and_unknown_arc_choice_fail_closed(self) -> None:
        character = replace(self.bibles.characters[0], age=17)
        self.assert_violation("CHARACTER_NOT_ADULT", replace(self.bibles, characters=(character, *self.bibles.characters[1:])))
        character = replace(self.bibles.characters[0], arc_choice_ids=("missing",))
        self.assert_violation("CHARACTER_ARC_REFERENCE", replace(self.bibles, characters=(character, *self.bibles.characters[1:])))

    def test_wrong_asset_role_and_scene_choice_fail_closed(self) -> None:
        character = replace(self.bibles.characters[0], appearance_anchor_asset_id=self.bibles.scenes[0].scene_anchor_asset_id)
        self.assert_violation("CHARACTER_ASSET_REFERENCE", replace(self.bibles, characters=(character, *self.bibles.characters[1:])))
        scene = replace(self.bibles.scenes[0], allowed_choice_ids=("c12_final_broadcast",))
        self.assert_violation("SCENE_CHOICE_REFERENCE", replace(self.bibles, scenes=(scene, *self.bibles.scenes[1:])))

    def test_cross_script_binding_fails_closed(self) -> None:
        self.assert_violation("CROSS_SCRIPT_IDENTITY", replace(self.bibles, package_hash="0" * 64))


if __name__ == "__main__":
    unittest.main()
