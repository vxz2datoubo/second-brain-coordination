from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from creative_runtime import (
    MultiScriptDirectorCompiler,
    ScriptPackageRegistry,
    canonical_json,
    compile_consequence_coverage,
    flagship_story_fixture,
    load_catalog,
    materialize_catalog,
)


class FlagshipStoryTests(unittest.TestCase):
    def test_fixture_is_registry_and_catalog_compatible(self) -> None:
        package, graph, bibles = flagship_story_fixture()
        registry = ScriptPackageRegistry()
        self.assertIs(registry.register(package), package)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = Path("catalog") / "flagship.json"
            materialize_catalog(root, path, (package,))
            compiler = MultiScriptDirectorCompiler(load_catalog(root, path))
            binding = compiler.select(script_id=package.script_id, script_revision=package.script_revision,
                                      package_hash=package.package_hash, style_profile_id="ink_animation")
            brief = compiler.compile(binding)
            self.assertEqual(brief.content_binding.package_hash, graph.package_hash)
            self.assertEqual(brief.style_profile.style_profile_id, "ink_animation")
        self.assertEqual(len(bibles.characters), 4)

    def test_fixture_is_fully_deterministic(self) -> None:
        first = flagship_story_fixture()
        second = flagship_story_fixture()
        self.assertEqual(tuple(canonical_json(item) for item in first), tuple(canonical_json(item) for item in second))

    def test_every_major_choice_has_two_meaningful_outcomes(self) -> None:
        _, graph, _ = flagship_story_fixture()
        for choice in graph.choices:
            self.assertEqual(len(choice.options), 2)
            self.assertNotEqual(choice.options[0].consequence.summary, choice.options[1].consequence.summary)
            self.assertTrue(all(option.consequence.reward_tags and option.consequence.cost_tags for option in choice.options))
        self.assertEqual(compile_consequence_coverage(graph).option_count, 24)

    def test_static_content_has_no_player_or_session_authority(self) -> None:
        package, graph, bibles = flagship_story_fixture()
        text = canonical_json((package, graph, bibles)).lower()
        for forbidden in ("campaign_id", "player_state", "session_path", "media_job", "provider_request"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
