from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from creative_runtime import (
    DirectorBriefV2Violation,
    DirectorScriptSelection,
    MultiScriptDirectorCompiler,
    approved_synthetic_script_packages,
    canonical_json,
    load_catalog,
    materialize_catalog,
)


class DirectorBriefV2Tests(unittest.TestCase):
    relative_path = Path("catalog") / "scripts.v1.json"

    def assert_violation(self, code: str, operation) -> None:
        with self.assertRaises(DirectorBriefV2Violation) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def compiler(self, root: Path, packages=None) -> MultiScriptDirectorCompiler:
        values = approved_synthetic_script_packages() if packages is None else packages
        materialize_catalog(root, self.relative_path, values)
        return MultiScriptDirectorCompiler(load_catalog(root, self.relative_path))

    def binding(self, compiler: MultiScriptDirectorCompiler, index: int = 0, style: str = "cinematic_live_action"):
        entry = compiler.list_scripts()[index]
        return compiler.select(
            script_id=entry.script_id,
            script_revision=entry.script_revision,
            package_hash=entry.package_hash,
            style_profile_id=style,
        )

    def test_compile_is_deterministic_and_contains_exact_validated_content(self) -> None:
        with TemporaryDirectory() as directory:
            compiler = self.compiler(Path(directory))
            binding = self.binding(compiler)
            first = compiler.compile(binding)
            second = compiler.compile(binding)
            self.assertEqual(first, second)
            self.assertEqual(canonical_json(first), canonical_json(second))
            self.assertEqual(first.content_binding, binding)
            self.assertEqual(first.style_profile.style_profile_id, binding.style_profile_id)
            self.assertEqual(first.content_rating, "non_explicit")
            self.assertTrue(first.character_bibles)
            self.assertTrue(first.scene_bibles)
            self.assertTrue(first.story_beats)
            self.assertTrue(first.asset_manifest)
            self.assertIs(compiler.inspect(first), first)

    def test_compiled_content_is_deeply_immutable(self) -> None:
        with TemporaryDirectory() as directory:
            compiler = self.compiler(Path(directory))
            brief = compiler.compile(self.binding(compiler))
            with self.assertRaises(FrozenInstanceError):
                brief.compile_hash = "0" * 64
            with self.assertRaises(TypeError):
                brief.world_bible["title"] = "forged"
            with self.assertRaises(TypeError):
                brief.character_bibles[0]["goal"] = "forged"

    def test_multi_script_and_style_switch_is_pure_and_deterministic(self) -> None:
        with TemporaryDirectory() as directory:
            compiler = self.compiler(Path(directory))
            first_binding = self.binding(compiler, 0, "cinematic_live_action")
            target_binding = self.binding(compiler, 1, "ink_animation")
            current = compiler.compile(first_binding)
            current_json = canonical_json(current)
            switched_once = compiler.switch(current, target_binding)
            switched_twice = compiler.switch(current, target_binding)
            self.assertEqual(switched_once, switched_twice)
            self.assertNotEqual(switched_once.compile_hash, current.compile_hash)
            self.assertEqual(switched_once.content_binding, target_binding)
            self.assertEqual(switched_once.style_profile.style_profile_id, "ink_animation")
            self.assertEqual(canonical_json(current), current_json)
            self.assertIs(compiler.inspect(switched_once), switched_once)

    def test_switch_rejects_tampered_current_before_compiling_target(self) -> None:
        with TemporaryDirectory() as directory:
            compiler = self.compiler(Path(directory))
            current = compiler.compile(self.binding(compiler, 0))
            target = self.binding(compiler, 1)
            tampered = replace(current, compile_hash="0" * 64)
            self.assert_violation("DIRECTOR_BRIEF_HASH_MISMATCH", lambda: compiler.switch(tampered, target))

    def test_recomputed_hash_cannot_hide_compiled_content_substitution(self) -> None:
        with TemporaryDirectory() as directory:
            compiler = self.compiler(Path(directory))
            brief = compiler.compile(self.binding(compiler))
            forged_world = {**brief.world_bible, "premise": "forged directing premise"}
            forged = replace(brief, world_bible=forged_world, compile_hash="")
            material = forged.to_dict()
            material.pop("brief_id")
            material.pop("compile_hash")
            forged_hash = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
            forged = replace(forged, brief_id=f"briefv2_{forged_hash[:24]}", compile_hash=forged_hash)
            self.assert_violation("DIRECTOR_BRIEF_SUBSTITUTION", lambda: compiler.inspect(forged))

    def test_cross_catalog_and_binding_substitution_fail_closed(self) -> None:
        packages = approved_synthetic_script_packages()
        with TemporaryDirectory() as full_directory, TemporaryDirectory() as partial_directory:
            full = self.compiler(Path(full_directory), packages)
            partial = self.compiler(Path(partial_directory), (packages[0],))
            full_binding = self.binding(full, 0)
            self.assert_violation(
                "DIRECTOR_CATALOG_SUBSTITUTION",
                lambda: partial.compile(full_binding),
            )
            forged = replace(full_binding, source_provenance_hash="0" * 64)
            self.assert_violation(
                "DIRECTOR_PROVENANCE_SUBSTITUTION",
                lambda: full.compile(forged),
            )

    def test_wrong_identity_revision_hash_and_style_fail_closed(self) -> None:
        with TemporaryDirectory() as directory:
            compiler = self.compiler(Path(directory))
            entry = compiler.list_scripts()[0]
            cases = (
                ({"script_id": "unknown"}, "SCRIPT_UNKNOWN"),
                ({"script_revision": "9.9.9"}, "SCRIPT_REVISION_UNKNOWN"),
                ({"package_hash": "0" * 64}, "PACKAGE_HASH_MISMATCH"),
                ({"style_profile_id": "unknown"}, "STYLE_PROFILE_UNKNOWN"),
            )
            base = {
                "script_id": entry.script_id,
                "script_revision": entry.script_revision,
                "package_hash": entry.package_hash,
                "style_profile_id": "japanese_animation",
            }
            for change, code in cases:
                with self.subTest(code=code):
                    self.assert_violation(code, lambda change=change: compiler.select(**{**base, **change}))

    def test_compile_selection_revalidates_manual_selection(self) -> None:
        with TemporaryDirectory() as directory:
            compiler = self.compiler(Path(directory))
            entry = compiler.list_scripts()[0]
            manual = DirectorScriptSelection(
                entry.script_id,
                entry.script_revision,
                entry.package_hash,
                "stylized_3d",
            )
            brief = compiler.compile_selection(manual)
            self.assertEqual(brief.style_profile.style_profile_id, "stylized_3d")
            forged = replace(manual, package_hash="0" * 64)
            self.assert_violation("PACKAGE_HASH_MISMATCH", lambda: compiler.compile_selection(forged))

    def test_no_runtime_job_or_session_authority_is_created(self) -> None:
        with TemporaryDirectory() as directory:
            compiler = self.compiler(Path(directory))
            compiler.compile(self.binding(compiler))
            for name in (
                "campaigns",
                "sessions",
                "session_ledger",
                "save_slots",
                "director_jobs",
                "media_jobs",
                "queue",
                "scheduler",
            ):
                self.assertFalse(hasattr(compiler, name))

    def test_untyped_catalog_binding_brief_and_selection_fail_closed(self) -> None:
        self.assert_violation("DIRECTOR_CATALOG_INVALID", lambda: MultiScriptDirectorCompiler(object()))
        with TemporaryDirectory() as directory:
            compiler = self.compiler(Path(directory))
            self.assert_violation("DIRECTOR_BINDING_INVALID", lambda: compiler.compile(object()))
            self.assert_violation("DIRECTOR_BRIEF_INVALID", lambda: compiler.inspect(object()))
            self.assert_violation("DIRECTOR_SELECTION_INVALID", lambda: compiler.compile_selection(object()))


if __name__ == "__main__":
    unittest.main()
